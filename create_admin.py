"""
create_admin.py — Run once to create the first admin user.

Usage:
    python create_admin.py

Credentials are read from environment variables so they are
never stored in plain text in this file.
"""

import os
import bcrypt
from dotenv import load_dotenv
import db as database

load_dotenv()

def main():
    username  = input("Enter admin username  [admin]: ").strip() or "admin"
    full_name = input("Enter admin full name [Admin User]: ").strip() or "Admin User"
    password  = input("Enter admin password  : ").strip()

    if not password:
        print("Password cannot be empty. Aborting.")
        return

    # Hash password with bcrypt (salt is auto-generated)
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Check if username already exists
    existing = database.query(
        "SELECT user_id FROM users WHERE username = %s",
        (username,),
        fetchone=True,
    )
    if existing:
        print(f"User '{username}' already exists. Use a different username or edit in MySQL.")
        return

    database.execute(
        "INSERT INTO users (username, password, full_name, role) VALUES (%s, %s, %s, 'admin')",
        (username, hashed, full_name),
    )
    print(f"\nAdmin user '{username}' created successfully. You can now log in.")

if __name__ == "__main__":
    main()
