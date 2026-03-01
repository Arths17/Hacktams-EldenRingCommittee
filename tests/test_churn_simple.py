"""Standalone churn prediction tests (no main.py import)."""

import sys
import os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "model"))

from datetime import datetime, timedelta
from churn_prediction import churn_predictor


def test_churn_predictor_initialization():
    """Test churn predictor initialization."""
    assert churn_predictor.is_trained
    assert len(churn_predictor.feature_names) == 8
    print("✓ test_churn_predictor_initialization passed")


def test_churn_predictor_feature_extraction():
    """Test feature extraction from user data."""
    sample_data = {
        "user_id": "test_user_123",
        "last_login": (datetime.now() - timedelta(days=5)).isoformat(),
        "login_history": [
            (datetime.now() - timedelta(days=i)).isoformat()
            for i in range(20)
        ],
        "total_goals": 5,
        "completed_goals": 3,
        "total_meals": 30,
        "adhered_meals": 24,
        "feedback_count": 8,
        "days_since_signup": 90,
        "activity_days": 60,
        "profile_completion_percent": 85,
        "health_check_count": 15,
    }
    
    features, feature_dict = churn_predictor.extract_features(sample_data)
    assert len(features) == 8
    assert len(feature_dict) == 8
    assert all(k in churn_predictor.feature_names for k in feature_dict.keys())
    print("✓ test_churn_predictor_feature_extraction passed")


def test_churn_prediction():
    """Test churn prediction for single user."""
    sample_data = {
        "user_id": "test_user_123",
        "last_login": (datetime.now() - timedelta(days=5)).isoformat(),
        "login_history": [
            (datetime.now() - timedelta(days=i)).isoformat()
            for i in range(20)
        ],
        "total_goals": 5,
        "completed_goals": 3,
        "total_meals": 30,
        "adhered_meals": 24,
        "feedback_count": 8,
        "days_since_signup": 90,
        "activity_days": 60,
        "profile_completion_percent": 85,
        "health_check_count": 15,
    }
    
    result = churn_predictor.predict(sample_data)
    assert 0 <= result.churn_probability <= 1
    assert result.risk_level in ["low", "medium", "high", "critical"]
    assert len(result.risk_factors) == 8
    assert len(result.recommended_actions) > 0
    print("✓ test_churn_prediction passed")
    print(f"  - Churn probability: {result.churn_probability:.4f}")
    print(f"  - Risk level: {result.risk_level}")
    print(f"  - Recommendations: {result.recommended_actions}")


def test_churn_batch_prediction():
    """Test batch churn prediction."""
    sample_data = {
        "user_id": "test_user_123",
        "last_login": (datetime.now() - timedelta(days=5)).isoformat(),
        "login_history": [
            (datetime.now() - timedelta(days=i)).isoformat()
            for i in range(20)
        ],
        "total_goals": 5,
        "completed_goals": 3,
        "total_meals": 30,
        "adhered_meals": 24,
        "feedback_count": 8,
        "days_since_signup": 90,
        "activity_days": 60,
        "profile_completion_percent": 85,
        "health_check_count": 15,
    }
    
    users_data = [sample_data] * 5
    results = churn_predictor.batch_predict(users_data)
    assert len(results) == 5
    assert all(0 <= r.churn_probability <= 1 for r in results)
    print("✓ test_churn_batch_prediction passed")
    print(f"  - Processed {len(results)} users")


if __name__ == "__main__":
    test_churn_predictor_initialization()
    test_churn_predictor_feature_extraction()
    test_churn_prediction()
    test_churn_batch_prediction()
    print("\n✓✓✓ All tests passed! ✓✓✓")
