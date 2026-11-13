import os
import json
import sqlite3
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime
import database

PORT = int(os.environ.get('PORT', 8080))
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'public')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'public', 'uploads')

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class HostelPoolHandler(SimpleHTTPRequestHandler):
    directory = STATIC_DIR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def send_json(self, data, status_code=200):
        body = json.dumps(data, default=str).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def read_json_body(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                raw_data = self.rfile.read(content_length).decode('utf-8')
                return json.loads(raw_data)
        except Exception as e:
            print("[JSON Parse Error]:", e)
        return {}

    def get_token(self):
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header.split('Bearer ', 1)[1].strip()
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        return query.get('token', [''])[0]

    def get_current_user(self):
        token = self.get_token()
        user = database.get_user_by_token(token) if token else None
        if user and user.get('status') == 'blocked':
            return None # Blocked users cannot perform actions
        return user

    def require_founder(self):
        user = self.get_current_user()
        if not user or user.get('role') != 'founder':
            self.send_json({"error": "Unauthorized: Founder access required."}, 403)
            return None
        return user

    # ------------------ REQUEST ROUTING ------------------ #

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        query = parse_qs(parsed.query)

        # Health & Version Check
        if path in ('/api/version', '/api/auth/version'):
            return self.send_json({
                "app": "BulkBite",
                "founder": "Kedar Patil",
                "version": "3.0-founder-multicampus",
                "auth_enabled": True
            })

        # Public Settings & Helpline
        if path == '/api/settings':
            return self.handle_get_settings()

        # College Communities
        if path == '/api/colleges':
            return self.handle_get_colleges()

        # Auth & Profile
        if path in ('/api/auth/me', '/api/me', '/auth/me'):
            return self.handle_auth_me()

        # Pools & Feeds
        if path == '/api/pools':
            return self.handle_get_pools(query)
        elif path.startswith('/api/pools/') and not path.endswith('/items'):
            parts = path.split('/')
            if len(parts) >= 4 and parts[3].isdigit():
                return self.handle_get_pool_detail(int(parts[3]))
        elif path == '/api/notifications':
            return self.handle_get_notifications(query)
        elif path == '/api/stats':
            return self.handle_get_stats()
        elif path == '/api/health':
            return self.send_json({"status": "ok", "time": datetime.now().isoformat(), "version": "3.0"})

        # Founder / Admin Endpoints
        elif path == '/api/admin/users':
            return self.handle_admin_get_users()
        elif path == '/api/admin/stats':
            return self.handle_admin_get_stats()

        # Static assets fallback
        if path == '/' or path == '':
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        print(f"[HTTP POST] {path}")

        # Authentication routes
        if path in ('/api/auth/login', '/api/login', '/auth/login', '/api/users/login'):
            return self.handle_auth_login()
        elif path in ('/api/auth/register', '/api/register', '/auth/register', '/api/users'):
            return self.handle_auth_register()
        elif path in ('/api/auth/logout', '/api/logout', '/auth/logout'):
            return self.handle_auth_logout()

        # Order Pool routes
        elif path == '/api/pools':
            return self.handle_create_pool()
        elif path.startswith('/api/pools/') and path.endswith('/items'):
            parts = path.split('/')
            if len(parts) >= 4 and parts[3].isdigit():
                return self.handle_add_pool_item(int(parts[3]))
        elif path == '/api/upload':
            return self.handle_upload_file()
        elif path.startswith('/api/pools/') and path.endswith('/broadcast'):
            parts = path.split('/')
            if len(parts) >= 4 and parts[3].isdigit():
                return self.handle_broadcast_message(int(parts[3]))

        # Founder / Admin Actions
        elif path == '/api/admin/colleges':
            return self.handle_admin_create_college()
        elif path == '/api/admin/broadcast':
            return self.handle_admin_global_broadcast()

        print(f"[404 Not Found] Unrecognized POST path: {path}")
        self.send_json({"error": f"Endpoint not found: {path}"}, 404)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path.startswith('/api/pools/') and path.endswith('/status'):
            parts = path.split('/')
            if len(parts) >= 4 and parts[3].isdigit():
                return self.handle_update_pool_status(int(parts[3]))
        elif path.startswith('/api/pools/') and path.endswith('/payments'):
            parts = path.split('/')
            if len(parts) >= 4 and parts[3].isdigit():
                return self.handle_update_payment_status(int(parts[3]))

        # Founder / Admin Moderation
        elif path.startswith('/api/admin/users/') and path.endswith('/status'):
            parts = path.split('/')
            if len(parts) >= 5 and parts[4].isdigit():
                return self.handle_admin_update_user_status(int(parts[4]))
        elif path == '/api/admin/settings':
            return self.handle_admin_update_settings()

        self.send_json({"error": "Endpoint not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path.startswith('/api/pools/') and '/items/' in path:
            parts = path.split('/')
            pool_id = int(parts[3])
            item_id = int(parts[5])
            return self.handle_delete_pool_item(pool_id, item_id)
        elif path.startswith('/api/pools/'):
            parts = path.split('/')
            if len(parts) == 4 and parts[3].isdigit():
                return self.handle_delete_pool(int(parts[3]))

        # Founder / Admin Deletions
        elif path.startswith('/api/admin/users/'):
            parts = path.split('/')
            if len(parts) == 5 and parts[4].isdigit():
                return self.handle_admin_delete_user(int(parts[4]))
        elif path.startswith('/api/admin/colleges/'):
            parts = path.split('/')
            if len(parts) == 5 and parts[4].isdigit():
                return self.handle_admin_delete_college(int(parts[4]))

        self.send_json({"error": "Endpoint not found"}, 404)

    # ------------------ AUTH HANDLERS ------------------ #

    def handle_auth_register(self):
        data = self.read_json_body()
        name = data.get('name', '').strip()
        room = data.get('room_number', '').strip()
        hostel = data.get('hostel_block', 'Hostel 3').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '').strip()
        upi_id = data.get('upi_id', '').strip()
        college_id = int(data.get('college_id', 1))

        if not name or not room or not phone or not password:
            return self.send_json({"error": "Name, Room Number, Phone, and Password are required"}, 400)

        if len(password) < 4:
            return self.send_json({"error": "Password must be at least 4 characters long"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, status FROM users WHERE phone = ?', (phone,))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            if existing['status'] == 'blocked':
                return self.send_json({"error": "This phone number has been blocked by the founder for community guideline violations."}, 403)
            return self.send_json({"error": f"An account with phone number {phone} already exists. Please log in."}, 400)

        colors = ['#3B82F6', '#10B981', '#EC4899', '#8B5CF6', '#F59E0B', '#06B6D4', '#EF4444', '#14B8A6']
        import random
        color = random.choice(colors)
        pwd_hash = database.hash_password(password)

        try:
            cursor.execute('''
            INSERT INTO users (name, room_number, hostel_block, phone, password_hash, upi_id, avatar_color, college_id, role, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'student', 'active')
            ''', (name, room, hostel, phone, pwd_hash, upi_id, color, college_id))
            user_id = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return self.send_json({"error": "Phone number already in use"}, 400)

        cursor.execute('''
        SELECT u.id, u.name, u.room_number, u.hostel_block, u.phone, u.upi_id, u.avatar_color, u.role, u.status, u.college_id,
               COALESCE(c.name, 'Main Engineering Campus') as college_name
        FROM users u
        LEFT JOIN colleges c ON u.college_id = c.id
        WHERE u.id = ?
        ''', (user_id,))
        user = dict(cursor.fetchone())
        conn.close()

        token = database.create_session(user_id)
        print(f"[AUTH] Registered new student: {user['name']} ({user['room_number']}) at college #{college_id}")
        self.send_json({"user": user, "token": token}, 201)

    def handle_auth_login(self):
        data = self.read_json_body()
        phone = data.get('phone', '').strip()
        password = data.get('password', '').strip()

        if not phone or not password:
            return self.send_json({"error": "Phone number and password are required"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT u.*, COALESCE(c.name, 'Main Engineering Campus') as college_name, COALESCE(c.code, 'CAMPUS-1') as college_code
        FROM users u
        LEFT JOIN colleges c ON u.college_id = c.id
        WHERE u.phone = ?
        ''', (phone,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            print(f"[AUTH FAIL] No user found for phone: {phone}")
            return self.send_json({"error": f"No student account found with phone {phone}. Please check or sign up."}, 401)

        user = dict(row)
        if user.get('status') == 'blocked':
            print(f"[BLOCKED USER LOGIN BLOCKED] Phone: {phone}")
            return self.send_json({
                "error": "🚨 Your account has been suspended by Founder KEDAR PATIL for violating community rules. Please contact the Helpline."
            }, 403)

        if not database.verify_password(password, user['password_hash']):
            print(f"[AUTH FAIL] Incorrect password for phone: {phone}")
            return self.send_json({"error": "Incorrect password. Default demo password is: hostel123"}, 401)

        token = database.create_session(user['id'])
        print(f"[AUTH SUCCESS] Logged in: {user['name']} ({user['room_number']}) - Role: {user['role']}")

        user_clean = {
            "id": user['id'],
            "name": user['name'],
            "room_number": user['room_number'],
            "hostel_block": user['hostel_block'],
            "phone": user['phone'],
            "upi_id": user['upi_id'],
            "avatar_color": user['avatar_color'],
            "role": user.get('role', 'student'),
            "status": user.get('status', 'active'),
            "college_id": user.get('college_id', 1),
            "college_name": user.get('college_name', 'Main Engineering Campus'),
            "college_code": user.get('college_code', 'CAMPUS-1')
        }

        self.send_json({"user": user_clean, "token": token})

    def handle_auth_me(self):
        user = self.get_current_user()
        if not user:
            return self.send_json({"authenticated": False})
        return self.send_json({"authenticated": True, "user": user})

    def handle_auth_logout(self):
        token = self.get_token()
        if token:
            database.delete_session(token)
        self.send_json({"message": "Logged out successfully"})

    # ------------------ SETTINGS & COMMUNITIES ------------------ #

    def handle_get_settings(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM system_settings')
        settings = {r['key']: r['value'] for r in cursor.fetchall()}
        conn.close()
        self.send_json(settings)

    def handle_get_colleges(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT c.*, 
               COUNT(DISTINCT u.id) as student_count,
               COUNT(DISTINCT p.id) as pool_count
        FROM colleges c
        LEFT JOIN users u ON u.college_id = c.id
        LEFT JOIN pools p ON p.college_id = c.id
        GROUP BY c.id
        ORDER BY c.name ASC
        ''')
        colleges = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json(colleges)

    # ------------------ ORDER POOL HANDLERS ------------------ #

    def handle_get_pools(self, query):
        status_filter = query.get('status', ['all'])[0]
        platform_filter = query.get('platform', ['all'])[0]
        college_id_filter = query.get('college_id', ['all'])[0]

        conn = database.get_connection()
        cursor = conn.cursor()

        sql = '''
        SELECT p.*, 
               u.name as host_name, u.room_number as host_room, u.hostel_block as host_block, 
               u.phone as host_phone, u.upi_id as host_upi, u.avatar_color as host_avatar,
               c.name as college_name, c.code as college_code,
               COALESCE(SUM(pi.price * pi.quantity), 0) as current_total,
               COUNT(DISTINCT pi.id) as item_count,
               COUNT(DISTINCT pi.user_id) as participant_count
        FROM pools p
        JOIN users u ON p.host_id = u.id
        LEFT JOIN colleges c ON p.college_id = c.id
        LEFT JOIN pool_items pi ON p.id = pi.pool_id
        WHERE 1=1
        '''
        params = []

        if status_filter != 'all':
            sql += ' AND p.status = ?'
            params.append(status_filter)
        if platform_filter != 'all':
            sql += ' AND LOWER(p.platform) = LOWER(?)'
            params.append(platform_filter)
        if college_id_filter != 'all' and college_id_filter.isdigit():
            sql += ' AND p.college_id = ?'
            params.append(int(college_id_filter))

        sql += ' GROUP BY p.id ORDER BY p.created_at DESC'

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        pools = []
        for r in rows:
            pool = dict(r)
            current_total = float(pool['current_total'])
            target = float(pool['target_amount'])
            progress = min(100.0, round((current_total / target) * 100.0, 1)) if target > 0 else 100.0
            remaining = max(0.0, round(target - current_total, 2))

            pool['progress_percent'] = progress
            pool['remaining_amount'] = remaining
            pool['is_target_reached'] = current_total >= target
            pools.append(pool)

        conn.close()
        self.send_json(pools)

    def handle_get_pool_detail(self, pool_id):
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT p.*, 
               u.name as host_name, u.room_number as host_room, u.hostel_block as host_block, 
               u.phone as host_phone, u.upi_id as host_upi, u.avatar_color as host_avatar,
               c.name as college_name, c.code as college_code
        FROM pools p
        JOIN users u ON p.host_id = u.id
        LEFT JOIN colleges c ON p.college_id = c.id
        WHERE p.id = ?
        ''', (pool_id,))
        pool_row = cursor.fetchone()
        if not pool_row:
            conn.close()
            return self.send_json({"error": "Order pool not found"}, 404)

        pool = dict(pool_row)

        cursor.execute('''
        SELECT pi.*, u.name as user_name, u.room_number as user_room, u.phone as user_phone, u.avatar_color as user_avatar
        FROM pool_items pi
        JOIN users u ON pi.user_id = u.id
        WHERE pi.pool_id = ?
        ORDER BY pi.created_at ASC
        ''', (pool_id,))
        items = [dict(row) for row in cursor.fetchall()]

        cursor.execute('SELECT * FROM payments WHERE pool_id = ?', (pool_id,))
        payments = {row['user_id']: dict(row) for row in cursor.fetchall()}

        participants_map = {}
        total_amount = 0.0

        for item in items:
            uid = item['user_id']
            item_subtotal = float(item['price']) * int(item['quantity'])
            total_amount += item_subtotal

            if uid not in participants_map:
                pay_info = payments.get(uid, {})
                participants_map[uid] = {
                    "user_id": uid,
                    "name": item['user_name'],
                    "room_number": item['user_room'],
                    "phone": item['user_phone'],
                    "avatar_color": item['user_avatar'],
                    "items": [],
                    "total_amount": 0.0,
                    "payment_status": pay_info.get('status', 'pending'),
                    "is_host": (uid == pool['host_id'])
                }
            participants_map[uid]['items'].append(item)
            participants_map[uid]['total_amount'] = round(participants_map[uid]['total_amount'] + item_subtotal, 2)

        participants = list(participants_map.values())
        target = float(pool['target_amount'])
        pool['current_total'] = round(total_amount, 2)
        pool['remaining_amount'] = max(0.0, round(target - total_amount, 2))
        pool['progress_percent'] = min(100.0, round((total_amount / target) * 100.0, 1)) if target > 0 else 100.0
        pool['is_target_reached'] = total_amount >= target
        pool['items'] = items
        pool['participants'] = participants

        host_upi = pool['host_upi'] or 'hostel.pool@upi'
        pool['upi_qr_data'] = f"upi://pay?pa={host_upi}&pn={pool['host_name']}&cu=INR"

        conn.close()
        self.send_json(pool)

    def handle_create_pool(self):
        user = self.get_current_user()
        if not user:
            return self.send_json({"error": "Authentication required. Please log in to your student account."}, 401)

        data = self.read_json_body()
        host_id = user['id']
        college_id = int(data.get('college_id', user.get('college_id', 1)))
        title = data.get('title', '').strip()
        platform = data.get('platform', 'Blinkit').strip()
        target_amount = float(data.get('target_amount', 200.0))
        delivery_fee_saved = float(data.get('delivery_fee_saved', 40.0))
        order_time = data.get('order_time', '').strip()
        gate_location = data.get('gate_location', 'Main Hostel Gate').strip()
        notes = data.get('notes', '').strip()
        initial_item = data.get('initial_item', {})

        if not title or not order_time:
            return self.send_json({"error": "Title and Order Time are required"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO pools (host_id, college_id, title, platform, target_amount, delivery_fee_saved, order_time, gate_location, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        ''', (host_id, college_id, title, platform, target_amount, delivery_fee_saved, order_time, gate_location, notes))
        pool_id = cursor.lastrowid

        if initial_item and initial_item.get('item_name'):
            cursor.execute('''
            INSERT INTO pool_items (pool_id, user_id, item_name, quantity, price, product_link, image_url, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pool_id, host_id,
                initial_item.get('item_name', '').strip(),
                int(initial_item.get('quantity', 1)),
                float(initial_item.get('price', 0.0)),
                initial_item.get('product_link', '').strip(),
                initial_item.get('image_url', '').strip(),
                initial_item.get('notes', '').strip()
            ))

        host_desc = f"{user['name']} ({user['room_number']})"
        cursor.execute('''
        INSERT INTO notifications (pool_id, college_id, title, message, type)
        VALUES (?, ?, ?, 'new_pool')
        ''', (pool_id, college_id, f"New {platform} Order Pool!", f"{host_desc} opened a pool for {platform} - Ordering at {order_time}! Join to skip ₹{int(delivery_fee_saved)} delivery!"))

        conn.commit()
        conn.close()

        self.send_json({"id": pool_id, "message": "Pool created successfully!"}, 201)

    def handle_add_pool_item(self, pool_id):
        user = self.get_current_user()
        if not user:
            return self.send_json({"error": "Authentication required. Please log in to add items to this cart."}, 401)

        data = self.read_json_body()
        user_id = user['id']
        item_name = data.get('item_name', '').strip()
        quantity = int(data.get('quantity', 1))
        price = float(data.get('price', 0.0))
        product_link = data.get('product_link', '').strip()
        image_url = data.get('image_url', '').strip()
        notes = data.get('notes', '').strip()

        if not item_name or price <= 0:
            return self.send_json({"error": "Valid item name and price are required"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM pools WHERE id = ?', (pool_id,))
        pool = cursor.fetchone()
        if not pool:
            conn.close()
            return self.send_json({"error": "Pool not found"}, 404)
        if pool['status'] != 'open':
            conn.close()
            return self.send_json({"error": "This pool is closed for new items"}, 400)

        cursor.execute('''
        INSERT INTO pool_items (pool_id, user_id, item_name, quantity, price, product_link, image_url, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pool_id, user_id, item_name, quantity, price, product_link, image_url, notes))
        item_id = cursor.lastrowid

        cursor.execute('SELECT SUM(price * quantity) as total FROM pool_items WHERE pool_id = ?', (pool_id,))
        new_total = cursor.fetchone()['total'] or 0.0

        u_name = user['name']
        u_room = user['room_number']

        if new_total >= pool['target_amount']:
            cursor.execute('''
            INSERT INTO notifications (pool_id, college_id, title, message, type)
            VALUES (?, ?, ?, ?, 'target_reached')
            ''', (pool_id, pool['college_id'], "🎉 Free Delivery Goal Reached!", f"{u_name} ({u_room}) added '{item_name}'. Cart is now ₹{int(new_total)}! Delivery charges are ₹0!"))
        else:
            remaining = pool['target_amount'] - new_total
            cursor.execute('''
            INSERT INTO notifications (pool_id, college_id, title, message, type)
            VALUES (?, ?, ?, ?, 'item_added')
            ''', (pool_id, pool['college_id'], "Item Added to Cart", f"{u_name} ({u_room}) added '{item_name}' (₹{int(price)}). Only ₹{int(remaining)} more needed!"))

        conn.commit()
        conn.close()

        self.send_json({"id": item_id, "message": "Item added to cart!"}, 201)

    def handle_delete_pool_item(self, pool_id, item_id):
        user = self.get_current_user()
        if not user:
            return self.send_json({"error": "Authentication required"}, 401)

        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT pi.user_id as item_user, p.host_id as pool_host FROM pool_items pi JOIN pools p ON pi.pool_id = p.id WHERE pi.id = ? AND pi.pool_id = ?', (item_id, pool_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return self.send_json({"error": "Item not found"}, 404)

        if user['id'] != row['item_user'] and user['id'] != row['pool_host'] and user.get('role') != 'founder':
            conn.close()
            return self.send_json({"error": "You can only remove your own items"}, 403)

        cursor.execute('DELETE FROM pool_items WHERE id = ? AND pool_id = ?', (item_id, pool_id))
        conn.commit()
        conn.close()
        self.send_json({"message": "Item removed from cart"})

    def handle_delete_pool(self, pool_id):
        user = self.get_current_user()
        if not user:
            return self.send_json({"error": "Authentication required"}, 401)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT host_id FROM pools WHERE id = ?', (pool_id,))
        row = cursor.fetchone()
        if not row or (row['host_id'] != user['id'] and user.get('role') != 'founder'):
            conn.close()
            return self.send_json({"error": "Only the order host or founder can delete this pool"}, 403)

        cursor.execute('DELETE FROM pool_items WHERE pool_id = ?', (pool_id,))
        cursor.execute('DELETE FROM payments WHERE pool_id = ?', (pool_id,))
        cursor.execute('DELETE FROM pools WHERE id = ?', (pool_id,))
        conn.commit()
        conn.close()
        self.send_json({"message": "Pool deleted"})

    def handle_update_pool_status(self, pool_id):
        user = self.get_current_user()
        if not user:
            return self.send_json({"error": "Authentication required"}, 401)

        data = self.read_json_body()
        new_status = data.get('status')
        delivery_eta = data.get('delivery_eta', '').strip()

        valid_statuses = ['open', 'ordering', 'on_the_way', 'at_gate', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return self.send_json({"error": "Invalid status"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT p.*, u.name as host_name, u.room_number as host_room FROM pools p JOIN users u ON p.host_id = u.id WHERE p.id = ?', (pool_id,))
        pool = cursor.fetchone()
        if not pool:
            conn.close()
            return self.send_json({"error": "Pool not found"}, 404)

        if pool['host_id'] != user['id'] and user.get('role') != 'founder':
            conn.close()
            return self.send_json({"error": "Only the order host or founder can update this pool's status"}, 403)

        if delivery_eta:
            cursor.execute('UPDATE pools SET status = ?, delivery_eta = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, delivery_eta, pool_id))
        else:
            cursor.execute('UPDATE pools SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, pool_id))

        status_titles = {
            'ordering': "🛒 Order is Being Placed!",
            'on_the_way': "🚴 Order is On The Way!",
            'at_gate': "🚨 ORDER ARRIVED AT THE GATE!",
            'completed': "✅ Order Completed & Settled!",
            'cancelled': "❌ Order Cancelled"
        }

        status_messages = {
            'ordering': f"{pool['host_name']} ({pool['host_room']}) is currently placing the {pool['platform']} order.",
            'on_the_way': f"{pool['host_name']}: Order placed! Estimated delivery: {delivery_eta or '10-15 minutes'}.",
            'at_gate': f"🚨 HURRY! Delivery partner is at {pool['gate_location']}. Meet {pool['host_name']} to collect your items and clear UPI bill!",
            'completed': f"All items collected and bills settled for {pool['title']}.",
            'cancelled': f"The order pool was cancelled."
        }

        if new_status in status_titles:
            cursor.execute('''
            INSERT INTO notifications (pool_id, college_id, title, message, type)
            VALUES (?, ?, ?, ?, ?)
            ''', (pool_id, pool['college_id'], status_titles[new_status], status_messages[new_status], 'gate_alert' if new_status == 'at_gate' else 'status_change'))

        conn.commit()
        conn.close()

        self.send_json({"message": f"Status updated to {new_status}"})

    def handle_update_payment_status(self, pool_id):
        user = self.get_current_user()
        if not user:
            return self.send_json({"error": "Authentication required"}, 401)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT host_id FROM pools WHERE id = ?', (pool_id,))
        pool = cursor.fetchone()
        if not pool or (pool['host_id'] != user['id'] and user.get('role') != 'founder'):
            conn.close()
            return self.send_json({"error": "Only the order host can manage payment status"}, 403)

        data = self.read_json_body()
        target_user_id = data.get('user_id')
        status = data.get('status', 'pending')
        amount = float(data.get('amount', 0.0))

        if not target_user_id:
            conn.close()
            return self.send_json({"error": "Target User ID required"}, 400)

        cursor.execute('SELECT * FROM payments WHERE pool_id = ? AND user_id = ?', (pool_id, target_user_id))
        existing = cursor.fetchone()

        paid_at = datetime.now().isoformat() if status == 'paid' else None
        if existing:
            cursor.execute('UPDATE payments SET status = ?, paid_at = ? WHERE pool_id = ? AND user_id = ?', (status, paid_at, pool_id, target_user_id))
        else:
            cursor.execute('INSERT INTO payments (pool_id, user_id, amount, status, paid_at) VALUES (?, ?, ?, ?, ?)', (pool_id, target_user_id, amount, status, paid_at))

        conn.commit()
        conn.close()

        self.send_json({"message": f"Payment updated to {status}"})

    def handle_broadcast_message(self, pool_id):
        user = self.get_current_user()
        if not user:
            return self.send_json({"error": "Authentication required"}, 401)

        data = self.read_json_body()
        custom_message = data.get('message', '').strip()
        if not custom_message:
            return self.send_json({"error": "Message cannot be empty"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT p.*, u.name, u.room_number FROM pools p JOIN users u ON p.host_id = u.id WHERE p.id = ?', (pool_id,))
        pool = cursor.fetchone()

        if not pool:
            conn.close()
            return self.send_json({"error": "Pool not found"}, 404)

        if pool['host_id'] != user['id'] and user.get('role') != 'founder':
            conn.close()
            return self.send_json({"error": "Only the order host can send broadcasts"}, 403)

        cursor.execute('''
        INSERT INTO notifications (pool_id, college_id, title, message, type)
        VALUES (?, ?, ?, ?, 'gate_alert')
        ''', (pool_id, pool['college_id'], f"📢 Announcement from {user['name']} ({user['room_number']})", custom_message))

        conn.commit()
        conn.close()

        self.send_json({"message": "Broadcast sent to all students in pool!"})

    def handle_get_notifications(self, query):
        college_id_filter = query.get('college_id', ['all'])[0]
        conn = database.get_connection()
        cursor = conn.cursor()

        sql = 'SELECT * FROM notifications WHERE 1=1'
        params = []
        if college_id_filter != 'all' and college_id_filter.isdigit():
            sql += ' AND (college_id = ? OR type = "admin_broadcast")'
            params.append(int(college_id_filter))

        sql += ' ORDER BY id DESC LIMIT 25'
        cursor.execute(sql, params)
        notifs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        self.send_json(notifs)

    def handle_get_stats(self):
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as total_pools FROM pools')
        total_pools = cursor.fetchone()['total_pools']

        cursor.execute('SELECT COUNT(*) as active_pools FROM pools WHERE status IN ("open", "ordering", "on_the_way", "at_gate")')
        active_pools = cursor.fetchone()['active_pools']

        cursor.execute('SELECT COUNT(*) as total_students FROM users WHERE status != "blocked"')
        total_students = cursor.fetchone()['total_students']

        cursor.execute('SELECT COUNT(*) as total_colleges FROM colleges')
        total_colleges = cursor.fetchone()['total_colleges']

        cursor.execute('''
        SELECT COUNT(DISTINCT pi.user_id || '-' || pi.pool_id) as total_pooled_orders,
               COALESCE(SUM(p.delivery_fee_saved), 0) as direct_saved
        FROM pool_items pi
        JOIN pools p ON pi.pool_id = p.id
        ''')
        row = cursor.fetchone()
        pooled_count = row['total_pooled_orders'] or 0

        estimated_savings = max(pooled_count * 40.0, 160.0)
        conn.close()

        self.send_json({
            "total_pools": total_pools,
            "active_pools": active_pools,
            "total_students": total_students,
            "total_colleges": total_colleges,
            "total_delivery_saved": estimated_savings
        })

    # ------------------ FOUNDER / PARENT APP ADMIN HANDLERS ------------------ #

    def handle_admin_get_users(self):
        if not self.require_founder():
            return

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT u.id, u.name, u.room_number, u.hostel_block, u.phone, u.upi_id, u.role, u.status, u.created_at,
               COALESCE(c.name, 'Unassigned Campus') as college_name
        FROM users u
        LEFT JOIN colleges c ON u.college_id = c.id
        ORDER BY u.created_at DESC
        ''')
        users = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json(users)

    def handle_admin_update_user_status(self, user_id):
        if not self.require_founder():
            return

        data = self.read_json_body()
        new_status = data.get('status', 'active') # 'active' or 'blocked'
        if new_status not in ('active', 'blocked'):
            return self.send_json({"error": "Invalid status value"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET status = ? WHERE id = ?', (new_status, user_id))
        
        # If blocked, terminate active sessions
        if new_status == 'blocked':
            cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))

        conn.commit()
        conn.close()

        print(f"[FOUNDER MODERATION] User #{user_id} status updated to: {new_status}")
        self.send_json({"message": f"User status successfully updated to {new_status}"})

    def handle_admin_delete_user(self, user_id):
        founder = self.require_founder()
        if not founder:
            return

        if founder['id'] == user_id:
            return self.send_json({"error": "Cannot delete founder account"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM pool_items WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM payments WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

        print(f"[FOUNDER MODERATION] User #{user_id} deleted permanently.")
        self.send_json({"message": "User permanently removed from platform"})

    def handle_admin_create_college(self):
        if not self.require_founder():
            return

        data = self.read_json_body()
        name = data.get('name', '').strip()
        code = data.get('code', '').strip().upper()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        icon = data.get('icon', '🎓').strip()

        if not name or not code:
            return self.send_json({"error": "College name and code are required"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO colleges (name, code, city, state, icon)
            VALUES (?, ?, ?, ?, ?)
            ''', (name, code, city, state, icon))
            college_id = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return self.send_json({"error": "A college with this name or code already exists"}, 400)

        conn.close()
        print(f"[FOUNDER ADMIN] Created new college community: {name} ({code})")
        self.send_json({"id": college_id, "message": f"College community '{name}' launched successfully!"}, 201)

    def handle_admin_delete_college(self, college_id):
        if not self.require_founder():
            return

        if college_id == 1:
            return self.send_json({"error": "Cannot delete default college campus"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM colleges WHERE id = ?', (college_id,))
        conn.commit()
        conn.close()
        self.send_json({"message": "College community removed"})

    def handle_admin_update_settings(self):
        if not self.require_founder():
            return

        data = self.read_json_body()
        for k, v in data.items():
            database.set_setting(k, str(v).strip())

        print(f"[FOUNDER ADMIN] System settings updated: {list(data.keys())}")
        self.send_json({"message": "System settings updated instantly across app!"})

    def handle_admin_global_broadcast(self):
        founder = self.require_founder()
        if not founder:
            return

        data = self.read_json_body()
        title = data.get('title', '📢 Announcement from Founder Kedar Patil').strip()
        message = data.get('message', '').strip()

        if not message:
            return self.send_json({"error": "Message cannot be empty"}, 400)

        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO notifications (pool_id, college_id, title, message, type)
        VALUES (NULL, NULL, ?, ?, 'admin_broadcast')
        ''', (title, message))
        conn.commit()
        conn.close()

        # Also update live announcement ticker
        database.set_setting('live_announcement', message)
        database.set_setting('announcement_active', '1')

        print(f"[FOUNDER GLOBAL BROADCAST] {title} => {message}")
        self.send_json({"message": "Global announcement broadcasted to all colleges in seconds!"})

    def handle_admin_get_stats(self):
        if not self.require_founder():
            return

        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM users WHERE role != "founder"')
        total_students = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM users WHERE status = "blocked"')
        blocked_students = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM colleges')
        total_colleges = cursor.fetchone()['count']

        cursor.execute('SELECT COUNT(*) as count FROM pools')
        total_pools = cursor.fetchone()['count']

        cursor.execute('''
        SELECT COUNT(DISTINCT pi.user_id || '-' || pi.pool_id) * 40.0 as total_saved
        FROM pool_items pi
        ''')
        total_saved = cursor.fetchone()['total_saved'] or 160.0

        conn.close()
        self.send_json({
            "total_students": total_students,
            "blocked_students": blocked_students,
            "total_colleges": total_colleges,
            "total_pools": total_pools,
            "total_saved": total_saved
        })

    def handle_upload_file(self):
        data = self.read_json_body()
        base64_data = data.get('image_base64', '')
        filename = data.get('filename', f"item_{int(datetime.now().timestamp())}.jpg")

        if not base64_data:
            return self.send_json({"error": "No image data provided"}, 400)

        import base64
        try:
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            file_bytes = base64.b64decode(base64_data)
            clean_filename = f"item_{int(datetime.now().timestamp())}_{os.path.basename(filename)}"
            dest_path = os.path.join(UPLOAD_DIR, clean_filename)
            with open(dest_path, 'wb') as f:
                f.write(file_bytes)
            url = f"/uploads/{clean_filename}"
            return self.send_json({"url": url})
        except Exception as e:
            return self.send_json({"error": str(e)}, 500)

def run(port=PORT):
    database.init_db()
    server_address = ('0.0.0.0', port)
    httpd = ThreadedHTTPServer(server_address, HostelPoolHandler)
    print("=" * 65)
    print(f"  🍔 BulkBite v3.0 (Founder HQ & Multi-Campus Edition)")
    print(f"  Founder: KEDAR PATIL")
    print(f"  URL: http://localhost:{port}")
    print(f"  Founder Login: Phone 8390461240 | Password: hostel123")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == '__main__':
    run()
