"""REST API publik (JSON, token Bearer). Perilaku dan format log sama dengan versi awal."""
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_, text

from tapak.errors import ApiError
from tapak.extensions import db
from tapak.logs import L, client_ip
from tapak.models import Order, Product, Review, User
from tapak.security import read_token, sign_token
from tapak.services import attempt_login, create_order, register_user
from tapak.util import escape_html, parse_int

bp = Blueprint("api", __name__, url_prefix="/api")
COLS = "id, name, brand, category, price, stock"


def body():
    if not request.get_data():
        return {}
    data = request.get_json(force=True, silent=True)
    if data is None:
        raise ApiError(400, "JSON tidak valid")
    return data if isinstance(data, dict) else {}


def api_user():
    a = request.headers.get("Authorization", "")
    if not a.startswith("Bearer "):
        return None
    uid = read_token(a[7:])
    u = db.session.get(User, uid) if uid else None
    return u if u and u.is_active else None


def need_auth():
    u = api_user()
    if not u:
        raise ApiError(401, "unauthorized")
    return u


@bp.get("/health")
def health():
    return jsonify(status="ok", vuln=current_app.config["VULN"])


@bp.post("/register")
def register():
    b = body()
    u, p = str(b.get("username") or "").strip(), str(b.get("password") or "")
    if not u or len(u) > 50 or len(p) < 6:
        raise ApiError(400, "username/password tidak valid")
    user = register_user(u, p)
    if not user:
        raise ApiError(409, "username sudah dipakai")
    return jsonify(id=user.id, username=u), 201


@bp.post("/login")
def login():
    b = body()
    u = attempt_login(str(b.get("username") or ""), str(b.get("password") or ""))
    if not u:
        raise ApiError(401, "login gagal")
    return jsonify(token=sign_token(u.id), role=u.role, username=u.username)


@bp.get("/products")
def products():
    return jsonify([p.to_dict() for p in db.session.scalars(db.select(Product).order_by(Product.id))])


@bp.get("/products/search")
def search():
    q = request.args.get("q", "")
    L("INFO", "SEARCH", q=q, ip=client_ip())
    if current_app.config["VULN"]["VULN_SQLI"]:
        # RENTAN: string digabung langsung ke SQL (SQL injection). Tanda ':' di-escape hanya
        # agar text() tidak menganggapnya parameter; tanda kutip tetap bisa menyuntik SQL.
        sql = f"SELECT {COLS} FROM products WHERE name LIKE '%{q}%'".replace(":", "\\:")
        try:
            return jsonify([dict(r._mapping) for r in db.session.execute(text(sql))])
        except Exception as e:  # galat SQL bocor ke klien (sengaja)
            db.session.rollback()
            return jsonify(error=str(e)), 500
    like = f"%{q}%"
    rows = db.session.scalars(db.select(Product).where(or_(Product.name.like(like), Product.brand.like(like))).order_by(Product.id))
    return jsonify([p.to_dict() for p in rows])


@bp.get("/products/<int:pid>/reviews")
def reviews(pid):
    rows = db.session.scalars(db.select(Review).where(Review.product_id == pid).order_by(Review.id))
    return jsonify([dict(id=r.id, user_id=r.user_id, username=r.user.username, rating=r.rating, comment=r.comment) for r in rows])


def store_review(pid, user, rating, comment):
    """Simpan ulasan. AMAN: HTML di-escape saat disimpan. RENTAN (VULN_XSS=1): disimpan apa adanya."""
    if not current_app.config["VULN"]["VULN_XSS"]:
        comment = escape_html(comment)
    rating = min(5, max(1, parse_int(rating, 5) or 5))
    r = Review(product_id=pid, user_id=user.id, rating=rating, comment=comment)
    db.session.add(r)
    db.session.commit()
    return r


@bp.post("/products/<int:pid>/reviews")
def add_review(pid):
    user = need_auth()
    b = body()
    r = store_review(pid, user, b.get("rating", 5), str(b.get("comment") or ""))
    return jsonify(id=r.id), 201


@bp.post("/orders")
def post_order():
    user = need_auth()
    # Jalur API lama: pembayaran dianggap langsung lunas (simulasi). Jalur web memakai alur bukti bayar.
    o = create_order(user, body().get("items") or [], status="paid")
    return jsonify(id=o.id, total=o.total), 201


@bp.get("/orders")
def my_orders():
    user = need_auth()
    rows = db.session.scalars(db.select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()))
    return jsonify([dict(id=o.id, total=o.total, status=o.status) for o in rows])


@bp.get("/orders/<int:oid>")
def order(oid):
    user = need_auth()
    o = db.session.get(Order, oid)
    if not o:
        raise ApiError(404, "tidak ditemukan")
    # RENTAN (IDOR): kepemilikan tidak dicek bila VULN_IDOR=1.
    if not current_app.config["VULN"]["VULN_IDOR"] and o.user_id != user.id and user.role != "admin":
        L("WARNING", "ORDER_ACCESS_DENIED", order=o.id, user=user.username, ip=client_ip())
        raise ApiError(403, "dilarang")
    items = [dict(product_id=i.product_id, qty=i.qty, size=i.size, unit_price=i.unit_price) for i in o.items]
    return jsonify(id=o.id, user_id=o.user_id, total=o.total, status=o.status, items=items)
