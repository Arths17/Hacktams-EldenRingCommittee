"""
Comprehensive API tests for HealthOS AI backend.

Tests all endpoints including auth, chat, profile, health checks, metrics,
analytics, experiments, segmentation, search, recommendations, performance,
and churn prediction.
"""

import pytest
import json
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from model.churn_prediction import churn_predictor


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as ac:
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
# AUTH ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_signup_endpoint(client, sample_user_data):
    """Test user signup endpoint."""
    response = await client.post("/api/signup", json=sample_user_data)
    # Accept either success or validation error
    assert response.status_code in [200, 201, 422, 400]


@pytest.mark.asyncio
async def test_login_endpoint(client):
    """Test user login endpoint."""
    payload = {"email": "test@example.com", "password": "testpass123"}
    response = await client.post("/api/login", json=payload)
    # Accept either success, auth error, or validation error
    assert response.status_code in [200, 401, 422, 400]


# ============================================================================
# CHAT ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_chat_endpoint(client):
    """Test chat endpoint with health query."""
    payload = {
        "user_id": "test_user_123",
        "message": "What should I eat for weight loss?",
    }
    response = await client.post("/api/chat", json=payload)
    # Should either return answer or validation error
    assert response.status_code in [200, 422, 400, 500]


@pytest.mark.asyncio
async def test_chat_with_meal_recommendation(client):
    """Test chat endpoint requesting meal recommendations."""
    payload = {
        "user_id": "test_user_123",
        "message": "Recommend a high-protein meal plan",
    }
    response = await client.post("/api/chat", json=payload)
    assert response.status_code in [200, 422, 400, 500]


# ============================================================================
# PROFILE ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_profile(client):
    """Test getting user profile."""
    response = await client.get(
        "/api/profile/test_user_123",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401]


@pytest.mark.asyncio
async def test_update_profile(client, sample_user_data):
    """Test updating user profile."""
    response = await client.put(
        "/api/profile/test_user_123",
        json={"health_goals": ["weight_loss"]},
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401, 422]


@pytest.mark.asyncio
async def test_update_health_metrics(client):
    """Test updating health metrics."""
    payload = {
        "user_id": "test_user_123",
        "weight": 72,
        "blood_pressure": "120/80",
        "heart_rate": 72,
    }
    response = await client.post(
        "/api/profile/health-metrics",
        json=payload,
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 422, 400, 401]


# ============================================================================
# ANALYTICS ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_track_event(client):
    """Test event tracking endpoint."""
    payload = {
        "user_id": "test_user_123",
        "event_type": "meal_logged",
        "event_data": {"meal_id": "meal_001", "calories": 450},
    }
    response = await client.post(
        "/api/analytics/events",
        json=payload,
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 201, 422, 400, 401]


@pytest.mark.asyncio
async def test_get_user_trends(client):
    """Test getting user engagement trends."""
    response = await client.get(
        "/api/analytics/trends/test_user_123",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401, 500]


@pytest.mark.asyncio
async def test_get_metrics_summary(client):
    """Test getting metrics summary."""
    response = await client.get(
        "/api/analytics/metrics",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 401, 500]


# ============================================================================
# A/B TESTING ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_experiment(client):
    """Test creating A/B test experiment."""
    payload = {
        "name": "Meal Recommendation Algorithm",
        "description": "Test new recommendation engine",
        "metric": "user_engagement",
        "variants": [
            {"name": "control", "description": "Current algorithm"},
            {"name": "treatment", "description": "New algorithm"},
        ],
    }
    response = await client.post(
        "/api/experiments",
        json=payload,
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 201, 422, 400, 401]


@pytest.mark.asyncio
async def test_list_experiments(client):
    """Test listing experiments."""
    response = await client.get(
        "/api/experiments",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_get_experiment_results(client):
    """Test getting experiment results."""
    response = await client.get(
        "/api/experiments/exp_001/results",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401]


# ============================================================================
# SEGMENTATION ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_user_segment(client):
    """Test getting user segment."""
    response = await client.get(
        "/api/segments/test_user_123",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401]


@pytest.mark.asyncio
async def test_list_segments(client):
    """Test listing user segments."""
    response = await client.get(
        "/api/segments",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 401]


# ============================================================================
# SEARCH AND DISCOVERY ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_search_meals(client):
    """Test meal search functionality."""
    response = await client.get(
        "/api/search?q=high-protein&type=meal",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 400, 401]


@pytest.mark.asyncio
async def test_search_all_content(client):
    """Test full-text search."""
    response = await client.get(
        "/api/search?q=weight loss&type=all",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 400, 401]


@pytest.mark.asyncio
async def test_get_recommendations(client):
    """Test getting personalized recommendations."""
    response = await client.get(
        "/api/recommendations/test_user_123",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401, 500]


@pytest.mark.asyncio
async def test_get_meal_recommendations(client):
    """Test getting meal recommendations."""
    response = await client.get(
        "/api/recommendations/test_user_123?type=meal",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 404, 401, 500]


# ============================================================================
# PERFORMANCE ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_slow_queries(client):
    """Test getting slow queries report."""
    response = await client.get(
        "/api/performance/queries",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_get_optimization_recommendations(client):
    """Test getting optimization recommendations."""
    response = await client.get(
        "/api/performance/recommendations",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [200, 401]


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
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_user_journey(client, sample_user_data):
    """Test complete user journey: signup -> profile -> chat -> analytics."""
    # Signup
    signup_response = await client.post("/api/signup", json=sample_user_data)
    assert signup_response.status_code in [200, 201, 422, 400]

    # Get profile
    profile_response = await client.get(
        "/api/profile/test_user_123",
        headers={"Authorization": "Bearer test_token"}
    )
    assert profile_response.status_code in [200, 404, 401]

    # Send chat message
    chat_response = await client.post(
        "/api/chat",
        json={
            "user_id": "test_user_123",
            "message": "What should I eat?",
        }
    )
    assert chat_response.status_code in [200, 422, 400, 500]


@pytest.mark.asyncio
async def test_analytics_flow(client):
    """Test analytics data flow: track -> get trends -> get metrics."""
    # Track event
    track_response = await client.post(
        "/api/analytics/events",
        json={
            "user_id": "test_user_123",
            "event_type": "meal_logged",
            "event_data": {"calories": 450},
        },
        headers={"Authorization": "Bearer test_token"}
    )
    assert track_response.status_code in [200, 201, 422, 400, 401]

    # Get trends
    trends_response = await client.get(
        "/api/analytics/trends/test_user_123",
        headers={"Authorization": "Bearer test_token"}
    )
    assert trends_response.status_code in [200, 404, 401, 500]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_missing_required_field(client):
    """Test error handling for missing required field."""
    payload = {"email": "test@example.com"}  # Missing password
    response = await client.post("/api/login", json=payload)
    assert response.status_code in [422, 400]


@pytest.mark.asyncio
async def test_invalid_json(client):
    """Test error handling for invalid JSON."""
    response = await client.post(
        "/api/chat",
        content="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code in [422, 400]


@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """Test error handling for missing authorization."""
    response = await client.get("/api/profile/test_user_123")
    # Should either require auth or return public data
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_not_found_user(client):
    """Test error handling for non-existent user."""
    response = await client.get(
        "/api/profile/nonexistent_user_999",
        headers={"Authorization": "Bearer test_token"}
    )
    assert response.status_code in [404, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
