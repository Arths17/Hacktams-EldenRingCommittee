# HealthOS API v3.0 — Production-Grade Documentation

## Overview

HealthOS API is a **medical-grade health optimization system** for college students, providing:
- **Smart Protocol Ranking** based on user state and feedback
- **Meal Planning & Substitution** with nutritional constraints
- **Real-time Feedback Learning** that adapts over time
- **Streaming AI Advice** powered by Ollama (llama3.1:8b)

---

## Quick Start

### 1. Installation & Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your SUPABASE_URL and SUPABASE_KEY
```

### 2. Start the API

```bash
# With uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the Python runner
python main.py
```

### 3. Access Documentation

```
Interactive Swagger Docs: http://localhost:8000/api/docs
ReDoc Documentation:      http://localhost:8000/api/redoc
OpenAPI JSON:             http://localhost:8000/api/openapi.json
```

---

## Authentication

### JWT Tokens

All authenticated endpoints require a **Bearer token** in the `Authorization` header:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Lifecycle

1. **Signup** (`POST /api/signup`) → Receive token
2. **Login** (`POST /login`) → Receive token
3. **Use token** in all subsequent requests
4. **Logout** (`POST /api/logout`) → Delete token client-side (stateless JWT)

---

## API Endpoints

### Health & System

#### `GET /api/health` — System Health Check

Check API and service health.

**Request:**
```http
GET /api/health
```

**Response (200):**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2026-03-01T10:30:00Z",
  "services": {
    "ollama": "healthy",
    "supabase": "healthy",
    "nutrition_db": "healthy"
  }
}
```

**Error Response (503):**
```json
{
  "success": false,
  "error": "One or more services unavailable",
  "status": "degraded",
  "services": {
    "ollama": "unavailable: connection refused",
    "supabase": "healthy",
    "nutrition_db": "healthy"
  }
}
```

---

### Authentication

#### `POST /login` — User Login

Authenticate with username and password.

**Request:**
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=alice&password=securepass123
```

**Response (200):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "username": "alice",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:**
- **401 Unauthorized** — Incorrect password
- **404 Not Found** — User doesn't exist
- **429 Too Many Requests** — Rate limit exceeded (5/300s)

---

#### `POST /api/signup` — User Registration

Create a new account.

**Request:**
```http
POST /api/signup
Content-Type: application/x-www-form-urlencoded

username=alice&password=securepass123&password_confirm=securepass123
```

**Response (200):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "username": "alice",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:**
- **409 Conflict** — Username already taken
- **422 Unprocessable Entity** — Validation failed
  ```json
  {
    "success": false,
    "error": "Request validation failed",
    "error_code": "VALIDATION_ERROR",
    "details": {
      "errors": [
        {"field": "username", "message": "ensure this value has at least 3 characters"},
        {"field": "password", "message": "ensure this value has at least 8 characters"}
      ]
    }
  }
  ```
- **429 Too Many Requests** — Rate limit exceeded (3/3600s)

---

#### `POST /api/logout` — User Logout

Logout user (client-side: delete token).

**Request:**
```http
POST /api/logout
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true
}
```

---

### Profile Management

#### `GET /api/me` — Get Current User Profile

Retrieve authenticated user's profile.

**Request:**
```http
GET /api/me
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "username": "alice",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile": {
    "age": 20,
    "weight_kg": 75.0,
    "height_cm": 180.0,
    "activity_level": "moderate",
    "dietary_restrictions": ["vegetarian"],
    "health_goals": ["improve energy", "better sleep"],
    "medications": [],
    "allergies": ["peanuts"]
  }
}
```

**Errors:**
- **401 Unauthorized** — Not authenticated

---

#### `POST /api/profile` — Update User Profile

Update user's health profile.

**Request:**
```http
POST /api/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "age": 21,
  "weight_kg": 74.0,
  "height_cm": 180.0,
  "activity_level": "very_active",
  "health_goals": ["build muscle", "improve sleep"],
  "medications": ["vitamin_d"],
  "allergies": ["shellfish"]
}
```

**Response (200):**
```json
{
  "success": true
}
```

**Errors:**
- **401 Unauthorized** — Not authenticated
- **422 Unprocessable Entity** — Invalid data
  ```json
  {
    "success": false,
    "error": "Age must be between 13 and 120",
    "error_code": "VALIDATION_ERROR"
  }
  ```

**Profile Fields (All Optional):**
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `age` | integer | 13-120 | User age |
| `weight_kg` | float | 30-200 | Weight in kilograms |
| `height_cm` | float | 100-250 | Height in centimeters |
| `activity_level` | string | `sedentary`, `light`, `moderate`, `active`, `very_active` | Exercise frequency |
| `dietary_restrictions` | array | max 10 items | e.g., `["vegetarian", "gluten-free"]` |
| `health_goals` | array | max 10 items | e.g., `["improve energy", "better sleep"]` |
| `medications` | array | max 20 items | Current medications |
| `allergies` | array | max 10 items | Food/ingredient allergies |

---

### Chat & Health Advice

#### `POST /api/chat` — Stream Health Advice

Send a message and receive streaming AI health recommendations.

**Request:**
```http
POST /api/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "I've been feeling tired lately. Any suggestions?",
  "include_protocols": true,
  "include_meals": true
}
```

**Response (200):** Streaming text/plain
```
Based on your fatigue, I recommend:

Protocol Priorities:
1. sleep_protocol (0.92) — Sleep is foundational
2. energy_protocol (0.87) — Support ATP production
3. stress_protocol (0.84) — Chronic stress drains energy

Daily Nutrition:
- Iron: 18mg (support oxygen transport)
- B-vitamins: comprehensive (energy metabolism)
- Magnesium: 400mg (muscle recovery)

Meals I recommend:
1. Salmon with quinoa and roasted vegetables...
```

**Request Fields:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | string | required | Health question (1-2000 chars) |
| `include_protocols` | boolean | true | Include protocol recommendations |
| `include_meals` | boolean | true | Include meal suggestions |

**Errors:**
- **401 Unauthorized** — Not authenticated
- **422 Unprocessable Entity** — Message too long/empty
- **429 Too Many Requests** — Rate limit exceeded (30/3600s)
- **503 Service Unavailable** — Ollama/external service failed

---

## Error Handling

### Error Response Format

All errors follow a standard format:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "specific details",
    "additional": "context"
  }
}
```

### Common Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `AUTH_FAILED` | 401 | Authentication failed (invalid credentials) |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists (e.g., username taken) |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_SERVER_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | External service unavailable |

### Rate Limiting

Requests are rate-limited per endpoint and per user:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/login` | 5 | 300s (5 min) |
| `/api/signup` | 3 | 3600s (1 hour) |
| `/api/chat` | 30 | 3600s (1 hour) |
| `/api/profile` | 20 | 3600s (1 hour) |
| `/api/me` | 100 | 3600s (1 hour) |

**Rate Limit Exceeded Response:**
```json
{
  "success": false,
  "error": "Rate limit exceeded. Try again in 240 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "retry_after": 240
  }
}
```

---

## Usage Examples

### Example 1: Complete User Flow

```bash
#!/bin/bash
API="http://localhost:8000"

# 1. Signup
echo "📝 Signing up..."
SIGNUP=$(curl -s -X POST "$API/api/signup" \
  -d "username=alice" \
  -d "password=securepass123" \
  -d "password_confirm=securepass123")

TOKEN=$(echo $SIGNUP | jq -r '.token')
echo "✓ Token: $TOKEN"

# 2. Update profile
echo "📊 Updating profile..."
curl -s -X POST "$API/api/profile" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 20,
    "weight_kg": 75,
    "activity_level": "moderate",
    "health_goals": ["improve energy"]
  }'

# 3. Get profile
echo "👤 Fetching profile..."
curl -s -X GET "$API/api/me" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# 4. Chat
echo "💬 Asking for health advice..."
curl -s -X POST "$API/api/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "I feel tired lately"}'

# 5. Logout
echo "🚪 Logging out..."
curl -s -X POST "$API/api/logout" \
  -H "Authorization: Bearer $TOKEN"
```

### Example 2: Python Client

```python
import requests
import json

class HealthOSClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def signup(self, username: str, password: str) -> str:
        """Create account and return token."""
        res = requests.post(
            f"{self.base_url}/api/signup",
            data={"username": username, "password": password, "password_confirm": password}
        )
        res.raise_for_status()
        self.token = res.json()["token"]
        return self.token
    
    def chat(self, message: str) -> str:
        """Send message and get streaming response."""
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.post(
            f"{self.base_url}/api/chat",
            json={"message": message},
            headers=headers,
            stream=True
        )
        res.raise_for_status()
        return res.text

# Usage
client = HealthOSClient()
client.signup("alice", "securepass123")
advice = client.chat("I've been feeling tired")
print(advice)
```

---

## Advanced Features

### Feedback Learning

The system learns from your feedback:

```python
# Send feedback about how interventions worked
message = "My energy improved! energy: +2"

# System automatically:
# 1. Extracts feedback signal: {"energy": 2.0}
# 2. Updates protocol weights: energy_protocol 0.80 → 0.8125
# 3. Re-ranks protocols for next recommendation
# 4. Persists to per-user JSON file
```

### Meal Swapping

Ask for meal alternatives:

```python
message = "I'm eating salmon, but I'm bored. Any alternatives?"

# System:
# 1. Detects swap request for salmon
# 2. Finds alternatives matching active protocols
# 3. Validates nutritional constraints
# 4. Suggests compatible meals
```

### Constraint Validation

Automatically respects:
- Dietary restrictions (vegetarian, vegan, etc.)
- Allergies (peanuts, shellfish, etc.)
- Medication interactions
- Health conditions

---

## Deployment

### Production Checklist

- [ ] Generate strong `SECRET_KEY` (don't use "elden_ring")
- [ ] Set `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- [ ] Use HTTPS (reverse proxy with Nginx/Apache)
- [ ] Enable CORS appropriately for frontend domain
- [ ] Monitor logs in `/var/log/healthos/`
- [ ] Set up rate limiting (consider Redis for distributed systems)
- [ ] Regular backups of user profiles
- [ ] SSL certificates with auto-renewal (Let's Encrypt)

### Docker Deployment

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Monitoring & Logs

### Log Levels

```python
# INFO: User actions
"✓ Login successful: alice (Supabase)"

# WARNING: Recoverable issues
"Supabase unavailable, falling back to local storage"

# ERROR: Failures requiring attention
"Token decode error: invalid signature"
```

### Health Metrics

Monitor `/api/health` endpoint:

```json
{
  "status": "healthy",
  "services": {
    "ollama": "healthy",
    "supabase": "healthy"
  }
}
```

---

## Support & Troubleshooting

### Ollama Not Responding

```bash
# Check if Ollama is running
lsof -i :11434

# Start Ollama
ollama serve

# Pull model if needed
ollama pull llama3.1:8b
```

### Supabase Connection Issues

```bash
# Test Supabase credentials
python -c "from supabase import create_client; create_client('$SUPABASE_URL', '$SUPABASE_KEY')"
```

### Rate Limit Testing

```bash
# Trigger rate limit on /login
for i in {1..10}; do
  curl -X POST http://localhost:8000/login \
    -d "username=test&password=pass" \
    -d "Content-Type: application/x-www-form-urlencoded"
done
```

---

## API Changes (v3.0)

### What's New

✨ **Comprehensive Error Handling**
- Structured error responses with error codes
- Detailed validation messages
- Automatic fallback between Supabase and local storage

✨ **Rate Limiting**
- Per-endpoint limits
- Per-user tracking
- Configurable via `rate_limiter.py`

✨ **Input Validation**
- Pydantic models for all requests
- Profile field constraints
- Message length limits

✨ **Logging & Monitoring**
- Structured logs with timestamps
- Service health checks
- Startup/shutdown hooks

✨ **OpenAPI Documentation**
- Interactive Swagger UI
- Request/response examples
- Error code documentation

### Migration from v2

If upgrading from HealthOS v2:

1. **Token format unchanged** — v2 tokens work in v3
2. **Endpoints mostly compatible** — Minor response format changes
3. **Profile structure updated** — New optional fields supported
4. **Error responses different** — Always check `error_code` now

---

**Generated:** March 1, 2026  
**Version:** 3.0.0  
**Maintainer:** HealthOS Development Team
