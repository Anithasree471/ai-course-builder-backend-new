from database import get_connection

def migrate_add_role():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='users'
    """)
    table = cursor.fetchone()

    if not table:
        print("Users table does not exist yet.")
        conn.close()
        return

    cursor.execute("PRAGMA table_info(users)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "role" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        cursor.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
        conn.commit()
        print("Role column added successfully.")
    else:
        print("Role column already exists.")

    conn.close()

if __name__ == "__main__":
    migrate_add_role()