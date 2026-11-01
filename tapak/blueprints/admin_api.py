"""REST API admin (JSON, token Bearer). Semua akses dicatat, diberikan maupun ditolak."""
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import func

from tapak.blueprints.api import api_user, body
from tapak.errors import ApiError
from tapak.extensions import db
from tapak.logs import L, client_ip
from tapak.models import Order, Product, User
from tapak.util import read_product

bp = Blueprint("admin_api", __name__, url_prefix="/admin")


def admin_guard():
    u = api_user()
    base = dict(path=request.path, method=request.method, ip=client_ip())
    g.actor = u.username if u else "anonymous"
    if current_app.config["VULN"]["VULN_ADMIN"]:  # RENTAN: tanpa autentikasi/otorisasi
        L("INFO", "ADMIN_ACCESS", **base, user=g.actor, result="GRANTED", note="vuln_mode")
        return
    if not u:
        L("WARNING", "ADMIN_ACCESS", **base, user=g.actor, result="DENIED", reason="unauthenticated")
        raise ApiError(401, "unauthorized")
    if u.role != "admin":
        L("WARNING", "ADMIN_ACCESS", **base, user=u.username, result="DENIED", reason="not_admin")
        raise ApiError(403, "dilarang")
    L("INFO", "ADMIN_ACCESS", **base, user=u.username, result="GRANTED")


@bp.get("/stats")
def stats():
    admin_guard()
    n = lambda stmt: int(db.session.scalar(stmt) or 0)
    return jsonify(
        users=n(db.select(func.count(User.id))),
        products=n(db.select(func.count(Product.id))),
        orders=n(db.select(func.count(Order.id))),
        low_stock=n(db.select(func.count(Product.id)).where(Product.stock < 10)),
        revenue=n(db.select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == "paid")),
    )


@bp.get("/users")
def users():
    admin_guard()
    return jsonify([dict(id=u.id, username=u.username, role=u.role) for u in db.session.scalars(db.select(User).order_by(User.id))])


@bp.get("/orders")
def orders():
    admin_guard()
    rows = db.session.scalars(db.select(Order).order_by(Order.id.desc()))
    return jsonify([dict(id=o.id, user_id=o.user_id, total=o.total, status=o.status) for o in rows])


@bp.post("/products")
def product_create():
    admin_guard()
    error, v = read_product(body())
    if error:
        raise ApiError(400, error)
    p = Product(**v)
    db.session.add(p)
    db.session.commit()
    L("INFO", "PRODUCT_CREATE", id=p.id, name=v["name"], by=g.actor, ip=client_ip())
    return jsonify(id=p.id, **v), 201


@bp.put("/products/<int:pid>")
def product_update(pid):
    admin_guard()
    p = db.session.get(Product, pid)
    if not p:
        raise ApiError(404, "tidak ditemukan")
    error, v = read_product(body())
    if error:
        raise ApiError(400, error)
    for k, val in v.items():
        setattr(p, k, val)
    db.session.commit()
    L("INFO", "PRODUCT_UPDATE", id=pid, name=v["name"], price=v["price"], by=g.actor, ip=client_ip())
    return jsonify(id=pid, **v)


@bp.delete("/products/<int:pid>")
def product_delete(pid):
    admin_guard()
    p = db.session.get(Product, pid)
    if not p:
        raise ApiError(404, "tidak ditemukan")
    name = p.name
    db.session.delete(p)
    db.session.commit()
    L("WARNING", "PRODUCT_DELETE", id=pid, name=name, by=g.actor, ip=client_ip())
    return jsonify(deleted=pid)
