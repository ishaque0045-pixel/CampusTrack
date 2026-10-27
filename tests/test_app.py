"""
tests/test_app.py — Automated tests for CampusTrack.

Tests use pytest-flask fixtures and monkeypatching so they do NOT
touch the production MySQL database.  All database calls in app.py
go through the `db` module; we mock that module's `query` and
`execute` functions to return controlled data.

Run tests:
    cd CampusTrack
    pytest tests/ -v
"""

import sys
import os
import bcrypt
import pytest

# Make the project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ──────────────────────────────────────────────────────────────
# App fixture
# ──────────────────────────────────────────────────────────────

@pytest.fixture()
def app_instance(monkeypatch):
    """
    Return a Flask test app with DB calls monkeypatched.
    Each test can refine the patches further.
    """
    # Patch DB before importing app so the pool is never created
    import db as database_module

    monkeypatch.setattr(database_module, "query",   lambda *a, **kw: [] )
    monkeypatch.setattr(database_module, "execute", lambda *a, **kw: (1, 1))

    import app as flask_app
    flask_app.app.config["TESTING"]             = True
    flask_app.app.config["WTF_CSRF_ENABLED"]    = False
    flask_app.app.config["SECRET_KEY"]          = "test-secret"
    return flask_app.app


@pytest.fixture()
def client(app_instance):
    return app_instance.test_client()


# ──────────────────────────────────────────────────────────────
# Helper: simulate a logged-in session
# ──────────────────────────────────────────────────────────────

def login_session(client, app_instance):
    """Push a fake session so protected routes are accessible."""
    with client.session_transaction() as sess:
        sess["user_id"]   = 1
        sess["username"]  = "admin"
        sess["full_name"] = "Admin User"
        sess["role"]      = "admin"


# ──────────────────────────────────────────────────────────────
# TC-01  Login page loads
# ──────────────────────────────────────────────────────────────

def test_login_page_loads(client):
    """GET /login should return 200 and contain Login."""
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Login" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-02  Login with empty fields (server-side validation)
# ──────────────────────────────────────────────────────────────

def test_login_empty_fields(client):
    """POST /login with no data should flash validation errors."""
    resp = client.post("/login", data={"username": "", "password": ""},
                       follow_redirects=True)
    assert resp.status_code == 200
    # Both field errors should appear
    assert b"Username is required" in resp.data
    assert b"Password is required" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-03  Invalid credentials
# ──────────────────────────────────────────────────────────────

def test_login_invalid_credentials(client, app_instance, monkeypatch):
    """POST /login with wrong password should flash error message."""
    import db as database_module
    monkeypatch.setattr(database_module, "query", lambda *a, **kw: None)

    resp = client.post(
        "/login",
        data={"username": "nouser", "password": "wrongpass"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-04  Successful login
# ──────────────────────────────────────────────────────────────

def test_login_success(client, app_instance, monkeypatch):
    """POST /login with correct credentials should redirect to dashboard."""
    import db as database_module

    hashed = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    fake_user = {
        "user_id": 1, "username": "admin",
        "password": hashed, "full_name": "Admin User", "role": "admin",
    }
    monkeypatch.setattr(database_module, "query", lambda *a, **kw: fake_user)

    resp = client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/dashboard" in resp.headers["Location"]


# ──────────────────────────────────────────────────────────────
# TC-05  Protected route without login → redirect to /login
# ──────────────────────────────────────────────────────────────

def test_dashboard_requires_login(client):
    """GET /dashboard without session should redirect to login."""
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_students_requires_login(client):
    """GET /students without session should redirect to login."""
    resp = client.get("/students", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ──────────────────────────────────────────────────────────────
# TC-06  Dashboard loads when logged in
# ──────────────────────────────────────────────────────────────

def test_dashboard_logged_in(client, app_instance, monkeypatch):
    """GET /dashboard with session should return 200."""
    import db as database_module

    def mock_query(sql, params=(), fetchone=False):
        if fetchone:
            return {"cnt": 0}
        return []

    monkeypatch.setattr(database_module, "query", mock_query)
    login_session(client, app_instance)

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-07  Students list loads
# ──────────────────────────────────────────────────────────────

def test_students_list(client, app_instance, monkeypatch):
    import db as database_module
    monkeypatch.setattr(database_module, "query", lambda *a, **kw: [])
    login_session(client, app_instance)

    resp = client.get("/students")
    assert resp.status_code == 200
    assert b"Students" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-08  Add student with missing required fields → validation
# ──────────────────────────────────────────────────────────────

def test_add_student_missing_fields(client, app_instance, monkeypatch):
    import db as database_module
    monkeypatch.setattr(database_module, "query", lambda *a, **kw: None)
    login_session(client, app_instance)

    resp = client.post(
        "/students/add",
        data={"roll_number": "", "full_name": "", "department": "", "semester": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"required" in resp.data.lower()


# ──────────────────────────────────────────────────────────────
# TC-09  Add student – duplicate roll number is rejected
# ──────────────────────────────────────────────────────────────

def test_add_student_duplicate_roll(client, app_instance, monkeypatch):
    import db as database_module

    # query returns existing student (duplicate found)
    monkeypatch.setattr(database_module, "query",
                        lambda *a, **kw: {"student_id": 99})

    login_session(client, app_instance)
    resp = client.post(
        "/students/add",
        data={
            "roll_number": "CS2401",
            "full_name":   "Test",
            "department":  "CS",
            "semester":    "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-10  Add student success → redirect to /students
# ──────────────────────────────────────────────────────────────

def test_add_student_success(client, app_instance, monkeypatch):
    import db as database_module

    # No duplicate found
    monkeypatch.setattr(database_module, "query",  lambda *a, **kw: None)
    monkeypatch.setattr(database_module, "execute", lambda *a, **kw: (5, 1))

    login_session(client, app_instance)
    resp = client.post(
        "/students/add",
        data={
            "roll_number": "CS9999",
            "full_name":   "Test Student",
            "department":  "CS",
            "semester":    "1",
            "email":       "",
            "phone":       "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/students" in resp.headers["Location"]


# ──────────────────────────────────────────────────────────────
# TC-11  Delete student
# ──────────────────────────────────────────────────────────────

def test_delete_student(client, app_instance, monkeypatch):
    import db as database_module
    monkeypatch.setattr(database_module, "execute", lambda *a, **kw: (0, 1))
    login_session(client, app_instance)

    resp = client.post("/students/1/delete", follow_redirects=False)
    assert resp.status_code == 302
    assert "/students" in resp.headers["Location"]


# ──────────────────────────────────────────────────────────────
# TC-12  Mark attendance – missing subject/date → validation
# ──────────────────────────────────────────────────────────────

def test_attendance_missing_fields(client, app_instance, monkeypatch):
    import db as database_module
    monkeypatch.setattr(database_module, "query", lambda *a, **kw: [])
    login_session(client, app_instance)

    resp = client.post(
        "/attendance",
        data={"subject_id": "", "date": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Please select" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-13  Duplicate attendance → INSERT IGNORE, skipped count
# ──────────────────────────────────────────────────────────────

def test_attendance_duplicate_skipped(client, app_instance, monkeypatch):
    """
    When execute returns rowcount=0, it means INSERT IGNORE skipped
    the row (duplicate). The flash message should mention 'skipped'.
    """
    import db as database_module

    fake_students = [
        {"student_id": 1, "roll_number": "CS01",
         "full_name": "A", "department": "CS"},
    ]
    monkeypatch.setattr(database_module, "query", lambda *a, **kw: fake_students)
    monkeypatch.setattr(database_module, "execute", lambda *a, **kw: (0, 0))  # skipped

    login_session(client, app_instance)
    resp = client.post(
        "/attendance",
        data={"subject_id": "1", "date": "2025-01-01",
              "status_1": "Present"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"skipped" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-14  Reports page loads
# ──────────────────────────────────────────────────────────────

def test_reports_page(client, app_instance, monkeypatch):
    import db as database_module
    monkeypatch.setattr(database_module, "query", lambda *a, **kw: [])
    login_session(client, app_instance)

    resp = client.get("/reports")
    assert resp.status_code == 200
    assert b"Reports" in resp.data


# ──────────────────────────────────────────────────────────────
# TC-15  Logout clears session
# ──────────────────────────────────────────────────────────────

def test_logout(client, app_instance):
    login_session(client, app_instance)
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # After logout, dashboard should redirect again
    resp2 = client.get("/dashboard", follow_redirects=False)
    assert resp2.status_code == 302
