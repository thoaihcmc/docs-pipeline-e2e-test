"""Database authentication module with SQLite backend.

Provides user registration, login, session management, and an auth gate
that other modules call before granting access.

Usage:
  python auth_module.py register
  python auth_module.py login
  python auth_module.py logout
  python auth_module.py status
  python auth_module.py --gui
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import secrets
import sqlite3
import sys
import tkinter as tk
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import messagebox, ttk
from typing import NamedTuple

_APP_DIR = Path.home() / ".docs_pipeline_app"
_DB_PATH = _APP_DIR / "app_auth.db"
_SESSION_PATH = _APP_DIR / ".app_session"

_HASH_ITERATIONS = 600_000
_SESSION_LIFETIME_HOURS = 24


class User(NamedTuple):
    id: int
    username: str
    created_at: str


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _ensure_app_dir() -> None:
    _APP_DIR.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    _ensure_app_dir()
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT  NOT NULL,
                salt        TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token       TEXT    NOT NULL UNIQUE,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                expires_at  TEXT    NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _HASH_ITERATIONS,
    ).hex()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return secrets.compare_digest(_hash_password(password, salt), stored_hash)


# ---------------------------------------------------------------------------
# Registration & login
# ---------------------------------------------------------------------------

def register(username: str, password: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    init_db()
    salt = secrets.token_hex(32)
    pw_hash = _hash_password(password, salt)
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, pw_hash, salt),
        )
        conn.commit()
        return True, f"User '{username}' registered successfully."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' is already taken."
    finally:
        conn.close()


def login(username: str, password: str) -> tuple[bool, str]:
    """Authenticate and create a session. Returns (success, message)."""
    init_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, password_hash, salt FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return False, "Invalid username or password."

        user_id, stored_hash, salt = row
        if not _verify_password(password, salt, stored_hash):
            return False, "Invalid username or password."

        token = secrets.token_urlsafe(48)
        expires = datetime.now(timezone.utc) + timedelta(hours=_SESSION_LIFETIME_HOURS)
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires.isoformat()),
        )
        conn.commit()

        _ensure_app_dir()
        _SESSION_PATH.write_text(token, encoding="utf-8")
        return True, f"Logged in as '{username}'."
    finally:
        conn.close()


def logout() -> tuple[bool, str]:
    """Destroy the current session. Returns (success, message)."""
    init_db()
    token = _read_session_token()
    if not token:
        return False, "No active session."

    conn = _get_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()

    if _SESSION_PATH.exists():
        _SESSION_PATH.unlink()
    return True, "Logged out."


def validate_session() -> User | None:
    """Return the current user if a valid session exists, else None."""
    init_db()
    token = _read_session_token()
    if not token:
        return None

    conn = _get_conn()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.username, u.created_at
            FROM sessions s JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > datetime('now')
            """,
            (token,),
        ).fetchone()
        if row is None:
            if _SESSION_PATH.exists():
                _SESSION_PATH.unlink()
            return None
        return User(id=row[0], username=row[1], created_at=row[2])
    finally:
        conn.close()


def _read_session_token() -> str | None:
    if not _SESSION_PATH.exists():
        return None
    token = _SESSION_PATH.read_text(encoding="utf-8").strip()
    return token or None


# ---------------------------------------------------------------------------
# Auth gate — called by other modules
# ---------------------------------------------------------------------------

def require_auth(*, gui: bool = False) -> str:
    """Ensure the user is authenticated before proceeding.

    In CLI mode, prompts for login if no session exists.
    In GUI mode, opens a login/register dialog.
    Returns the username on success; exits the process on failure.
    """
    user = validate_session()
    if user is not None:
        return user.username

    if gui:
        username = _gui_auth_gate()
    else:
        username = _cli_auth_gate()

    if username is None:
        sys.exit(1)
    return username


def _cli_auth_gate() -> str | None:
    """CLI interactive login/register flow."""
    print("Authentication required.")
    print("  1) Login")
    print("  2) Register")
    choice = input("Choice [1/2]: ").strip()

    if choice == "2":
        username = input("Choose username: ").strip()
        password = getpass.getpass("Choose password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.")
            return None
        ok, msg = register(username, password)
        print(msg)
        if not ok:
            return None
        ok, msg = login(username, password)
        print(msg)
        return username if ok else None

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    ok, msg = login(username, password)
    print(msg)
    return username if ok else None


def _gui_auth_gate() -> str | None:
    """Tkinter login/register dialog. Returns username on success."""
    result: list[str | None] = [None]

    dialog = tk.Tk()
    dialog.title("Authentication Required")
    dialog.resizable(False, False)
    dialog.geometry("340x280")

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # --- Login tab ---
    login_frame = ttk.Frame(notebook, padding=12)
    notebook.add(login_frame, text="Login")

    ttk.Label(login_frame, text="Username").grid(row=0, column=0, sticky="w", pady=(0, 4))
    login_user_var = tk.StringVar()
    ttk.Entry(login_frame, textvariable=login_user_var, width=30).grid(row=1, column=0, sticky="ew", pady=(0, 8))

    ttk.Label(login_frame, text="Password").grid(row=2, column=0, sticky="w", pady=(0, 4))
    login_pass_var = tk.StringVar()
    ttk.Entry(login_frame, textvariable=login_pass_var, show="*", width=30).grid(row=3, column=0, sticky="ew", pady=(0, 12))

    def on_login() -> None:
        ok, msg = login(login_user_var.get().strip(), login_pass_var.get())
        if ok:
            result[0] = login_user_var.get().strip()
            dialog.destroy()
        else:
            messagebox.showerror("Login failed", msg, parent=dialog)

    ttk.Button(login_frame, text="Login", command=on_login).grid(row=4, column=0, sticky="ew")

    # --- Register tab ---
    reg_frame = ttk.Frame(notebook, padding=12)
    notebook.add(reg_frame, text="Register")

    ttk.Label(reg_frame, text="Username").grid(row=0, column=0, sticky="w", pady=(0, 4))
    reg_user_var = tk.StringVar()
    ttk.Entry(reg_frame, textvariable=reg_user_var, width=30).grid(row=1, column=0, sticky="ew", pady=(0, 8))

    ttk.Label(reg_frame, text="Password").grid(row=2, column=0, sticky="w", pady=(0, 4))
    reg_pass_var = tk.StringVar()
    ttk.Entry(reg_frame, textvariable=reg_pass_var, show="*", width=30).grid(row=3, column=0, sticky="ew", pady=(0, 8))

    ttk.Label(reg_frame, text="Confirm password").grid(row=4, column=0, sticky="w", pady=(0, 4))
    reg_confirm_var = tk.StringVar()
    ttk.Entry(reg_frame, textvariable=reg_confirm_var, show="*", width=30).grid(row=5, column=0, sticky="ew", pady=(0, 12))

    def on_register() -> None:
        pw = reg_pass_var.get()
        if pw != reg_confirm_var.get():
            messagebox.showerror("Error", "Passwords do not match.", parent=dialog)
            return
        ok, msg = register(reg_user_var.get().strip(), pw)
        if not ok:
            messagebox.showerror("Registration failed", msg, parent=dialog)
            return
        ok, msg = login(reg_user_var.get().strip(), pw)
        if ok:
            result[0] = reg_user_var.get().strip()
            dialog.destroy()
        else:
            messagebox.showerror("Login failed", msg, parent=dialog)

    ttk.Button(reg_frame, text="Register & Login", command=on_register).grid(row=6, column=0, sticky="ew")

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.mainloop()
    return result[0]


# ---------------------------------------------------------------------------
# Standalone CLI / GUI
# ---------------------------------------------------------------------------

def show_cli_status() -> None:
    user = validate_session()
    if user:
        print(f"Logged in as: {user.username} (since {user.created_at})")
    else:
        print("Not logged in.")


def show_gui() -> None:
    """Standalone auth management GUI."""
    root = tk.Tk()
    root.title("Auth Manager")
    root.resizable(False, False)

    main_frame = ttk.Frame(root, padding=16)
    main_frame.pack(fill="both", expand=True)

    status_var = tk.StringVar()

    def refresh_status() -> None:
        user = validate_session()
        if user:
            status_var.set(f"Logged in as: {user.username}")
            login_btn.state(["disabled"])
            reg_btn.state(["disabled"])
            logout_btn.state(["!disabled"])
        else:
            status_var.set("Not logged in.")
            login_btn.state(["!disabled"])
            reg_btn.state(["!disabled"])
            logout_btn.state(["disabled"])

    ttk.Label(main_frame, textvariable=status_var, font=("Segoe UI", 11)).pack(pady=(0, 12))

    def do_login() -> None:
        username = _gui_auth_gate()
        if username:
            refresh_status()

    def do_register() -> None:
        username = _gui_auth_gate()
        if username:
            refresh_status()

    def do_logout() -> None:
        ok, msg = logout()
        messagebox.showinfo("Logout", msg, parent=root)
        refresh_status()

    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill="x")

    login_btn = ttk.Button(btn_frame, text="Login", command=do_login)
    login_btn.pack(fill="x", pady=(0, 4))

    reg_btn = ttk.Button(btn_frame, text="Register", command=do_register)
    reg_btn.pack(fill="x", pady=(0, 4))

    logout_btn = ttk.Button(btn_frame, text="Logout", command=do_logout)
    logout_btn.pack(fill="x")

    refresh_status()
    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Authentication manager")
    parser.add_argument("--gui", action="store_true", help="open auth manager GUI")
    parser.add_argument(
        "action",
        nargs="?",
        choices=["register", "login", "logout", "status"],
        help="auth action to perform (CLI mode)",
    )
    return parser


def main() -> None:
    init_db()
    args = build_parser().parse_args()

    if args.gui:
        show_gui()
        return

    if args.action is None:
        show_cli_status()
        return

    if args.action == "status":
        show_cli_status()
    elif args.action == "register":
        username = input("Choose username: ").strip()
        password = getpass.getpass("Choose password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.")
            sys.exit(1)
        ok, msg = register(username, password)
        print(msg)
        if not ok:
            sys.exit(1)
    elif args.action == "login":
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        ok, msg = login(username, password)
        print(msg)
        if not ok:
            sys.exit(1)
    elif args.action == "logout":
        ok, msg = logout()
        print(msg)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
