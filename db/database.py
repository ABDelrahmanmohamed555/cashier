import sqlite3
import os
from datetime import datetime
from config import DB_PATH, ADMIN_USERNAME, ADMIN_PASSWORD, EMPLOYEE_USERNAME, EMPLOYEE_PASSWORD


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 3000")
    except Exception:
        pass
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'employee',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            device_type TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM employees")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO employees (name, username, password, role) VALUES (?, ?, ?, ?)",
            ("المدير", ADMIN_USERNAME, ADMIN_PASSWORD, "admin"),
        )

    conn.commit()
    conn.close()


def authenticate(username, password):
    # 1) تحقق من config (للسماح بتغيير الباسوورد مباشرة من الملف)
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE role = 'admin' LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        admin_id = row[0] if row else 1
        return {
            "id": admin_id,
            "name": "admin",
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "role": "admin",
        }

    if username == EMPLOYEE_USERNAME and password == EMPLOYEE_PASSWORD:
        return {
            "id": 1,
            "name": "normal",
            "username": EMPLOYEE_USERNAME,
            "password": EMPLOYEE_PASSWORD,
            "role": "employee",
        }

    # 2) تحقق من قاعدة البيانات أيضاً (لدعم تغيير الباسوورد من الواجهة أو يدوياً في DB)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, username, password, role FROM employees WHERE username=? AND password=?", (username, password))
        row = cur.fetchone()
        conn.close()
        if row:
            return {"id": row["id"], "name": row["name"], "username": row["username"], "password": row["password"], "role": row["role"]}
    except Exception:
        pass

    return None


def get_next_order_number(date_str=None):
    conn = get_connection()
    cursor = conn.cursor()
    target_date = date_str or datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COALESCE(MAX(order_number), 0) + 1 FROM orders WHERE DATE(created_at) = ?",
        (target_date,),
    )
    result = cursor.fetchone()[0]
    conn.close()
    return result


def add_customer(name, phone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO customers (name, phone) VALUES (?, ?)",
        (name, phone),
    )
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    return customer_id


def add_order(customer_id, employee_id, device_type, notes="", created_at=None):
    conn = get_connection()
    cursor = conn.cursor()
    order_number = get_next_order_number(created_at[:10] if created_at else None)
    now = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO orders (order_number, customer_id, employee_id, device_type, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (order_number, customer_id, employee_id, device_type, notes, now),
    )
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id, order_number


def get_today_orders():
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        """
        SELECT o.id, o.order_number, c.name as customer_name, c.phone,
               o.device_type, o.notes, o.created_at, e.name as employee_name
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN employees e ON o.employee_id = e.id
        WHERE DATE(o.created_at) = ?
        ORDER BY o.order_number ASC
        """,
        (today,),
    )
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders


def get_all_orders():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT o.id, o.order_number, c.name as customer_name, c.phone,
               o.device_type, o.notes, o.created_at, e.name as employee_name
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        JOIN employees e ON o.employee_id = e.id
        ORDER BY o.created_at DESC
        """
    )
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders


def search_orders(name="", phone="", device="", date_from="", date_to=""):
    conn = get_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if name:
        conditions.append("c.name LIKE ?")
        params.append(f"%{name}%")
    if phone:
        conditions.append("c.phone LIKE ?")
        params.append(f"%{phone}%")
    if device:
        conditions.append("o.device_type LIKE ?")
        params.append(f"%{device}%")
    if date_from:
        conditions.append("DATE(o.created_at) >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(o.created_at) <= ?")
        params.append(date_to)

    where = " AND ".join(conditions) if conditions else "1=1"

    cursor.execute(
        f"""
        SELECT o.id, o.order_number, c.name as customer_name, c.phone,
               o.device_type, o.notes, o.created_at
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE {where}
        ORDER BY o.created_at DESC
        """,
        params,
    )
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders


def add_employee(name, username, password, role="employee"):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO employees (name, username, password, role) VALUES (?, ?, ?, ?)",
            (name, username, password, role),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False



def reset_admin(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE employees SET username = ?, password = ? WHERE role = 'admin'",
        (username, password),
    )
    conn.commit()
    conn.close()


def change_password(user_id, new_password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE employees SET password = ? WHERE id = ?",
        (new_password, user_id),
    )
    conn.commit()
    conn.close()


def update_order(order_id, customer_name, customer_phone, device_type, notes):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT customer_id FROM orders WHERE id = ?",
        (order_id,),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    customer_id = row[0]
    cursor.execute(
        "UPDATE customers SET name = ?, phone = ? WHERE id = ?",
        (customer_name, customer_phone, customer_id),
    )
    cursor.execute(
        "UPDATE orders SET device_type = ?, notes = ? WHERE id = ?",
        (device_type, notes, order_id),
    )
    conn.commit()
    conn.close()
    return True


def delete_order(order_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    customer_id = row[0]
    cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    cursor.execute(
        "DELETE FROM customers WHERE id = ? AND NOT EXISTS (SELECT 1 FROM orders WHERE customer_id = ?)",
        (customer_id, customer_id),
    )
    conn.commit()
    conn.close()
    return True
