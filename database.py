import os
import sqlite3

DB_NAME = os.environ.get("DB_PATH", "ai_course_builder.db")

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn