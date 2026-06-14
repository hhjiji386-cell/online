from flask import Blueprint, request, render_template, redirect, url_for, session
from supabase import create_client, Client

# Waxaan u dhalinaynaa qaab Blueprint ah si app.py u akhriyo
auth_bp = Blueprint('auth', __name__)

# URL-ka iyo Furahaaga rasmiga ah ee Supabase Cloud
SUPABASE_URL = "https://supabase.co"
SUPABASE_KEY = "sb_publishable_eDskTzDraePwlaXa5Y3z5Q_fUe4O-Lk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Khadka Diwaangelinta Cusub (Sign Up) ---
@auth_bp.route('/signup', methods=['POST'])
def handle_web_registration():
    try:
        email = request.form.get('username')
        password = request.form.get('password')

        if not email or not password:
            return render_template('index.html', error="Fadlan buuxi email-ka iyo furaha sirta ah!")

        supabase.auth.sign_up({"email": email, "password": password})
        session['user_email'] = email
        return redirect(url_for('dashboard'))
    except Exception as e:
        return render_template('index.html', error=f"Sign up fashilmay: {str(e)}")

# --- Khadka Soo Gelista (Login) ---
@auth_bp.route('/login', methods=['POST'])
def handle_web_login():
    try:
        email = request.form.get('username')
        password = request.form.get('password')

        supabase.auth.sign_in_with_password({"email": email, "password": password})
        session['user_email'] = email
        return redirect(url_for('dashboard'))
    except Exception as e:
        return render_template('index.html', error="Email-ka ama furaha sirta ah ayaa khaldan!")

# --- Badhanka Google OAuth (Cinwaanka wuxuu ku soo laabanayaa port 5001) ---
@auth_bp.route('/login/google')
def login_google():
    try:
        res = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": "http://127.0.0"
            }
        })
        return redirect(res.url)
    except Exception as e:
        return render_template('index.html', error=f"Google ma furmin: {str(e)}")

# --- Badhanka Facebook OAuth (Cinwaanka wuxuu ku soo laabanayaa port 5001) ---
@auth_bp.route('/login/facebook')
def login_facebook():
    try:
        res = supabase.auth.sign_in_with_oauth({
            "provider": "facebook",
            "options": {
                "redirect_to": "http://127.0.0"
            }
        })
        return redirect(res.url)
    except Exception as e:
        return render_template('index.html', error=f"Facebook ma furmin: {str(e)}")
