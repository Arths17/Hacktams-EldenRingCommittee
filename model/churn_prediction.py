"""
Churn prediction module for HealthOS AI.

Predicts likelihood of user churn based on engagement metrics, goal progress,
meal adherence, and activity trends using logistic regression.
"""

import math
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import numpy as np


@dataclass
class ChurnRiskScore:
    """Risk score for user churn."""
    user_id: str
    churn_probability: float
    risk_level: str  # "low", "medium", "high", "critical"
    risk_factors: Dict[str, float]  # Factor name -> contribution
    recommended_actions: List[str]
    prediction_timestamp: datetime

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "churn_probability": round(self.churn_probability, 4),
            "risk_level": self.risk_level,
            "risk_factors": {k: round(v, 4) for k, v in self.risk_factors.items()},
            "recommended_actions": self.recommended_actions,
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
        }


class ChurnPredictor:
    """ML-based churn prediction model."""

    def __init__(self):
        """Initialize churn predictor."""
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.scaler = StandardScaler()
        self.feature_names = [
            "days_since_last_login",
            "login_frequency",
            "goals_completion_rate",
            "meal_adherence_rate",
            "feedback_frequency",
            "activity_consistency",
            "profile_completion",
            "health_check_frequency",
        ]
        self.is_trained = False
        self.model_timestamp = None
        self._init_default_model()

    def _init_default_model(self):
        """Initialize with default trained model for demo."""
        # Default coefficients based on typical churn patterns
        self.model.coef_ = np.array(
            [
                [0.85, -0.72, -1.15, -0.98, -0.65, -0.58, -0.42, -0.50]
            ]
        )
        self.model.intercept_ = np.array([0.5])
        self.model.classes_ = np.array([0, 1])
        self.is_trained = True
        self.model_timestamp = datetime.now()

    def extract_features(self, user_data: Dict) -> Tuple[np.ndarray, Dict]:
        """Extract churn prediction features from user data.
        
        Args:
            user_data: Dictionary with user engagement metrics
            
        Returns:
            Tuple of (feature_array, feature_dict)
        """
        now = datetime.now()
        last_login = user_data.get("last_login")
        
        # Calculate days since last login
        if last_login:
            if isinstance(last_login, str):
                last_login = datetime.fromisoformat(last_login)
            days_since_login = (now - last_login).days
        else:
            days_since_login = 30  # Default to inactive

        # Login frequency (logins per week in last 30 days)
        login_history = user_data.get("login_history", [])
        recent_logins = sum(
            1 for login in login_history
            if isinstance(login, str) and
            (now - datetime.fromisoformat(login)).days <= 30
        )
        login_freq = recent_logins / 4.3  # Normalize to weeks

        # Goals completion rate
        total_goals = user_data.get("total_goals", 1)
        completed_goals = user_data.get("completed_goals", 0)
        goal_completion = (
            completed_goals / total_goals if total_goals > 0 else 0.0
        )

        # Meal adherence rate
        total_meals = user_data.get("total_meals", 1)
        adhered_meals = user_data.get("adhered_meals", 0)
        meal_adherence = (
            adhered_meals / total_meals if total_meals > 0 else 0.0
        )

        # Feedback frequency
        feedback_count = user_data.get("feedback_count", 0)
        days_active = user_data.get("days_since_signup", 1)
        feedback_freq = feedback_count / max(days_active / 7, 1)  # Per week

        # Activity consistency (days with activity / total days)
        activity_days = user_data.get("activity_days", 0)
        activity_consistency = activity_days / max(days_active, 1)

        # Profile completion (0-1)
        profile_completion = user_data.get("profile_completion_percent", 0.0) / 100

        # Health check frequency
        health_checks = user_data.get("health_check_count", 0)
        health_freq = health_checks / max(days_active / 7, 1)  # Per week

        features = np.array(
            [
                days_since_login,
                login_freq,
                goal_completion,
                meal_adherence,
                feedback_freq,
                activity_consistency,
                profile_completion,
                health_freq,
            ],
            dtype=float,
        )

        feature_dict = {
            name: float(feat)
            for name, feat in zip(self.feature_names, features)
        }

        return features, feature_dict

    def predict(self, user_data: Dict) -> ChurnRiskScore:
        """Predict churn risk for a user.
        
        Args:
            user_data: Dictionary with user engagement metrics
            
        Returns:
            ChurnRiskScore with probability and recommendations
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        # Extract features
        features, feature_dict = self.extract_features(user_data)
        
        # Reshape for sklearn
        X = features.reshape(1, -1)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Get probability
        proba = self.model.predict_proba(X_scaled)[0]
        churn_prob = float(proba[1])  # Probability of churn (class 1)

        # Determine risk level
        if churn_prob < 0.25:
            risk_level = "low"
        elif churn_prob < 0.50:
            risk_level = "medium"
        elif churn_prob < 0.75:
            risk_level = "high"
        else:
            risk_level = "critical"

        # Calculate risk factor contributions
        risk_factors = self._calculate_risk_factors(features, feature_dict)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            feature_dict, risk_level
        )

        return ChurnRiskScore(
            user_id=user_data.get("user_id", "unknown"),
            churn_probability=churn_prob,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommended_actions=recommendations,
            prediction_timestamp=datetime.now(),
        )

    def _calculate_risk_factors(
        self, features: np.ndarray, feature_dict: Dict
    ) -> Dict[str, float]:
        """Calculate contribution of each feature to churn risk."""
        risk_factors = {}
        
        # Normalize by feature importance (coefficient magnitude)
        if hasattr(self.model, "coef_"):
            coefs = np.abs(self.model.coef_[0])
            total_coef = np.sum(coefs)
            
            for name, feat, coef in zip(self.feature_names, features, coefs):
                # Higher values = lower risk for most features
                # Normalize contribution
                contribution = (feat / (max(feat, 1) + 1)) * (coef / total_coef)
                risk_factors[name] = float(contribution)
        else:
            # Fallback: equal distribution
            equal_weight = 1.0 / len(self.feature_names)
            for name in self.feature_names:
                risk_factors[name] = equal_weight

        return risk_factors

    def _generate_recommendations(
        self, feature_dict: Dict, risk_level: str
    ) -> List[str]:
        """Generate actionable recommendations based on risk profile."""
        recommendations = []

        # Days since last login
        if feature_dict["days_since_last_login"] > 14:
            recommendations.append(
                "Send re-engagement email or push notification"
            )

        # Login frequency
        if feature_dict["login_frequency"] < 1.0:
            recommendations.append("Promote app features in email campaign")

        # Goals completion
        if feature_dict["goals_completion_rate"] < 0.3:
            recommendations.append(
                "Offer personalized goal guidance and coaching"
            )

        # Meal adherence
        if feature_dict["meal_adherence_rate"] < 0.4:
            recommendations.append(
                "Suggest easier meal plans or adjust nutrition targets"
            )

        # Feedback frequency
        if feature_dict["feedback_frequency"] < 0.5:
            recommendations.append(
                "Incentivize feedback with rewards or insights"
            )

        # Activity consistency
        if feature_dict["activity_consistency"] < 0.5:
            recommendations.append("Offer habit-building challenges and streaks")

        # Profile completion
        if feature_dict["profile_completion"] < 0.6:
            recommendations.append("Guide user through profile completion")

        # Health check frequency
        if feature_dict["health_check_frequency"] < 1.0:
            recommendations.append(
                "Send reminders about health tracking benefits"
            )

        # Risk level specific
        if risk_level == "critical":
            recommendations.insert(
                0, "Immediate intervention: Assign account manager"
            )
        elif risk_level == "high":
            recommendations.insert(
                0, "Schedule check-in call with user support team"
            )

        return recommendations[:5]  # Top 5 recommendations

    def batch_predict(self, users_data: List[Dict]) -> List[ChurnRiskScore]:
        """Predict churn risk for multiple users.
        
        Args:
            users_data: List of user data dictionaries
            
        Returns:
            List of ChurnRiskScore objects
        """
        results = []
        for user_data in users_data:
            try:
                result = self.predict(user_data)
                results.append(result)
            except Exception as e:
                print(f"Error predicting churn for user {user_data.get('user_id')}: {e}")
                continue

        return results

    def get_at_risk_cohort(
        self, users_data: List[Dict], threshold: float = 0.5
    ) -> List[ChurnRiskScore]:
        """Get list of users at risk of churn above threshold.
        
        Args:
            users_data: List of user data dictionaries
            threshold: Churn probability threshold (0.0-1.0)
            
        Returns:
            List of ChurnRiskScore for at-risk users
        """
        predictions = self.batch_predict(users_data)
        return [p for p in predictions if p.churn_probability >= threshold]

    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the churn prediction model.
        
        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target labels (0=no churn, 1=churn)
        """
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        self.model_timestamp = datetime.now()


# Global instance
churn_predictor = ChurnPredictor()
