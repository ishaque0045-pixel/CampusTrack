"""
db.py — Database connection helper for CampusTrack.

We use mysql-connector-python's connection-pooling so that each
Flask request can grab a connection from the pool rather than
opening a new TCP connection every time.
"""

import os
import mysql.connector
from mysql.connector import pooling

# ──────────────────────────────────────────────────────────────
# Read credentials from environment variables (set in .env or
# your shell before starting the app).
# ──────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "127.0.0.1"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "campustrack_db"),
    "charset":  "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": True,
}

_pool = None


def _get_pool():
    """Lazily create the connection pool (singleton)."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="campustrack",
            pool_size=5,
            **DB_CONFIG,
        )
    return _pool


def get_db():
    """
    Return a connection from the pool.
    Call .close() when done — it returns the connection to the pool,
    it does NOT close the physical TCP connection.
    """
    return _get_pool().get_connection()


def query(sql: str, params: tuple = (), fetchone: bool = False):
    """
    Execute a SELECT and return rows.
    Uses a parameterised query to prevent SQL injection.
    """
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchone() if fetchone else cur.fetchall()
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()):
    """
    Execute INSERT / UPDATE / DELETE.
    Returns (lastrowid, rowcount).
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.lastrowid, cur.rowcount
    finally:
        conn.close()
