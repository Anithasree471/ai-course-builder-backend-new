from database import get_connection
from werkzeug.security import generate_password_hash

def create_admin():
    conn = get_connection()
    cursor = conn.cursor()

    name = "Admin"
    email = "admin@gmail.com"
    password = "admin123"
    hashed_password = generate_password_hash(password)
    role = "admin"

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
        conn.commit()
        print("Admin already exists. Role updated to admin.")
    else:
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, role)
        )
        conn.commit()
        print("Admin created successfully.")

    conn.close()

if __name__ == "__main__":
    create_admin()