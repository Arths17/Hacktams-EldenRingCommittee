"""
HealthOS — FastAPI Backend
All AI logic lives in model/. Frontend templates live in templates/.
"""

import os
import sys
import json
import bcrypt
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "model"))
import nutrition_db
import user_state
import rag
import session_memory
from model import (
    analyze_profile, profile_to_context,
    SYSTEM_PROMPT, MODEL_NAME,
)
import ollama

# Supabase (falls back to local users.json if offline)
try:
    from db import create_user as db_create, login_user as db_login
    from db import save_profile as db_save_profile, load_profile as db_load_profile
    from db import save_message, load_chat_history
    USE_SUPABASE = True
except Exception:
    USE_SUPABASE = False

USERS_FILE = "users.json"
SECRET_KEY  = os.environ.get("SECRET_KEY", "healthos_secret")

app = FastAPI(title="HealthOS")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup():
    index_path = os.path.join("model", "nutrition_index.json")
    if os.path.exists(index_path):
        nutrition_db.load(index_path)
        rag.build(index_path)


# ── local user helpers ────────────────────────────────────────────────────────

def _local_users() -> list:
    try:
        with open(USERS_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _save_local_users(users: list):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def _local_signup(username: str, password: str) -> dict:
    users = _local_users()
    if any(u["username"] == username for u in users):
        return {"success": False, "error": "Username already taken"}
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_id = max((u.get("id", 0) for u in users), default=0) + 1
    users.append({"id": new_id, "username": username, "password": hashed})
    _save_local_users(users)
    return {"success": True, "user_id": new_id}

def _local_login(username: str, password: str) -> dict:
    for u in _local_users():
        if u["username"] == username:
            if bcrypt.checkpw(password.encode(), u["password"].encode()):
                return {"success": True, "user_id": u["id"], "username": username}
            return {"success": False, "error": "Incorrect password"}
    return {"success": False, "error": "User not found"}

def current_user(request: Request) -> dict:
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"user_id": uid, "username": request.session.get("username", "")}


# ══════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


# ══════════════════════════════════════════════
# AUTH API
# ══════════════════════════════════════════════

@app.post("/api/signup")
async def signup(request: Request,
                 username: str = Form(...),
                 password: str = Form(...)):
    if len(username) < 3:
        return JSONResponse({"success": False, "error": "Username too short (min 3)"})
    if len(password) < 6:
        return JSONResponse({"success": False, "error": "Password too short (min 6)"})
    result = db_create(username, password) if USE_SUPABASE else _local_signup(username, password)
    if result["success"]:
        request.session["user_id"]  = result["user_id"]
        request.session["username"] = username
    return JSONResponse(result)


@app.post("/api/login")
async def api_login(request: Request,
                    username: str = Form(...),
                    password: str = Form(...)):
    result = db_login(username, password) if USE_SUPABASE else _local_login(username, password)
    if result["success"]:
        request.session["user_id"]  = result["user_id"]
        request.session["username"] = result.get("username", username)
    return JSONResponse(result)


# keep /login working for existing frontend forms
@app.post("/login")
async def login(request: Request,
                username: str = Form(...),
                password: str = Form(...)):
    return await api_login(request, username, password)


@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"success": True})


# ══════════════════════════════════════════════
# PROFILE API
# ══════════════════════════════════════════════

PROFILE_KEYS = [
    "name", "age", "gender", "height", "weight", "goal", "diet_type",
    "allergies", "budget", "cooking_access", "cultural_prefs",
    "class_schedule", "sleep_schedule", "workout_times",
    "stress_level", "energy_level", "sleep_quality", "mood", "extra",
]

@app.post("/api/profile")
async def save_profile_ep(
    request: Request,
    user: dict = Depends(current_user),
    name: str = Form(""), age: str = Form(""), gender: str = Form(""),
    height: str = Form(""), weight: str = Form(""), goal: str = Form(""),
    diet_type: str = Form(""), allergies: str = Form(""), budget: str = Form(""),
    cooking_access: str = Form(""), cultural_prefs: str = Form(""),
    class_schedule: str = Form(""), sleep_schedule: str = Form(""),
    workout_times: str = Form(""), stress_level: str = Form(""),
    energy_level: str = Form(""), sleep_quality: str = Form(""),
    mood: str = Form(""), extra: str = Form(""),
):
    profile = {k: locals()[k] for k in PROFILE_KEYS}
    uid = user["user_id"]
    if USE_SUPABASE:
        ok = db_save_profile(uid, profile)
    else:
        try:
            with open("user_profile.json") as f:
                all_p = json.load(f)
                if not isinstance(all_p, dict):
                    all_p = {}
        except Exception:
            all_p = {}
        all_p[str(uid)] = profile
        with open("user_profile.json", "w") as f:
            json.dump(all_p, f, indent=2)
        ok = True
    return JSONResponse({"success": ok})


@app.get("/api/profile")
async def get_profile_ep(user: dict = Depends(current_user)):
    uid = user["user_id"]
    if USE_SUPABASE:
        profile = db_load_profile(uid)
    else:
        try:
            with open("user_profile.json") as f:
                all_p = json.load(f)
            profile = all_p.get(str(uid), {})
        except Exception:
            profile = {}
    return JSONResponse({"success": True, "profile": profile})


# ══════════════════════════════════════════════
# CHAT API  (streaming SSE)
# ══════════════════════════════════════════════

@app.post("/api/chat")
async def chat_ep(
    request: Request,
    user:    dict = Depends(current_user),
    message: str  = Form(...),
):
    uid      = user["user_id"]
    username = user["username"]

    if USE_SUPABASE:
        profile = db_load_profile(uid)
    else:
        try:
            with open("user_profile.json") as f:
                all_p = json.load(f)
            profile = all_p.get(str(uid), {})
        except Exception:
            profile = {}

    if not profile:
        return JSONResponse({"success": False, "error": "Complete your profile first."})

    history = load_chat_history(uid, limit=10) if USE_SUPABASE else []

    analysis    = analyze_profile(profile)
    state       = user_state.analyze_user_state(profile)
    protocols   = user_state.map_state_to_protocols(state)
    prioritized = user_state.prioritize_protocols(protocols, state)
    constraints = user_state.build_constraints_from_profile(profile)
    cr          = user_state.solve_constraints(prioritized, constraints, state)
    nutrients   = user_state.protocols_to_nutrients({p: s for p, s in prioritized[:10]})
    pblock      = user_state.format_priority_block(prioritized, nutrients, cr)
    rag_ctx     = rag.query(message, [p for p, _ in prioritized[:5]], n=8)
    mem_ctx     = session_memory.format_memory_context(
                      session_memory.load_recent_logs(username))
    seed = profile_to_context(profile, analysis, pblock, rag_ctx, mem_ctx)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if not history:
        messages += [
            {"role": "user",      "content": seed},
            {"role": "assistant", "content": "Understood. I have your full profile."},
        ]
    else:
        messages.extend(history[-10:])

    send_msg = (f"[Food data:{rag_ctx}]\n\n{message}" if rag_ctx else message)
    messages.append({"role": "user", "content": send_msg})

    if USE_SUPABASE:
        save_message(uid, "user", message)

    def generate():
        full = []
        try:
            for chunk in ollama.chat(model=MODEL_NAME, messages=messages, stream=True):
                token = chunk.message.content
                full.append(token)
                yield "data: " + json.dumps({"token": token}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"error": str(e)}) + "\n\n"
            return
        if USE_SUPABASE:
            save_message(uid, "assistant", "".join(full))
        yield "data: " + json.dumps({"done": True}) + "\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ══════════════════════════════════════════════
# HISTORY + ANALYSIS
# ══════════════════════════════════════════════

@app.get("/api/history")
async def get_history(user: dict = Depends(current_user)):
    uid = user["user_id"]
    history = load_chat_history(uid, limit=50) if USE_SUPABASE else []
    return JSONResponse({"success": True, "history": history})


@app.get("/api/analysis")
async def get_analysis(user: dict = Depends(current_user)):
    uid = user["user_id"]
    if USE_SUPABASE:
        profile = db_load_profile(uid)
    else:
        try:
            with open("user_profile.json") as f:
                all_p = json.load(f)
            profile = all_p.get(str(uid), {})
        except Exception:
            profile = {}
    if not profile:
        return JSONResponse({"success": False, "error": "No profile found"})
    analysis    = analyze_profile(profile)
    state       = user_state.analyze_user_state(profile)
    protocols   = user_state.map_state_to_protocols(state)
    prioritized = user_state.prioritize_protocols(protocols, state)
    return JSONResponse({
        "success":       True,
        "analysis":      analysis,
        "top_protocols": [{"name": p, "score": round(s, 3)} for p, s in prioritized[:5]],
    })
