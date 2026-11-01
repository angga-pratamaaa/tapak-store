"""Logika bisnis yang dipakai bersama oleh REST API dan halaman web."""
from flask import current_app, request

from tapak.errors import ApiError
from tapak.extensions import db
from tapak.logs import L, client_ip
from tapak.models import Order, OrderItem, Product, User
from tapak.security import hash_password, verify_password
from tapak.util import parse_int


def find_user(name):
    return db.session.scalars(db.select(User).filter_by(username=name)).first()


def attempt_login(name, password):
    """Kembalikan User bila berhasil, None bila gagal. Semua hasil dicatat ke log.
    Tanpa pembatasan percobaan: sasaran uji brute force (lab)."""
    u = find_user(name)
    ua = request.headers.get("User-Agent", "-")
    if not u or not verify_password(u.password_hash, password):
        L("WARNING", "LOGIN_FAILED", user=name, ip=client_ip(), reason="bad_password" if u else "unknown_user", ua=ua)
        return None
    if not u.is_active:
        L("WARNING", "LOGIN_FAILED", user=name, ip=client_ip(), reason="inactive", ua=ua)
        return None
    L("INFO", "LOGIN_OK", user=u.username, role=u.role, ip=client_ip(), ua=ua)
    return u


def register_user(username, password, email=None):
    """Kembalikan User baru, atau None bila username sudah dipakai."""
    if find_user(username):
        L("WARNING", "REGISTER_FAILED", user=username, ip=client_ip(), reason="username_taken")
        return None
    u = User(username=username, email=email or None, password_hash=hash_password(password), role="client")
    db.session.add(u)
    db.session.commit()
    L("INFO", "REGISTER_OK", user=username, ip=client_ip())
    return u


def create_order(user, raw_items, status="pending"):
    """Buat pesanan dari daftar {product_id, qty, size[, price]}. Harga dari server,
    kecuali VULN_PRICE=1 (RENTAN: harga dari klien dipercaya)."""
    vuln = current_app.config["VULN"]
    if not isinstance(raw_items, list):
        raw_items = []
    items, total = [], 0
    for it in raw_items:
        it = it if isinstance(it, dict) else {}
        p = db.session.get(Product, parse_int(it.get("product_id")))
        qty, size = parse_int(it.get("qty")), parse_int(it.get("size"))
        if not p or qty < 1 or size < 36 or size > 46:
            raise ApiError(400, "item tidak valid (ukuran 36-46)")
        unit = parse_int(it["price"]) if vuln["VULN_PRICE"] and it.get("price") is not None else p.price
        items.append(OrderItem(product_id=p.id, qty=qty, size=size, unit_price=unit))
        total += unit * qty
    if not items:
        raise ApiError(400, "keranjang kosong")
    o = Order(user_id=user.id, total=total, status=status, items=items)
    db.session.add(o)
    db.session.commit()
    L("INFO", "ORDER", id=o.id, user=user.username, total=total, ip=client_ip())
    return o
