
import sqlite3
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

DATABASE = "students.db"


# 1. Connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# 2. Create the database table
def initialize_database():
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                program TEXT NOT NULL,
                year INTEGER NOT NULL,
                section TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# 3. Validate student information
def validate_student(data):
    if not isinstance(data, dict):
        return None, "Invalid student data."

    student_id = str(data.get("student_id") or "").strip()
    name = str(data.get("name") or "").strip()
    program = str(data.get("program") or "").strip()
    section = str(data.get("section") or "").strip()
    year = data.get("year")

    if not student_id or not name or not program or not section:
        return None, "Please fill in all fields."

    if isinstance(year, bool):
        return None, "Year must be between 1 and 6."

    try:
        year = int(year)
    except (ValueError, TypeError):
        return None, "Year must be a whole number."

    if year < 1 or year > 6:
        return None, "Year must be between 1 and 6."

    return {
        "student_id": student_id,
        "name": name,
        "program": program,
        "year": year,
        "section": section
    }, None


# 4. Home page
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


# 5. Display all students
@app.route("/students", methods=["GET"])
def get_students():
    conn = get_db_connection()
    try:
        students = conn.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(student) for student in students])
    finally:
        conn.close()


# 6. Search students by program
@app.route("/students/program/<program>", methods=["GET"])
def search_students_by_program(program):
    conn = get_db_connection()
    try:
        students = conn.execute(
            """
            SELECT * FROM students
            WHERE program LIKE ?
            ORDER BY name
            """,
            ("%" + program.strip() + "%",)
        ).fetchall()
        return jsonify([dict(student) for student in students])
    finally:
        conn.close()


# 7. Greeting API
@app.route("/hello", methods=["GET"])
def hello():
    name = request.args.get("name", "Student").strip()
    name = name or "Student"

    return jsonify({
        "message": f"Hello, {name}! Welcome to the Student Information System."
    })


# 8. GET: Read-only endpoint for all students
@app.route("/api/students", methods=["GET"])
def api_students():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()


# 9. GET: Display one student
@app.route("/api/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    conn = get_db_connection()
    try:
        student = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        if student is None:
            return jsonify({"error": "Student not found."}), 404

        return jsonify(dict(student))
    finally:
        conn.close()


# 10. POST: Add a student
@app.route("/api/students", methods=["POST"])
def add_student():
    data, error = validate_student(request.get_json(silent=True))

    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO students
            (student_id, name, program, year, section)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["student_id"],
                data["name"],
                data["program"],
                data["year"],
                data["section"]
            )
        )
        conn.commit()

        return jsonify({
            "message": "Student added successfully.",
            "id": cursor.lastrowid
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "This Student ID already exists."
        }), 409

    finally:
        conn.close()


# 11. PUT: Update a student
@app.route("/api/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    data, error = validate_student(request.get_json(silent=True))

    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        if existing is None:
            return jsonify({"error": "Student not found."}), 404

        conn.execute(
            """
            UPDATE students
            SET student_id = ?, name = ?, program = ?,
                year = ?, section = ?
            WHERE id = ?
            """,
            (
                data["student_id"],
                data["name"],
                data["program"],
                data["year"],
                data["section"],
                student_id
            )
        )
        conn.commit()

        return jsonify({
            "message": "Student updated successfully."
        })

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "This Student ID already exists."
        }), 409

    finally:
        conn.close()


# 12. DELETE: Remove a student
@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,)
        )
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Student not found."}), 404

        return jsonify({
            "message": "Student deleted successfully."
        })

    finally:
        conn.close()


# 13. Run the application
if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
