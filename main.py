import os
import sys
import json
import bcrypt
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

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
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "elden_ring"),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _local_login(username: str, password: str):
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        for u in users:
            if u["username"] == username:
                if bcrypt.checkpw(password.encode(), u["password"].encode()):
                    return True, None
                return False, "Incorrect password"
        return False, "User not found"
    except FileNotFoundError:
        return False, "No users registered yet"

def _local_signup(username: str, password: str):
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []
    for u in users:
        if u["username"] == username:
            return False, "Username already taken"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users.append({"id": len(users) + 1, "username": username, "password": hashed})
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)
    return True, None

# ── routes ───────────────────────────────────────────────────────────────────

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if USE_SUPABASE:
        try:
            res = _sb.table("users").select("*").eq("username", username).execute()
            if res.data:
                row = res.data[0]
                if bcrypt.checkpw(password.encode(), row["password"].encode()):
                    request.session["user_id"] = row["id"]
                    request.session["username"] = username
                    return JSONResponse({"success": True})
                return JSONResponse({"success": False, "error": "Incorrect password"})
            return JSONResponse({"success": False, "error": "User not found"})
        except Exception:
            pass  # fall through to local
    ok, err = _local_login(username, password)
    if ok:
        request.session["username"] = username
        return JSONResponse({"success": True})
    return JSONResponse({"success": False, "error": err})


@app.post("/api/signup")
async def signup(request: Request, username: str = Form(...), password: str = Form(...)):
    if USE_SUPABASE:
        try:
            existing = _sb.table("users").select("id").eq("username", username).execute()
            if existing.data:
                return JSONResponse({"success": False, "error": "Username already taken"})
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            _sb.table("users").insert({"username": username, "password": hashed}).execute()
            request.session["username"] = username
            return JSONResponse({"success": True})
        except Exception:
            pass
    ok, err = _local_signup(username, password)
    if ok:
        request.session["username"] = username
        return JSONResponse({"success": True})
    return JSONResponse({"success": False, "error": err})


@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"success": True})


@app.get("/api/me")
async def me(request: Request):
    username = request.session.get("username")
    if not username:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)
    profile = {}
    if USE_SUPABASE:
        try:
            user_id = request.session.get("user_id")
            if user_id:
                res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
                if res.data:
                    profile = res.data[0]
        except Exception:
            pass
    if not profile:
        try:
            with open("user_profile.json", "r") as f:
                profile = json.load(f)
        except FileNotFoundError:
            pass
    return JSONResponse({"success": True, "username": username, "profile": profile})


@app.post("/api/profile")
async def save_profile(request: Request):
    username = request.session.get("username")
    if not username:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)
    data = await request.json()
    if USE_SUPABASE:
        try:
            user_id = request.session.get("user_id")
            if user_id:
                existing = _sb.table("profiles").select("id").eq("user_id", user_id).execute()
                if existing.data:
                    _sb.table("profiles").update(data).eq("user_id", user_id).execute()
                else:
                    _sb.table("profiles").insert({**data, "user_id": user_id}).execute()
                return JSONResponse({"success": True})
        except Exception:
            pass
    with open("user_profile.json", "w") as f:
        json.dump(data, f, indent=2)
    return JSONResponse({"success": True})


@app.post("/api/chat")
async def chat(request: Request):
    username = request.session.get("username")
    if not username:
        return JSONResponse({"success": False, "error": "Not logged in"}, status_code=401)

    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"success": False, "error": "No message provided"})

    # Load profile
    profile = {}
    if USE_SUPABASE:
        try:
            user_id = request.session.get("user_id")
            if user_id:
                res = _sb.table("profiles").select("*").eq("user_id", user_id).execute()
                if res.data:
                    profile = res.data[0]
        except Exception:
            pass
    if not profile:
        try:
            with open("user_profile.json", "r") as f:
                profile = json.load(f)
        except FileNotFoundError:
            pass

    def generate():
        try:
            import ollama
            import nutrition_db
            from model import SYSTEM_PROMPT, MODEL_NAME, profile_to_context

            nutrition_db.load()
            nutrition_ctx = nutrition_db.build_nutrition_context(profile)
            system_full = SYSTEM_PROMPT + "\n\n" + profile_to_context(profile) + nutrition_ctx

            messages = [
                {"role": "system", "content": system_full},
                {"role": "user",   "content": message},
            ]
            stream = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)
            for chunk in stream:
                content = chunk["message"]["content"]
                if content:
                    yield content
        except Exception as e:
            yield f"[Error: {e}]"

    return StreamingResponse(generate(), media_type="text/plain")

