from fastapi import APIRouter, HTTPException, Depends, Form, Header
from fastapi.responses import JSONResponse
import logging
from app.containers.container import get_container
from app.utils.auth import verify_password, create_access_token, refresh_token, get_token_stats

logger = logging.getLogger("dsa.auth")
router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """Login endpoint for lecturers and students."""
    logger.info(f"Login attempt for username: {username}")

    container = get_container()
    repo = container.get_repository()

    user = repo.get_user_by_username(username)
    logger.info(f"User found: {user is not None}")

    if not user:
        logger.warning(f"User not found: {username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    password_valid = verify_password(password, user["password_hash"])
    logger.info(f"Password valid: {password_valid}")

    if not password_valid:
        logger.warning(f"Invalid password for user: {username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Create token with 20 hours expiry
    token = create_access_token(user["id"], user["username"], user["role"])
    logger.info(f"Login successful for: {username}, role: {user['role']}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["id"],
        "username": user["username"],
        "email": user.get("email", ""),
        "full_name": user["full_name"],
        "role": user["role"],
        "expires_in": "20 hours"
    }

@router.post("/refresh")
async def refresh_access_token(authorization: str = Header(...)):
    """Refresh access token."""
    token = authorization.replace("Bearer ", "").strip()

    new_token = refresh_token(token)
    if not new_token:
        raise HTTPException(status_code=401, detail="Token expired. Please login again.")

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": "20 hours"
    }

@router.get("/stats")
async def get_auth_stats():
    """Get authentication statistics (admin only)."""
    return get_token_stats()
