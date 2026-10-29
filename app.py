import os
import sqlite3
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

DATABASE = "students.db"

# CLASSMATE'S RENDER URL
PARTNER_URL = "https://jezalyn-indic.onrender.com"


# 1. Connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# 2. Initialize the database
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
                section TEXT NOT NULL,
                source TEXT DEFAULT 'Local'
            )
        """)

        # Add source column to existing databases if missing
        columns = conn.execute("PRAGMA table_info(students)").fetchall()
        if "source" not in [column["name"] for column in columns]:
            conn.execute("""
                ALTER TABLE students
                ADD COLUMN source TEXT DEFAULT 'Local'
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

    if not all([student_id, name, program, section]):
        return None, "Please fill in all fields."

    if isinstance(year, bool):
        return None, "Year must be a whole number between 1 and 6."

    if isinstance(year, float) and not year.is_integer():
        return None, "Year must be a whole number."

    try:
        year = int(year)
    except (ValueError, TypeError, OverflowError):
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


# 5. Display all local students
@app.route("/students", methods=["GET"])
def get_students():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM students ORDER BY id DESC"
        ).fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()


# 6. Search local students by program
@app.route("/students/program/<program>", methods=["GET"])
def search_students_by_program(program):
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM students
            WHERE program LIKE ?
            ORDER BY name
        """, ("%" + program.strip() + "%",)).fetchall()
        return jsonify([dict(row) for row in rows])
    finally:
        conn.close()


# 7. Greeting API
@app.route("/hello", methods=["GET"])
def hello():
    name = request.args.get("name", "Student").strip() or "Student"
    return jsonify({
        "message": f"Hello, {name}! Welcome to the Student Information System."
    })


# 8. GET: All local students API
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


# 9. GET: One local student
@app.route("/api/students/<int:student_id>", methods=["GET"])
def get_student(student_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        if row is None:
            return jsonify({"error": "Student not found."}), 404

        return jsonify(dict(row))
    finally:
        conn.close()


# 10. POST: Add student
@app.route("/api/students", methods=["POST"])
def add_student():
    payload = request.get_json(silent=True)
    data, error = validate_student(payload)

    if error:
        return jsonify({"error": error}), 400

    source = str(payload.get("source") or "External API").strip() or "External API"

    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO students
                (student_id, name, program, year, section, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["student_id"],
            data["name"],
            data["program"],
            data["year"],
            data["section"],
            source
        ))
        conn.commit()

        return jsonify({
            "message": "Student added successfully.",
            "id": cursor.lastrowid
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "This Student ID already exists."}), 409
    finally:
        conn.close()


# 11. PUT: Update student
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

        conn.execute("""
            UPDATE students
            SET student_id = ?, name = ?, program = ?,
                year = ?, section = ?
            WHERE id = ?
        """, (
            data["student_id"], data["name"], data["program"],
            data["year"], data["section"], student_id
        ))
        conn.commit()
        return jsonify({"message": "Student updated successfully."})

    except sqlite3.IntegrityError:
        return jsonify({"error": "This Student ID already exists."}), 409
    finally:
        conn.close()


# 12. DELETE: Remove student
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

        return jsonify({"message": "Student deleted successfully."})
    finally:
        conn.close()


# Helper: validate a public Render service URL
def validate_render_url(url):
    try:
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or not parsed.hostname.endswith(".onrender.com")
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            return None
        return parsed
    except ValueError:
        return None


# 13. Fetch records from a classmate's Render service
@app.route("/api/classmate-records", methods=["POST"])
def fetch_classmate_records():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Please provide a Render URL."}), 400

    url = str(data.get("url") or "").strip().rstrip("/")
    if not url:
        return jsonify({"error": "Please enter a Render URL."}), 400

    parsed = validate_render_url(url)
    if parsed is None:
        return jsonify({
            "error": "Enter a valid HTTPS Render URL, such as https://your-classmate.onrender.com"
        }), 400

    try:
        response = requests.get(
            url + "/api/students",
            headers={"Accept": "application/json"},
            timeout=15,
            allow_redirects=False
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Unable to retrieve records. Make sure the classmate's /api/students endpoint is public and returns HTTP 200."
            }), 502

        records = response.json()
        if not isinstance(records, list):
            return jsonify({"error": "The classmate API must return a JSON list."}), 502

        for record in records:
            if isinstance(record, dict):
                record["source"] = parsed.hostname

        return jsonify({
            "source": parsed.hostname,
            "count": len(records),
            "records": records
        })

    except requests.Timeout:
        return jsonify({"error": "The classmate's server took too long to respond."}), 504
    except requests.RequestException:
        return jsonify({"error": "Could not connect to the classmate's Render service."}), 502
    except ValueError:
        return jsonify({"error": "The classmate API returned invalid JSON."}), 502


# 14. Fetch records from a partner Flask API
@app.route("/partner-records", methods=["GET"])
def partner_records():
    url = str(request.args.get("url") or "").strip().rstrip("/")
    if not url:
        return jsonify({"error": "Enter your partner's public Render URL."}), 400

    parsed = validate_render_url(url)
    if parsed is None:
        return jsonify({
            "error": "Enter a valid HTTPS Render URL, such as https://partner-project.onrender.com"
        }), 400

    try:
        response = requests.get(
            url + "/partner-records",
            headers={"Accept": "application/json"},
            timeout=15,
            allow_redirects=False
        )
        if response.status_code != 200:
            return jsonify({
                "error": "Partner API request failed. Confirm that /partner-records is public and returns HTTP 200."
            }), 502

        payload = response.json()
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
            records = payload["records"]
        else:
            return jsonify({
                "error": "Partner API must return a JSON list or an object containing a records list."
            }), 502

        safe_records = []
        for record in records:
            if isinstance(record, dict):
                item = dict(record)
                item["source"] = parsed.hostname
                safe_records.append(item)

        return jsonify({
            "source": parsed.hostname,
            "count": len(safe_records),
            "records": safe_records
        })

    except requests.Timeout:
        return jsonify({"error": "The partner API took too long to respond."}), 504
    except requests.RequestException:
        return jsonify({"error": "Could not connect to the partner Flask API."}), 502
    except ValueError:
        return jsonify({"error": "The partner API returned invalid JSON."}), 502


# 15. Save one partner record into the local SQLite database
@app.route("/api/partner-records/save", methods=["POST"])
def save_partner_record():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("record"), dict):
        return jsonify({"error": "A partner record is required."}), 400

    record = payload["record"]
    data, error = validate_student(record)
    if error:
        return jsonify({
            "error": "This record cannot be saved. Required fields are student_id, name, program, year (1–6), and section. " + error
        }), 400

    source = str(record.get("source") or "Partner API").strip()[:255]
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO students (student_id, name, program, year, section, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["student_id"], data["name"], data["program"],
            data["year"], data["section"], source
        ))
        conn.commit()
        return jsonify({
            "message": "Partner record saved to your database successfully.",
            "id": cursor.lastrowid
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "This Student ID already exists in your database."}), 409
    finally:
        conn.close()


# 16. Import one selected partner record into the local database
@app.route("/import-student", methods=["POST"])
def import_student():
    record = request.get_json(silent=True)
    if not isinstance(record, dict):
        return jsonify({"error": "Invalid student data."}), 400

    data, error = validate_student(record)
    if error:
        return jsonify({"error": error}), 400

    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO students
                (student_id, name, program, year, section, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["student_id"], data["name"], data["program"],
            data["year"], data["section"],
            str(record.get("source") or "Classmate API").strip()[:255]
        ))
        conn.commit()
        return jsonify({
            "message": "Remote record saved",
            "id": cursor.lastrowid,
            "source": str(record.get("source") or "Classmate API").strip()[:255]
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "This Student ID already exists in your database."}), 409
    finally:
        conn.close()


# 17. Send one practice record to Student B's POST endpoint
@app.route("/send-practice-record", methods=["POST"])
def send_practice_record():
    payload = request.get_json(silent=True)

    # Use the URL entered in the website. If none is provided, use the
    # configured classmate URL at the top of this file.
    url = str((payload or {}).get("url") or PARTNER_URL).strip().rstrip("/")
    parsed = validate_render_url(url)

    if parsed is None:
        return jsonify({
            "error": "Enter a valid HTTPS Render URL, such as https://your-classmate.onrender.com"
        }), 400

    practice_record = {
        "student_id": "EXT-001",
        "name": "Sample Exchange Record",
        "program": "BSIT",
        "year": 1,
        "section": "A",
        "source": "Partner API"
    }

    try:
        response = requests.post(
            url + "/api/students",
            json=practice_record,
            headers={"Accept": "application/json"},
            timeout=30,
            allow_redirects=False
        )

        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text[:2000]

        return jsonify({
            "message": (
                "Practice record added successfully to the partner API."
                if response.status_code == 201
                else "The partner API responded. Check the status and response details."
            ),
            "partner_url": url,
            "endpoint": url + "/api/students",
            "status_code": response.status_code,
            "response": response_data
        }), 200

    except requests.Timeout:
        return jsonify({
            "error": "The partner server took too long to respond.",
            "partner_url": url
        }), 504
    except requests.RequestException as error:
        return jsonify({
            "error": "Could not connect to the partner's Render service.",
            "details": str(error),
            "partner_url": url
        }), 502


# Start application
initialize_database()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
