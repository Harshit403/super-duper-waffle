from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import redislite

app = FastAPI()

# Mount static and templates directories
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Setup redislite database
db_path = "database/data.db"
redis = redislite.Redis(db_path)

# Routes
@app.get("/", response_class=HTMLResponse)
def user_dashboard(request: Request):
    # Fetch data for user dashboard
    courses = redis.hgetall("courses")
    course_data = {}
    for course_id, course_name in courses.items():
        plans = redis.hgetall(f"course:{course_id}:plans")
        course_data[course_id] = {
            "name": course_name.decode(),
            "plans": {k.decode(): v.decode() for k, v in plans.items()},
        }
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "course_data": course_data})

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    courses = redis.hgetall("courses")
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "courses": {k.decode(): v.decode() for k, v in courses.items()}})

@app.post("/admin/add-course")
def add_course(title: str = Form(...)):
    course_id = f"course:{len(redis.hgetall('courses')) + 1}"
    redis.hset("courses", course_id, title)
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/add-plan/{course_id}", response_class=HTMLResponse)
def add_plan(request: Request, course_id: str):
    course_name = redis.hget("courses", course_id).decode()
    return templates.TemplateResponse("add_plan.html", {"request": request, "course_id": course_id, "course_name": course_name})

@app.post("/admin/add-plan/{course_id}")
async def save_plan(course_id: str, name: str = Form(...), pdf: UploadFile = File(...)):
    # Save PDF file
    file_path = f"static/uploaded_files/{pdf.filename}"
    with open(file_path, "wb") as f:
        f.write(await pdf.read())

    # Save plan in database
    redis.hset(f"course:{course_id}:plans", name, file_path)
    return RedirectResponse("/admin", status_code=303)
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18931)
