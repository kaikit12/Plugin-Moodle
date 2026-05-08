from fastapi import APIRouter, HTTPException, Header, Depends, Form
from typing import Optional, List
from pydantic import BaseModel
import datetime
from datetime import datetime as dt, timedelta
import logging
from app.containers.container import get_container
from app.utils.auth import verify_token
from app.schemas.schemas import SubmissionSchema, DashboardStats, SubmissionDetailSchema, SubmissionPagination
from app.api.dependencies import get_admin_user

logger = logging.getLogger("dsa.admin")

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/submissions", response_model=SubmissionPagination)
async def get_all_submissions(
    page: int = 1,
    page_size: int = 50,
    student_id: Optional[str] = None,
    topic: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_admin_user)
):
    """Get all submissions for lecturers with server-side filtering."""
    try:
        container = get_container()
        repo = container.get_repository()
        result = repo.get_all_submissions(
            page=page,
            page_size=page_size,
            student_id=student_id,
            topic=topic,
            status=status
        )

        logger.info(f"Admin {user['username']} fetched {len(result['submissions'])} submissions (page {page})")
        return result
    except Exception as e:
        logger.error(f"Get all submissions failed: {e}")
        return {
            "submissions": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "error": str(e)
        }

@router.delete("/submissions/all")
async def delete_all_submissions(user=Depends(get_admin_user)):
    """Delete all submissions from the database."""
    container = get_container()
    repo = container.get_repository()
    
    with repo.get_session() as session:
        from app.core.database import GradingHistory, RunResult
        # Also clean up RunResult tables which reference GradingHistory
        session.query(RunResult).delete()
        count = session.query(GradingHistory).delete()
        session.commit()
        
    logger.warning(f"Admin {user['username']} deleted ALL {count} submissions")
    return {"message": f"Successfully deleted {count} submissions"}

@router.delete("/submission/{submission_id}")
async def delete_submission(submission_id: int, user=Depends(get_admin_user)):
    """Delete a submission."""
    container = get_container()
    repo = container.get_repository()
    success = repo.delete_submission(submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission deleted successfully"}

@router.get("/submission/{submission_id}")
async def get_submission_detail(submission_id: int, user=Depends(get_admin_user)):
    """Get detailed view of a submission including test runs."""
    container = get_container()
    repo = container.get_repository()

    submission = repo.get_result_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    runs = repo.get_runs_by_submission(submission_id)

    return {
        "submission": submission,
        "runs": runs,
    }

class ReviewRequest(BaseModel):
    new_score: float
    reason: str
    feedback: Optional[str] = ""

@router.post("/submission/{submission_id}/review")
async def override_score(submission_id: int, request: ReviewRequest, user=Depends(get_admin_user)):
    """Instructor override score."""
    container = get_container()
    repo = container.get_repository()
    
    success = repo.update_submission_score(
        submission_id=submission_id,
        new_score=request.new_score,
        reviewer_id=user.get("username", "admin"),
        reason=request.reason,
        feedback=request.feedback
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Unable to update score")

    return {"message": "Score override saved successfully"}

@router.get("/stats", response_model=DashboardStats)
async def get_admin_stats(user=Depends(get_admin_user)):
    """Get detailed stats for lecturers with optimized query."""
    container = get_container()
    repo = container.get_repository()

    try:
        stats = repo.get_summary_stats()
        return stats
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        return {
            "total_submissions": 0,
            "error": str(e)
        }


def _parse_date(date_str: str) -> dt:
    """Parse date string to datetime."""
    try:
        if isinstance(date_str, dt):
            return date_str
        return dt.fromisoformat(date_str.replace('Z', '+00:00').split('+')[0])
    except:
        return dt.now()

@router.get("/topics")
async def get_all_topics(user=Depends(get_admin_user)):
    """Get all topics for testcase management."""
    from app.services.testcase_loader import get_all_topics
    return get_all_topics()

@router.get("/testcases/{topic}")
async def get_topic_testcases(topic: str, user=Depends(get_admin_user)):
    """Get testcases for a specific topic."""
    from app.services.testcase_loader import get_test_cases
    return get_test_cases(topic)

@router.post("/testcases/{topic}")
async def create_testcase(
    topic: str, 
    test_id: str = Form(...), 
    input_str: str = Form(...), 
    expected: str = Form(...),
    user=Depends(get_admin_user)
):
    """Add or update a testcase."""
    from app.services.testcase_loader import save_test_case
    success = save_test_case(topic, test_id, input_str, expected)
    if not success:
        raise HTTPException(status_code=500, detail="Unable to save testcase")
    return {"message": "Testcase saved successfully"}

@router.get("/me")
async def get_current_admin(user=Depends(get_admin_user)):
    """Get current admin context."""
    return {"username": user.get("username", "Admin"), "role": user.get("role", "LECTURER")}

@router.post("/regrade")
async def regrade_all_submissions(user=Depends(get_admin_user)):
    """Regrade all submissions in the system."""
    from app.services.regrade_service import get_regrade_service

    regrade_service = get_regrade_service()
    result = await regrade_service.regrade_all(
        reviewer_id=user.get("username", "admin")
    )

    if result.get("success"):
        return {
            "message": "Started regrading all submissions",
            "job_id": result.get("job_id"),
            "total": result.get("total_submissions"),
            "regraded": result.get("regraded_count"),
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@router.post("/regrade/batch/{assignment_code}")
async def regrade_by_assignment(assignment_code: str, user=Depends(get_admin_user)):
    """Regrade all submissions for a specific assignment."""
    from app.services.regrade_service import get_regrade_service

    regrade_service = get_regrade_service()
    result = await regrade_service.regrade_by_assignment(
        assignment_code=assignment_code,
        reviewer_id=user.get("username", "admin")
    )

    if result.get("success"):
        return {
            "message": f"Regraded {result.get('regraded_count')}/{result.get('total_submissions')} submissions",
            "job_id": result.get("job_id"),
            "score_changes": result.get("score_changes", []),
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@router.get("/regrade/status/{job_id}")
async def get_regrade_status(job_id: str, user=Depends(get_admin_user)):
    """Get status of a regrade job."""
    from app.services.regrade_service import get_regrade_service

    regrade_service = get_regrade_service()
    return await regrade_service.get_regrade_status(job_id)

@router.delete("/testcases/{topic}/{test_id}")
async def remove_testcase(topic: str, test_id: str, user=Depends(get_admin_user)):
    """Delete a testcase."""
    from app.services.testcase_loader import delete_test_case
    success = delete_test_case(topic, test_id)
    if not success:
        raise HTTPException(status_code=500, detail="Unable to delete testcase")
    return {"message": "Testcase deleted"}

@router.get("/student/{student_id}/history")
async def get_student_history(student_id: str, user=Depends(get_admin_user)):
    """Get all submissions for a specific student."""
    container = get_container()
    repo = container.get_repository()
    return repo.get_student_scores(student_id)

@router.get("/export/grades")
async def export_grades(topic: Optional[str] = None, user=Depends(get_admin_user)):
    """Export summary of grades to CSV format."""
    from datetime import datetime as dt
    import csv
    import io
    from fastapi.responses import StreamingResponse

    container = get_container()
    repo = container.get_repository()
    data = repo.get_all_submissions(page_size=1000)
    submissions = data.get("submissions", [])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Full Name", "Topic", "Original Score", "Final Score", "Status", "Submitted At"])

    for s in submissions:
        if topic and s["topic"] != topic:
            continue
        writer.writerow([
            s.get("student_id", ""),
            s.get("student_name", ""),
            s.get("topic", ""),
            s.get("total_score", 0),
            s.get("final_score") if s.get("final_score") is not None else s.get("total_score", 0),
            s.get("status", ""),
            s.get("submitted_at", "")
        ])

    output.seek(0)
    filename = f"dsa_grades_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue().encode('utf-8-sig')]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )

@router.post("/seed/demo-data")
async def seed_demo_data(user=Depends(get_admin_user)):
    """Seed demo data for testing (lecturer only)."""
    from app.utils.seeder import seed_demo_data

    if user["role"] != "LECTURER":
        raise HTTPException(status_code=403, detail="Only lecturers can seed data")

    result = seed_demo_data()

    return {
        "success": True,
        "message": f"Seeded {result['submissions_created']} demo submissions",
        "users": result["users_created"],
        "submissions": result["submissions_created"]
    }

@router.post("/submission/{submission_id}/regrade")
async def regrade_single_submission(submission_id: int, user=Depends(get_admin_user)):
    """Trigger a regrade for a specific submission."""
    from app.services.regrade_service import get_regrade_service

    regrade_service = get_regrade_service()
    result = await regrade_service.regrade_single(
        submission_id=submission_id,
        reviewer_id=user.get("username", "admin")
    )

    if result.get("success"):
        return {
            "message": "Submission regraded successfully",
            "old_score": result.get("old_score"),
            "new_score": result.get("new_score"),
            "score_change": result.get("score_change"),
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Unable to regrade"))

@router.get("/submissions/search")
async def search_submissions(
    query: Optional[str] = None, 
    search: Optional[str] = None,
    topic: Optional[str] = None, 
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    user=Depends(get_admin_user)
):
    """Deep search for submissions with filters using optimized repo method."""
    search_term = query or search
    
    container = get_container()
    repo = container.get_repository()
    
    # We use the same optimized method for search
    return repo.get_all_submissions(
        page=page,
        page_size=page_size,
        student_id=search_term, # Try searching by ID directly if it matches exactly
        topic=topic,
        status=status
    )
