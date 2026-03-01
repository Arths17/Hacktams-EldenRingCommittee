"""
HealthOS — Supabase Database Layer

Handles: user auth (signup/login), profile save/load, chat log persistence.
All passwords are bcrypt-hashed — never stored in plaintext.
"""

import os
import bcrypt
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_url: str = os.environ.get("SUPABASE_URL", "")
_key: str = os.environ.get("SUPABASE_KEY", "")
_db:  Client = None


def get_db() -> Client:
    global _db
    if _db is None:
        if not _url or "your-project-ref" in _url:
            raise RuntimeError(
                "SUPABASE_URL not set. Paste your project URL into .env\n"
                "  Find it at: Supabase → Settings → General → Reference ID\n"
                "  It looks like: https://xxxxxxxxxxxx.supabase.co"
            )
        if not _key:
            raise RuntimeError("SUPABASE_KEY not set in .env")
        _db = create_client(_url, _key)
    return _db


# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

def create_user(username: str, password: str) -> dict:
    """
    Register a new user. Returns {"success": True, "user_id": ...}
    or {"success": False, "error": "..."}.
    """
    db = get_db()

    # Check username taken
    existing = db.table("users").select("id").eq("username", username).execute()
    if existing.data:
        return {"success": False, "error": "Username already taken"}

    if len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters"}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters"}

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    result = db.table("users").insert({"username": username, "password": hashed}).execute()

    if result.data:
        return {"success": True, "user_id": result.data[0]["id"]}
    return {"success": False, "error": "Could not create user"}


def login_user(username: str, password: str) -> dict:
    """
    Verify credentials. Returns {"success": True, "user_id": ..., "username": ...}
    or {"success": False, "error": "..."}.
    """
    db     = get_db()
    result = db.table("users").select("*").eq("username", username).execute()

    if not result.data:
        return {"success": False, "error": "User not found"}

    user = result.data[0]
    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return {"success": False, "error": "Incorrect password"}

    return {"success": True, "user_id": user["id"], "username": user["username"]}


# ──────────────────────────────────────────────
# PROFILES
# ──────────────────────────────────────────────

def save_profile(user_id: str, profile: dict) -> bool:
    """Upsert profile for a user. Returns True on success."""
    db   = get_db()
    data = {k: v for k, v in profile.items() if k != "id"}
    data["user_id"]    = user_id
    data["updated_at"] = "now()"

    existing = db.table("profiles").select("id").eq("user_id", user_id).execute()
    if existing.data:
        result = (
            db.table("profiles")
            .update(data)
            .eq("user_id", user_id)
            .execute()
        )
    else:
        result = db.table("profiles").insert(data).execute()

    return bool(result.data)


def load_profile(user_id: str) -> dict:
    """Load a user's profile. Returns dict or {} if not found."""
    db     = get_db()
    result = db.table("profiles").select("*").eq("user_id", user_id).execute()
    if result.data:
        row = result.data[0]
        # Strip Supabase-internal keys
        return {k: v for k, v in row.items() if k not in ("id", "user_id", "updated_at")}
    return {}


# ──────────────────────────────────────────────
# CHAT LOGS
# ──────────────────────────────────────────────

def save_message(user_id: str, role: str, content: str) -> bool:
    """Append one message to chat_logs. role = 'user' | 'assistant'."""
    db     = get_db()
    result = db.table("chat_logs").insert({
        "user_id": user_id,
        "role":    role,
        "content": content,
    }).execute()
    return bool(result.data)


def load_chat_history(user_id: str, limit: int = 20) -> list[dict]:
    """
    Load last `limit` messages for a user.
    Returns list of {"role": ..., "content": ...} dicts, oldest first.
    """
    db     = get_db()
    result = (
        db.table("chat_logs")
        .select("role, content, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if not result.data:
        return []
    return [{"role": r["role"], "content": r["content"]} for r in reversed(result.data)]


def clear_chat_history(user_id: str) -> bool:
    """Wipe all chat logs for a user (e.g. on profile reset)."""
    db = get_db()
    db.table("chat_logs").delete().eq("user_id", user_id).execute()
    return True
