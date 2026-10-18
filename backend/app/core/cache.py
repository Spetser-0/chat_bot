"""
Redis caching utility for Spetser AI.
Provides decorator-based caching for expensive operations.
"""
from __future__ import annotations

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as redis

from app.core.config import get_settings

# Initialize Redis connection
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global redis_client
    if redis_client is None:
        settings = get_settings()
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


def cache_result(ttl: int = 300, prefix: str = "cache"):
    """
    Decorator to cache function results in Redis.
    
    Args:
        ttl: Time-to-live in seconds (default: 5 minutes)
        prefix: Cache key prefix for namespacing
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                r = await get_redis()
                
                # Generate cache key from function name and arguments
                key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cache_key = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
                
                # Try to get from cache
                cached = await r.get(cache_key)
                if cached is not None:
                    return json.loads(cached)
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await r.setex(cache_key, ttl, json.dumps(result, default=str))
                
                return result
            except Exception:
                # If Redis is down or unavailable, execute without caching
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def invalidate_cache(pattern: str) -> None:
    """Invalidate all cache keys matching a pattern."""
    try:
        r = await get_redis()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception:
        pass  # Silently fail if Redis is down
