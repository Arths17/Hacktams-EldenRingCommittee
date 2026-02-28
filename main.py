from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER
import json
with open("users.json") as file:
    data = file.nextLine()
app = FastAPI()
app.middleware(SessionMiddleware, secret_key="elden_ring")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.get("/", response_class=HTMLResponse)
async def login_page(request:Request):
    return templates.TemplateResponse("login.html", request)

app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with open("users.json", "r") as file1:
        u = file1.read()
    if u['user'] == username and u["password"] == password:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False})

app.get("/signUp", response_class=HTMLResponse)
async def sign_up(request: Request):
    return templates.TemplateResponse("signUp.html", request)

app.post("/signUp")
async def sign(request:Request, username: str = Form(...), password: str = Form(...), passVerify: str = Form(...)):
    if (password == passVerify) and (username.length() > 5) and (password.length()>7):
        with open("users.json", "a") as file:
            dat = {
                "user": username,
                "password": password
            }
            json.dumps(dat)
        return JSONResponse({"success": True})
    return ({"success": False})

