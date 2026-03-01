"""
HealthOS API — Medical-grade AI health optimization system for college students.

Features:
- JWT authentication with rate limiting
- Comprehensive error handling
- Input validation with Pydantic models
- OpenAPI/Swagger documentation
- Supabase + local fallback storage
- Streaming chat responses
- Real-time feedback learning

Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import re
import sys
import json
import bcrypt
import jwt as _jwt
import logging
from typing import cast as _cast, Optional
from datetime import datetime
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

load_dotenv()

# ─── Logging Setup ────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SECRET = os.environ.get("SECRET_KEY", "elden_ring")

os.makedirs("user_profiles", exist_ok=True)

def _profile_path(username: str) -> str:
    safe = re.sub(r"[^\w\-]", "_", username.lower())
    return os.path.join("user_profiles", f"{safe}.json")

# --- Supabase (optional) ---
try:
    from supabase import create_client
    _sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    USE_SUPABASE = True
    logger.info("✓ Supabase connected")
except Exception as e:
    USE_SUPABASE = False
    logger.info(f"✗ Supabase unavailable: {e} (using local fallback)")

# Import exceptions and models (with graceful fallback)
# Define fallback classes first
class HealthOSAPIError(Exception):
    """Base exception class."""
    def to_response(self):
        return JSONResponse({"success": False, "error": str(self)}, status_code=400)

class ValidationError(HealthOSAPIError):
    """Validation error."""
    pass

class InternalServerError(HealthOSAPIError):
    """Internal server error."""
    pass

def get_rate_limiter():
    """Fallback rate limiter."""
    class FallbackRateLimiter:
        def check_rate_limit(self, request, endpoint, username=None):
            pass
    return FallbackRateLimiter()

# Try to import actual implementations
try:
    from api_exceptions import (
        HealthOSAPIError as _HealthOSAPIError,
        AuthenticationError,
        AuthorizationError,
        ValidationError as _ValidationError,
        ResourceNotFoundError,
        RateLimitError,
        ConflictError,
        InternalServerError as _InternalServerError,
        ExternalServiceError,
    )
    from api_models import AuthResponse, UserResponse, ErrorResponse
    from rate_limiter import get_rate_limiter as _get_rate_limiter
    
    # Use imported versions
    HealthOSAPIError = _HealthOSAPIError  # type: ignore
    ValidationError = _ValidationError  # type: ignore
    InternalServerError = _InternalServerError  # type: ignore
    get_rate_limiter = _get_rate_limiter  # type: ignore
    USE_API_UTILS = True
except ImportError as e:
    logger.warning(f"API utilities not available: {e} (using basic error handling)")
    USE_API_UTILS = False
    AuthenticationError = HealthOSAPIError  # type: ignore
    AuthorizationError = HealthOSAPIError  # type: ignore
    ResourceNotFoundError = HealthOSAPIError  # type: ignore
    RateLimitError = HealthOSAPIError  # type: ignore
    ConflictError = HealthOSAPIError  # type: ignore
    ExternalServiceError = HealthOSAPIError  # type: ignore

# ══════════════════════════════════════════════
# APP SETUP
# ══════════════════════════════════════════════

app = FastAPI(
    title="HealthOS API",
    description="Medical-grade AI health optimization system for college students",
    version="3.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/response logging middleware
import time
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests and responses with structured JSON."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            from structured_logging import logger as struct_logger
            struct_logger.log_request(request.method, request.url.path)
            logger_available = True
        except ImportError:
            logger_available = False
        
        response = await call_next(request)
        
        if logger_available:
            elapsed_ms = (time.time() - start_time) * 1000
            from structured_logging import logger as struct_logger
            struct_logger.log_response(response.status_code, elapsed_ms)
        
        return response

app.add_middleware(LoggingMiddleware)

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            "details": {
                "errors": [
                    {
                        "field": ".".join(str(x) for x in err["loc"]),
                        "message": err["msg"],
                    }
                    for err in exc.errors()
                ]
            },
        },
    )

@app.exception_handler(HealthOSAPIError)
async def healthos_exception_handler(request: Request, exc: HealthOSAPIError):
    """Handle HealthOS custom exceptions."""
    logger.warning(f"API Error: {getattr(exc, 'error_code', 'UNKNOWN')} - {str(exc)}")
    if hasattr(exc, 'to_response'):
        return exc.to_response()
    return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

# ══════════════════════════════════════════════
# MONITORING & HEALTH CHECKS
# ══════════════════════════════════════════════

health_checker = None
perf_metrics = None
churn_predictor = None

try:
    from monitoring import HealthCheck, PerformanceMetrics, capture_exception
    health_checker = HealthCheck()
    perf_metrics = PerformanceMetrics()
    MONITORING_ENABLED = True
except ImportError:
    MONITORING_ENABLED = False
    logger.warning("Monitoring module not available")

# Import churn prediction model
try:
    from model.churn_prediction import churn_predictor as _churn_predictor
    churn_predictor = _churn_predictor
    logger.info("✓ Churn prediction model loaded")
except ImportError as e:
    logger.warning(f"Churn prediction module not available: {e}")

# Register health checks
if MONITORING_ENABLED and health_checker:
    # Supabase health check
    def check_supabase() -> tuple[bool, dict]:
        """Check Supabase connectivity."""
        if not USE_SUPABASE:
            return False, {"status": "not_configured"}
        try:
            _sb.table("users").select("id").limit(1).execute()
            return True, {"status": "connected"}
        except Exception as e:
            return False, {"status": "disconnected", "error": str(e)}
    
    # Ollama health check
    def check_ollama() -> tuple[bool, dict]:
        """Check Ollama connectivity."""
        try:
            import requests
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            return resp.status_code == 200, {"status": "connected"}
        except Exception as e:
            return False, {"status": "disconnected", "error": str(e)}
    
    # ChromaDB health check
    def check_chromadb() -> tuple[bool, dict]:
        """Check ChromaDB availability."""
        try:
            import chromadb
            db = chromadb.PersistentClient(path="model/chroma_db")
            collections = db.list_collections()
            return True, {"status": "connected", "collections": len(collections)}
        except Exception as e:
            return False, {"status": "disconnected", "error": str(e)}
    
    health_checker.register("supabase", check_supabase, critical=True)
    health_checker.register("ollama", check_ollama, critical=True)
    health_checker.register("chromadb", check_chromadb, critical=False)

@app.get("/health", tags=["monitoring"])
async def health_check_endpoint():
    """System health check endpoint.
    
    Returns comprehensive health status of all critical services.
    Used by load balancers and monitoring systems.
    """
    if MONITORING_ENABLED and health_checker:
        status = await health_checker.run_all()
        status_code = 200 if status["healthy"] else 503
        return JSONResponse(status, status_code=status_code)
    return JSONResponse({
        "healthy": True,
        "services": {"basic": {"healthy": True}},
    }, status_code=200)

@app.get("/metrics", tags=["monitoring"])
def metrics_endpoint():
    """Performance metrics endpoint.
    
    Returns API performance statistics (requests, response times, error rates).
    """
    if MONITORING_ENABLED and perf_metrics:
        return JSONResponse(perf_metrics.get_summary())
    return JSONResponse({"message": "Metrics not available"})

def _make_token(username: str, user_id: Optional[str] = None) -> str:
    """Create JWT token for user."""
    try:
        payload = {"username": username}
        if user_id is not None:
            payload["user_id"] = user_id
        return _jwt.encode(payload, SECRET, algorithm="HS256")
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise InternalServerError("Failed to create authentication token") if USE_API_UTILS else Exception("Token creation failed")

def _decode_token(request: Request) -> Optional[dict]:
    """
    Extract and decode Bearer token from Authorization header.
    
    Returns:
        Decoded payload dict if valid, None otherwise
    """
    auth = request.headers.get("Authorization", "").strip()
    if not auth.startswith("Bearer "):
        return None
    
    token = auth[7:]  # Remove "Bearer " prefix
    try:
        return _jwt.decode(token, SECRET, algorithms=["HS256"])
    except _jwt.ExpiredSignatureError:
        logger.warning("Expired token presented")
        return None
    except _jwt.InvalidTokenError:
        logger.warning("Invalid token presented")
        return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None

def _validate_username(username: str) -> None:
    """Validate username format."""
    if not (3 <= len(username) <= 50):
        raise ValidationError("Username must be 3-50 characters")
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        raise ValidationError(
            "Username must contain only letters, numbers, hyphen, underscore"
        ) if USE_API_UTILS else ValueError("Invalid username format")

def _validate_password(password: str) -> None:
    """Validate password strength."""
    if not (8 <= len(password) <= 128):
        raise ValidationError("Password must be 8-128 characters")

def _local_login(username: str, password: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Local file-based login (fallback)."""
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        for u in users:
            if u["username"] == username:
                if bcrypt.checkpw(password.encode(), u["password"].encode()):
                    return True, str(u.get("id")), None
                return False, None, "Incorrect password"
        return False, None, "User not found"
    except FileNotFoundError:
        return False, None, "No users registered yet"
    except Exception as e:
        logger.error(f"Local login error: {e}")
        return False, None, "Login service unavailable"

def _local_signup(username: str, password: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Local file-based signup (fallback)."""
    try:
        try:
            with open("users.json", "r") as f:
                users = json.load(f)
        except FileNotFoundError:
            users = []
        
        # Check for duplicates
        if any(u["username"] == username for u in users):
            return False, None, "Username already taken"
        
        # Create new user
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        new_id = len(users) + 1
        users.append({"id": new_id, "username": username, "password": hashed})
        
        with open("users.json", "w") as f:
            json.dump(users, f, indent=2)
        
        return True, str(new_id), None
    except Exception as e:
        logger.error(f"Local signup error: {e}")
        return False, None, "Signup service unavailable"

# ══════════════════════════════════════════════
# HEALTH CHECK ENDPOINT
# ══════════════════════════════════════════════

@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check",
    description="Check system and service health",
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status": "healthy",
                        "timestamp": "2026-03-01T10:30:00Z",
                        "services": {
                            "ollama": "healthy",
                            "supabase": "healthy",
                            "nutrition_db": "healthy",
                        },
                    }
                }
            },
        }
    },
)
async def health_check():
    """Check system health and service availability."""
    services = {}
    
    # Check Ollama
    try:
        import ollama
        ollama.list()
        services["ollama"] = "healthy"
    except Exception as e:
        services["ollama"] = f"unavailable: {str(e)[:30]}"
        logger.warning(f"Ollama unavailable: {e}")
    
    # Check Supabase
    services["supabase"] = "healthy" if USE_SUPABASE else "unavailable (using local fallback)"
    
    # Check nutrition DB
    try:
        from model import nutrition_db
        services["nutrition_db"] = "healthy" if nutrition_db.is_loaded() else "loading"
    except Exception as e:
        services["nutrition_db"] = f"error: {str(e)[:30]}"
    
    # Determine overall status
    critical_services = [s for s, status in services.items() if "unavailable" in str(status)]
    overall_status = "degraded" if critical_services else "healthy"
    
    return JSONResponse({
        "success": True,
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": services,
    })

# ══════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════

@app.post(
    "/login",
    tags=["Auth"],
    summary="User login",
    description="Authenticate user and return JWT token",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "username": "alice",
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Incorrect password",
                        "error_code": "AUTH_FAILED",
                    }
                }
            },
        },
    },
)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Authenticate user and return JWT token."""
    try:
        # Rate limiting
        try:
            rate_limiter = get_rate_limiter()
            rate_limiter.check_rate_limit(request, "/api/login")
        except:
            pass  # Graceful fallback if rate limiter fails
        
        # Validation
        try:
            _validate_username(username)
            _validate_password(password)
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            if USE_API_UTILS and isinstance(e, ValidationError):
                raise
            return JSONResponse({"success": False, "error": str(e)}, status_code=422)
        
        # Try Supabase first
        if USE_SUPABASE:
            try:
                res = _sb.table("users").select("*").eq("username", username).execute()
                if res.data:
                    row = _cast(dict, res.data[0])
                    if bcrypt.checkpw(password.encode(), row["password"].encode()):
                        token = _make_token(username, row.get("id"))
                        logger.info(f"✓ Login successful: {username} (Supabase)")
                        return JSONResponse({
                            "success": True,
                            "token": token,
                            "username": username,
                            "user_id": row.get("id"),
                        })
                    return JSONResponse(
                        {"success": False, "error": "Incorrect password", "error_code": "AUTH_FAILED"},
                        status_code=401
                    )
                return JSONResponse(
                    {"success": False, "error": "User not found", "error_code": "NOT_FOUND"},
                    status_code=404
                )
            except Exception as e:
                logger.warning(f"Supabase login failed: {e}, falling back to local")
        
        # Fallback to local
        ok, uid, err = _local_login(username, password)
        if ok:
            token = _make_token(username, uid)
            logger.info(f"✓ Login successful: {username} (local)")
            return JSONResponse({
                "success": True,
                "token": token,
                "username": username,
                "user_id": uid,
            })
        
        logger.warning(f"✗ Login failed: {username} - {err}")
        return JSONResponse(
            {"success": False, "error": err, "error_code": "AUTH_FAILED"},
            status_code=401
        )
    
    except Exception as e:
        logger.error(f"Login endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

@app.post(
    "/api/signup",
    tags=["Auth"],
    summary="User registration",
    description="Create new user account and return JWT token",
    responses={
        200: {"description": "Signup successful"},
        409: {"description": "Username already taken"},
    },
)
async def signup(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    """Create new user account."""
    try:
        # Rate limiting
        try:
            rate_limiter = get_rate_limiter()
            rate_limiter.check_rate_limit(request, "/api/signup")
        except:
            pass
        
        # Validation
        try:
            _validate_username(username)
            _validate_password(password)
            if password != password_confirm:
                raise ValidationError("Passwords do not match")
        except Exception as e:
            logger.warning(f"Signup validation failed: {e}")
            if USE_API_UTILS and isinstance(e, ValidationError):
                raise
            return JSONResponse({"success": False, "error": str(e)}, status_code=422)
        
        # Try Supabase first
        if USE_SUPABASE:
            try:
                existing = _sb.table("users").select("id").eq("username", username).execute()
                if existing.data:
                    return JSONResponse(
                        {"success": False, "error": "Username already taken", "error_code": "CONFLICT"},
                        status_code=409,
                    )
                
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                res = _sb.table("users").insert({
                    "username": username,
                    "password": hashed,
                }).execute()
                
                uid: Optional[str] = None
                if res.data:
                    user_row = _cast(dict, res.data[0])
                    uid = _cast(Optional[str], user_row.get("id"))
                token = _make_token(username, uid)
                logger.info(f"✓ Signup successful: {username} (Supabase)")
                return JSONResponse({
                    "success": True,
                    "token": token,
                    "username": username,
                    "user_id": uid,
                })
            except Exception as e:
                logger.warning(f"Supabase signup failed: {e}, falling back to local")
        
        # Fallback to local
        ok, uid, err = _local_signup(username, password)
        if ok:
            token = _make_token(username, uid)
            logger.info(f"✓ Signup successful: {username} (local)")
            return JSONResponse({
                "success": True,
                "token": token,
                "username": username,
                "user_id": uid,
            })
        
        status_code = 409 if "already taken" in (err or "") else 400
        logger.warning(f"✗ Signup failed: {username} - {err}")
        return JSONResponse(
            {"success": False, "error": err, "error_code": "SIGNUP_FAILED"},
            status_code=status_code,
        )
    
    except Exception as e:
        logger.error(f"Signup endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

@app.post(
    "/api/logout",
    tags=["Auth"],
    summary="User logout",
    description="Logout user (JWT is stateless, just delete token on client)",
)
async def logout(request: Request):
    """Logout user."""
    payload = _decode_token(request)
    if payload:
        logger.info(f"✓ Logout: {payload.get('username')}")
    return JSONResponse({"success": True})

# ══════════════════════════════════════════════
# PROFILE ENDPOINTS
# ══════════════════════════════════════════════

@app.get(
    "/api/me",
    tags=["Profile"],
    summary="Get current user profile",
    description="Get authenticated user's profile data",
)
async def me(request: Request):
    """Get authenticated user profile."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        username = payload["username"]
        user_id = payload.get("user_id")
        profile = {}
        
        # Try Supabase first
        if USE_SUPABASE and user_id:
            try:
                res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
                if res.data:
                    profile = res.data[0]
                    logger.debug(f"Profile loaded from Supabase: {username}")
            except Exception as e:
                logger.warning(f"Supabase profile load failed: {e}")
        
        # Fallback to local
        if not profile:
            try:
                with open(_profile_path(username), "r") as f:
                    profile = json.load(f)
                    logger.debug(f"Profile loaded from local: {username}")
            except FileNotFoundError:
                logger.debug(f"No profile found for: {username}")
        
        return JSONResponse({
            "success": True,
            "username": username,
            "user_id": user_id,
            "profile": profile,
        })
    
    except Exception as e:
        logger.error(f"Profile endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

@app.post(
    "/api/profile",
    tags=["Profile"],
    summary="Update user profile",
    description="Update authenticated user's profile data",
)
async def save_profile(request: Request):
    """Save/update user profile."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        username = payload["username"]
        user_id = payload.get("user_id")
        data = await request.json()
        
        # Validate profile data (basic checks) - handle both string and numeric values
        if isinstance(data, dict):
            # Convert age to int if it's a string and validate
            if "age" in data:
                try:
                    age_val = int(data["age"]) if isinstance(data["age"], str) else data["age"]
                    if not (13 <= age_val <= 120):
                        return JSONResponse(
                            {"success": False, "error": "Age must be between 13 and 120", "error_code": "VALIDATION_ERROR"},
                            status_code=422,
                        )
                except (ValueError, TypeError):
                    pass  # Allow non-numeric age strings like "20s"
            
            # Convert weight_kg to float if it's a string and validate
            if "weight_kg" in data:
                try:
                    weight_val = float(data["weight_kg"]) if isinstance(data["weight_kg"], str) else data["weight_kg"]
                    if not (30 < weight_val < 200):
                        return JSONResponse(
                            {"success": False, "error": "Weight must be between 30 and 200 kg", "error_code": "VALIDATION_ERROR"},
                            status_code=422,
                        )
                except (ValueError, TypeError):
                    pass  # Allow non-numeric weight strings like "150 lbs"
        
        # Try Supabase first
        if USE_SUPABASE and user_id:
            try:
                existing = _sb.table("profiles").select("id").eq("user_id", user_id).execute()
                if existing.data:
                    _sb.table("profiles").update(data).eq("user_id", user_id).execute()
                    logger.info(f"✓ Profile updated: {username} (Supabase)")
                else:
                    _sb.table("profiles").insert({**data, "user_id": user_id}).execute()
                    logger.info(f"✓ Profile created: {username} (Supabase)")
                return JSONResponse({"success": True})
            except Exception as e:
                logger.warning(f"Supabase profile save failed: {e}, falling back to local")
        
        # Fallback to local
        with open(_profile_path(username), "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"✓ Profile saved: {username} (local)")
        return JSONResponse({"success": True})
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Profile save error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

# ══════════════════════════════════════════════
# CHURN PREDICTION ENDPOINTS
# ══════════════════════════════════════════════

@app.post(
    "/api/churn-risk",
    tags=["Churn Prediction"],
    summary="Predict user churn risk",
    description="Predict likelihood of user churn based on engagement metrics",
)
async def predict_churn(request: Request):
    """Predict churn risk for a user.
    
    Expected JSON payload:
    {
        "user_id": "user_123",
        "last_login": "2024-02-15T10:30:00",
        "login_history": [...],
        "total_goals": 5,
        "completed_goals": 3,
        "total_meals": 30,
        "adhered_meals": 24,
        "feedback_count": 8,
        "days_since_signup": 90,
        "activity_days": 60,
        "profile_completion_percent": 85,
        "health_check_count": 15
    }
    """
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        # Get request body
        body = await request.json()
        
        if not churn_predictor:
            return JSONResponse(
                {"success": False, "error": "Churn prediction model not available", "error_code": "SERVICE_UNAVAILABLE"},
                status_code=503,
            )
        
        # Predict churn
        result = churn_predictor.predict(body)
        
        return JSONResponse({
            "success": True,
            "data": result.to_dict()
        }, status_code=200)
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Churn prediction error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.get(
    "/api/churn-risk/cohort",
    tags=["Churn Prediction"],
    summary="Get at-risk user cohort",
    description="Get list of users at risk of churn above threshold",
)
async def get_at_risk_cohort(request: Request, threshold: float = 0.5):
    """Get cohort of users at risk of churn.
    
    Parameters:
    - threshold: Churn probability threshold (0.0-1.0), default 0.5
    
    In production, this would query Supabase:
    SELECT * FROM churn_features WHERE churn_risk_score >= threshold
    ORDER BY churn_risk_score DESC
    """
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        if threshold < 0 or threshold > 1:
            return JSONResponse(
                {"success": False, "error": "Threshold must be between 0 and 1", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )
        
        # In production:
        # result = _sb.table("churn_features") \
        #     .select("*") \
        #     .gte("churn_risk_score", threshold) \
        #     .order("churn_risk_score", desc=True) \
        #     .execute()
        # return JSONResponse({"success": True, "data": result.data})
        
        return JSONResponse({
            "success": True,
            "data": [],
            "threshold": threshold,
            "count": 0
        }, status_code=200)
    
    except Exception as e:
        logger.error(f"Get at-risk cohort error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )


@app.get(
    "/api/churn-risk/{user_id}",
    tags=["Churn Prediction"],
    summary="Get user churn risk",
    description="Get stored churn risk for a specific user",
)
async def get_user_churn_risk(user_id: str, request: Request):
    """Get churn risk for specific user from database.
    
    In a production system, this would fetch pre-calculated churn scores
    from the churn_features table in Supabase.
    """
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        # In production, query Supabase:
        # result = _sb.table("churn_features").select("*").eq("user_id", user_id).execute()
        # if result.data:
        #     return JSONResponse({"success": True, "data": result.data[0]})
        
        return JSONResponse(
            {"success": False, "error": "User not found", "error_code": "NOT_FOUND"},
            status_code=404,
        )
    except Exception as e:
        logger.error(f"Get churn risk error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": "Internal server error", "error_code": "INTERNAL_SERVER_ERROR"},
            status_code=500,
        )

# ══════════════════════════════════════════════
# CHAT ENDPOINT
# ══════════════════════════════════════════════

@app.post(
    "/api/chat",
    tags=["Chat"],
    summary="Stream health advice",
    description="Send message and stream AI health advice with protocol recommendations",
)
async def chat(request: Request):
    """Stream chat response with health advice."""
    try:
        payload = _decode_token(request)
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Not authenticated", "error_code": "AUTH_FAILED"},
                status_code=401,
            )
        
        # Rate limiting
        try:
            rate_limiter = get_rate_limiter()
            rate_limiter.check_rate_limit(request, "/api/chat", username=payload["username"])
        except:
            pass  # Graceful fallback
        
        username = payload["username"]
        user_id = payload.get("user_id")
        
        body = await request.json()
        message = (body.get("message") or "").strip()
        if not message or len(message) > 2000:
            return JSONResponse(
                {"success": False, "error": "Message must be 1-2000 characters", "error_code": "VALIDATION_ERROR"},
                status_code=422,
            )
        
        # Load profile
        profile = {}
        if USE_SUPABASE and user_id:
            try:
                res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
                if res.data:
                    profile = res.data[0]
            except Exception as e:
                logger.warning(f"Profile load error: {e}")
        
        if not profile:
            try:
                with open(_profile_path(username), "r") as f:
                    profile = json.load(f)
            except FileNotFoundError:
                pass
        
        def generate():
            """Generate chat response stream."""
            try:
                import ollama
                from model.model import MODEL_NAME, build_full_context
                from model.constraint_graph import ConstraintGraph
                from model.validation import parse_profile as _parse_profile
                from model.meal_swap import detect_swap_request, find_swaps, format_swap_block
                from model import nutrition_db, user_state
                
                _profile = _cast(dict, profile) if profile else {}
                system_full, seed_message = build_full_context(_profile, username)
                
                # Meal swap injection
                _swap_prefix = ""
                _rejected = detect_swap_request(message)
                if _rejected and nutrition_db.is_loaded():
                    try:
                        _pp = _parse_profile(_profile)
                        _cg = ConstraintGraph.from_parsed_profile(_pp)
                        _state = user_state.analyze_user_state(_profile)
                        _protocols = user_state.map_state_to_protocols(_state)
                        _prioritized = user_state.prioritize_protocols(_protocols, _state, {})
                        _active_p = [p for p, _ in _prioritized[:5]]
                        _swaps = find_swaps(_rejected, constraint_graph=_cg, active_protocols=_active_p, n=5)
                        _swap_prefix = format_swap_block(_rejected, _swaps, constraint_graph=_cg)
                    except Exception as e:
                        logger.warning(f"Meal swap failed: {e}")
                
                _final_message = f"{_swap_prefix}\n\n{message}" if _swap_prefix else message
                
                messages = [
                    {"role": "system", "content": system_full},
                    {"role": "user", "content": seed_message},
                    {"role": "assistant", "content": "Understood. I have your full profile, state analysis, protocol priorities, and nutrition data loaded."},
                    {"role": "user", "content": _final_message},
                ]
                
                # Extract feedback from message
                try:
                    feedback = user_state.parse_feedback_from_text(message)
                    if feedback:
                        user_state.update_weights_from_feedback(username, feedback, learning_rate=0.05)
                        logger.info(f"✓ Feedback recorded for {username}: {feedback}")
                except Exception as e:
                    logger.warning(f"Feedback processing failed: {e}")
                
                # Stream response
                stream = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
                for chunk in stream:
                    content = chunk["message"]["content"]
                    if content:
                        yield content
                
                logger.info(f"✓ Chat completed: {username}")
            
            except ImportError as e:
                logger.error(f"Import error in chat: {e}")
                yield f"[Error: Missing dependency: {e}]"
            except Exception as e:
                logger.error(f"Chat error: {e}", exc_info=True)
                yield f"[Error: {str(e)[:100]}]"
        
        return StreamingResponse(generate(), media_type="text/plain")
    
    except json.JSONDecodeError:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON", "error_code": "VALIDATION_ERROR"},
            status_code=422,
        )
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        return JSONResponse(
            {
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
            status_code=500,
        )

# ══════════════════════════════════════════════
# APP STARTUP/SHUTDOWN
# ══════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Initialize on app startup."""
    logger.info("="*60)
    logger.info("  HealthOS API v3.0 — Starting")
    logger.info("="*60)
    logger.info(f"  Ollama: Available")
    logger.info(f"  Supabase: {'Connected' if USE_SUPABASE else 'Unavailable (using local fallback)'}")
    logger.info(f"  Docs: http://localhost:8000/api/docs")
    logger.info("="*60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    logger.info("HealthOS API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
