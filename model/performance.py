"""
Performance Optimization & Tuning for HealthOS.
Query optimization, caching strategies, and load testing.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from functools import wraps
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class QueryProfiler:
    """Profile database queries for bottlenecks."""
    
    def __init__(self):
        self.queries: Dict[str, List[float]] = defaultdict(list)
        self.slow_threshold_ms = 100  # Flag queries > 100ms
    
    def profile_query(self, query_name: str, execution_time_ms: float):
        """Record query execution time.
        
        Args:
            query_name: Name/description of query
            execution_time_ms: Execution time in milliseconds
        """
        self.queries[query_name].append(execution_time_ms)
        
        if execution_time_ms > self.slow_threshold_ms:
            logger.warning(f"⚠️  SLOW QUERY: {query_name} took {execution_time_ms}ms")
    
    def get_slowest_queries(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get slowest queries by average execution time.
        
        Args:
            limit: Number of queries to return
            
        Returns:
            List of (query_name, avg_time_ms) tuples
        """
        avg_times = [
            (query, statistics.mean(times))
            for query, times in self.queries.items()
        ]
        
        return sorted(avg_times, key=lambda x: x[1], reverse=True)[:limit]
    
    def get_query_stats(self, query_name: str) -> Dict[str, float]:
        """Get detailed stats for a query.
        
        Args:
            query_name: Name of query
            
        Returns:
            Stats dict
        """
        times = self.queries.get(query_name, [])
        
        if not times:
            return {"error": "Query not found"}
        
        return {
            "count": len(times),
            "avg_time_ms": round(statistics.mean(times), 2),
            "min_time_ms": round(min(times), 2),
            "max_time_ms": round(max(times), 2),
            "p95_time_ms": round(statistics.quantiles(times, n=20)[18], 2) if len(times) > 19 else None,
            "p99_time_ms": round(statistics.quantiles(times, n=100)[98], 2) if len(times) > 99 else None,
        }


class QueryOptimizer:
    """Identify and suggest query optimizations."""
    
    @staticmethod
    def suggest_indexes(slow_queries: List[str]) -> List[Dict[str, Any]]:
        """Suggest database indexes based on slow queries.
        
        Args:
            slow_queries: List of slow query names
            
        Returns:
            List of index suggestions
        """
        suggestions = []
        
        # Pattern matching for common optimization opportunities
        index_patterns = {
            "users_by_username": {
                "table": "users",
                "columns": ["username"],
                "reason": "Frequently filtered by username"
            },
            "meals_by_user": {
                "table": "meals",
                "columns": ["user_id", "created_at"],
                "reason": "Common filter: user_id with date sorting"
            },
            "feedback_by_user_date": {
                "table": "feedback",
                "columns": ["user_id", "created_at"],
                "reason": "Feedback lookup by user and date"
            },
            "goals_by_user": {
                "table": "user_goals",
                "columns": ["user_id"],
                "reason": "User goal lookups"
            },
        }
        
        for query in slow_queries:
            for pattern, suggestion in index_patterns.items():
                if pattern in query.lower():
                    suggestions.append(suggestion)
                    break
        
        return suggestions
    
    @staticmethod
    def detect_n_plus_one(query_pattern: str) -> bool:
        """Detect potential N+1 query patterns.
        
        Args:
            query_pattern: Description of query pattern
            
        Returns:
            True if likely N+1 issue
        """
        n_plus_one_indicators = [
            "loop",
            "for each",
            "iterate",
            "individual",
            "one by one",
        ]
        
        pattern_lower = query_pattern.lower()
        return any(indicator in pattern_lower for indicator in n_plus_one_indicators)


class CacheStrategy:
    """Intelligent caching strategies."""
    
    @staticmethod
    def get_cache_ttl(data_type: str, frequency: str = "medium") -> int:
        """Get recommended cache TTL for data type.
        
        Args:
            data_type: Type of data (user_profile, meal, recommendation, etc)
            frequency: How often data changes (low/medium/high)
            
        Returns:
            TTL in seconds
        """
        base_ttls = {
            "user_profile": 3600,  # 1 hour
            "meal_data": 7200,  # 2 hours
            "recommendation": 1800,  # 30 minutes
            "leaderboard": 600,  # 10 minutes
            "health_metric": 300,  # 5 minutes
            "trending": 60,  # 1 minute
        }
        
        base = base_ttls.get(data_type, 3600)
        
        # Adjust based on change frequency
        if frequency == "low":
            return base * 2
        elif frequency == "high":
            return base // 2
        else:
            return base
    
    @staticmethod
    def should_cache(operation: str) -> bool:
        """Determine if operation result should be cached.
        
        Args:
            operation: Type of operation
            
        Returns:
            True if should cache
        """
        cacheable = [
            "read",
            "get",
            "list",
            "search",
            "recommend",
            "aggregate",
        ]
        
        return any(op in operation.lower() for op in cacheable)


def benchmark_function(func: Callable) -> Callable:
    """Decorator to benchmark function execution time.
    
    Usage:
        @benchmark_function
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed_ms = (time.time() - start) * 1000
        
        logger.debug(f"Benchmark: {func.__name__} took {elapsed_ms:.2f}ms")
        
        return result
    return wrapper


class LoadTester:
    """Load testing and stress testing utilities."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
    
    def simulate_load(self, endpoint_func: Callable, num_requests: int = 100,
                     concurrent: int = 10) -> Dict[str, Any]:
        """Simulate load on an endpoint.
        
        Args:
            endpoint_func: Function to call for each request
            num_requests: Total number of requests
            concurrent: Concurrent requests (simulated)
            
        Returns:
            Load test results
        """
        times = []
        errors = 0
        
        for i in range(num_requests):
            start = time.time()
            try:
                endpoint_func()
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            except Exception as e:
                errors += 1
                logger.error(f"Load test error on request {i}: {e}")
        
        if not times:
            return {"error": "No successful requests"}
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(times),
            "failed_requests": errors,
            "error_rate": round(errors / num_requests * 100, 2),
            "avg_response_time_ms": round(statistics.mean(times), 2),
            "min_response_time_ms": round(min(times), 2),
            "max_response_time_ms": round(max(times), 2),
            "p95_response_time_ms": round(statistics.quantiles(times, n=20)[18], 2) if len(times) > 19 else None,
            "p99_response_time_ms": round(statistics.quantiles(times, n=100)[98], 2) if len(times) > 99 else None,
            "requests_per_second": round(num_requests / sum(times) * 1000, 2),
        }


class PerformanceOptimizer:
    """Recommended optimizations based on analysis."""
    
    def __init__(self, profiler: QueryProfiler):
        self.profiler = profiler
        self.optimizer = QueryOptimizer()
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get list of recommended optimizations.
        
        Returns:
            List of recommendations with priority
        """
        recommendations = []
        
        # 1. Index suggestions based on slow queries
        slowest = self.profiler.get_slowest_queries(limit=5)
        if slowest:
            slow_query_names = [q[0] for q in slowest]
            indexes = self.optimizer.suggest_indexes(slow_query_names)
            
            for index in indexes:
                recommendations.append({
                    "type": "add_index",
                    "priority": "high",
                    "table": index["table"],
                    "columns": index["columns"],
                    "reason": index["reason"],
                })
        
        # 2. Caching recommendations
        recommendations.append({
            "type": "implement_caching",
            "priority": "high",
            "suggestions": [
                "Cache user profiles (TTL: 1 hour)",
                "Cache meal recommendations (TTL: 30 min)",
                "Cache trending metrics (TTL: 5 min)",
            ]
        })
        
        # 3. Connection pooling
        recommendations.append({
            "type": "connection_pooling",
            "priority": "medium",
            "suggestion": "Implement connection pool (size: 20-50)",
        })
        
        # 4. Query batching
        recommendations.append({
            "type": "batch_queries",
            "priority": "medium",
            "suggestion": "Batch similar queries to reduce round trips",
        })
        
        return recommendations


# Global instances
query_profiler = QueryProfiler()
load_tester = LoadTester()
