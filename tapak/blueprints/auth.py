"""Halaman web: login, register, logout (sesi cookie + CSRF)."""
from functools import wraps
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from tapak.forms import LoginForm, RegisterForm
from tapak.logs import L, client_ip
from tapak.security import web_user
from tapak.services import attempt_login, register_user

bp = Blueprint("auth", __name__)


def safe_next(target, default="shop.home"):
    """Cegah open redirect: hanya path lokal yang diizinkan."""
    if target and target.startswith("/") and not target.startswith("//") and not urlparse(target).netloc:
        return target
    return url_for(default)


def login_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if not web_user():
            flash("Silakan masuk terlebih dahulu.", "err")
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return f(*a, **k)
    return wrapper


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        u = attempt_login(form.username.data.strip(), form.password.data)
        if u:
            session.clear()
            session["uid"] = u.id
            flash(f"Selamat datang, {u.username}.", "ok")
            return redirect(safe_next(request.args.get("next")))
        flash("Username atau kata sandi salah, atau akun dinonaktifkan.", "err")
    return render_template("auth/login.html", form=form), (401 if form.is_submitted() and form.errors == {} else 200)


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if register_user(form.username.data.strip(), form.password.data, form.email.data.strip()):
            flash("Akun dibuat. Silakan masuk.", "ok")
            return redirect(url_for("auth.login"))
        form.username.errors.append("Username sudah dipakai.")
    return render_template("auth/register.html", form=form)


@bp.post("/logout")
def logout():
    u = web_user()
    if u:
        L("INFO", "LOGOUT", user=u.username, ip=client_ip())
    session.clear()
    flash("Anda sudah keluar.", "ok")
    return redirect(url_for("shop.home"))
