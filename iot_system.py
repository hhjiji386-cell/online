import http.server
import json
import os
import sqlite3
import socketserver
import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

PORT = 8000
DB_PATH = "iot_data.db"
STATIC_DIR = "static"

# SSE support for live dashboard updates
last_update = None
update_event = threading.Event()

SQL_CREATE_TELEMETRY = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    status TEXT,
    created_at TEXT NOT NULL
)
"""

SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(SQL_CREATE_TELEMETRY)
    cursor.execute("PRAGMA table_info(telemetry)")
    columns = [row[1] for row in cursor.fetchall()]
    if "status" not in columns:
        cursor.execute("ALTER TABLE telemetry ADD COLUMN status TEXT")
    
    cursor.execute(SQL_CREATE_USERS)
    # Create a default admin user for development/demo if none exists
    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", ("admin",))
        if not cursor.fetchone():
            default_pw = "1234"
            cursor.execute(
                "INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
                ("Admin", "admin", hash_password(default_pw), datetime.utcnow().isoformat() + "Z"),
            )
            print("Created default admin user: admin / 1234")
    except Exception:
        # If something goes wrong here, continue without blocking DB init
        pass
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM telemetry")
    telemetry_count = cursor.fetchone()[0]
    conn.close()

    if telemetry_count == 0:
        seed_demo_telemetry()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def insert_rows(rows):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    for row in rows:
        cursor.execute(
            "INSERT INTO telemetry (device_id, timestamp, metric, value, unit, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                row.get("device_id", "unknown"),
                row.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                row.get("metric", "unknown"),
                float(row.get("value", 0)),
                row.get("unit", ""),
                row.get("status", ""),
                now,
            ),
        )
    conn.commit()
    conn.close()
    global last_update
    last_update = datetime.utcnow().isoformat() + "Z"
    update_event.set()

def seed_demo_telemetry():
    now = datetime.utcnow()
    sample_rows = [
        {"device_id": "meter-1", "timestamp": (now).isoformat() + "Z", "metric": "power", "value": 4.8, "unit": "kW", "status": "ON"},
        {"device_id": "meter-1", "timestamp": (now).isoformat() + "Z", "metric": "energy", "value": 8.6, "unit": "kWh"},
        {"device_id": "meter-1", "timestamp": (now).isoformat() + "Z", "metric": "solar_irradiance", "value": 580, "unit": "W/m²"},
        {"device_id": "sensor-1", "timestamp": (now).isoformat() + "Z", "metric": "room_temperature", "value": 23.6, "unit": "°C"},
        {"device_id": "sensor-1", "timestamp": (now).isoformat() + "Z", "metric": "humidity", "value": 46.2, "unit": "%"},
        {"device_id": "sensor-2", "timestamp": (now).isoformat() + "Z", "metric": "water_level", "value": 72, "unit": "%"},
        {"device_id": "sensor-2", "timestamp": (now).isoformat() + "Z", "metric": "flow_rate", "value": 12.4, "unit": "L/min"},
        {"device_id": "sensor-2", "timestamp": (now).isoformat() + "Z", "metric": "water_temperature", "value": 29.1, "unit": "°C"},
        {"device_id": "battery-1", "timestamp": (now).isoformat() + "Z", "metric": "battery_voltage", "value": 12.1, "unit": "V"},
        {"device_id": "power-panel", "timestamp": (now).isoformat() + "Z", "metric": "power_status", "value": 1, "status": "ON"},
    ]
    insert_rows(sample_rows)
    print("Seeded demo telemetry data.")


def get_recent_timestamp(minutes=10):
    return (datetime.utcnow() - timedelta(minutes=minutes)).isoformat() + "Z"


def query_latest(device_id=None, metric=None, window_minutes=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    recent_threshold = get_recent_timestamp(window_minutes)
    filters = ["timestamp >= ?"]
    params = [recent_threshold]
    if device_id:
        filters.append("device_id = ?")
        params.append(device_id)
    if metric:
        filters.append("metric = ?")
        params.append(metric)

    sql = "SELECT device_id, timestamp, metric, value, unit, status FROM telemetry"
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY timestamp DESC LIMIT 100"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "device_id": row[0],
            "timestamp": row[1],
            "metric": row[2],
            "value": row[3],
            "unit": row[4],
            "status": row[5],
        }
        for row in rows
    ]

def query_summary(window_minutes=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    recent_threshold = get_recent_timestamp(window_minutes)
    cursor.execute(
        "SELECT device_id, metric, timestamp, value, unit, status FROM telemetry WHERE timestamp >= ? AND id IN (SELECT MAX(id) FROM telemetry WHERE timestamp >= ? GROUP BY device_id, metric)",
        (recent_threshold, recent_threshold),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "device_id": row[0],
            "metric": row[1],
            "timestamp": row[2],
            "value": row[3],
            "unit": row[4],
            "status": row[5],
        }
        for row in rows
    ]

def query_history(device_id=None, metric=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    filters = []
    params = []
    if device_id:
        filters.append("device_id = ?")
        params.append(device_id)
    if metric:
        filters.append("metric = ?")
        params.append(metric)

    sql = "SELECT device_id, timestamp, metric, value, unit, status FROM telemetry"
    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY timestamp DESC LIMIT 100"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "device_id": row[0],
            "timestamp": row[1],
            "metric": row[2],
            "value": row[3],
            "unit": row[4],
            "status": row[5],
        }
        for row in rows
    ]

def create_jwt_token(user_id, name, email):
    import base64
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b'=').decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"id": user_id, "name": name, "email": email}).encode()
    ).rstrip(b'=').decode()
    signature = base64.urlsafe_b64encode(
        hashlib.sha256((header + '.' + payload).encode()).digest()
    ).rstrip(b'=').decode()
    return f"{header}.{payload}.{signature}"

class IoTRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def send_json(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"retry: 1000\n\n")
            self.wfile.flush()
            last_sent = None
            try:
                while True:
                    update_event.wait(15)
                    if last_update and last_update != last_sent:
                        payload = f"data: {last_update}\n\n".encode("utf-8")
                        self.wfile.write(payload)
                        self.wfile.flush()
                        last_sent = last_update
                    update_event.clear()
                    time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                return

        if parsed.path == "/api/latest":
            query = parse_qs(parsed.query)
            device = query.get("device_id", [None])[0]
            metric = query.get("metric", [None])[0]
            data = query_summary() if device is None and metric is None else query_latest(device, metric)
            self.send_json(200, {"status": "ok", "data": data})
            return

        if parsed.path == "/api/history":
            query = parse_qs(parsed.query)
            device = query.get("device_id", [None])[0]
            metric = query.get("metric", [None])[0]
            data = query_history(device, metric)
            self.send_json(200, {"status": "ok", "data": data})
            return

        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            payload = json.loads(body)
        except:
            self.send_json(400, {"status": "error", "message": "Invalid JSON"})
            return

        if parsed.path == "/api/login":
            email = payload.get("email", "").strip()
            password = payload.get("password", "").strip()
            
            if not email or not password:
                self.send_json(400, {"status": "error", "message": "Email and password required"})
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, password FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()
            
            if user and user[2] == hash_password(password):
                token = create_jwt_token(user[0], user[1], email)
                self.send_json(200, {"status": "ok", "token": token, "name": user[1], "email": email})
            else:
                self.send_json(401, {"status": "error", "message": "Invalid email or password"})
            return

        if parsed.path == "/api/signup":
            name = payload.get("name", "").strip()
            email = payload.get("email", "").strip()
            password = payload.get("password", "").strip()
            
            if not name or not email or not password:
                self.send_json(400, {"status": "error", "message": "Name, email, and password required"})
                return
            
            if len(password) < 8:
                self.send_json(400, {"status": "error", "message": "Password must be at least 8 characters"})
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (name, email, password, created_at) VALUES (?, ?, ?, ?)",
                    (name, email, hash_password(password), datetime.utcnow().isoformat() + "Z")
                )
                conn.commit()
                conn.close()
                self.send_json(201, {"status": "ok", "message": "Account created successfully"})
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json(409, {"status": "error", "message": "Email already registered"})
            return

        if parsed.path == "/api/telemetry":
            rows = payload if isinstance(payload, list) else [payload]
            insert_rows(rows)
            self.send_json(201, {"status": "ok", "rows": len(rows)})
            return

        self.send_json(404, {"status": "error", "message": "Not found"})

def run():
    init_db()
    os.makedirs(STATIC_DIR, exist_ok=True)
    handler = IoTRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"IoT monitoring server running at http://localhost:{PORT}")
        print("Use /api/login for login, /api/signup for registration")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")

if __name__ == "__main__":
    run()
