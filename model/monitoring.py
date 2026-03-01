"""
Monitoring & observability module for HealthOS API.
Integrates health checks, error tracking (Sentry), and performance metrics.
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# Sentry integration (optional, graceful fallback)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    
    SENTRY_DSN = os.environ.get("SENTRY_DSN")
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,  # 10% sampling for performance
            environment=os.environ.get("ENV", "development"),
        )
        SENTRY_ENABLED = True
        logger.info("✓ Sentry error tracking initialized")
    else:
        SENTRY_ENABLED = False
except ImportError:
    SENTRY_ENABLED = False
    logger.info("✗ Sentry not installed (error tracking disabled)")


class HealthCheck:
    """Health check status aggregator."""
    
    def __init__(self):
        self.start_time = time.time()
        self.checks: Dict[str, Dict[str, Any]] = {}
    
    def register(self, name: str, check_fn, critical: bool = False):
        """Register a health check function.
        
        Args:
            name: Check name (e.g., 'supabase', 'ollama', 'redis')
            check_fn: Async or sync function returning (is_healthy: bool, details: dict)
            critical: If True, whole system unhealthy if this fails
        """
        self.checks[name] = {
            "fn": check_fn,
            "critical": critical,
            "status": None,
            "last_checked": None,
            "error": None,
        }
    
    async def run_all(self) -> Dict[str, Any]:
        """Run all health checks.
        
        Returns:
            Health status dict with overall status and per-service details
        """
        results = {}
        critical_failed = False
        
        for name, check_data in self.checks.items():
            try:
                check_fn = check_data["fn"]
                # Handle both async and sync functions
                if hasattr(check_fn, "__await__"):
                    healthy, details = await check_fn()
                else:
                    healthy, details = check_fn()
                
                results[name] = {
                    "healthy": healthy,
                    "details": details,
                    "checked_at": datetime.utcnow().isoformat(),
                }
                
                if check_data["critical"] and not healthy:
                    critical_failed = True
                    
            except Exception as e:
                error_msg = str(e)
                results[name] = {
                    "healthy": False,
                    "error": error_msg,
                    "checked_at": datetime.utcnow().isoformat(),
                }
                if check_data["critical"]:
                    critical_failed = True
        
        return {
            "healthy": not critical_failed,
            "uptime_seconds": time.time() - self.start_time,
            "timestamp": datetime.utcnow().isoformat(),
            "services": results,
        }


class PerformanceMetrics:
    """Track API performance metrics."""
    
    def __init__(self):
        self.request_count = 0
        self.total_response_time = 0.0
        self.error_count = 0
        self.endpoint_stats: Dict[str, Dict[str, Any]] = {}
    
    def track_request(self, endpoint: str, response_time: float, success: bool):
        """Track request metrics.
        
        Args:
            endpoint: API endpoint path
            response_time: Response time in seconds
            success: Whether request was successful
        """
        self.request_count += 1
        self.total_response_time += response_time
        
        if not success:
            self.error_count += 1
        
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
                "errors": 0,
            }
        
        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += response_time
        stats["min_time"] = min(stats["min_time"], response_time)
        stats["max_time"] = max(stats["max_time"], response_time)
        if not success:
            stats["errors"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        avg_response_time = (
            self.total_response_time / self.request_count
            if self.request_count > 0
            else 0
        )
        
        endpoint_summary = {}
        for endpoint, stats in self.endpoint_stats.items():
            endpoint_summary[endpoint] = {
                "requests": stats["count"],
                "avg_time_ms": round((stats["total_time"] / stats["count"]) * 1000, 2),
                "min_time_ms": round(stats["min_time"] * 1000, 2),
                "max_time_ms": round(stats["max_time"] * 1000, 2),
                "error_rate": round((stats["errors"] / stats["count"] * 100), 2),
            }
        
        return {
            "total_requests": self.request_count,
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "error_count": self.error_count,
            "error_rate": round(
                (self.error_count / self.request_count * 100) if self.request_count > 0 else 0,
                2
            ),
            "endpoints": endpoint_summary,
        }


def performance_middleware(metrics: PerformanceMetrics):
    """Decorator for tracking endpoint performance.
    
    Usage:
        @app.get("/api/endpoint")
        @performance_middleware(metrics)
        async def endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                elapsed = time.time() - start
                endpoint = getattr(func, "__name__", "unknown")
                metrics.track_request(endpoint, elapsed, success)
            
            return result
        
        return wrapper
    return decorator


def capture_exception(exc: Exception, context: Optional[Dict[str, Any]] = None):
    """Capture exception to error tracker (Sentry).
    
    Args:
        exc: Exception to capture
        context: Additional context dictionary
    """
    if SENTRY_ENABLED:
        if context:
            sentry_sdk.set_context("custom", context)
        sentry_sdk.capture_exception(exc)
    
    logger.error(f"Exception captured: {exc}", exc_info=True)


def capture_message(message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
    """Capture message to error tracker.
    
    Args:
        message: Message to log
        level: Log level ('info', 'warning', 'error')
        context: Additional context dictionary
    """
    if SENTRY_ENABLED:
        if context:
            sentry_sdk.set_context("custom", context)
        sentry_sdk.capture_message(message, level=level)
    
    getattr(logger, level)(message)


# Global instances
health_check = HealthCheck()
performance_metrics = PerformanceMetrics()
