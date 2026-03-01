from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import json
import bcrypt

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="elden_ring")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with open("users.json", "r") as f:
        users = json.load(f)
    for u in users:
        if u["username"] == username:
            if bcrypt.checkpw(password.encode(), u["password"].encode()):
                request.session["username"] = username
                return JSONResponse({"success": True, "username": username})
            return JSONResponse({"success": False, "error": "Incorrect password"})
    return JSONResponse({"success": False, "error": "User not found"})


@app.post("/api/signup")
async def signup(request: Request, username: str = Form(...), password: str = Form(...)):
    if len(username) < 3:
        return JSONResponse({"success": False, "error": "Username too short"})
    if len(password) < 6:
        return JSONResponse({"success": False, "error": "Password too short"})
    with open("users.json", "r") as f:
        users = json.load(f)
    if any(u["username"] == username for u in users):
        return JSONResponse({"success": False, "error": "Username already taken"})
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    new_id = max((u.get("id", 0) for u in users), default=0) + 1
    users.append({"id": new_id, "username": username, "password": hashed})
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)
    request.session["username"] = username
    return JSONResponse({"success": True, "username": username})
