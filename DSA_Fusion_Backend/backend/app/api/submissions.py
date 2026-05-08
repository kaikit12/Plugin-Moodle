import asyncio
import logging
import uuid
from typing import List, Optional, Tuple

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.containers.container import get_container
from app.services.grading_service import GradingService
from app.services.testcase_loader import get_all_topics
from app.utils.archive_handler import extract_archive, is_archive_file

# Initialize Logger
logger = logging.getLogger("dsa.api.submissions")
router = APIRouter(prefix="/submissions", tags=["Submissions"])

# ---------------------------------------------------------------------------
#  Topic Inference & Response Mapping Helpers
# ---------------------------------------------------------------------------

def _infer_topic(name: str, code: str, available_topics: List[str]) -> str:
    """
    Infer the Data Structure / Algorithm topic from the filename or code content.
    Supports English and Vietnamese keywords.
    """
    # 1. Direct match from filename
    name_lower = name.lower()
    for t in available_topics:
        if t.lower() in name_lower:
            return t

    # 2. Heuristic match from code content keywords
    code_lower = code.lower()
    keyword_map = {
        "search": ["search", "tìm kiếm", "binary_search"],
        "sort": ["sort", "sắp xếp", "bubble", "quick", "merge"],
        "linkedlist": ["linkedlist", "danh sách liên kết", "node", "prev"],
        "queue": ["queue", "hàng đợi"],
        "stack": ["stack", "ngăn xếp"],
        "tree": ["tree", "cây", "bst"],
        "graph": ["graph", "đồ thị", "bfs", "dfs"],
        "greedy": ["greedy", "tham lam"],
        "knapsack": ["dp", "dynamic programming", "quy hoạch động"],
        "recursion": ["recursion", "đệ quy"],
        "factorial": ["factorial", "giai thừa"],
        "fibonacci": ["fibonacci"],
    }

    for topic, keywords in keyword_map.items():
        if any(k in code_lower for k in keywords):
            return topic

    return ""


def _map_to_frontend_format(results: dict, student_id: str) -> dict:
    """
    Map GradingService business results to the specific JSON format 
    expected by the Legacy Next.js frontend.
    """
    grading_results = results.get("results", [])
    summary = results.get("summary", {})
    
    file_evaluations = []
    total_time_ms = 0.0
    
    for r in grading_results:
        # Build individual file feedback based on dynamic test results or AST analysis
        feedbacks = []
        test_results = r.get("test_results", [])
        
        if test_results:
            for tr in test_results:
                feedbacks.append({
                    "testcase": tr.get("testcase", "Test Case"),
                    "status": "AC" if tr.get("passed") else "WA",
                    "message": tr.get("message", "N/A"),
                    "hint": tr.get("hint"),
                    "points": tr.get("points", 0)
                })
        else:
            # Fallback to static analysis summary if no dynamic tests were executed
            feedbacks.append({
                "testcase": "Phân tích cấu trúc (AST)",
                "status": r.get("status", "AC"),
                "message": r.get("reasoning", "Mã nguồn hợp lệ"),
                "hint": None,
                "points": r.get("total_score", 0)
            })

        # Calculate time in milliseconds
        time_ms = float(r.get("time_used", 0) or 0) * 1000
        total_time_ms += time_ms

        file_evaluations.append({
            "file_name": r.get("filename", "submission.py"),
            "score": r.get("total_score", 0.0),
            "status": r.get("status", "AC"),
            "time_ms": time_ms,
            "feedbacks": feedbacks,
            "ai_advice": r.get("improvement") or r.get("reasoning") or "",
            "optimized_code": r.get("optimized_code"),
            "complexity_curve": r.get("complexity_curve", [])
        })

    # Return structured response matching Frontend's ResultRecord type
    avg_score = summary.get("avg_score", 0.0) if summary else 0.0
    if avg_score is None:
        avg_score = 0.0

    return {
        "submission_id": str(uuid.uuid4()),
        "student_id": student_id,
        "student_name": (grading_results[0].get("student_name") if grading_results else "") or "Sinh viên",
        "total_score": avg_score,
        "total_time_ms": total_time_ms,
        "status": "AC" if avg_score >= 5 else "WA",
        "file_evaluations": file_evaluations,
        "overall_ai_summary": results.get("ai_summary", "Hệ thống đã hoàn tất chấm điểm bài làm của bạn.") or "Hệ thống đã hoàn tất chấm điểm bài làm của bạn."
    }


# ---------------------------------------------------------------------------
#  Primary Submission Endpoint
# ---------------------------------------------------------------------------

@router.post("/", summary="Submit assignment for grading")
async def submit_multi_file(
    files: List[UploadFile] = File(...),
    student_id: str = Form(...),
    student_name: str = Form("Sinh viên")
):
    """
    Submission entry point for students. 
    Handles file upload, archive extraction, topic auto-detection, 
    and orchestrates the grading pipeline via GradingService.
    """
    # Initialize Core Service via Container
    container = get_container()
    grading_service: GradingService = container.get_grading_service()
    
    py_files_to_grade: List[Tuple[str, str]] = []

    # Step 1: Extract and Sanitize Source Files
    try:
        for uploaded_file in files:
            content = await uploaded_file.read()
            name = uploaded_file.filename or "unknown.py"
            
            if is_archive_file(name):
                # Handle ZIP/RAR archives
                extracted = extract_archive(content, name)
                py_files_to_grade.extend(extracted)
            elif name.lower().endswith(".py"):
                # Handle direct Python files with encoding fallback
                code = None
                for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                    try:
                        code = content.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                
                if code:
                    py_files_to_grade.append((name, code))
    except Exception as exc:
        logger.error(f"Failed to process uploaded files: {exc}")
        raise HTTPException(status_code=400, detail=f"Lỗi xử lý tệp: {str(exc)}")

    if not py_files_to_grade:
        raise HTTPException(status_code=400, detail="Không tìm thấy mã nguồn Python (.py) hợp lệ.")

    # Step 2: Topic Inference
    # Detect the most appropriate topic for EACH file individually
    available_topics = get_all_topics()
    inferred_topics = [_infer_topic(fn, fc, available_topics) for fn, fc in py_files_to_grade]

    # Use the first valid topic detected as the batch topic
    batch_topic = next((t for t in inferred_topics if t), "")
    logger.info("Batch submission detected for student %s | Topic: %s | Files: %d", 
                student_id, batch_topic or "General", len(py_files_to_grade))

    # Step 3: Execute Grading Pipeline
    try:
        # The orchestrator handles AST, Dynamic Tests, AI, Plagiarism, and DB Persistence
        grading_results = await grading_service.grade_submission(
            files=py_files_to_grade,
            topic=batch_topic,
            student_name=student_name,
            student_id=student_id,
            assignment_code="WEB_PORTAL"
        )
        
        # Step 4: Format and Return results to Frontend
        return _map_to_frontend_format(grading_results, student_id)

    except Exception as exc:
        logger.error(f"Grading orchestration service failure: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi hệ thống trong quá trình chấm điểm chuyên sâu.")
