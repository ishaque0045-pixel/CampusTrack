# CampusTrack — Student Attendance & Academic Management System

A complete college mini-project built with **Python 3 · Flask · MySQL 8 · Bootstrap 5**.

---

## Quick-Start (macOS — Beginner Friendly)

### Step 1 — Install Homebrew (if not installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2 — Install Python 3 and MySQL 8
```bash
brew install python mysql
```
Start MySQL:
```bash
brew services start mysql
```
Set a MySQL root password if prompted:
```bash
mysql_secure_installation
```

### Step 3 — Clone / Download the project
Put the `CampusTrack` folder wherever you like.

### Step 4 — Create a virtual environment
```bash
cd /path/to/CampusTrack
python3 -m venv venv
source venv/bin/activate
```
Your terminal prompt should now start with `(venv)`.

### Step 5 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 6 — Configure environment variables
```bash
cp .env.example .env
```
Open `.env` in any text editor and fill in:
```
DB_PASSWORD=your_mysql_root_password
SECRET_KEY=any-long-random-string-you-choose
```

### Step 7 — Create the database and tables
```bash
mysql -u root -p < schema.sql
```
Type your MySQL password when prompted.

### Step 8 — Create the admin user (first time only)
```bash
python create_admin.py
```
Follow the prompts. Example:
```
Enter admin username  [admin]:
Enter admin full name [Admin User]:
Enter admin password  : mysecretpassword
Admin user 'admin' created successfully.
```

### Step 9 — Run the application
```bash
python app.py
```
Open your browser at **http://127.0.0.1:5000**

### Step 10 — Run automated tests
```bash
pytest tests/ -v
```

---

## Project Structure
```
CampusTrack/
├── app.py               ← Flask routes and business logic
├── db.py                ← MySQL connection pool helper
├── schema.sql           ← Database schema and demo data
├── create_admin.py      ← One-time admin user creation
├── requirements.txt     ← Python package list
├── .env.example         ← Environment variable template
├── .gitignore
├── README.md
├── templates/
│   ├── base.html            ← Sidebar layout
│   ├── login.html
│   ├── dashboard.html
│   ├── students.html
│   ├── student_form.html    ← Used for Add and Edit
│   ├── subjects.html
│   ├── subject_form.html
│   ├── attendance.html      ← Mark attendance
│   ├── attendance_history.html
│   └── reports.html         ← Attendance % report
├── static/
│   └── css/
│       └── style.css
└── tests/
    ├── __init__.py
    └── test_app.py
```

---

## Common Errors and Fixes

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | venv not active | Run `source venv/bin/activate` |
| `mysql.connector.errors.ProgrammingError: Table doesn't exist` | Schema not loaded | Run `mysql -u root -p < schema.sql` |
| `Access denied for user 'root'` | Wrong DB_PASSWORD in .env | Edit `.env` and set correct password |
| `Address already in use` | Port 5000 taken | Run `python app.py` — it will say which port; or change `port=5000` in app.py |
| `Can't connect to MySQL server` | MySQL not running | Run `brew services start mysql` |
| `bcrypt` import error | Not installed | Run `pip install bcrypt` |

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | 127.0.0.1 | MySQL server host |
| `DB_PORT` | 3306 | MySQL port |
| `DB_USER` | root | MySQL username |
| `DB_PASSWORD` | *(empty)* | **Must set this** |
| `DB_NAME` | campustrack_db | Database name |
| `SECRET_KEY` | change-me… | **Must set to a random string** |
