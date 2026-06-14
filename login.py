from tkinter import *
from tkinter import messagebox
import json
import os
import subprocess
import sys
import webbrowser
import bcrypt
from db_helper import execute_query, get_db_connection

root = Tk()
root.title("Login System")
root.geometry("500x400")
root.config(bg="white")

# Title
Label(
    root,
    text="LOGIN HERE",
    font=("Arial", 20, "bold"),
    bg="white",
    fg="green"
).pack(pady=20)

# Database status
lbl_db_status = Label(
    root,
    text="Database status: unknown",
    font=("Arial", 10),
    bg="white",
    fg="orange"
)
lbl_db_status.pack(pady=(0, 10))

# Email
Label(
    root,
    text="Email",
    font=("Arial", 12),
    bg="white"
).pack()

txt_email = Entry(root, font=("Arial", 12))
txt_email.pack(pady=5)

saved_email = load_saved_email()
if saved_email:
    txt_email.insert(0, saved_email)
    remember_var.set(1)

# Password
Label(
    root,
    text="Password",
    font=("Arial", 12),
    bg="white"
).pack()

txt_password = Entry(root, show="*", font=("Arial", 12))
txt_password.pack(pady=5)

show_password_var = IntVar(value=0)
remember_var = IntVar(value=0)
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "user_settings.json")

def toggle_login_password():
    txt_password.config(show="" if show_password_var.get() else "*")

Checkbutton(
    root,
    text="Show password",
    variable=show_password_var,
    command=toggle_login_password,
    bg="white"
).pack()

Checkbutton(
    root,
    text="Remember my email",
    variable=remember_var,
    bg="white"
).pack()


def load_saved_email():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("remembered_email", "")
    except Exception:
        return ""


def save_email(email: str):
    try:
        data = {"remembered_email": email if remember_var.get() else ""}
        with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file)
    except Exception:
        pass

# Login Function
def login(event=None):
    email = txt_email.get().strip()
    password = txt_password.get().strip()

    if email == "" or password == "":
        messagebox.showerror("Error", "All fields are required")
        return

    try:
        connection, cursor = get_db_connection()
        execute_query(cursor, "SELECT password FROM register WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            stored = row[0] or ""
            save_email(email)
            try:
                is_hashed = isinstance(stored, str) and stored.startswith("$2")
            except Exception:
                is_hashed = False
            if is_hashed:
                if bcrypt.checkpw(password.encode(), stored.encode()):
                    messagebox.showinfo("Success", "Login successful")
                    try:
                        webbrowser.open("http://localhost:8000/dashboard.html?session=active")
                    except Exception:
                        pass
                else:
                    messagebox.showerror("Error", "Invalid email or password")
            else:
                execute_query(cursor, "SELECT id FROM register WHERE email = ? AND password = ?", (email, password))
                if cursor.fetchone():
                    messagebox.showinfo("Success", "Login successful")
                    try:
                        webbrowser.open("http://localhost:8000/dashboard.html?session=active")
                    except Exception:
                        pass
                else:
                    messagebox.showerror("Error", "Invalid email or password")
        else:
            messagebox.showerror("Error", "Invalid email or password")
    except Exception as error:
        messagebox.showerror("Error", f"Database error: {error}")
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

def open_register_window():
    try:
        subprocess.Popen([sys.executable, "register.py"])
        root.destroy()
    except Exception as error:
        messagebox.showerror("Error", f"Unable to open sign up window: {error}")


def check_database_connection():
    try:
        connection, cursor = get_db_connection()
        lbl_db_status.config(text="Database status: connected", fg="green")
    except Exception as error:
        lbl_db_status.config(text=f"Database status: error: {error}", fg="red")
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass


def forgot_password_request():
    email = txt_email.get().strip()
    if email == "":
        messagebox.showerror("Error", "Enter your email address to reset your password")
        return

    try:
        connection, cursor = get_db_connection()
        execute_query(cursor, "SELECT security_question FROM register WHERE email = ?", (email,))
        row = cursor.fetchone()
        if not row:
            messagebox.showerror("Error", "No account found for this email")
            return

        question = row[0]
    except Exception as error:
        messagebox.showerror("Error", f"Database error: {error}")
        return
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

    reset_window = Toplevel(root)
    reset_window.title("Reset Password")
    reset_window.geometry("400x320")
    reset_window.config(bg="white")
    reset_window.resizable(False, False)

    Label(
        reset_window,
        text="Reset Your Password",
        font=("Arial", 16, "bold"),
        bg="white",
        fg="green"
    ).pack(pady=15)

    Label(
        reset_window,
        text=f"Security Question:\n{question}",
        bg="white",
        fg="#111827",
        justify="left"
    ).pack(pady=5)

    Label(reset_window, text="Answer", bg="white").pack(pady=(10, 0))
    answer_entry = Entry(reset_window, font=("Arial", 12))
    answer_entry.pack(pady=5, ipadx=50)

    Label(reset_window, text="New Password", bg="white").pack(pady=(10, 0))
    new_password_entry = Entry(reset_window, show="*", font=("Arial", 12))
    new_password_entry.pack(pady=5, ipadx=50)

    Label(reset_window, text="Confirm Password", bg="white").pack(pady=(10, 0))
    confirm_password_entry = Entry(reset_window, show="*", font=("Arial", 12))
    confirm_password_entry.pack(pady=5, ipadx=50)

    def reset_password():
        answer = answer_entry.get().strip()
        new_password = new_password_entry.get().strip()
        confirm_password = confirm_password_entry.get().strip()

        if not answer or not new_password or not confirm_password:
            messagebox.showerror("Error", "All fields are required")
            return

        if new_password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match")
            return

        try:
            connection, cursor = get_db_connection()
            execute_query(cursor, "SELECT answer FROM register WHERE email = ?", (email,))
            row = cursor.fetchone()
            if not row:
                messagebox.showerror("Error", "No account found for this email")
                return

            saved_answer = row[0] or ""
            if saved_answer.strip().lower() != answer.lower():
                messagebox.showerror("Error", "Security answer is incorrect")
                return

            # hash password before storing
            hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            execute_query(
                cursor,
                "UPDATE register SET password = ? WHERE email = ?",
                (hashed_pw, email),
            )
            connection.commit()
            messagebox.showinfo("Success", "Password has been reset successfully")
            reset_window.destroy()
        except Exception as error:
            messagebox.showerror("Error", f"Database error: {error}")
        finally:
            try:
                cursor.close()
                connection.close()
            except Exception:
                pass

    Button(
        reset_window,
        text="Reset Password",
        command=reset_password,
        bg="green",
        fg="white",
        font=("Arial", 12, "bold")
    ).pack(pady=15)

# Login Button
Button(
    root,
    text="LOGIN",
    command=login,
    bg="green",
    fg="white",
    font=("Arial", 12, "bold")
).pack(pady=10)

Button(
    root,
    text="SIGN UP",
    command=open_register_window,
    bg="#1b5e20",
    fg="white",
    font=("Arial", 12, "bold")
).pack(pady=5)

Button(
    root,
    text="Check Database",
    command=check_database_connection,
    bg="#2563eb",
    fg="white",
    font=("Arial", 10, "bold")
).pack(pady=5)

Button(
    root,
    text="Forgot Password?",
    command=forgot_password_request,
    bg="#f3f4f6",
    fg="#111827",
    font=("Arial", 10),
    relief="flat"
).pack(pady=5)

root.bind("<Return>", login)

root.mainloop()