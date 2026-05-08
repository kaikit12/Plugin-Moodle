import hashlib
import uuid
import time
from typing import Dict, Optional
from app.containers.container import get_container

# Simple in-memory token store (or use Redis if available)
_token_store: Dict[str, Dict] = {}

# Token expiration: 20 hours (balanced for security and convenience)
TOKEN_EXPIRY_SECONDS = 20 * 3600  # 20 hours

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with a simple salt."""
    salt = "dsa_grader_salt_2026"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    return hash_password(password) == password_hash

def create_access_token(user_id: int, username: str, role: str, expiry_seconds: int = None) -> str:
    """Create a new access token."""
    token = str(uuid.uuid4())
    expiry = expiry_seconds or TOKEN_EXPIRY_SECONDS

    _token_store[token] = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "expires": time.time() + expiry,
        "created_at": time.time()
    }
    return token

def verify_token(token: str) -> Optional[Dict]:
    """Verify an access token and return token data if valid."""
    data = _token_store.get(token)
    if not data:
        return None

    if data["expires"] < time.time():
        # Thread-safe removal to prevent KeyError during concurrent hits
        _token_store.pop(token, None)
        return None

    return data

def refresh_token(token: str) -> Optional[str]:
    """Refresh an existing token, extending its expiry."""
    data = verify_token(token)
    if not data:
        return None

    # Create new token with same user info
    new_token = create_access_token(
        data["user_id"],
        data["username"],
        data["role"]
    )

    # Remove old token safely
    _token_store.pop(token, None)

    return new_token

def get_current_user(token: str) -> Optional[Dict]:
    """Get the current user from a token."""
    token_data = verify_token(token)
    if not token_data:
        return None

    # Optionally verify against DB
    return token_data

def get_token_stats() -> Dict:
    """Get token store statistics."""
    now = time.time()
    active = sum(1 for t in _token_store.values() if t["expires"] > now)
    expired = len(_token_store) - active

    return {
        "total_tokens": len(_token_store),
        "active_tokens": active,
        "expired_tokens": expired,
        "expiry_hours": TOKEN_EXPIRY_SECONDS / 3600
    }
