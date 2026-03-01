"""
User Segmentation for HealthOS.
Cluster users by behavior, preferences, health goals, and engagement patterns.
"""

import logging
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
import statistics
from enum import Enum

logger = logging.getLogger(__name__)


class EngagementLevel(str, Enum):
    """User engagement classification."""
    HIGH = "high"  # Logs meals regularly, submits feedback
    MEDIUM = "medium"  # Moderate activity
    LOW = "low"  # Minimal activity
    INACTIVE = "inactive"  # No recent activity


class HealthGoal(str, Enum):
    """Primary health goal."""
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    ENERGY_BOOST = "energy_boost"
    DISEASE_MANAGEMENT = "disease_management"
    GENERAL_WELLNESS = "general_wellness"


class DietType(str, Enum):
    """Preferred diet approach."""
    LOW_CARB = "low_carb"
    KETO = "keto"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HIGH_PROTEIN = "high_protein"
    BALANCED = "balanced"
    FLEXIBLE = "flexible"


class UserSegment:
    """A user segment/cohort."""
    
    def __init__(self, segment_id: str, name: str, description: str = ""):
        """Initialize segment.
        
        Args:
            segment_id: Unique segment identifier
            name: Segment name
            description: Segment characteristics
        """
        self.segment_id = segment_id
        self.name = name
        self.description = description
        self.users: Set[str] = set()
        self.characteristics: Dict[str, Any] = {}
    
    def add_user(self, user_id: str):
        """Add user to segment."""
        self.users.add(user_id)
    
    def remove_user(self, user_id: str):
        """Remove user from segment."""
        self.users.discard(user_id)
    
    def get_size(self) -> int:
        """Get segment size."""
        return len(self.users)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "segment_id": self.segment_id,
            "name": self.name,
            "description": self.description,
            "size": self.get_size(),
            "characteristics": self.characteristics,
        }


class UserSegmenter:
    """Segment users based on behavior and preferences."""
    
    def __init__(self):
        self.segments: Dict[str, UserSegment] = {}
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
    
    def build_user_profile(self, user_id: str, events: List[Dict[str, Any]],
                          user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive user profile from events and data.
        
        Args:
            user_id: User identifier
            events: List of user events
            user_data: User account data (goals, preferences, etc)
            
        Returns:
            User profile dict
        """
        profile = {
            "user_id": user_id,
            "goals": user_data.get("goals", []),
            "diet_preference": user_data.get("diet_preference", DietType.BALANCED.value),
        }
        
        # Analyze event patterns
        meal_logs = len([e for e in events if e.get("type") == "meal_logged"])
        feedback_submissions = len([e for e in events if e.get("type") == "feedback"])
        
        # Engagement level
        if meal_logs > 20 and feedback_submissions > 5:
            profile["engagement"] = EngagementLevel.HIGH.value
        elif meal_logs > 10 and feedback_submissions > 2:
            profile["engagement"] = EngagementLevel.MEDIUM.value
        elif meal_logs > 0:
            profile["engagement"] = EngagementLevel.LOW.value
        else:
            profile["engagement"] = EngagementLevel.INACTIVE.value
        
        profile["meal_logs_count"] = meal_logs
        profile["feedback_count"] = feedback_submissions
        
        # Calculate adherence rate
        if feedback_submissions > 0:
            positive_feedback = len([e for e in events 
                                   if e.get("type") == "feedback" and 
                                   e.get("sentiment") in ["positive", "very_positive"]])
            profile["adherence_rate"] = round(positive_feedback / feedback_submissions * 100, 1)
        else:
            profile["adherence_rate"] = None
        
        self.user_profiles[user_id] = profile
        return profile
    
    def create_engagement_segments(self) -> Dict[str, UserSegment]:
        """Segment users by engagement level.
        
        Returns:
            Dict of engagement segments
        """
        segments = {
            EngagementLevel.HIGH.value: UserSegment(
                "engagement_high",
                "Highly Engaged",
                "Regular meal logging and feedback submission"
            ),
            EngagementLevel.MEDIUM.value: UserSegment(
                "engagement_medium",
                "Moderately Engaged",
                "Occasional meal logging and feedback"
            ),
            EngagementLevel.LOW.value: UserSegment(
                "engagement_low",
                "Low Engagement",
                "Minimal meal logging, little feedback"
            ),
            EngagementLevel.INACTIVE.value: UserSegment(
                "engagement_inactive",
                "Inactive",
                "No recent activity"
            ),
        }
        
        for user_id, profile in self.user_profiles.items():
            engagement = profile.get("engagement", EngagementLevel.INACTIVE.value)
            if engagement in segments:
                segments[engagement].add_user(user_id)
        
        self.segments.update(segments)
        return segments
    
    def create_goal_segments(self) -> Dict[str, UserSegment]:
        """Segment users by health goal.
        
        Returns:
            Dict of goal-based segments
        """
        segments = defaultdict(lambda: UserSegment("", "", ""))
        
        for user_id, profile in self.user_profiles.items():
            goals = profile.get("goals", [])
            for goal in goals:
                if goal not in segments:
                    goal_segment = UserSegment(
                        f"goal_{goal}",
                        f"Goal: {goal.replace('_', ' ').title()}",
                        f"Users pursuing {goal.replace('_', ' ')}"
                    )
                    segments[goal] = goal_segment
                
                segments[goal].add_user(user_id)
        
        self.segments.update(dict(segments))
        return dict(segments)
    
    def create_diet_preference_segments(self) -> Dict[str, UserSegment]:
        """Segment users by diet preference.
        
        Returns:
            Dict of diet preference segments
        """
        segments = defaultdict(lambda: UserSegment("", "", ""))
        
        for user_id, profile in self.user_profiles.items():
            diet = profile.get("diet_preference", DietType.BALANCED.value)
            
            if diet not in segments:
                diet_segment = UserSegment(
                    f"diet_{diet}",
                    f"Diet: {diet.replace('_', ' ').title()}",
                    f"Users following {diet.replace('_', ' ')} diet"
                )
                segments[diet] = diet_segment
            
            segments[diet].add_user(user_id)
        
        self.segments.update(dict(segments))
        return dict(segments)
    
    def create_performance_segments(self) -> Dict[str, UserSegment]:
        """Segment users by adherence performance.
        
        Returns:
            Dict of performance segments
        """
        adherence_rates = [
            p.get("adherence_rate") for p in self.user_profiles.values()
            if p.get("adherence_rate") is not None
        ]
        
        if not adherence_rates:
            return {}
        
        median = statistics.median(adherence_rates)
        
        high_performers = UserSegment(
            "performance_high",
            "High Performers",
            "Users with above-median adherence"
        )
        
        low_performers = UserSegment(
            "performance_low",
            "Low Performers",
            "Users with below-median adherence"
        )
        
        for user_id, profile in self.user_profiles.items():
            rate = profile.get("adherence_rate")
            if rate is not None:
                if rate >= median:
                    high_performers.add_user(user_id)
                else:
                    low_performers.add_user(user_id)
        
        segments = {
            "performance_high": high_performers,
            "performance_low": low_performers,
        }
        
        self.segments.update(segments)
        return segments
    
    def get_user_segments(self, user_id: str) -> List[str]:
        """Get all segments a user belongs to.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of segment IDs
        """
        user_segments = []
        for segment in self.segments.values():
            if user_id in segment.users:
                user_segments.append(segment.segment_id)
        return user_segments
    
    def get_segment_stats(self, segment_id: str) -> Dict[str, Any]:
        """Get statistics for a segment.
        
        Args:
            segment_id: Segment identifier
            
        Returns:
            Segment statistics
        """
        segment = self.segments.get(segment_id)
        if not segment:
            return {}
        
        segment_users = segment.users
        segment_profiles = [
            self.user_profiles[u] for u in segment_users
            if u in self.user_profiles
        ]
        
        adherence_rates = [
            p.get("adherence_rate") for p in segment_profiles
            if p.get("adherence_rate") is not None
        ]
        
        meal_counts = [p.get("meal_logs_count", 0) for p in segment_profiles]
        
        return {
            "segment_id": segment_id,
            "segment_name": segment.name,
            "user_count": len(segment_users),
            "avg_adherence_rate": round(statistics.mean(adherence_rates), 1) if adherence_rates else None,
            "avg_meals_logged": round(statistics.mean(meal_counts), 1) if meal_counts else None,
            "median_adherence": round(statistics.median(adherence_rates), 1) if adherence_rates else None,
        }
    
    def get_all_segments(self) -> List[Dict[str, Any]]:
        """Get all segments with stats.
        
        Returns:
            List of segment dicts
        """
        return [
            {**segment.to_dict(), **self.get_segment_stats(segment.segment_id)}
            for segment in self.segments.values()
        ]


# Global instance
segmenter = UserSegmenter()
