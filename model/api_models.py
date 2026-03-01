"""
Request and response models for HealthOS API with validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


# ══════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════

class LoginRequest(BaseModel):
    """Login endpoint request."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    
    class Config:
        example = {"username": "alice", "password": "securepass123"}


class SignupRequest(BaseModel):
    """Signup endpoint request."""
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str = Field(..., min_length=8, max_length=128)
    
    @validator("password_confirm")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v
    
    class Config:
        example = {
            "username": "alice",
            "password": "securepass123",
            "password_confirm": "securepass123",
        }


class ProfileUpdateRequest(BaseModel):
    """Profile update endpoint request."""
    age: Optional[int] = Field(None, ge=13, le=120)
    weight_kg: Optional[float] = Field(None, gt=30, lt=200)
    height_cm: Optional[float] = Field(None, gt=100, lt=250)
    activity_level: Optional[str] = Field(None, pattern="^(sedentary|light|moderate|active|very_active)$")
    dietary_restrictions: Optional[list[str]] = Field(None, max_items=10)
    health_goals: Optional[list[str]] = Field(None, max_items=10)
    medications: Optional[list[str]] = Field(None, max_items=20)
    allergies: Optional[list[str]] = Field(None, max_items=10)
    
    class Config:
        example = {
            "age": 20,
            "weight_kg": 75.0,
            "height_cm": 180.0,
            "activity_level": "moderate",
            "dietary_restrictions": ["vegetarian"],
            "health_goals": ["improve energy", "better sleep"],
            "medications": [],
            "allergies": ["peanuts"],
        }


class ChatRequest(BaseModel):
    """Chat endpoint request."""
    message: str = Field(..., min_length=1, max_length=2000)
    include_protocols: Optional[bool] = Field(True)
    include_meals: Optional[bool] = Field(True)
    
    class Config:
        example = {
            "message": "I've been feeling tired lately. What should I do?",
            "include_protocols": True,
            "include_meals": True,
        }


class FeedbackRequest(BaseModel):
    """Feedback endpoint request."""
    message: str = Field(..., min_length=1, max_length=500)
    
    class Config:
        example = {"message": "My energy improved a lot! energy: +2"}


# ══════════════════════════════════════════════
# RESPONSE MODELS
# ══════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        example = {
            "success": False,
            "error": "Username already taken",
            "error_code": "CONFLICT",
            "details": {"field": "username"},
        }


class AuthResponse(BaseModel):
    """Authentication response (login/signup)."""
    success: bool = True
    token: str
    username: str
    user_id: Optional[str] = None
    
    class Config:
        example = {
            "success": True,
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "username": "alice",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
        }


class UserResponse(BaseModel):
    """User profile response."""
    success: bool = True
    username: str
    user_id: Optional[str] = None
    profile: Dict[str, Any]
    created_at: Optional[datetime] = None
    
    class Config:
        example = {
            "success": True,
            "username": "alice",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "profile": {
                "age": 20,
                "weight_kg": 75.0,
                "activity_level": "moderate",
                "health_goals": ["improve energy"],
            },
        }


class ProtocolInfo(BaseModel):
    """Information about a health protocol."""
    name: str
    priority_score: float
    severity: float
    alignment: float


class ChatResponse(BaseModel):
    """Chat streaming response (non-streaming wrapper for documentation)."""
    success: bool = True
    message: str
    protocols: Optional[list[ProtocolInfo]] = None
    meals: Optional[list[str]] = None
    timestamp: datetime
    
    class Config:
        example = {
            "success": True,
            "message": "Based on your tiredness, I recommend...",
            "protocols": [
                {"name": "sleep_protocol", "priority_score": 0.9, "severity": 0.8, "alignment": 0.95},
                {"name": "energy_protocol", "priority_score": 0.85, "severity": 0.7, "alignment": 0.9},
            ],
            "meals": ["Salmon with quinoa", "Greek yogurt with berries"],
            "timestamp": "2026-03-01T10:30:00Z",
        }


class HealthCheckResponse(BaseModel):
    """Health check response."""
    success: bool = True
    status: str = "healthy"
    timestamp: datetime
    services: Dict[str, str]
    
    class Config:
        example = {
            "success": True,
            "status": "healthy",
            "timestamp": "2026-03-01T10:30:00Z",
            "services": {
                "ollama": "healthy",
                "supabase": "healthy",
                "nutrition_db": "healthy",
            },
        }


class FeedbackResponse(BaseModel):
    """Feedback processing response."""
    success: bool = True
    feedback_extracted: Dict[str, float]
    weights_updated: Dict[str, float]
    affected_protocols: list[str]
    
    class Config:
        example = {
            "success": True,
            "feedback_extracted": {"energy": 2.0, "focus": 1.0},
            "weights_updated": {
                "energy_protocol": 0.825,
                "b_complex_protocol": 0.7125,
                "cognitive_protocol": 0.736,
            },
            "affected_protocols": ["energy_protocol", "b_complex_protocol", "cognitive_protocol"],
        }
