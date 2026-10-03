"""Users, password hashing, sessions and role permissions."""
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta

from . import db

ROLES = ("admin", "editor", "viewer")
ROLE_TH = {"admin": "ผู้ดูแลระบบ", "editor": "ผู้จัดทำเอกสาร", "viewer": "ผู้ดูอย่างเดียว"}
STATUSES = ("active", "pending", "disabled")
SESSION_COOKIE = "sid"
SESSION_HOURS = 12
REMEMBER_DAYS = 30
MAX_FAILED = 5          # failed logins per email or IP ...
LOCK_MINUTES = 15       # ... within this window locks further attempts
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")


class AuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── passwords (stdlib scrypt) ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


def check_password_rules(password: str):
    if len(password or "") < 8:
        raise AuthError("รหัสผ่านต้องยาวอย่างน้อย 8 ตัวอักษร")
    if not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        raise AuthError("รหัสผ่านต้องมีทั้งตัวอักษรและตัวเลข")


# ── users ───────────────────────────────────────────────────────────────────

PUBLIC_FIELDS = "id, username, email, name, position, phone, role, status, created_at, last_login_at, last_login_ip, last_seen_at"


def public_user(u: dict | None) -> dict | None:
    if not u:
        return None
    out = {k: u.get(k) for k in PUBLIC_FIELDS.replace(" ", "").split(",")}
    out["role_th"] = ROLE_TH.get(u.get("role"), u.get("role"))
    return out


def user_count() -> int:
    return db.row("SELECT COUNT(*) n FROM users")["n"]


def get_user(uid: int) -> dict | None:
    return db.row("SELECT * FROM users WHERE id=?", (uid,))


def get_user_by_email(email: str) -> dict | None:
    return db.row("SELECT * FROM users WHERE email=?", ((email or "").strip().lower(),))


def get_user_by_login(login: str) -> dict | None:
    """Login with either the email address or the username."""
    login = (login or "").strip().lower()
    return db.row("SELECT * FROM users WHERE email=? OR username=?", (login, login))


def bootstrap_admin(username: str, password: str, email: str = "", name: str = "") -> str:
    """Create the admin from .env (ADMIN_USERNAME/ADMIN_PASSWORD) if that username doesn't exist yet.
    An existing account is left alone so a password changed in the web UI isn't reset on restart."""
    username = (username or "").strip().lower()
    if not username or not password:
        return "skipped: ADMIN_USERNAME/ADMIN_PASSWORD not set"
    if not USERNAME_RE.match(username):
        return f"skipped: ADMIN_USERNAME '{username}' must be 3-32 chars of a-z 0-9 . _ -"
    if len(password) < 8:
        return "skipped: ADMIN_PASSWORD must be at least 8 characters"
    if db.row("SELECT id FROM users WHERE username=?", (username,)):
        return f"exists: admin '{username}' already present (password not changed)"
    email = (email or f"{username}@localhost.local").strip().lower()
    if get_user_by_email(email):
        db.execute("UPDATE users SET username=?, role='admin', status='active' WHERE email=?", (username, email))
        return f"linked: existing account {email} is now admin '{username}'"
    db.execute(
        "INSERT INTO users(username, email, name, password_hash, role, status) VALUES (?,?,?,?, 'admin', 'active')",
        (username, email, (name or "ผู้ดูแลระบบ").strip(), hash_password(password)),
    )
    return f"created: admin '{username}'"


def register(email: str, password: str, name: str, position: str = "", phone: str = "", mode: str = "approval",
             username: str = "") -> dict:
    """First user becomes an active admin. Later users depend on the registration mode."""
    email = (email or "").strip().lower()
    username = (username or "").strip().lower() or None
    if not EMAIL_RE.match(email):
        raise AuthError("รูปแบบอีเมลไม่ถูกต้อง")
    if username and not USERNAME_RE.match(username):
        raise AuthError("ชื่อผู้ใช้ต้องยาว 3-32 ตัว ใช้ได้เฉพาะ a-z 0-9 . _ -")
    if username and get_user_by_login(username):
        raise AuthError("ชื่อผู้ใช้นี้ถูกใช้แล้ว")
    if not (name or "").strip():
        raise AuthError("ต้องระบุชื่อ")
    check_password_rules(password)
    first = user_count() == 0
    if not first and mode == "closed":
        raise AuthError("ปิดรับสมัครสมาชิก กรุณาติดต่อผู้ดูแลระบบ", 403)
    if get_user_by_email(email):
        raise AuthError("อีเมลนี้มีบัญชีอยู่แล้ว")
    role = "admin" if first else "editor"
    status = "active" if first or mode == "open" else "pending"
    uid = db.execute(
        "INSERT INTO users(username, email, name, position, phone, password_hash, role, status) VALUES (?,?,?,?,?,?,?,?)",
        (username, email, name.strip(), (position or "").strip(), (phone or "").strip(), hash_password(password), role, status),
    )
    return get_user(uid)


def recent_failures(email: str, ip: str) -> int:
    since = (datetime.now() - timedelta(minutes=LOCK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    return db.row(
        "SELECT COUNT(*) n FROM activity_logs WHERE action='auth.login_failed' AND ts>=? AND (target=? OR ip=?)",
        (since, (email or "").strip().lower(), ip),
    )["n"]


def authenticate(login: str, password: str, ip: str) -> dict:
    if recent_failures(login, ip) >= MAX_FAILED:
        raise AuthError(f"เข้าสู่ระบบผิดหลายครั้ง ระงับชั่วคราว {LOCK_MINUTES} นาที", 429)
    u = get_user_by_login(login)
    if not u or not verify_password(password or "", u["password_hash"]):
        raise AuthError("ชื่อผู้ใช้/อีเมล หรือรหัสผ่านไม่ถูกต้อง", 401)
    if u["status"] == "pending":
        raise AuthError("บัญชีรอผู้ดูแลระบบอนุมัติ", 403)
    if u["status"] == "disabled":
        raise AuthError("บัญชีถูกระงับ กรุณาติดต่อผู้ดูแลระบบ", 403)
    return u


def update_profile(uid: int, name=None, position=None, phone=None):
    u = get_user(uid)
    if name is not None and not name.strip():
        raise AuthError("ต้องระบุชื่อ")
    db.execute("UPDATE users SET name=?, position=?, phone=? WHERE id=?", (
        (name if name is not None else u["name"]).strip(),
        (position if position is not None else u["position"] or "").strip(),
        (phone if phone is not None else u["phone"] or "").strip(), uid))
    return get_user(uid)


def change_password(uid: int, current: str, new: str):
    u = get_user(uid)
    if not verify_password(current or "", u["password_hash"]):
        raise AuthError("รหัสผ่านปัจจุบันไม่ถูกต้อง")
    check_password_rules(new)
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new), uid))


def admin_update(uid: int, actor_id: int, role=None, status=None, name=None, position=None):
    u = get_user(uid)
    if not u:
        raise AuthError("ไม่พบผู้ใช้", 404)
    if role is not None and role not in ROLES:
        raise AuthError("บทบาทไม่ถูกต้อง")
    if status is not None and status not in STATUSES:
        raise AuthError("สถานะไม่ถูกต้อง")
    new_role = role or u["role"]
    new_status = status or u["status"]
    if uid == actor_id and (new_role != "admin" or new_status != "active"):
        raise AuthError("ลดสิทธิ์หรือระงับบัญชีของตัวเองไม่ได้")
    if u["role"] == "admin" and (new_role != "admin" or new_status != "active"):
        admins = db.row("SELECT COUNT(*) n FROM users WHERE role='admin' AND status='active'")["n"]
        if admins <= 1:
            raise AuthError("ต้องมีผู้ดูแลระบบที่ใช้งานได้อย่างน้อย 1 คน")
    db.execute("UPDATE users SET role=?, status=?, name=?, position=? WHERE id=?",
               (new_role, new_status, (name or u["name"]).strip(), (position if position is not None else u["position"] or ""), uid))
    if new_status != "active":
        revoke_user_sessions(uid)
    return get_user(uid)


def admin_reset_password(uid: int) -> str:
    """Set a random temporary password and end the user's sessions; returns it once for the admin."""
    if not get_user(uid):
        raise AuthError("ไม่พบผู้ใช้", 404)
    temp = secrets.token_urlsafe(6) + "9a"
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(temp), uid))
    revoke_user_sessions(uid)
    return temp


def delete_user(uid: int, actor_id: int):
    u = get_user(uid)
    if not u:
        raise AuthError("ไม่พบผู้ใช้", 404)
    if uid == actor_id:
        raise AuthError("ลบบัญชีของตัวเองไม่ได้")
    if u["role"] == "admin" and db.row("SELECT COUNT(*) n FROM users WHERE role='admin' AND status='active'")["n"] <= 1:
        raise AuthError("ต้องมีผู้ดูแลระบบที่ใช้งานได้อย่างน้อย 1 คน")
    db.execute("DELETE FROM users WHERE id=?", (uid,))  # sessions cascade; logs keep email text


# ── sessions ───────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(uid: int, ip: str, user_agent: str, remember: bool) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + (timedelta(days=REMEMBER_DAYS) if remember else timedelta(hours=SESSION_HOURS))
    db.execute(
        "INSERT INTO sessions(token_hash, user_id, ip, user_agent, expires_at, last_seen_at) VALUES (?,?,?,?,?,?)",
        (_hash_token(token), uid, ip, user_agent[:400], expires.strftime("%Y-%m-%d %H:%M:%S"), _now()),
    )
    db.execute("UPDATE users SET last_login_at=?, last_login_ip=? WHERE id=?", (_now(), ip, uid))
    return token, expires


def session_user(token: str | None) -> tuple[dict | None, dict | None]:
    """(user, session) for a valid, unexpired session of an active user."""
    if not token:
        return None, None
    s = db.row("SELECT * FROM sessions WHERE token_hash=?", (_hash_token(token),))
    if not s or s["expires_at"] < _now():
        return None, None
    u = get_user(s["user_id"])
    if not u or u["status"] != "active":
        return None, None
    db.execute("UPDATE sessions SET last_seen_at=? WHERE id=?", (_now(), s["id"]))
    db.execute("UPDATE users SET last_seen_at=? WHERE id=?", (_now(), u["id"]))
    return u, s


def end_session(token: str | None):
    if token:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (_hash_token(token),))


def revoke_session(session_id: int, user_id: int | None = None):
    if user_id is None:
        db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    else:
        db.execute("DELETE FROM sessions WHERE id=? AND user_id=?", (session_id, user_id))


def revoke_user_sessions(uid: int, keep_session_id: int | None = None):
    db.execute("DELETE FROM sessions WHERE user_id=? AND id IS NOT ?", (uid, keep_session_id))


def list_sessions(uid: int | None = None) -> list[dict]:
    sql = ("SELECT s.id, s.user_id, u.email, u.name, s.ip, s.user_agent, s.created_at, s.last_seen_at, s.expires_at "
           "FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.expires_at>=?")
    args: tuple = (_now(),)
    if uid is not None:
        sql += " AND s.user_id=?"
        args += (uid,)
    return db.rows(sql + " ORDER BY s.last_seen_at DESC", args)


# ── permissions ─────────────────────────────────────────────────────────────

PUBLIC_API = {
    ("GET", "/api/auth/state"), ("POST", "/api/auth/login"), ("POST", "/api/auth/register"),
    ("POST", "/api/auth/logout"), ("GET", "/api/branding"),
}


def required_role(method: str, path: str) -> str | None:
    """Minimum role for a request; None = public. Static UI files are public (the SPA shows login)."""
    if not (path.startswith("/api/") or path.startswith("/files/")):
        return None
    if (method, path) in PUBLIC_API:
        return None
    if path.startswith("/api/admin/") or path.startswith("/api/settings"):
        return "admin"
    if path.startswith("/api/auth/") or path.startswith("/api/profile"):
        return "viewer"
    if method in ("GET", "HEAD") or path.endswith("/download-zip"):
        return "viewer"
    return "editor"


def has_role(user: dict | None, needed: str) -> bool:
    if not user:
        return False
    rank = {"viewer": 0, "editor": 1, "admin": 2}
    return rank.get(user["role"], -1) >= rank[needed]
