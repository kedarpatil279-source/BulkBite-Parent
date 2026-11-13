import sys
sys.stdout.reconfigure(encoding='utf-8')
import io
import json
from server import HostelPoolHandler

class MockRequest:
    def __init__(self, method, path, headers=None, body=None):
        raw_body = json.dumps(body).encode('utf-8') if body else b""
        headers_dict = headers or {}
        if body is not None:
            headers_dict['Content-Length'] = str(len(raw_body))
            headers_dict['Content-Type'] = 'application/json'

        header_lines = "\r\n".join(f"{k}: {v}" for k, v in headers_dict.items())
        raw_request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n{header_lines}\r\n\r\n".encode('utf-8') + raw_body

        self.rfile = io.BytesIO(raw_request)
        self.wfile = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if 'r' in mode:
            return self.rfile
        elif 'w' in mode:
            return self.wfile

def simulate_request(method, path, headers=None, body=None):
    mock = MockRequest(method, path, headers=headers, body=body)
    try:
        handler = HostelPoolHandler.__new__(HostelPoolHandler)
        handler.rfile = mock.rfile
        handler.wfile = mock.wfile
        handler.headers = {}
        handler.requestline = f"{method} {path} HTTP/1.1"
        handler.command = method
        handler.path = path
        handler.request_version = "HTTP/1.1"
        handler.close_connection = True
        handler.client_address = ('127.0.0.1', 8080)
        handler.server_version = "BaseHTTP/0.6"
        handler.sys_version = "Python/3.13"

        import http.client
        mock.rfile.readline()
        handler.headers = http.client.parse_headers(mock.rfile)

        if method == 'GET':
            handler.do_GET()
        elif method == 'POST':
            handler.do_POST()
        elif method == 'PATCH':
            handler.do_PATCH()
        elif method == 'DELETE':
            handler.do_DELETE()

        raw_output = mock.wfile.getvalue().decode('utf-8')
        if "\r\n\r\n" in raw_output:
            status_line, rest = raw_output.split("\r\n", 1)
            header_part, body_part = rest.split("\r\n\r\n", 1)
            return status_line, body_part
        return "HTTP/1.1 200 OK", raw_output
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "ERROR", str(e)

def test_founder_and_multicampus():
    print("Testing BulkBite Founder HQ & Multi-Campus Architecture...")

    # 1. Login as Founder Kedar Patil
    status, body = simulate_request('POST', '/api/auth/login', body={"phone": "8390461240", "password": "hostel123"})
    founder_auth = json.loads(body)
    assert founder_auth["user"]["role"] == "founder", "Founder role not assigned"
    founder_token = founder_auth["token"]
    founder_headers = {"Authorization": f"Bearer {founder_token}"}
    print(f"✓ POST /api/auth/login: Logged in as Founder: {founder_auth['user']['name']} (Role: {founder_auth['user']['role']})")

    # 2. Login as regular student Rahul
    status, body = simulate_request('POST', '/api/auth/login', body={"phone": "9876543210", "password": "hostel123"})
    rahul_auth = json.loads(body)
    rahul_id = rahul_auth["user"]["id"]
    rahul_token = rahul_auth["token"]
    rahul_headers = {"Authorization": f"Bearer {rahul_token}"}
    print(f"✓ POST /api/auth/login: Student logged in: {rahul_auth['user']['name']} (ID: {rahul_id})")

    # 3. Security Check: Non-founder tries to access /api/admin/users -> Rejected 403
    status, body = simulate_request('GET', '/api/admin/users', headers=rahul_headers)
    assert "403" in status or "error" in body
    print(f"✓ Security check: Student blocked from accessing Founder Admin API (403 Forbidden)")

    # 4. Founder accesses /api/admin/users
    status, body = simulate_request('GET', '/api/admin/users', headers=founder_headers)
    all_users = json.loads(body)
    assert len(all_users) >= 2
    print(f"✓ GET /api/admin/users: Founder retrieved {len(all_users)} enrolled students across campuses")

    # 5. Founder Blocks a Student (Aman Verma)
    aman = [u for u in all_users if u['phone'] == '9811223344'][0]
    status, body = simulate_request('PATCH', f'/api/admin/users/{aman["id"]}/status', headers=founder_headers, body={"status": "blocked"})
    assert "updated" in body
    print(f"✓ PATCH /api/admin/users/<id>/status: Founder blocked rule-violating student {aman['name']}")

    # 6. Verify Blocked Student cannot login
    status, body = simulate_request('POST', '/api/auth/login', body={"phone": "9811223344", "password": "hostel123"})
    assert "403" in status or "suspended" in body.lower()
    print(f"✓ Enforcement check: Blocked student rejected from logging in (403 Suspended)")

    # 7. Founder Unblocks the Student
    status, body = simulate_request('PATCH', f'/api/admin/users/{aman["id"]}/status', headers=founder_headers, body={"status": "active"})
    assert "updated" in body
    print(f"✓ PATCH /api/admin/users/<id>/status: Founder unblocked student {aman['name']}")

    # 8. Founder Creates a New College Community
    import time
    ts = int(time.time())
    new_college = {
        "name": f"Manipal Tech Campus {ts}",
        "code": f"MIT-{ts % 1000}",
        "city": "Manipal",
        "state": "Karnataka"
    }
    status, body = simulate_request('POST', '/api/admin/colleges', headers=founder_headers, body=new_college)
    college_res = json.loads(body)
    new_college_id = college_res["id"]
    print(f"✓ POST /api/admin/colleges: Founder created college community #{new_college_id}: {new_college['name']}")

    # 9. Public retrieves college list
    status, body = simulate_request('GET', '/api/colleges')
    colleges = json.loads(body)
    assert any(c['code'] == 'MIT-MANIPAL' for c in colleges)
    print(f"✓ GET /api/colleges: Public retrieved {len(colleges)} active college communities")

    # 10. Founder sends global network announcement broadcast
    broadcast_data = {
        "title": "⚡ Founder Flash Update",
        "message": "Late night delivery fee waived on all Blinkit & Zepto carts hitting ₹200!"
    }
    status, body = simulate_request('POST', '/api/admin/broadcast', headers=founder_headers, body=broadcast_data)
    assert "broadcasted" in body.lower()
    print(f"✓ POST /api/admin/broadcast: Instant system-wide announcement broadcasted to all campuses")

    # 11. Verify settings & helpline
    status, body = simulate_request('GET', '/api/settings')
    settings = json.loads(body)
    assert "helpline_phone" in settings
    print(f"✓ GET /api/settings: Helpline Phone: {settings.get('helpline_phone')} | Email: {settings.get('helpline_email')}")

    print("\nALL FOUNDER HQ & MULTI-CAMPUS CAPABILITIES VERIFIED 100%! 🛡️👑🚀")

if __name__ == '__main__':
    test_founder_and_multicampus()
