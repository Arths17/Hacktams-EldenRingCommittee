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

app.get("/create_profile", response_class=HTMLResponse)
async def create_profile(request: Request):
    return templates.TemplatesResponse("create_profile.html", request)

def profile_maker(height, weight, name, age, gender, goal, diet_type, allergies, budget, cooking_access, cultural_prefs, class_schedule, sleep_schedule, workout_times, stress_level, energy_level, sleep_quality, mood, extra):
    return
app.post("/create_profile")
async def profile_send(request:Request, height: str = Form(...), weight: str = Form(...), name: str = Form(...), age: str = Form(...), gender: str = Form(...), goal: str = Form(...), diet_type: str = Form(...), allergies: str = Form(...), budget: str = Form(...), cooking_access: str = Form(...), cultural_prefs: str = Form(...), class_schedule: str = Form(...), sleep_schedule: str = Form(...), workout_times: str = Form(...), stress_level: str = Form(...), energy_level: str = Form(...), sleep_quality: str = Form(...), mood: str = Form(...), extra: str = Form(...) ):
    return

app.get("/profile", response_class=HTMLResponse)
async def profile(request:Request):
    return templates.TemplateResponse("profile.html", request)

app.post("/profile")
async def profile_send(request:Request, height: str = Form(...), weight: str = Form(...), name: str = Form(...), age: str = Form(...), gender: str = Form(...), goal: str = Form(...), diet_type: str = Form(...), allergies: str = Form(...), budget: str = Form(...), cooking_access: str = Form(...), cultural_prefs: str = Form(...), class_schedule: str = Form(...), sleep_schedule: str = Form(...), workout_times: str = Form(...), stress_level: str = Form(...), energy_level: str = Form(...), sleep_quality: str = Form(...), mood: str = Form(...), extra: str = Form(...) ):
    return None

