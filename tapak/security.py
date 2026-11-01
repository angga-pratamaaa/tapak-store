"""Kata sandi (scrypt), token API (HMAC), dan sesi web."""
import base64
import hashlib
import hmac
import json
import time

from flask import current_app, g, session
from werkzeug.security import check_password_hash, generate_password_hash

from tapak.extensions import db
from tapak.models import User


def hash_password(pw):
    return generate_password_hash(pw, method="scrypt")


def verify_password(pw_hash, pw):
    return check_password_hash(pw_hash, pw)


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_token(uid):
    secret = current_app.config["SECRET_KEY"]
    body = _b64(json.dumps({"uid": uid, "exp": int(time.time() * 1000) + 8 * 3600 * 1000}).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(tok):
    secret = current_app.config["SECRET_KEY"]
    try:
        body, sig = str(tok).split(".")
        want = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, want):
            return None
        p = json.loads(_unb64(body))
        return p["uid"] if p["exp"] > time.time() * 1000 else None
    except Exception:
        return None


def web_user():
    """Pengguna dari sesi (cookie). Akun nonaktif otomatis dikeluarkan."""
    if "web_user" not in g:
        u = db.session.get(User, session["uid"]) if "uid" in session else None
        if u is not None and not u.is_active:
            session.clear()
            u = None
        g.web_user = u
    return g.web_user
