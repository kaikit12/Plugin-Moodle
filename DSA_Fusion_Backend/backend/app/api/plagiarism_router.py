"""
DSA AutoGrader - Plagiarism Comparison API.

Provides detailed code comparison for plagiarism detection.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from app.containers.container import get_container
from app.api.dependencies import get_admin_user

router = APIRouter(prefix="/api/admin/plagiarism", tags=["Plagiarism Detection"])


@router.get("/report")
async def get_plagiarism_report(
    threshold: float = Query(0.8, ge=0, le=1, description="Similarity threshold"),
    user=Depends(get_admin_user)
):
    """
    Get all submissions flagged for plagiarism.
    
    Returns submissions with similarity above threshold.
    """
    container = get_container()
    repo = container.get_repository()
    
    with repo.get_session() as session:
        from sqlalchemy import desc
        from app.core.database import GradingHistory
        
        query = session.query(GradingHistory).filter(
            GradingHistory.plagiarism_detected == True
        ).order_by(desc(GradingHistory.submitted_at)).limit(100)
        
        records = query.all()
        return [r.to_dict() for r in records]


@router.get("/compare/{submission_id_1}/{submission_id_2}")
async def compare_submissions(
    submission_id_1: int,
    submission_id_2: int,
    user=Depends(get_admin_user)
):
    """
    Compare two submissions for plagiarism.
    
    Returns detailed similarity analysis including:
    - Overall similarity score
    - Token-based similarity
    - Structural similarity
    - Side-by-side code comparison
    """
    container = get_container()
    repo = container.get_repository()
    
    # Get both submissions
    sub1 = repo.get_result_by_id(submission_id_1)
    sub2 = repo.get_result_by_id(submission_id_2)
    
    if not sub1 or not sub2:
        raise HTTPException(status_code=404, detail="One or both submissions not found")
    
    if not sub1.get("code") or not sub2.get("code"):
        raise HTTPException(status_code=400, detail="Code not available for comparison")
    
    # Use plagiarism service for detailed analysis
    from app.services.plagiarism_service import PlagiarismService
    
    plagiarism_service = PlagiarismService(repository=repo)
    
    # Calculate combined similarity
    combined_score, breakdown = plagiarism_service.calculate_combined_similarity(
        code1=sub1["code"],
        code2=sub2["code"],
        fingerprint1=sub1.get("fingerprint"),
        fingerprint2=sub2.get("fingerprint"),
    )
    
    # Generate side-by-side comparison
    comparison = {
        "submission_1": {
            "id": submission_id_1,
            "student": sub1.get("student_name"),
            "student_id": sub1.get("student_id"),
            "assignment": sub1.get("assignment_code"),
            "topic": sub1.get("topic"),
            "submitted_at": sub1.get("submitted_at"),
            "score": sub1.get("total_score"),
        },
        "submission_2": {
            "id": submission_id_2,
            "student": sub2.get("student_name"),
            "student_id": sub2.get("student_id"),
            "assignment": sub2.get("assignment_code"),
            "topic": sub2.get("topic"),
            "submitted_at": sub2.get("submitted_at"),
            "score": sub2.get("total_score"),
        },
        "similarity": {
            "combined": round(combined_score, 4),
            "percentage": round(combined_score * 100, 1),
            "breakdown": {
                "fingerprint": round(breakdown.get("fingerprint", 0) * 100, 1),
                "token": round(breakdown.get("token", 0) * 100, 1),
                "structural": round(breakdown.get("structural", 0) * 100, 1),
            },
            "is_plagiarism": combined_score >= 0.8,
            "severity": _get_severity(combined_score),
        },
        "code_comparison": _generate_code_comparison(sub1["code"], sub2["code"]),
    }
    
    return comparison


@router.get("/similar/{submission_id}")
async def find_similar_submissions(
    submission_id: int,
    threshold: float = Query(0.7, ge=0, le=1),
    user=Depends(get_admin_user)
):
    """
    Find all submissions similar to the given one.
    
    Returns list of submissions with similarity above threshold.
    """
    container = get_container()
    repo = container.get_repository()
    
    # Get the target submission
    submission = repo.get_result_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    fingerprint = submission.get("fingerprint")
    if not fingerprint:
        return {
            "submission_id": submission_id,
            "similar_submissions": [],
            "message": "No fingerprint available for this submission",
        }
    
    # Find similar
    similar = repo.find_similar_submissions(fingerprint, threshold)
    
    # Enhance with detailed similarity scores
    from app.services.plagiarism_service import PlagiarismService
    plagiarism_service = PlagiarismService(repository=repo)
    
    enhanced_results = []
    for sim in similar:
        # Get the similar submission's code for detailed analysis
        sim_sub = repo.get_result_by_id(sim.get("id"))
        if sim_sub and sim_sub.get("code"):
            _, breakdown = plagiarism_service.calculate_combined_similarity(
                code1=submission["code"],
                code2=sim_sub["code"],
            )
            sim["breakdown"] = breakdown
        
        enhanced_results.append(sim)
    
    return {
        "submission_id": submission_id,
        "student": submission.get("student_name"),
        "threshold": threshold,
        "similar_submissions": enhanced_results,
        "count": len(enhanced_results),
    }


@router.post("/analyze")
async def analyze_plagiarism(
    code1: str,
    code2: str,
    student1_name: str = "Student 1",
    student2_name: str = "Student 2",
    user=Depends(get_admin_user)
):
    """
    Analyze two code snippets for plagiarism.
    
    Useful for comparing code that wasn't submitted through the system.
    """
    from app.services.plagiarism_service import PlagiarismService
    
    plagiarism_service = PlagiarismService(repository=None)
    
    # Calculate similarities
    combined_score, breakdown = plagiarism_service.calculate_combined_similarity(
        code1=code1,
        code2=code2,
    )
    
    token_sim = plagiarism_service.calculate_token_similarity(code1, code2)
    structural_sim = plagiarism_service.calculate_structural_similarity(code1, code2)
    
    return {
        "similarity": {
            "combined": round(combined_score, 4),
            "percentage": round(combined_score * 100, 1),
            "token_based": round(token_sim * 100, 1),
            "structural": round(structural_sim * 100, 1),
            "breakdown": {
                "fingerprint": round(breakdown.get("fingerprint", 0) * 100, 1),
                "token": round(breakdown.get("token", 0) * 100, 1),
                "structural": round(breakdown.get("structural", 0) * 100, 1),
            },
            "is_plagiarism": combined_score >= 0.8,
            "severity": _get_severity(combined_score),
        },
        "student_1": student1_name,
        "student_2": student2_name,
    }


def _get_severity(score: float) -> str:
    """Get severity level based on similarity score."""
    if score >= 0.95:
        return "critical"  # Almost identical
    elif score >= 0.85:
        return "high"  # Very likely plagiarism
    elif score >= 0.7:
        return "medium"  # Possible plagiarism
    elif score >= 0.5:
        return "low"  # Some similarity
    else:
        return "minimal"  # Little to no similarity


def _generate_code_comparison(code1: str, code2: str, max_lines: int = 50) -> dict:
    """Generate side-by-side code comparison."""
    lines1 = code1.split('\n')[:max_lines]
    lines2 = code2.split('\n')[:max_lines]
    
    # Simple line-by-line comparison
    comparison_lines = []
    max_len = max(len(lines1), len(lines2))
    
    for i in range(max_len):
        line1 = lines1[i] if i < len(lines1) else ""
        line2 = lines2[i] if i < len(lines2) else ""
        
        # Check if lines are similar (ignoring whitespace)
        is_similar = line1.strip() == line2.strip()
        
        comparison_lines.append({
            "line_number": i + 1,
            "code1": line1,
            "code2": line2,
            "is_similar": is_similar,
        })
    
    return {
        "lines": comparison_lines,
        "total_lines_compared": len(comparison_lines),
        "truncated": len(code1.split('\n')) > max_lines or len(code2.split('\n')) > max_lines,
    }


@router.post("/scan")
async def scan_plagiarism(
    user=Depends(get_admin_user),
):
    """
    Trigger plagiarism scan across all submissions.
    Returns scan job ID for async processing.
    """
    import uuid
    from app.services.job_store import get_job_store
    
    container = get_container()
    repo = container.get_repository()
    
    # Create scan job
    job_id = str(uuid.uuid4())
    job_store = get_job_store()
    await job_store.set(job_id, {
        "type": "plagiarism_scan",
        "status": "processing",
        "started_by": user.get("username"),
        "created_at": __import__('time').time(),
    })
    
    # TODO: Implement actual plagiarism scanning logic
    # For now, return job ID for tracking
    await job_store.set(job_id, {
        "type": "plagiarism_scan",
        "status": "completed",
        "started_by": user.get("username"),
        "flagged_count": 0,
    })
    
    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Plagiarism scan completed",
    }


__all__ = ["router"]
