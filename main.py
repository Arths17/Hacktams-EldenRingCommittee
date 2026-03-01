from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import json
import bcrypt

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="elden_ring")
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
                return JSONResponse({"success": True})
            return JSONResponse({"success": False, "error": "Incorrect password"})
    return JSONResponse({"success": False, "error": "User not found"})
