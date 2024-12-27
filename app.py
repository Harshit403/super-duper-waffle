from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sqlite3

app = FastAPI()

# Mount static and templates directories
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Setup SQLite database
db_path = "database/data.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

# Create necessary tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses (id)
)
""")
conn.commit()

# Routes
@app.get("/", response_class=HTMLResponse)
def user_dashboard(request: Request):
    # Fetch data for user dashboard
    cursor.execute("SELECT id, title FROM courses")
    courses = cursor.fetchall()
    course_data = {}
    for course_id, course_name in courses:
        cursor.execute("SELECT name, file_path FROM plans WHERE course_id = ?", (course_id,))
        plans = cursor.fetchall()
        course_data[course_id] = {
            "name": course_name,
            "plans": {plan[0]: plan[1] for plan in plans},
        }
    return templates.TemplateResponse("user_dashboard.html", {"request": request, "course_data": course_data})

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    cursor.execute("SELECT id, title FROM courses")
    courses = cursor.fetchall()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "courses": dict(courses)})

@app.post("/admin/add-course")
def add_course(title: str = Form(...)):
    cursor.execute("INSERT INTO courses (title) VALUES (?)", (title,))
    conn.commit()
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/add-plan/{course_id}", response_class=HTMLResponse)
def add_plan(request: Request, course_id: int):
    cursor.execute("SELECT title FROM courses WHERE id = ?", (course_id,))
    course_name = cursor.fetchone()[0]
    return templates.TemplateResponse("add_plan.html", {"request": request, "course_id": course_id, "course_name": course_name})

@app.post("/admin/add-plan/{course_id}")
async def save_plan(course_id: int, name: str = Form(...), pdf: UploadFile = File(...)):
    # Save PDF file
    file_path = f"static/uploaded_files/{pdf.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(await pdf.read())

    # Save plan in database
    cursor.execute("INSERT INTO plans (course_id, name, file_path) VALUES (?, ?, ?)", (course_id, name, file_path))
    conn.commit()
    return RedirectResponse("/admin", status_code=303)
