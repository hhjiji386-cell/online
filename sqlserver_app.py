import pyodbc
import bcrypt
from flask import Flask, render_template, request

app = Flask(__name__)
app.secret_key = "change_this_secret"


def get_db_connection():
    # Connects to your active local Windows SQL Server
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=master;"
        "Trusted_Connection=yes;"
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username_input = request.form.get("username")
        password_input = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM users WHERE username = ?",
            (username_input,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            stored_hash = row[0]
            if stored_hash and bcrypt.checkpw(password_input.encode(), stored_hash.encode()):
                return f"<h1>Success! Welcome, {username_input}. Verified via local SQL Server!</h1>"
        error = "Invalid credentials."

    return render_template("login.html", error=error)


if __name__ == "__main__":
    app.run(debug=True)
