"""
Advanced Analytics Engine for HealthOS.
Tracks user behavior, detects trends, segments users, and enables predictive modeling.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class Event:
    """User event for analytics tracking."""
    
    def __init__(self, user_id: str, event_type: str, properties: Dict[str, Any], timestamp: Optional[datetime] = None):
        """Initialize event.
        
        Args:
            user_id: User identifier
            event_type: Type of event (signup, login, feedback, meal_viewed, etc)
            properties: Event-specific properties
            timestamp: When event occurred (default: now)
        """
        self.user_id = user_id
        self.event_type = event_type
        self.properties = properties
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "event_type": self.event_type,
            "properties": self.properties,
            "timestamp": self.timestamp.isoformat(),
        }


class EventStore:
    """In-memory event store (production: use BigQuery, Snowflake, ClickHouse)."""
    
    def __init__(self):
        self.events: List[Event] = []
        self.event_index: Dict[str, List[Event]] = defaultdict(list)
    
    def add_event(self, event: Event):
        """Add event to store."""
        self.events.append(event)
        self.event_index[event.user_id].append(event)
        logger.debug(f"Event recorded: {event.event_type} for {event.user_id}")
    
    def get_user_events(self, user_id: str, event_type: Optional[str] = None, 
                       hours: int = 24) -> List[Event]:
        """Get user events within time window.
        
        Args:
            user_id: User identifier
            event_type: Filter by event type (optional)
            hours: Time window in hours
            
        Returns:
            List of events matching criteria
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        events = self.event_index.get(user_id, [])
        
        filtered = [e for e in events if e.timestamp >= cutoff]
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        return filtered
    
    def get_all_events(self, event_type: Optional[str] = None, 
                       hours: int = 24) -> List[Event]:
        """Get all events within time window."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        events = [e for e in self.events if e.timestamp >= cutoff]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events


class TrendDetector:
    """Detect trends in user behavior and health metrics."""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    def get_user_trend(self, user_id: str, metric: str, days: int = 7) -> Dict[str, Any]:
        """Get user trend for a metric.
        
        Args:
            user_id: User identifier
            metric: Metric name (adherence, weight, mood, energy, etc)
            days: Number of days to analyze
            
        Returns:
            Trend analysis dict
        """
        events = self.event_store.get_user_events(
            user_id, 
            event_type="metric_update", 
            hours=days*24
        )
        
        values = []
        timestamps = []
        
        for event in events:
            if event.properties.get("metric") == metric:
                values.append(float(event.properties.get("value", 0)))
                timestamps.append(event.timestamp)
        
        if not values:
            return {"metric": metric, "trend": "no_data", "data_points": 0}
        
        # Calculate trend direction
        if len(values) >= 2:
            start = values[0]
            end = values[-1]
            change = ((end - start) / start * 100) if start != 0 else 0
            
            if abs(change) < 5:
                trend = "stable"
            elif change > 0:
                trend = "improving"
            else:
                trend = "declining"
        else:
            trend = "insufficient_data"
        
        return {
            "metric": metric,
            "trend": trend,
            "change_percent": round(change, 2) if len(values) >= 2 else None,
            "current_value": end if len(values) >= 2 else values[0],
            "data_points": len(values),
            "avg_value": round(statistics.mean(values), 2),
            "std_dev": round(statistics.stdev(values), 2) if len(values) > 1 else None,
        }
    
    def get_success_patterns(self, days: int = 30) -> Dict[str, Any]:
        """Identify patterns in successful user journeys.
        
        Args:
            days: Analysis window
            
        Returns:
            Common patterns in successful users
        """
        # Get users with positive feedback
        feedback_events = self.event_store.get_all_events("feedback_submitted", hours=days*24)
        
        successful_users = defaultdict(list)
        for event in feedback_events:
            if event.properties.get("sentiment") in ["positive", "very_positive"]:
                user_id = event.user_id
                successful_users[user_id].append(event)
        
        # Analyze their behavior
        patterns = {
            "meal_frequency": [],
            "engagement_level": [],
            "feedback_frequency": [],
        }
        
        for user_id, events in successful_users.items():
            user_events = self.event_store.get_user_events(
                user_id, hours=days*24
            )
            meal_events = len([e for e in user_events if e.event_type == "meal_logged"])
            patterns["meal_frequency"].append(meal_events)
            patterns["engagement_level"].append(len(user_events))
            patterns["feedback_frequency"].append(len(events))
        
        return {
            "successful_users": len(successful_users),
            "avg_meals_per_user": round(statistics.mean(patterns["meal_frequency"]), 1) if patterns["meal_frequency"] else 0,
            "avg_engagements": round(statistics.mean(patterns["engagement_level"]), 1) if patterns["engagement_level"] else 0,
            "avg_feedback_submissions": round(statistics.mean(patterns["feedback_frequency"]), 1) if patterns["feedback_frequency"] else 0,
        }


class MetricsAggregator:
    """Aggregate analytics metrics for dashboards."""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    def get_dashboard_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get high-level metrics for dashboard.
        
        Args:
            hours: Time window
            
        Returns:
            Key metrics dict
        """
        all_events = self.event_store.get_all_events(hours=hours)
        
        # Count events by type
        event_counts = defaultdict(int)
        user_set = set()
        
        for event in all_events:
            event_counts[event.event_type] += 1
            user_set.add(event.user_id)
        
        return {
            "total_events": len(all_events),
            "active_users": len(user_set),
            "event_breakdown": dict(event_counts),
            "time_window_hours": hours,
        }
    
    def get_user_health_summary(self, user_id: str) -> Dict[str, Any]:
        """Get user health metrics summary.
        
        Args:
            user_id: User identifier
            
        Returns:
            Health summary with key metrics
        """
        events = self.event_store.get_user_events(user_id, hours=30*24)
        
        # Extract metric updates
        metrics = defaultdict(list)
        for event in events:
            if event.event_type == "metric_update":
                metric_name = event.properties.get("metric")
                value = event.properties.get("value")
                if metric_name and value:
                    metrics[metric_name].append(float(value))
        
        summary = {}
        for metric, values in metrics.items():
            summary[metric] = {
                "current": values[-1] if values else None,
                "average": round(statistics.mean(values), 2) if values else None,
                "trend": "up" if len(values) > 1 and values[-1] > values[0] else "down",
            }
        
        return summary


def track_event(user_id: str, event_type: str, properties: Dict[str, Any]):
    """Convenience function to track an event.
    
    Args:
        user_id: User identifier
        event_type: Type of event
        properties: Event properties
    """
    event = Event(user_id, event_type, properties)
    logger.info(f"Event: {event_type} | User: {user_id} | Props: {properties}")
    # In production: send to event warehouse (BigQuery, Snowflake, etc)


# Global analytics instances
event_store = EventStore()
trend_detector = TrendDetector(event_store)
metrics_aggregator = MetricsAggregator(event_store)
