"""
services/auth_service.py
User authentication — email/password + Google/GitHub OAuth.
"""
import re
from models import Session, User


# ── VALIDATION HELPERS ────────────────────────────────
def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def _valid_username(username: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_]{3,30}$", username))

def _sanitize(s: str) -> str:
    return s.strip()[:200]


# ── EMAIL / PASSWORD AUTH ─────────────────────────────

def register_user(username: str, email: str, password: str) -> dict:
    username = _sanitize(username).lower()
    email    = _sanitize(email).lower()

    if not _valid_username(username):
        return {"success": False, "error": "Username must be 3-30 chars, letters/numbers/underscore only."}
    if not _valid_email(email):
        return {"success": False, "error": "Invalid email address."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}

    db = Session()
    try:
        if db.query(User).filter_by(username=username).first():
            return {"success": False, "error": "Username already taken."}
        if db.query(User).filter_by(email=email).first():
            return {"success": False, "error": "Email already registered."}

        user = User(username=username, email=email)
        user.set_password(password)
        db.add(user)
        db.commit()
        return {"success": True, "user": user.to_dict()}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": f"Registration failed: {e}"}
    finally:
        db.close()


def login_user(identifier: str, password: str) -> dict:
    identifier = _sanitize(identifier).lower()
    db = Session()
    try:
        user = (db.query(User).filter_by(username=identifier).first() or
                db.query(User).filter_by(email=identifier).first())

        if not user:
            return {"success": False, "error": "No account found with that username or email."}
        if not user.password_hash:
            provider = user.oauth_provider or "social login"
            return {"success": False, "error": f"This account uses {provider}. Please sign in with that provider."}
        if not user.check_password(password):
            return {"success": False, "error": "Incorrect password."}

        return {"success": True, "user": user.to_dict()}
    finally:
        db.close()


# ── OAUTH AUTH ────────────────────────────────────────

def oauth_get_or_create(provider: str, oauth_id: str,
                         email: str, username: str,
                         avatar_url: str = None) -> dict:
    """
    Find existing OAuth user or create a new one.
    Called from the OAuth callback route.
    """
    email    = _sanitize(email).lower()
    username = _sanitize(username).lower()

    db = Session()
    try:
        # 1. Look up by provider + oauth_id (most reliable)
        user = db.query(User).filter_by(
            oauth_provider=provider, oauth_id=str(oauth_id)
        ).first()

        if user:
            # Update avatar in case it changed
            if avatar_url:
                user.avatar_url = avatar_url
            db.commit()
            return {"success": True, "user": user.to_dict()}

        # 2. Email already registered with password → link accounts
        user = db.query(User).filter_by(email=email).first()
        if user:
            user.oauth_provider = provider
            user.oauth_id       = str(oauth_id)
            if avatar_url:
                user.avatar_url = avatar_url
            db.commit()
            return {"success": True, "user": user.to_dict()}

        # 3. New user — create account
        # Ensure username is unique
        base = re.sub(r"[^a-z0-9_]", "", username)[:25] or "user"
        final_username = base
        counter = 1
        while db.query(User).filter_by(username=final_username).first():
            final_username = f"{base}{counter}"
            counter += 1

        user = User(
            username       = final_username,
            email          = email,
            oauth_provider = provider,
            oauth_id       = str(oauth_id),
            avatar_url     = avatar_url,
        )
        db.add(user)
        db.commit()
        return {"success": True, "user": user.to_dict()}

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# ── HELPERS ───────────────────────────────────────────

def get_user_by_id(user_id: int) -> dict | None:
    db = Session()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        return user.to_dict() if user else None
    finally:
        db.close()

def get_user_count() -> int:
    db = Session()
    try:
        return db.query(User).count()
    finally:
        db.close()
