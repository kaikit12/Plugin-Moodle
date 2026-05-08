"""
Shared FastAPI Dependencies
============================
Central location for all reusable dependency injection functions.
This eliminates code duplication across multiple router modules.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.containers.container import get_container

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Extract and validate JWT bearer token.
    Returns user dict if valid, None if no token, raises 401 if invalid.
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        container = get_container()
        repo = container.get_repository()
        
        # Decode and validate token
        user_data = repo.verify_token(token)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_admin_user(
    current_user=Depends(get_current_user),
):
    """
    Require authenticated user with LECTURER role.
    Raises 403 if user doesn't have sufficient permissions.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_role = current_user.get("role", "")
    if user_role != "LECTURER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lecturer role required",
        )

    return current_user


async def get_admin_only(
    current_user=Depends(get_current_user),
):
    """
    Require authenticated user with LECTURER role only.
    Raises 403 if user is not LECTURER.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if current_user.get("role") != "LECTURER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lecturer role required",
        )

    return current_user
