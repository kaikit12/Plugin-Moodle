"""
DSA AutoGrader - Rate Limiter.

Simple in-memory rate limiting.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("dsa.rate_limiter")


class RateLimiter:
    """In-memory rate limiter."""

    def __init__(self, per_minute: int = 60, per_hour: int = 1000):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        # Clean old requests
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > hour_ago]

        # Check limits
        recent = self.requests[client_ip]
        minute_count = sum(1 for t in recent if t > minute_ago)
        hour_count = len(recent)

        if minute_count >= self.per_minute:
            return False, 60
        if hour_count >= self.per_hour:
            return False, 3600

        # Record request
        self.requests[client_ip].append(now)
        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, per_minute: int = 60, per_hour: int = 1000):
        super().__init__(app)
        self.limiter = RateLimiter(per_minute, per_hour)

    async def dispatch(self, request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        allowed, retry_after = self.limiter.is_allowed(client_ip)

        if not allowed:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": retry_after},
            )

        # Process request
        response = await call_next(request)
        return response
