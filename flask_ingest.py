import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
CORS(app)

# Meesha si ku-meel-gaar ah loogu kaydinayo dadka iska diiwaan-geliyay (In-memory Database)
users_db = {
    "admin@example.com": "12345"  # Tusaale akoon horey u jiray
}
telemetry_storage = []

# --- 1. BOGGA HORE (HOME) ---
@app.route('/')
def home():
    return render_template('index.html')

# --- 2. BOGGA LOGIN-KA (GET iyo POST) ---
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        # Haddii foomka caadiga ah la soo buuxiyo
        email = request.form.get('username') or request.form.get('email')
        password = request.form.get('password')
        
        if email in users_db and users_db[email] == password:
            return redirect('/dashboard') # Haddii uu sax yahay wuxuu u gudbayaa dashboard
        else:
            return "Erayga sirta ah ama Email-ka ayaa khaldan!", 401
            
    return render_template('login.html')

# --- 3. BOGGA SIGNUP-KA (GET iyo POST) ---
@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return "Fadlan buuxi dhammaan meelaha banaan!", 400
            
        # Keydi isticmaalaha cusub
        users_db[email] = password
        return "Diiwaan-gelinta waa ay guuleysatay! Hadda dib u laabo oo Login dheh."
        
    return render_template('signup.html')

# --- 4. BOGGA PASSWORD-KA LA ILOOBAY (FORGET PASSWORD) ---
@app.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if email in users_db:
            return f"Xiriirka dib-u-dejinta erayga sirta ah waxaa loo diray: {email}"
        return "Email-kan laguma hayo nidaamka!", 404
        
    return render_template('forget.html') if os.path.exists(os.path.join(app.template_folder, 'forget.html')) else "Fadlan abuur faylka forget.html"

# --- 5. BADANADA GOOGLE IYO FACEBOOK ---
@app.route('/login/google')
def login_google():
    return "Wuxuu u wareegayaa boggaga aqoonsiga ee Google..."

@app.route('/login/facebook')
def login_facebook():
    return "Wuxuu u wareegayaa boggaga aqoonsiga ee Facebook..."

# --- 6. SYSTEM DASHBOARD ---
@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

# --- 7. TELEMETRY INGESTION ENDPOINTS (Koodhkii aad hore u lahayd) ---
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
    filtered_data = [row for row in telemetry_storage if row["timestamp"] >= threshold]
    filtered_data.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"status": "ok", "data": filtered_data[:500]})
