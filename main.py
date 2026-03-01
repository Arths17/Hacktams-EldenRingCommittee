import os
import sys
import json
import bcrypt
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "model"))

# ── Supabase connection ───────────────────────────────────────────────────────
try:
    from db import create_user as db_create, login_user as db_login
    from db import save_profile as db_save_profile, load_profile as db_load_profile
    USE_SUPABASE = True
    print("[startup] Supabase connected")
except Exception as e:
    USE_SUPABASE = False
    print(f"[startup] Supabase unavailable, using users.json ({e})")

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "elden_ring"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── Local fallback helpers ────────────────────────────────────────────────────
USERS_FILE = "users.json"

def _local_users():
    try:
        with open(USERS_FILE) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _local_login(username, password):
    for u in _local_users():
        if u["username"] == username:
            if bcrypt.checkpw(password.encode(), u["password"].encode()):
                return {"success": True, "user_id": u["id"], "username": username}
            return {"success": False, "error": "Incorrect password"}
    return {"success": False, "error": "User not found"}

def _local_signup(username, password):
    users = _local_users()
    if any(u["username"] == username for u in users):
        return {"success": False, "error": "Username already taken"}
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_id = max((u.get("id", 0) for u in users), default=0) + 1
    users.append({"id": new_id, "username": username, "password": hashed})
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)
    return {"success": True, "user_id": new_id, "username": username}

# ── Page routes ───────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# ── Auth API ──────────────────────────────────────────────────────────────────
@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    result = db_login(username, password) if USE_SUPABASE else _local_login(username, password)
    if result["success"]:
        request.session["username"] = result["username"]
        request.session["user_id"]  = str(result["user_id"])
    return JSONResponse(result)

@app.post("/api/signup")
async def signup(request: Request, username: str = Form(...), password: str = Form(...)):
    if len(username) < 3:
        return JSONResponse({"success": False, "error": "Username too short (min 3)"})
    if len(password) < 6:
        return JSONResponse({"success": False, "error": "Password too short (min 6)"})
    result = db_create(username, password) if USE_SUPABASE else _local_signup(username, password)
    if result["success"]:
        request.session["username"] = result["username"]
        request.session["user_id"]  = str(result["user_id"])
    return JSONResponse(result)

@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"success": True})

# ── Profile API ───────────────────────────────────────────────────────────────
@app.get("/api/me")
async def get_me(request: Request):
    username = request.session.get("username")
    user_id  = request.session.get("user_id")
    if not username:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)
    profile = {}
    if USE_SUPABASE and user_id:
        profile = db_load_profile(user_id) or {}
    return JSONResponse({"success": True, "username": username, "profile": profile})

@app.post("/api/profile")
async def save_profile(
    request: Request,
    name: str = Form(""), age: str = Form(""), gender: str = Form(""),
    height: str = Form(""), weight: str = Form(""), goal: str = Form(""),
    diet_type: str = Form(""), allergies: str = Form(""), budget: str = Form(""),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)
    profile = {
        "name": name, "age": age, "gender": gender,
        "height": height, "weight": weight, "goal": goal,
        "diet_type": diet_type, "allergies": allergies, "budget": budget,
    }
    if USE_SUPABASE:
        ok = db_save_profile(user_id, profile)
    else:
        try:
            with open("user_profile.json") as f:
                all_p = json.load(f)
                if not isinstance(all_p, dict): all_p = {}
        except Exception:
            all_p = {}
        all_p[user_id] = profile
        with open("user_profile.json", "w") as f:
            json.dump(all_p, f, indent=2)
        ok = True
    return JSONResponse({"success": ok})
