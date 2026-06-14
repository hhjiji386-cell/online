import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timedelta

# Nidaamka rasmiga ah ee Vercel ku qasbaya galka templates
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
CORS(app)

# In-memory storage block for serverless compatibility
telemetry_storage = []

# --- ROUTE TO DISPLAY WELCOME LANDING PAGE ---
@app.route('/')
def home():
    return render_template('index.html')

# --- ROUTE TO DISPLAY WEBCODE CLOCK LOGIN PAGE ---
@app.route('/login')
def login_page():
    return render_template('login.html')

# --- ROUTE TO DISPLAY THE SIGNUP PAGE ---
@app.route('/signup')
def signup_page():
    return render_template('signup.html')

# --- ROUTE TO DISPLAY THE SYSTEM DASHBOARD ---
@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

# --- API ROUTE TO PROCESS LOGIN SUBMISSIONS ---
@app.route('/api/login', methods=['POST'])
def handle_login():
    if not request.is_json:
        return jsonify({"status": "error", "message": "JSON body format required"}), 400
        
    data = request.get_json()
    email = data.get('username')
    password = data.get('password')
    
    if email == "admin@example.com" and password == "12345":
        return jsonify({"status": "success", "message": "Login authorization accepted!"}), 200
        
    return jsonify({"status": "error", "message": "Access Denied: Invalid credentials"}), 401

# --- TELEMETRY INGESTION ENDPOINTS ---
@app.route("/api/ingest", methods=["POST"])
def ingest():
    if not request.is_json:
        return jsonify({"status": "error", "message": "JSON required"}), 400
        
    payload = request.get_json()
    rows = payload if isinstance(payload, list) else [payload]
    now = datetime.utcnow().isoformat() + "Z"
    
    for row in rows:
        telemetry_storage.append({
            "device_id": row.get("device_id", "unknown"),
            "timestamp": row.get("timestamp") or now,
            "metric": row.get("metric", "unknown"),
            "value": float(row.get("value", 0)) if row.get("value") is not None else 0.0,
            "unit": row.get("unit", ""),
            "status": row.get("status", ""),
            "created_at": now
        })
    
    if len(telemetry_storage) > 1000:
        del telemetry_storage[:len(telemetry_storage) - 500]
        
    return jsonify({"status": "ok", "rows": len(rows)}), 201

@app.route("/api/latest", methods=["GET"])
def latest():
    minutes = int(request.args.get("minutes", 10))
    threshold = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat() + "Z"
    
    filtered_data = [
        row for row in telemetry_storage 
        if row["timestamp"] >= threshold
    ]
    
    filtered_data.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"status": "ok", "data": filtered_data[:500]})

# FOOMKAAN WAA LAGA SAARAY app.run(debug=True) SABABTOO AH VERCEL AYAA MAAMULAYA SERVER-KA
