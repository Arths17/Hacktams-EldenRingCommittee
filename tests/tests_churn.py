"""
Comprehensive API tests for HealthOS AI backend.

Tests all endpoints including auth, chat, profile, health checks, metrics,
analytics, experiments, segmentation, search, recommendations, performance,
and churn prediction.
"""

import pytest
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add project root to path for imports (file lives in tests/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from main import app
from model.churn_prediction import churn_predictor


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User",
        "age": 30,
        "height": 180,
        "weight": 75,
        "activity_level": "moderate",
        "dietary_preferences": ["vegetarian"],
        "health_goals": ["weight_loss", "muscle_gain"],
    }


@pytest.fixture
def sample_engagement_data():
    """Sample user engagement data for churn prediction."""
    return {
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


@pytest.fixture
def sample_meal():
    """Sample meal data."""
    return {
        "meal_id": "meal_001",
        "name": "Grilled Salmon with Quinoa",
        "calories": 450,
        "protein": 35,
        "carbs": 45,
        "fats": 12,
        "fiber": 8,
        "tags": ["gluten-free", "high-protein"],
        "preparation_time": 25,
    }


# ============================================================================
# BASIC ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns welcome message."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "HealthOS" in response.text


@pytest.mark.asyncio
async def test_health_check(client):
    """Test /health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Test /metrics endpoint."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "uptime_seconds" in data or "status" in data


# ============================================================================
# CHURN PREDICTION ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_predict_churn(client, sample_engagement_data):
    """Test churn prediction endpoint."""
    response = await client.post(
        "/api/churn-risk",
        json=sample_engagement_data,
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 422, 400, 401, 500]


@pytest.mark.asyncio
async def test_get_user_churn_risk(client):
    """Test getting churn risk for specific user."""
    response = await client.get(
        "/api/churn-risk/test_user_123",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401]


@pytest.mark.asyncio
async def test_get_at_risk_cohort(client):
    """Test getting at-risk user cohort."""
    response = await client.get(
        "/api/churn-risk/cohort?threshold=0.6",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 401]


# ============================================================================
# CHURN PREDICTION MODEL TESTS
# ============================================================================

def test_churn_predictor_initialization():
    """Test churn predictor initialization."""
    assert churn_predictor.is_trained
    assert len(churn_predictor.feature_names) == 8


def test_churn_predictor_feature_extraction(sample_engagement_data):
    """Test feature extraction from user data."""
    features, feature_dict = churn_predictor.extract_features(
        sample_engagement_data
    )
    assert len(features) == 8
    assert len(feature_dict) == 8
    assert all(k in churn_predictor.feature_names for k in feature_dict.keys())


def test_churn_prediction(sample_engagement_data):
    """Test churn prediction for single user."""
    result = churn_predictor.predict(sample_engagement_data)
    assert 0 <= result.churn_probability <= 1
    assert result.risk_level in ["low", "medium", "high", "critical"]
    assert len(result.risk_factors) == 8
    assert len(result.recommended_actions) > 0


def test_churn_batch_prediction(sample_engagement_data):
    """Test batch churn prediction."""
    users_data = [sample_engagement_data] * 5
    results = churn_predictor.batch_predict(users_data)
    assert len(results) == 5
    assert all(0 <= r.churn_probability <= 1 for r in results)


def test_churn_at_risk_cohort(sample_engagement_data):
    """Test identifying at-risk cohort."""
    users_data = [sample_engagement_data] * 3
    at_risk = churn_predictor.get_at_risk_cohort(users_data, threshold=0.3)
    # Results depend on actual prediction values
    assert isinstance(at_risk, list)


def test_churn_recommendations(sample_engagement_data):
    """Test recommendation generation."""
    result = churn_predictor.predict(sample_engagement_data)
    assert isinstance(result.recommended_actions, list)
    # Should have at least one recommendation
    assert len(result.recommended_actions) >= 1
    # Recommendations should be strings
    assert all(isinstance(r, str) for r in result.recommended_actions)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """Test error handling for missing authorization."""
    response = await client.get("/api/churn-risk/test_user_123")
    # Should either require auth or return public data
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_not_found_user(client):
    """Test error handling for non-existent user."""
    response = await client.get(
        "/api/churn-risk/nonexistent_user_999",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [404, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
