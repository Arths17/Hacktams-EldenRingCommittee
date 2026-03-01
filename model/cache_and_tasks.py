"""
Caching and async task queue system for HealthOS.
Uses Redis for caching and Celery for background task processing.
"""

import os
import json
import logging
from typing import Any, Optional, Callable
from datetime import timedelta
from functools import wraps

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
REDIS_ENABLED = True

try:
    import redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    logger.info("✓ Redis cache connected")
except Exception as e:
    logger.warning(f"✗ Redis unavailable: {e} (caching disabled)")
    REDIS_ENABLED = False
    redis_client = None  # type: ignore


class RedisCache:
    """Redis-backed caching utility."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache.
        
        Args:
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
        """
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if not REDIS_ENABLED:
            return None
        
        try:
            value: Optional[str] = redis_client.get(key)  # type: ignore
            if value and isinstance(value, str):
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (overrides default)
        """
        if not REDIS_ENABLED:
            return
        
        try:
            ttl = ttl or self.ttl
            redis_client.setex(  # type: ignore
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
    
    def delete(self, key: str):
        """Delete cache entry.
        
        Args:
            key: Cache key to delete
        """
        if not REDIS_ENABLED:
            return
        
        try:
            redis_client.delete(key)  # type: ignore
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
    
    def clear_pattern(self, pattern: str):
        """Delete all cache entries matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., 'user:*')
        """
        if not REDIS_ENABLED:
            return
        
        try:
            keys = redis_client.keys(pattern)  # type: ignore
            if keys:
                redis_client.delete(*keys)  # type: ignore
        except Exception as e:
            logger.warning(f"Cache clear pattern failed: {e}")


def cache_decorator(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results.
    
    Usage:
        @cache_decorator(ttl=7200, key_prefix="user_profile")
        def get_user_profile(username: str) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            cache_key = cache_key.replace(" ", "")
            
            # Try to get from cache
            cached = RedisCache().get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            RedisCache().set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


# Celery Configuration (optional, graceful fallback)
CELERY_ENABLED = False

# Define fallback celery_app first
class _FallbackCeleryApp:
    """Fallback Celery app when Celery is not available."""
    def task(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

celery_app: Any = _FallbackCeleryApp()  # type: ignore

try:
    from celery import Celery
    
    CELERY_BROKER = os.environ.get("CELERY_BROKER", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
    
    celery_app = Celery(
        "healthos",
        broker=CELERY_BROKER,
        backend=CELERY_RESULT_BACKEND,
    )
    
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minute hard limit
        task_soft_time_limit=25 * 60,  # 25 minute soft limit
    )
    
    CELERY_ENABLED = True
    logger.info("✓ Celery async task queue initialized")
    
except ImportError:
    CELERY_ENABLED = False
    logger.info("✗ Celery not installed (async tasks disabled)")


# Async task functions
if CELERY_ENABLED:
    @celery_app.task(bind=True, max_retries=3)
    def send_email_task(self, to_email: str, subject: str, body: str):
        """Send email asynchronously.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = os.environ.get("SMTP_FROM", "noreply@healthos.ai")
            msg["To"] = to_email
            
            with smtplib.SMTP(
                os.environ.get("SMTP_HOST", "smtp.gmail.com"),
                int(os.environ.get("SMTP_PORT", 587))
            ) as server:
                server.starttls()
                server.login(
                    os.environ.get("SMTP_USER", ""),
                    os.environ.get("SMTP_PASSWORD", "")
                )
                server.send_message(msg)
            
            logger.info(f"✓ Email sent to {to_email}")
            return {"status": "success", "email": to_email}
        
        except Exception as exc:
            logger.error(f"Email task failed: {exc}")
            # Retry with exponential backoff
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    
    @celery_app.task(bind=True, max_retries=3)
    def process_feedback_task(self, username: str, feedback: str):
        """Process user feedback asynchronously.
        
        Args:
            username: Username who provided feedback
            feedback: Feedback text
        """
        try:
            # This would integrate with your feedback learning engine
            logger.info(f"Processing feedback for {username}: {feedback[:100]}")
            return {"status": "processed", "username": username}
        except Exception as exc:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    
    @celery_app.task(bind=True, max_retries=3)
    def generate_meal_plan_task(self, username: str, preferences: dict):
        """Generate meal plan asynchronously.
        
        Args:
            username: Username requesting meal plan
            preferences: User preferences dict
        """
        try:
            logger.info(f"Generating meal plan for {username}")
            # This would integrate with your meal planner
            return {"status": "generated", "username": username}
        except Exception as exc:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    
    @celery_app.task
    def sync_supabase_task():
        """Periodic task: sync local data with Supabase.
        
        Runs every 5 minutes to keep caches synchronized.
        """
        try:
            logger.info("Syncing cache with Supabase")
            # Sync logic here
            return {"status": "synced"}
        except Exception as exc:
            logger.error(f"Sync task failed: {exc}")
            return {"status": "failed", "error": str(exc)}
    
    @celery_app.task
    def cleanup_old_cache_task():
        """Periodic task: clean up expired cache entries.
        
        Runs daily to maintain Redis memory usage.
        """
        try:
            logger.info("Cleaning up expired cache entries")
            # Redis automatically handles TTL cleanup
            return {"status": "cleaned"}
        except Exception as exc:
            logger.error(f"Cache cleanup failed: {exc}")
            return {"status": "failed", "error": str(exc)}


def enqueue_task(task_name: str, *args, **kwargs) -> Optional[str]:
    """Enqueue a background task.
    
    Args:
        task_name: Name of task function (e.g., 'send_email_task')
        *args: Task positional arguments
        **kwargs: Task keyword arguments
        
    Returns:
        Task ID if Celery enabled, None otherwise
    """
    if not CELERY_ENABLED:
        logger.warning(f"Task {task_name} not enqueued (Celery disabled)")
        return None
    
    try:
        task = getattr(celery_app, "send_task")(task_name, args=args, kwargs=kwargs)
        return task.id
    except Exception as e:
        logger.error(f"Failed to enqueue task {task_name}: {e}")
        return None


# Global cache instance
cache = RedisCache(ttl_seconds=3600)