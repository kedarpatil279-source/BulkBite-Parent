import sqlite3
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'hostel_pool.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    salt = "hostel_salt_2026"
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_session(user_id: int) -> str:
    token = secrets.token_hex(24)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user_id))
    conn.commit()
    conn.close()
    return token

def get_user_by_token(token: str):
    if not token:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.id, u.name, u.room_number, u.hostel_block, u.phone, u.upi_id, u.avatar_color, 
           u.role, u.status, u.college_id, u.created_at,
           COALESCE(c.name, 'Main Engineering Campus') as college_name,
           COALESCE(c.code, 'CAMPUS-1') as college_code
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    LEFT JOIN colleges c ON u.college_id = c.id
    WHERE s.token = ?
    ''', (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_session(token: str):
    if not token:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM system_settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO system_settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Colleges / Communities table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS colleges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        code TEXT NOT NULL,
        city TEXT NOT NULL DEFAULT '',
        state TEXT NOT NULL DEFAULT '',
        icon TEXT DEFAULT '🏫',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        room_number TEXT NOT NULL,
        hostel_block TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL DEFAULT '',
        upi_id TEXT DEFAULT '',
        avatar_color TEXT DEFAULT '#4F46E5',
        role TEXT DEFAULT 'student', -- 'student' or 'founder'
        status TEXT DEFAULT 'active', -- 'active' or 'blocked'
        college_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (college_id) REFERENCES colleges (id)
    )
    ''')

    # Sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # Order Pools table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host_id INTEGER NOT NULL,
        college_id INTEGER DEFAULT 1,
        title TEXT NOT NULL,
        platform TEXT NOT NULL,
        target_amount REAL NOT NULL DEFAULT 200.0,
        delivery_fee_saved REAL NOT NULL DEFAULT 40.0,
        order_time TEXT NOT NULL,
        gate_location TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open', -- open, ordering, on_the_way, at_gate, completed, cancelled
        delivery_eta TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (host_id) REFERENCES users (id),
        FOREIGN KEY (college_id) REFERENCES colleges (id)
    )
    ''')

    # Pool Items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pool_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pool_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        price REAL NOT NULL,
        product_link TEXT DEFAULT '',
        image_url TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pool_id) REFERENCES pools (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Payments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pool_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- pending, paid
        paid_at TIMESTAMP,
        FOREIGN KEY (pool_id) REFERENCES pools (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # Notifications / Activity table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pool_id INTEGER,
        college_id INTEGER DEFAULT 1,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'info', -- new_pool, item_added, status_change, gate_alert, admin_broadcast
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # System Settings & Helpline
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')

    conn.commit()

    # Dynamic migrations for existing databases
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [r['name'] for r in cursor.fetchall()]
    if 'role' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
    if 'status' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    if 'college_id' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN college_id INTEGER DEFAULT 1")
    if 'password_hash' not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
        cursor.execute("UPDATE users SET password_hash = ? WHERE password_hash = ''", (hash_password('hostel123'),))

    cursor.execute("PRAGMA table_info(pools)")
    pool_cols = [r['name'] for r in cursor.fetchall()]
    if 'college_id' not in pool_cols:
        cursor.execute("ALTER TABLE pools ADD COLUMN college_id INTEGER DEFAULT 1")

    cursor.execute("PRAGMA table_info(notifications)")
    notif_cols = [r['name'] for r in cursor.fetchall()]
    if 'college_id' not in notif_cols:
        cursor.execute("ALTER TABLE notifications ADD COLUMN college_id INTEGER DEFAULT 1")

    conn.commit()

    # Seed Default Colleges / Communities
    cursor.execute('SELECT COUNT(*) as count FROM colleges')
    if cursor.fetchone()['count'] == 0:
        seed_colleges(conn)

    # Seed Default Helpline & App Settings
    cursor.execute('SELECT COUNT(*) as count FROM system_settings')
    if cursor.fetchone()['count'] == 0:
        seed_settings(conn)

    # Seed initial students and Founder account
    seed_founder_and_students(conn)

    conn.close()

def seed_colleges(conn):
    cursor = conn.cursor()
    colleges = [
        ("Engineering College Campus (Hostels 1-4)", "CAMPUS-1", "Pune", "Maharashtra", "🏛️"),
        ("COEP Technological University", "COEP", "Pune", "Maharashtra", "🎓"),
        ("IIT Bombay (Powai Hostels 1-18)", "IITB", "Mumbai", "Maharashtra", "🔬"),
        ("VJTI Mumbai (Hostels A, B, C, D)", "VJTI", "Mumbai", "Maharashtra", "⚡"),
        ("MIT World Peace University", "MIT-WPU", "Pune", "Maharashtra", "🌟"),
        ("BITS Pilani (Hostel Blocks)", "BITS", "Pilani", "Rajasthan", "🚀")
    ]
    cursor.executemany('''
    INSERT OR IGNORE INTO colleges (name, code, city, state, icon)
    VALUES (?, ?, ?, ?, ?)
    ''', colleges)
    conn.commit()
    print("Seeded college communities.")

def seed_settings(conn):
    cursor = conn.cursor()
    settings = [
        ("helpline_phone", "+91 8390461240"),
        ("helpline_email", "support@bulkbite.in"),
        ("founder_name", "Kedar Patil"),
        ("founder_contact", "+91 8390461240"),
        ("live_announcement", "🚀 BulkBite is now live across college communities! Zero delivery fee enabled."),
        ("announcement_active", "1")
    ]
    cursor.executemany('''
    INSERT OR REPLACE INTO system_settings (key, value)
    VALUES (?, ?)
    ''', settings)
    conn.commit()

def seed_founder_and_students(conn):
    cursor = conn.cursor()
    default_hash = hash_password("hostel123")

    # Founder Kedar Patil Account
    founder_phone = "8390461240"
    cursor.execute('SELECT id FROM users WHERE phone = ?', (founder_phone,))
    founder = cursor.fetchone()

    if founder:
        cursor.execute('''
        UPDATE users 
        SET role = 'founder', status = 'active', name = 'Kedar Patil (Founder)', upi_id = 'kedarpatil@upi', college_id = 1
        WHERE id = ?
        ''', (founder['id'],))
    else:
        cursor.execute('''
        INSERT INTO users (name, room_number, hostel_block, phone, password_hash, upi_id, avatar_color, role, status, college_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'founder', 'active', 1)
        ''', ("Kedar Patil (Founder)", "Founder HQ", "Executive Block", founder_phone, default_hash, "kedarpatil@upi", "#F59E0B"))

    # Seed Sample Students if empty
    students = [
        ("Rahul Sharma", "Room 304", "Hostel 3 (Boys)", "9876543210", default_hash, "rahul304@oksbi", "#3B82F6", "student", 1),
        ("Aman Verma", "Room 210", "Hostel 3 (Boys)", "9811223344", default_hash, "amanverma@upi", "#10B981", "student", 1),
        ("Priya Nair", "Room 102", "Hostel 1 (Girls)", "9822334455", default_hash, "priya.nair@paytm", "#EC4899", "student", 1),
        ("Vikram Singh", "Room 415", "Hostel 4 (Boys)", "9833445566", default_hash, "vikram.s@icici", "#8B5CF6", "student", 2),
        ("Sneha Patel", "Room 205", "Hostel 2 (Girls)", "9844556677", default_hash, "sneha.p@okaxis", "#F59E0B", "student", 2)
    ]

    for s in students:
        cursor.execute('SELECT id FROM users WHERE phone = ?', (s[3],))
        if not cursor.fetchone():
            cursor.execute('''
            INSERT INTO users (name, room_number, hostel_block, phone, password_hash, upi_id, avatar_color, role, college_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', s)

    # Seed sample pool if none exist
    cursor.execute('SELECT COUNT(*) as count FROM pools')
    if cursor.fetchone()['count'] == 0:
        cursor.execute('SELECT id FROM users WHERE phone = "9876543210"')
        rahul = cursor.fetchone()
        if rahul:
            now = datetime.now()
            time1 = (now + timedelta(minutes=25)).strftime('%I:%M %p')
            cursor.execute('''
            INSERT INTO pools (host_id, college_id, title, platform, target_amount, delivery_fee_saved, order_time, gate_location, status, notes)
            VALUES (?, 1, 'Midnight Maggi & Energy Drinks 🍜⚡', 'Blinkit', 200.0, 40.0, ?, 'Main Hostel Gate', 'open', 'Ordering in 25 mins!')
            ''', (rahul['id'], time1))
            p_id = cursor.lastrowid
            cursor.execute('''
            INSERT INTO pool_items (pool_id, user_id, item_name, quantity, price, notes)
            VALUES (?, ?, 'Maggi 2-Minute Noodles (Pack of 4)', 1, 56.0, 'Masala flavor')
            ''', (p_id, rahul['id']))

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("BulkBite database initialized with Founder and multi-college support.")
