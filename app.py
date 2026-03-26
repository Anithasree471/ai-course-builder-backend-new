from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import json
import os   # ✅ added for Render
import traceback

from services.ai_generator import generate_course
from database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
from init_db import init_database

load_dotenv()

app = Flask(__name__)
CORS(app)

def calculate_grade(progress, is_programming):
    progress = progress or {}

    if is_programming:
        notes_score = 20 if progress.get("notesCompleted") else 0
        videos_score = 20 if progress.get("videosCompleted") else 0
        assessment_score = round((progress.get("assessmentScore", 0) / 100) * 20)
        coding_score = progress.get("codingScore", 0)
        articles_score = 20 if progress.get("articlesCompleted") else 0

        overall_score = notes_score + videos_score + assessment_score + coding_score + articles_score
    else:
        notes_score = 25 if progress.get("notesCompleted") else 0
        videos_score = 25 if progress.get("videosCompleted") else 0
        assessment_score = round((progress.get("assessmentScore", 0) / 100) * 25)
        articles_score = 25 if progress.get("articlesCompleted") else 0

        overall_score = notes_score + videos_score + assessment_score + articles_score

    if overall_score >= 90:
        grade = "A+"
    elif overall_score >= 80:
        grade = "A"
    elif overall_score >= 70:
        grade = "B"
    elif overall_score >= 60:
        grade = "C"
    elif overall_score >= 50:
        grade = "D"
    else:
        grade = "F"

    return overall_score, grade

init_database()


@app.route("/")
def home():
    return "AI Course Builder Backend Running"


# ---------------------------
# REGISTER API
# ---------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, "user")
            )
        conn.commit()

        return jsonify({
            "message": "User registered successfully"
        }), 201

    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            return jsonify({"error": "Email already exists"}), 409
       
        print("BACKEND ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------
# LOGIN API
# ---------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    if not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
    "message": "Login successful",
    "user": {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"] if user["role"] else "user"
    }
    }), 200


# ---------------------------
# GENERATE + SAVE COURSE API
# ---------------------------
@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    topic = data.get("topic")
    user_id = data.get("user_id")

    if not topic:
        return jsonify({"error": "Topic required"}), 400

    try:
        course = generate_course(topic)

        if user_id:
            progress = {
                "notesCompleted": False,
                "videosCompleted": False,
                "assessmentCompleted": False,
                "codingCompleted": False,
                "articlesCompleted": False,
                "assessmentScore": 0,
                "codingScore": 0
            }

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO courses (
                    user_id, title, topic, modules, mcq, assignment,
                    is_programming, youtube, articles, progress
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                course.get("title"),
                topic,
                json.dumps(course.get("modules", [])),
                json.dumps(course.get("mcq", [])),
                json.dumps(course.get("assignment")) if course.get("assignment") is not None else None,
                1 if course.get("isProgramming") else 0,
                json.dumps(course.get("youtube", [])),
                json.dumps(course.get("articles", [])),
                json.dumps(progress)
            ))

            course_id = cursor.lastrowid
            conn.commit()
            conn.close()

            course["id"] = course_id

        return jsonify({"course": course})

    except Exception as e:
        print("BACKEND ERROR:", e)
        return jsonify({"error": str(e)}), 500


# ---------------------------
# GET ALL COURSES OF A USER
# ---------------------------
@app.route("/courses/<int:user_id>", methods=["GET"])
def get_courses(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM courses WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    courses = []

    for row in rows:
        courses.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "title": row["title"],
            "topic": row["topic"],
            "modules": json.loads(row["modules"]) if row["modules"] else [],
            "mcq": json.loads(row["mcq"]) if row["mcq"] else [],
            "assignment": json.loads(row["assignment"]) if row["assignment"] else None,
            "isProgramming": bool(row["is_programming"]),
            "youtube": json.loads(row["youtube"]) if row["youtube"] else [],
            "articles": json.loads(row["articles"]) if row["articles"] else [],
            "progress": json.loads(row["progress"]) if row["progress"] else {}
        })

    return jsonify({"courses": courses}), 200


# ---------------------------
# GET ONE COURSE
# ---------------------------
@app.route("/course/<int:course_id>", methods=["GET"])
def get_course(course_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM courses WHERE id = ?",
        (course_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Course not found"}), 404

    course = {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "topic": row["topic"],
        "modules": json.loads(row["modules"]) if row["modules"] else [],
        "mcq": json.loads(row["mcq"]) if row["mcq"] else [],
        "assignment": json.loads(row["assignment"]) if row["assignment"] else None,
        "isProgramming": bool(row["is_programming"]),
        "youtube": json.loads(row["youtube"]) if row["youtube"] else [],
        "articles": json.loads(row["articles"]) if row["articles"] else [],
        "progress": json.loads(row["progress"]) if row["progress"] else {}
    }

    return jsonify({"course": course}), 200


# ---------------------------
# DELETE COURSE
# ---------------------------
@app.route("/course/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Course deleted successfully"}), 200


# ---------------------------
# UPDATE PROGRESS
# ---------------------------
@app.route("/course/<int:course_id>/progress", methods=["PUT"])
def update_progress(course_id):
    data = request.json
    progress = data.get("progress")

    if not progress:
        return jsonify({"error": "Progress data required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE courses SET progress = ? WHERE id = ?",
        (json.dumps(progress), course_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Progress updated successfully"}), 200

@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    admin_email = request.args.get("email")

    if not admin_email:
        return jsonify({"error": "Admin email required"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (admin_email,))
    admin_user = cursor.fetchone()

    if not admin_user or admin_user["role"] != "admin":
        conn.close()
        return jsonify({"error": "Unauthorized access"}), 403

    cursor.execute("SELECT id, name, email, role FROM users ORDER BY id DESC")
    users = cursor.fetchall()

    dashboard_data = []

    for user in users:
        if user["role"] == "admin":
            continue

        cursor.execute("SELECT * FROM courses WHERE user_id = ?", (user["id"],))
        courses = cursor.fetchall()

        if not courses:
            dashboard_data.append({
                "user_id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "course_title": "No course yet",
                "progress_percent": 0,
                "grade": "-"
            })
            continue

        for course in courses:
            progress = json.loads(course["progress"]) if course["progress"] else {}
            is_programming = bool(course["is_programming"])

            checklist_items = [
                progress.get("notesCompleted", False),
                progress.get("videosCompleted", False),
                progress.get("assessmentCompleted", False),
                progress.get("articlesCompleted", False)
            ]

            if is_programming:
                checklist_items.append(progress.get("codingCompleted", False))

            completed_count = sum(1 for item in checklist_items if item)
            progress_percent = round((completed_count / len(checklist_items)) * 100)

            overall_score, grade = calculate_grade(progress, is_programming)

            dashboard_data.append({
                "user_id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "course_title": course["title"],
                "progress_percent": progress_percent,
                "grade": grade
            })

    conn.close()

    return jsonify({"dashboard": dashboard_data}), 200


# ✅ FINAL CHANGE FOR RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)