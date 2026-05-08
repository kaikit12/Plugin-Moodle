"""
DSA AutoGrader - Rubric & Manual Grading API.

Features:
- Upload rubric files
- Create/manage rubrics
- Manual grading with rubrics
- Static grading by lecturers
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from app.containers.container import get_container
from app.api.dependencies import get_admin_user

router = APIRouter(prefix="/api/admin", tags=["Rubric & Manual Grading"])

# Upload directory
UPLOAD_DIR = "data/rubrics"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ═══════════════════════════════════════════
# Rubric Management
# ═══════════════════════════════════════════

@router.post("/rubric/upload")
async def upload_rubric_file(
    file: UploadFile = File(...),
    assignment_code: str = Form(...),
    topic: str = Form(...),
    user=Depends(get_admin_user)
):
    """Upload a rubric file (PDF, DOCX, images)."""
    try:
        # Validate file type
        allowed_extensions = [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".xlsx", ".xls"]
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {
            "success": True,
            "file_path": file_path,
            "filename": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/rubric/create")
async def create_rubric(
    assignment_code: str = Form(...),
    topic: str = Form(...),
    criteria_name: str = Form(...),
    max_score: float = Form(...),
    description: str = Form(""),
    file_path: str = Form(None),
    user=Depends(get_admin_user)
):
    """Create a new rubric."""
    container = get_container()
    repo = container.get_repository()
    
    rubric_id = repo.create_rubric(
        assignment_code=assignment_code,
        topic=topic,
        criteria_name=criteria_name,
        max_score=max_score,
        description=description,
        file_path=file_path or "",
        created_by=user["username"]
    )
    
    if not rubric_id:
        raise HTTPException(status_code=500, detail="Failed to create rubric")

    return {
        "success": True,
        "rubric_id": rubric_id,
        "message": "Rubric created successfully"
    }


@router.get("/rubric/{assignment_code}")
async def get_rubrics(assignment_code: str, user=Depends(get_admin_user)):
    """Get all rubrics for an assignment."""
    container = get_container()
    repo = container.get_repository()
    
    rubrics = repo.get_rubrics_by_assignment(assignment_code)
    
    return {
        "assignment_code": assignment_code,
        "rubrics": rubrics,
        "total": len(rubrics)
    }


@router.delete("/rubric/{rubric_id}")
async def delete_rubric(rubric_id: int, user=Depends(get_admin_user)):
    """Delete a rubric."""
    container = get_container()
    repo = container.get_repository()
    
    success = repo.delete_rubric(rubric_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Rubric not found")

    return {"success": True, "message": "Rubric deleted"}


# ═══════════════════════════════════════════
# Manual Grading
# ═══════════════════════════════════════════

@router.post("/grade/manual")
async def create_manual_grade(
    submission_id: int = Form(...),
    rubric_id: int = Form(None),
    criteria_scores: str = Form(...),  # JSON string
    total_score: float = Form(...),
    feedback: str = Form(""),
    rubric_file: UploadFile = File(None),
    user=Depends(get_admin_user)
):
    """
    Create a manual grade for a submission.
    
    Args:
        submission_id: Grading history ID
        rubric_id: Optional rubric ID
        criteria_scores: JSON string like {"criteria1": 8.5, "criteria2": 9.0}
        total_score: Total score (0-10)
        feedback: Feedback text
        rubric_file: Optional uploaded rubric file
    """
    try:
        import os
        import uuid
        
        container = get_container()
        repo = container.get_repository()
        
        # Parse criteria scores
        scores = json.loads(criteria_scores)
        
        # Handle rubric file upload if provided
        rubric_file_path = None
        if rubric_file:
            unique_filename = f"{uuid.uuid4()}_{rubric_file.filename}"
            rubric_file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            with open(rubric_file_path, "wb") as f:
                content = await rubric_file.read()
                f.write(content)
        
        # Get submission to get student info
        submission = repo.get_result_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Create manual grade
        grade_id = repo.create_manual_grade(
            grading_history_id=submission_id,
            student_id=submission.get("student_id", ""),
            assignment_code=submission.get("assignment_code", ""),
            rubric_id=rubric_id or 0,
            criteria_scores=scores,
            total_score=total_score,
            feedback=feedback,
            graded_by=user["username"],
            rubric_file_path=rubric_file_path
        )
        
        if not grade_id:
            raise HTTPException(status_code=500, detail="Failed to create manual grade")

        return {
            "success": True,
            "grade_id": grade_id,
            "message": f"Manual grading completed successfully. Score: {total_score}"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid criteria_scores JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual grading failed: {str(e)}")


@router.get("/manual-grades")
async def get_manual_grades(
    student_id: Optional[str] = None,
    assignment_code: Optional[str] = None,
    user=Depends(get_admin_user)
):
    """Get manual grades with optional filters."""
    container = get_container()
    repo = container.get_repository()
    
    grades = repo.get_manual_grades(
        student_id=student_id,
        assignment_code=assignment_code
    )
    
    return {
        "grades": grades,
        "total": len(grades)
    }


@router.get("/submission/{submission_id}/manual-grade")
async def get_submission_manual_grade(submission_id: int, user=Depends(get_admin_user)):
    """Get manual grade for a specific submission."""
    container = get_container()
    repo = container.get_repository()
    
    # Get all manual grades and filter by submission_id
    all_grades = repo.get_manual_grades()
    submission_grade = next((g for g in all_grades if g["grading_history_id"] == submission_id), None)
    
    if not submission_grade:
        return {"has_manual_grade": False, "grade": None}
    
    return {
        "has_manual_grade": True,
        "grade": submission_grade
    }


# ═══════════════════════════════════════════
# Static Grading (Testcase-based)
# ═══════════════════════════════════════════

@router.post("/grade/static")
async def create_static_grade(
    submission_id: int = Form(...),
    test_results: str = Form(...),  # JSON: [{testcase_id, passed, output, time_ms}]
    total_score: float = Form(...),
    feedback: str = Form(""),
    user=Depends(get_admin_user)
):
    """
    Create a static grade based on testcases.
    
    Lecturer can manually specify which testcases passed/failed.
    """
    try:
        container = get_container()
        repo = container.get_repository()
        
        # Parse test results
        results = json.loads(test_results)
        
        # Get submission
        submission = repo.get_result_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Update submission score
        success = repo.update_submission_score(
            submission_id=submission_id,
            new_score=total_score,
            reviewer_id=user["username"],
            reason=f"Static grading: {feedback}",
            feedback=feedback
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update score")

        # Save test results to run_results table
        repo.save_runs(submission_id, results)

        return {
            "success": True,
            "message": f"Static grading completed successfully. Score: {total_score}"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid test_results JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Static grading failed: {str(e)}")
