import os
import re
import sys
import json
import bcrypt
import jwt as _jwt
from typing import cast as _cast
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

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
except Exception:
    USE_SUPABASE = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "model"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def _make_token(username: str, user_id=None) -> str:
    payload = {"username": username}
    if user_id is not None:
        payload["user_id"] = user_id
    return _jwt.encode(payload, SECRET, algorithm="HS256")

def _decode_token(request: Request):
    """Extract and decode the Bearer token from the Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        return _jwt.decode(token, SECRET, algorithms=["HS256"])
    except Exception:
        return None

# ── helpers ───────────────────────────────────────────────────────────────────

def _local_login(username: str, password: str):
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        for u in users:
            if u["username"] == username:
                if bcrypt.checkpw(password.encode(), u["password"].encode()):
                    return True, u.get("id"), None
                return False, None, "Incorrect password"
        return False, None, "User not found"
    except FileNotFoundError:
        return False, None, "No users registered yet"

def _local_signup(username: str, password: str):
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []
    for u in users:
        if u["username"] == username:
            return False, None, "Username already taken"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_id = len(users) + 1
    users.append({"id": new_id, "username": username, "password": hashed})
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)
    return True, new_id, None

# ── routes ────────────────────────────────────────────────────────────────────

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if USE_SUPABASE:
        try:
            res = _sb.table("users").select("*").eq("username", username).execute()
            if res.data:
                row = _cast(dict, res.data[0])
                if bcrypt.checkpw(password.encode(), row["password"].encode()):
                    token = _make_token(username, row["id"])
                    return JSONResponse({"success": True, "token": token})
                return JSONResponse({"success": False, "error": "Incorrect password"})
            return JSONResponse({"success": False, "error": "User not found"})
        except Exception:
            pass
    ok, uid, err = _local_login(username, password)
    if ok:
        return JSONResponse({"success": True, "token": _make_token(username, uid)})
    return JSONResponse({"success": False, "error": err})


@app.post("/api/signup")
async def signup(username: str = Form(...), password: str = Form(...)):
    if USE_SUPABASE:
        try:
            existing = _sb.table("users").select("id").eq("username", username).execute()
            if existing.data:
                return JSONResponse({"success": False, "error": "Username already taken"})
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            res = _sb.table("users").insert({"username": username, "password": hashed}).execute()
            uid = (res.data[0] or {}).get("id") if res.data else None  # type: ignore[union-attr]
            return JSONResponse({"success": True, "token": _make_token(username, uid)})
        except Exception:
            pass
    ok, uid, err = _local_signup(username, password)
    if ok:
        return JSONResponse({"success": True, "token": _make_token(username, uid)})
    return JSONResponse({"success": False, "error": err})


@app.post("/api/logout")
async def logout():
    # JWT is stateless — client just deletes the token
    return JSONResponse({"success": True})


@app.get("/api/me")
async def me(request: Request):
    payload = _decode_token(request)
    if not payload:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)
    username = payload["username"]
    user_id  = payload.get("user_id")
    profile = {}
    if USE_SUPABASE and user_id:
        try:
            res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
            if res.data:
                profile = res.data[0]
        except Exception:
            pass
    if not profile:
        try:
            with open(_profile_path(username), "r") as f:
                profile = json.load(f)
        except FileNotFoundError:
            pass
    return JSONResponse({"success": True, "username": username, "profile": profile})


@app.post("/api/profile")
async def save_profile(request: Request):
    payload = _decode_token(request)
    if not payload:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)
    user_id = payload.get("user_id")
    data = await request.json()
    if USE_SUPABASE and user_id:
        try:
            existing = _sb.table("profiles").select("id").eq("user_id", user_id).execute()
            if existing.data:
                _sb.table("profiles").update(data).eq("user_id", user_id).execute()
            else:
                _sb.table("profiles").insert({**data, "user_id": user_id}).execute()
            return JSONResponse({"success": True})
        except Exception:
            pass
    with open(_profile_path(payload["username"]), "w") as f:
        json.dump(data, f, indent=2)
    return JSONResponse({"success": True})


@app.post("/api/chat")
async def chat(request: Request):
    payload = _decode_token(request)
    if not payload:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)
    username = payload["username"]
    user_id  = payload.get("user_id")

    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"success": False, "error": "No message provided"})

    profile = {}
    if USE_SUPABASE and user_id:
        try:
            res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
            if res.data:
                profile = res.data[0]
        except Exception:
            pass
    if not profile:
        try:
            with open(_profile_path(username), "r") as f:
                profile = json.load(f)
        except FileNotFoundError:
            pass

    def generate():
        try:
            import ollama, sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "model"))
            from model import MODEL_NAME, build_full_context
            from constraint_graph import ConstraintGraph
            from validation import parse_profile as _parse_profile
            from meal_swap import detect_swap_request, find_swaps, format_swap_block
            import nutrition_db, rag, user_state

            _profile: dict = _cast(dict, profile) if profile else {}
            system_full, seed_message = build_full_context(_profile, username)

            # ── Meal swap injection ────────────────────────────────────
            _swap_prefix = ""
            _rejected = detect_swap_request(message)
            if _rejected and nutrition_db.is_loaded():
                _pp = _parse_profile(_profile)
                _cg = ConstraintGraph.from_parsed_profile(_pp)
                _state       = user_state.analyze_user_state(_profile)
                _protocols   = user_state.map_state_to_protocols(_state)
                _prioritized = user_state.prioritize_protocols(_protocols, _state, {})
                _active_p    = [p for p, _ in _prioritized[:5]]
                _swaps = find_swaps(_rejected, constraint_graph=_cg,
                                    active_protocols=_active_p, n=5)
                _swap_prefix = format_swap_block(_rejected, _swaps, constraint_graph=_cg)

            _final_message = f"{_swap_prefix}\n\n{message}" if _swap_prefix else message

            messages = [
                {"role": "system", "content": system_full},
                {"role": "user",   "content": seed_message},
                {"role": "assistant", "content": "Understood. I have your full profile, state analysis, protocol priorities, and nutrition data loaded."},
                {"role": "user",   "content": _final_message},
            ]
            stream = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
            for chunk in stream:
                content = chunk["message"]["content"]
                if content:
                    yield content
        except Exception as e:
            import traceback; traceback.print_exc()
            yield f"[Error: {e}]"

    return StreamingResponse(generate(), media_type="text/plain")

