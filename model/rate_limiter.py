"""
Rate limiting middleware for HealthOS API.
"""

import time
from collections import defaultdict
from typing import Optional, Dict
from fastapi import Request
from api_exceptions import RateLimitError


class RateLimiter:
    """
    Token bucket rate limiter with per-user and per-endpoint limits.
    
    Supports:
    - Per-user rate limiting (by username or IP)
    - Per-endpoint rate limiting
    - Different limits for different endpoints
    """
    
    def __init__(self):
        # {user_key: {endpoint: (tokens, last_refill_time), ...}, ...}
        self.buckets: Dict[str, Dict[str, tuple[float, float]]] = defaultdict(dict)
        
        # Default limits: (requests_per_period, period_seconds)
        self.limits = {
            "/api/login": (5, 300),       # 5 requests per 5 minutes
            "/api/signup": (3, 3600),     # 3 requests per hour
            "/api/chat": (30, 3600),      # 30 requests per hour
            "/api/profile": (20, 3600),   # 20 requests per hour
            "/api/feedback": (60, 3600),  # 60 requests per hour
            "/api/me": (100, 3600),       # 100 requests per hour
            "default": (100, 3600),       # Default: 100 requests per hour
        }
    
    def set_limit(self, endpoint: str, requests_per_period: int, period_seconds: int):
        """Configure rate limit for an endpoint."""
        self.limits[endpoint] = (requests_per_period, period_seconds)
    
    def get_user_key(self, request: Request, username: Optional[str] = None) -> str:
        """Get unique identifier for request (username or IP)."""
        if username:
            return f"user:{username}"
        ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"
    
    def is_allowed(
        self,
        request: Request,
        endpoint: str,
        username: Optional[str] = None,
    ) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            (is_allowed, retry_after_seconds)
        """
        user_key = self.get_user_key(request, username)
        limit, period = self.limits.get(endpoint, self.limits["default"])
        
        now = time.time()
        bucket = self.buckets[user_key]
        
        # Initialize bucket if not present
        if endpoint not in bucket:
            bucket[endpoint] = (limit, now)
        
        tokens, last_refill = bucket[endpoint]
        
        # Refill tokens based on elapsed time
        elapsed = now - last_refill
        refill_rate = limit / period
        tokens = min(limit, tokens + (elapsed * refill_rate))
        
        # Check if request allowed
        if tokens >= 1:
            tokens -= 1
            bucket[endpoint] = (tokens, now)
            return True, 0
        
        # Calculate retry-after
        retry_after = int((1 - tokens) / refill_rate) + 1
        return False, retry_after
    
    def check_rate_limit(
        self,
        request: Request,
        endpoint: str,
        username: Optional[str] = None,
    ) -> None:
        """
        Check rate limit and raise RateLimitError if exceeded.
        """
        is_allowed, retry_after = self.is_allowed(request, endpoint, username)
        if not is_allowed:
            raise RateLimitError(retry_after=retry_after)


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    return _rate_limiter
