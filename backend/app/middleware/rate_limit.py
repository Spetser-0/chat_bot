"""
Rate limiting middleware for Spetser AI.
Uses Redis for distributed rate limiting with safe fail-open fallback.
"""
from __future__ import annotations

import hashlib
import time
from typing import Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import redis.asyncio as redis

from app.core.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter using Redis.
    
    Configuration via environment / arguments:
    - max_requests: Max requests per window (default: 100)
    - window_seconds: Window size in seconds (default: 60)
    """
    
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._redis: redis.Redis | None = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(settings.redis_url)
        return self._redis
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for health checks and doc endpoints
        if request.url.path in (
            "/api/v1/health/live",
            "/api/v1/health/ready",
            "/api/v1/health/metrics",
            "/health",
            "/live",
            "/ready",
            "/docs",
            "/openapi.json",
        ):
            return await call_next(request)
        
        # Get client identifier (IP or authenticated session/token)
        client_id = self._get_client_id(request)
        
        try:
            r = await self._get_redis()
            
            # Sliding window counter
            now = time.time()
            window_start = now - self.window_seconds
            key = f"rate_limit:{client_id}"
            
            # Remove old entries and add current request
            pipe = r.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds + 1)
            results = await pipe.execute()
            
            request_count = results[2]
            
            if request_count > self.max_requests:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "data": None,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                            "retry_after": self.window_seconds,
                        }
                    },
                    headers={
                        "Retry-After": str(self.window_seconds),
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                    },
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, self.max_requests - request_count)
            )
            return response
            
        except Exception:
            # If Redis is unavailable, allow the request fail-open
            return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Try to get user ID from auth header or session cookie
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return hashlib.md5(auth_header.encode()).hexdigest()
        
        session_cookie = request.cookies.get("spetser_session")
        if session_cookie:
            return hashlib.md5(session_cookie.encode()).hexdigest()
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"
