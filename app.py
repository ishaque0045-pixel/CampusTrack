"""
app.py — CampusTrack Flask application.

Routes
------
GET  /                  → redirect to dashboard or login
GET  /login             → show login form
POST /login             → authenticate
GET  /logout            → clear session

GET  /dashboard         → statistics overview

GET  /students          → list / search students
GET  /students/add      → add-student form
POST /students/add      → create student
GET  /students/<id>/edit → edit form
POST /students/<id>/edit → update student
POST /students/<id>/delete → delete student

GET  /subjects          → list subjects
GET  /subjects/add      → add-subject form
POST /subjects/add      → create subject
GET  /subjects/<id>/edit
POST /subjects/<id>/edit
POST /subjects/<id>/delete

GET  /attendance        → mark-attendance form (date + subject)
POST /attendance        → save attendance rows
GET  /attendance/history → browseable history with filters
GET  /reports           → per-student attendance % report
"""

import os
from datetime import date, datetime
from functools import wraps

import bcrypt
from flask import (Flask, flash, redirect, render_template,
                   request, session, url_for)
from dotenv import load_dotenv

import db as database

load_dotenv()   # read .env file if present

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me-in-production-env-var")


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def login_required(f):
    """Decorator: redirect to /login if not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def flash_errors(errors: list):
    for e in errors:
        flash(e, "danger")


# ──────────────────────────────────────────────────────────────
# Auth routes
# ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        errors = []
        if not username:
            errors.append("Username is required.")
        if not password:
            errors.append("Password is required.")

        if errors:
            flash_errors(errors)
            return render_template("login.html", username=username)

        user = database.query(
            "SELECT * FROM users WHERE username = %s",
            (username,),
            fetchone=True,
        )

        if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
            session["user_id"]   = user["user_id"]
            session["username"]  = user["username"]
            session["full_name"] = user["full_name"]
            session["role"]      = user["role"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")
        return render_template("login.html", username=username)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ──────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    student_count = database.query(
        "SELECT COUNT(*) AS cnt FROM students", fetchone=True
    )["cnt"]

    subject_count = database.query(
        "SELECT COUNT(*) AS cnt FROM subjects", fetchone=True
    )["cnt"]

    total_att = database.query(
        "SELECT COUNT(*) AS cnt FROM attendance", fetchone=True
    )["cnt"]

    present_att = database.query(
        "SELECT COUNT(*) AS cnt FROM attendance WHERE status = 'Present'",
        fetchone=True,
    )["cnt"]

    absent_att = total_att - present_att
    present_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0

    # Recent 5 attendance records
    recent = database.query(
        """
        SELECT a.date, s.full_name AS student, sub.subject_name, a.status
        FROM attendance a
        JOIN students s   ON s.student_id   = a.student_id
        JOIN subjects sub ON sub.subject_id = a.subject_id
        ORDER BY a.created_at DESC
        LIMIT 5
        """
    )

    return render_template(
        "dashboard.html",
        student_count=student_count,
        subject_count=subject_count,
        total_att=total_att,
        present_att=present_att,
        absent_att=absent_att,
        present_pct=present_pct,
        recent=recent,
    )


# ──────────────────────────────────────────────────────────────
# Students
# ──────────────────────────────────────────────────────────────

@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip()
    if q:
        rows = database.query(
            """
            SELECT * FROM students
            WHERE full_name LIKE %s OR roll_number LIKE %s OR department LIKE %s
            ORDER BY roll_number
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        )
    else:
        rows = database.query("SELECT * FROM students ORDER BY roll_number")
    return render_template("students.html", students=rows, q=q)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def student_add():
    if request.method == "POST":
        data, errors = _parse_student_form(request.form)
        if errors:
            flash_errors(errors)
            return render_template("student_form.html", action="Add", student=data)

        # Check duplicate roll number
        existing = database.query(
            "SELECT student_id FROM students WHERE roll_number = %s",
            (data["roll_number"],),
            fetchone=True,
        )
        if existing:
            flash(f"Roll number '{data['roll_number']}' already exists.", "danger")
            return render_template("student_form.html", action="Add", student=data)

        database.execute(
            """
            INSERT INTO students
                (roll_number, full_name, email, phone, department, semester)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                data["roll_number"], data["full_name"], data["email"],
                data["phone"], data["department"], data["semester"],
            ),
        )
        flash("Student added successfully.", "success")
        return redirect(url_for("students"))

    return render_template("student_form.html", action="Add", student={})


@app.route("/students/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def student_edit(sid):
    student = database.query(
        "SELECT * FROM students WHERE student_id = %s", (sid,), fetchone=True
    )
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("students"))

    if request.method == "POST":
        data, errors = _parse_student_form(request.form)
        if errors:
            flash_errors(errors)
            return render_template("student_form.html", action="Edit", student=data)

        # Duplicate roll check (exclude self)
        existing = database.query(
            "SELECT student_id FROM students WHERE roll_number = %s AND student_id != %s",
            (data["roll_number"], sid),
            fetchone=True,
        )
        if existing:
            flash(f"Roll number '{data['roll_number']}' is used by another student.", "danger")
            return render_template("student_form.html", action="Edit", student=data)

        database.execute(
            """
            UPDATE students SET
                roll_number=%s, full_name=%s, email=%s,
                phone=%s, department=%s, semester=%s
            WHERE student_id=%s
            """,
            (
                data["roll_number"], data["full_name"], data["email"],
                data["phone"], data["department"], data["semester"], sid,
            ),
        )
        flash("Student updated successfully.", "success")
        return redirect(url_for("students"))

    return render_template("student_form.html", action="Edit", student=student)


@app.route("/students/<int:sid>/delete", methods=["POST"])
@login_required
def student_delete(sid):
    database.execute("DELETE FROM students WHERE student_id = %s", (sid,))
    flash("Student deleted.", "success")
    return redirect(url_for("students"))


def _parse_student_form(form):
    data = {
        "roll_number": form.get("roll_number", "").strip(),
        "full_name":   form.get("full_name",   "").strip(),
        "email":       form.get("email",        "").strip(),
        "phone":       form.get("phone",        "").strip(),
        "department":  form.get("department",   "").strip(),
        "semester":    form.get("semester",     "").strip(),
    }
    errors = []
    if not data["roll_number"]: errors.append("Roll Number is required.")
    if not data["full_name"]:   errors.append("Full Name is required.")
    if not data["department"]:  errors.append("Department is required.")
    if not data["semester"]:    errors.append("Semester is required.")
    else:
        try:
            data["semester"] = int(data["semester"])
            if not (1 <= data["semester"] <= 8):
                errors.append("Semester must be between 1 and 8.")
        except ValueError:
            errors.append("Semester must be a number.")
    return data, errors


# ──────────────────────────────────────────────────────────────
# Subjects
# ──────────────────────────────────────────────────────────────

@app.route("/subjects")
@login_required
def subjects():
    rows = database.query("SELECT * FROM subjects ORDER BY subject_code")
    return render_template("subjects.html", subjects=rows)


@app.route("/subjects/add", methods=["GET", "POST"])
@login_required
def subject_add():
    if request.method == "POST":
        data, errors = _parse_subject_form(request.form)
        if errors:
            flash_errors(errors)
            return render_template("subject_form.html", action="Add", subject=data)

        existing = database.query(
            "SELECT subject_id FROM subjects WHERE subject_code = %s",
            (data["subject_code"],),
            fetchone=True,
        )
        if existing:
            flash(f"Subject code '{data['subject_code']}' already exists.", "danger")
            return render_template("subject_form.html", action="Add", subject=data)

        database.execute(
            """
            INSERT INTO subjects (subject_code, subject_name, department, semester)
            VALUES (%s, %s, %s, %s)
            """,
            (data["subject_code"], data["subject_name"], data["department"], data["semester"]),
        )
        flash("Subject added successfully.", "success")
        return redirect(url_for("subjects"))

    return render_template("subject_form.html", action="Add", subject={})


@app.route("/subjects/<int:sid>/edit", methods=["GET", "POST"])
@login_required
def subject_edit(sid):
    subject = database.query(
        "SELECT * FROM subjects WHERE subject_id = %s", (sid,), fetchone=True
    )
    if not subject:
        flash("Subject not found.", "danger")
        return redirect(url_for("subjects"))

    if request.method == "POST":
        data, errors = _parse_subject_form(request.form)
        if errors:
            flash_errors(errors)
            return render_template("subject_form.html", action="Edit", subject=data)

        existing = database.query(
            "SELECT subject_id FROM subjects WHERE subject_code=%s AND subject_id!=%s",
            (data["subject_code"], sid),
            fetchone=True,
        )
        if existing:
            flash(f"Subject code '{data['subject_code']}' is already in use.", "danger")
            return render_template("subject_form.html", action="Edit", subject=data)

        database.execute(
            """
            UPDATE subjects SET
                subject_code=%s, subject_name=%s, department=%s, semester=%s
            WHERE subject_id=%s
            """,
            (data["subject_code"], data["subject_name"], data["department"], data["semester"], sid),
        )
        flash("Subject updated successfully.", "success")
        return redirect(url_for("subjects"))

    return render_template("subject_form.html", action="Edit", subject=subject)


@app.route("/subjects/<int:sid>/delete", methods=["POST"])
@login_required
def subject_delete(sid):
    database.execute("DELETE FROM subjects WHERE subject_id = %s", (sid,))
    flash("Subject deleted.", "success")
    return redirect(url_for("subjects"))


def _parse_subject_form(form):
    data = {
        "subject_code": form.get("subject_code", "").strip(),
        "subject_name": form.get("subject_name", "").strip(),
        "department":   form.get("department",   "").strip(),
        "semester":     form.get("semester",     "").strip(),
    }
    errors = []
    if not data["subject_code"]: errors.append("Subject Code is required.")
    if not data["subject_name"]: errors.append("Subject Name is required.")
    if not data["department"]:   errors.append("Department is required.")
    if not data["semester"]:     errors.append("Semester is required.")
    else:
        try:
            data["semester"] = int(data["semester"])
            if not (1 <= data["semester"] <= 8):
                errors.append("Semester must be between 1 and 8.")
        except ValueError:
            errors.append("Semester must be a number.")
    return data, errors


# ──────────────────────────────────────────────────────────────
# Attendance
# ──────────────────────────────────────────────────────────────

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    students_list = database.query("SELECT * FROM students ORDER BY roll_number")
    subjects_list = database.query("SELECT * FROM subjects ORDER BY subject_code")

    if request.method == "POST":
        subject_id = request.form.get("subject_id", "").strip()
        att_date   = request.form.get("date", "").strip()
        errors = []

        if not subject_id: errors.append("Please select a subject.")
        if not att_date:   errors.append("Please select a date.")

        if errors:
            flash_errors(errors)
            return render_template(
                "attendance.html",
                students=students_list,
                subjects=subjects_list,
                today=date.today().isoformat(),
            )

        saved = skipped = 0
        for stu in students_list:
            sid   = stu["student_id"]
            key   = f"status_{sid}"
            status = request.form.get(key, "Absent")  # default Absent if unchecked

            # INSERT IGNORE handles the UNIQUE constraint gracefully
            _, rowcount = database.execute(
                """
                INSERT IGNORE INTO attendance
                    (student_id, subject_id, date, status, marked_by)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (sid, subject_id, att_date, status, session["user_id"]),
            )
            if rowcount:
                saved += 1
            else:
                skipped += 1

        msg = f"Attendance saved for {saved} student(s)."
        if skipped:
            msg += f" {skipped} record(s) skipped (already marked for that date/subject)."
        flash(msg, "success" if saved else "warning")
        return redirect(url_for("attendance_history"))

    return render_template(
        "attendance.html",
        students=students_list,
        subjects=subjects_list,
        today=date.today().isoformat(),
    )


@app.route("/attendance/history")
@login_required
def attendance_history():
    subject_id = request.args.get("subject_id", "")
    att_date   = request.args.get("date", "")
    student_q  = request.args.get("student_q", "").strip()

    sql = """
        SELECT a.attendance_id, a.date, a.status,
               s.roll_number, s.full_name AS student_name,
               sub.subject_code, sub.subject_name,
               u.username AS marked_by
        FROM attendance a
        JOIN students s   ON s.student_id   = a.student_id
        JOIN subjects sub ON sub.subject_id = a.subject_id
        LEFT JOIN users u ON u.user_id      = a.marked_by
        WHERE 1=1
    """
    params = []
    if subject_id:
        sql += " AND a.subject_id = %s"
        params.append(subject_id)
    if att_date:
        sql += " AND a.date = %s"
        params.append(att_date)
    if student_q:
        sql += " AND (s.full_name LIKE %s OR s.roll_number LIKE %s)"
        params += [f"%{student_q}%", f"%{student_q}%"]

    sql += " ORDER BY a.date DESC, s.roll_number"
    rows = database.query(sql, tuple(params))
    subjects_list = database.query("SELECT * FROM subjects ORDER BY subject_code")

    return render_template(
        "attendance_history.html",
        records=rows,
        subjects=subjects_list,
        subject_id=subject_id,
        att_date=att_date,
        student_q=student_q,
    )


# ──────────────────────────────────────────────────────────────
# Reports
# ──────────────────────────────────────────────────────────────

@app.route("/reports")
@login_required
def reports():
    subject_id = request.args.get("subject_id", "")
    dept       = request.args.get("department", "")

    sql = """
        SELECT
            s.student_id,
            s.roll_number,
            s.full_name,
            s.department,
            s.semester,
            sub.subject_code,
            sub.subject_name,
            COUNT(a.attendance_id)                                     AS total_classes,
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)       AS present_count,
            ROUND(
                SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)
                * 100.0 / COUNT(a.attendance_id), 1
            )                                                          AS attendance_pct
        FROM students s
        JOIN attendance a ON a.student_id = s.student_id
        JOIN subjects sub ON sub.subject_id = a.subject_id
        WHERE 1=1
    """
    params = []
    if subject_id:
        sql += " AND sub.subject_id = %s"
        params.append(subject_id)
    if dept:
        sql += " AND s.department = %s"
        params.append(dept)

    sql += """
        GROUP BY s.student_id, sub.subject_id
        HAVING total_classes > 0
        ORDER BY s.roll_number, sub.subject_code
    """
    rows = database.query(sql, tuple(params))
    subjects_list = database.query("SELECT * FROM subjects ORDER BY subject_code")

    # Distinct departments for filter
    depts = database.query(
        "SELECT DISTINCT department FROM students ORDER BY department"
    )

    return render_template(
        "reports.html",
        rows=rows,
        subjects=subjects_list,
        depts=depts,
        subject_id=subject_id,
        department=dept,
    )


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5001)
