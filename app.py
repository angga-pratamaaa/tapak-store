"""Sepatu RKS-313: REST API e-commerce sepatu (Flask) untuk lab SOC (PBL RKS-313).

PERINGATAN: aplikasi ini SENGAJA memuat kerentanan (toggle VULN_*) untuk diserang di
lingkungan lab terisolasi. JANGAN dipasang di jaringan produksi atau dibuka ke internet.

Mode rentan (VULN_*=1) dan aman (VULN_*=0) memakai endpoint yang sama, sehingga hasil
deteksi SOC bisa dibandingkan sebelum dan sesudah perbaikan.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from db import migrate

VULN_KEYS = ["VULN_SQLI", "VULN_IDOR", "VULN_XSS", "VULN_PRICE", "VULN_ADMIN"]
CATEGORIES = ["lari", "gunung", "basket", "kasual", "sandal", "futsal", "skate"]
PRODUCT_COLS = "id, name, brand, category, price, stock"


def env_vuln(env=None):
    env = os.environ if env is None else env
    return {k: env.get(k) == "1" for k in VULN_KEYS}


def escape_html(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def parse_int(v, default=0):
    """Meniru parseInt(): ambil awalan bilangan bulat; selain itu `default`."""
    if isinstance(v, bool):
        return default
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v == v and abs(v) != float("inf") else default
    m = re.match(r"\s*[-+]?\d+", str(v if v is not None else ""))
    return int(m.group()) if m else default


# ---- kata sandi (scrypt) dan token (HMAC) ----
def hash_password(pw):
    return generate_password_hash(pw, method="scrypt")


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_token(uid, secret):
    body = _b64(json.dumps({"uid": uid, "exp": int(time.time() * 1000) + 8 * 3600 * 1000}).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(tok, secret):
    try:
        body, sig = str(tok).split(".")
        want = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, want):
            return None
        p = json.loads(_unb64(body))
        return p["uid"] if p["exp"] > time.time() * 1000 else None
    except Exception:
        return None


def seed(db):
    migrate(db)
    if db.get("SELECT id FROM users LIMIT 1"):
        return False
    # Kata sandi sengaja lemah untuk uji brute force (hanya lab).
    for u, p, r in [("admin", "Admin#2026", "admin"), ("budi", "password123", "client"),
                    ("sari", "qwerty123", "client"), ("andi", "123456", "client")]:
        db.run("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)", [u, hash_password(p), r])
    # Merek fiktif (bukan merek dagang nyata).
    for n, br, cat, pr, st in [
        ("Langkah Runner Pro", "Langkah", "lari", 549000, 40), ("Rimba Trail X", "Rimba", "gunung", 699000, 25),
        ("Bayu Street Low", "Bayu", "kasual", 399000, 60), ("Langkah Court Elite", "Langkah", "basket", 799000, 20),
        ("Bayu Classic Canvas", "Bayu", "kasual", 289000, 80), ("Rimba Hiker Mid", "Rimba", "gunung", 850000, 15),
        ("Langkah Sprint Lite", "Langkah", "lari", 459000, 35), ("Bayu Sandal Pantai", "Bayu", "sandal", 149000, 100),
        ("Kilat Aero Racer", "Kilat", "lari", 629000, 30), ("Kilat Tempo Flow", "Kilat", "lari", 749000, 22),
        ("Garuda Slam High", "Garuda", "basket", 899000, 18), ("Garuda Court Low", "Garuda", "basket", 649000, 26),
        ("Garuda Futsal Strike", "Garuda", "futsal", 479000, 45), ("Nusa Pasir Slide", "Nusa", "sandal", 179000, 90),
        ("Nusa Kampung Loafer", "Nusa", "kasual", 349000, 50), ("Nusa Batik Sneaker", "Nusa", "kasual", 429000, 40),
        ("Cakra Deck Pro", "Cakra", "skate", 559000, 28), ("Cakra Ollie Mid", "Cakra", "skate", 519000, 24),
        ("Cakra Street Vulc", "Cakra", "skate", 459000, 33), ("Ombak Aqua Trail", "Ombak", "gunung", 599000, 20),
        ("Ombak Wave Slide", "Ombak", "sandal", 199000, 70), ("Ombak Marathon Elite", "Ombak", "lari", 1199000, 12),
        ("Kilat Futsal Turbo", "Kilat", "futsal", 519000, 38), ("Bayu Retro 90", "Bayu", "kasual", 479000, 55)]:
        db.run("INSERT INTO products (name, brand, category, price, stock) VALUES (?,?,?,?,?)", [n, br, cat, pr, st])
    return True


def _num(v):
    """Seperti Number() di JS untuk angka/string angka; None bila bukan bilangan bulat."""
    if isinstance(v, bool) or v is None or isinstance(v, (list, dict)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f == f and f not in (float("inf"), float("-inf")) and f.is_integer() else None


def read_product(b):
    """Validasi input produk (CRUD admin). Mengembalikan (error, nilai)."""
    b = b if isinstance(b, dict) else {}
    name = str(b.get("name") or "").strip()
    brand = str(b.get("brand") or "").strip()
    category = str(b.get("category") or "").strip()
    price, stock = _num(b.get("price")), _num(b.get("stock"))
    if not name or len(name) > 120:
        return "nama wajib diisi (maks. 120 karakter)", None
    if len(brand) > 60:
        return "merek maks. 60 karakter", None
    if category not in CATEGORIES:
        return "kategori harus salah satu dari: " + ", ".join(CATEGORIES), None
    if price is None or price < 0 or price > 100_000_000:
        return "harga harus bilangan bulat >= 0", None
    if stock is None or stock < 0 or stock > 100_000:
        return "stok harus bilangan bulat >= 0", None
    return None, {"name": name, "brand": brand, "category": category, "price": price, "stock": stock}


class ApiError(Exception):
    def __init__(self, status, msg):
        self.status, self.msg = status, msg


def create_app(db, vuln=None, secret=None, public_dir=None, log=print):
    vuln = env_vuln() if vuln is None else vuln
    secret = secret or os.environ.get("SECRET_KEY") or "ganti-di-env-lab"
    app = Flask(__name__, static_folder=None)
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    def ip():
        return request.headers.get("X-Forwarded-For") or request.remote_addr

    # Log berformat `waktu LEVEL event=NAMA kunci=nilai ...`. Nilai yang mengandung spasi, kutip,
    # atau baris baru di-escape (JSON) agar pengguna tidak bisa memalsukan baris log.
    def kv(v):
        s = "-" if v is None else str(v)
        return s if re.fullmatch(r"[\w.:@/-]+", s, re.ASCII) else json.dumps(s, ensure_ascii=False)

    def L(level, event, **f):
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        log(f"{ts} {level} event={event} " + " ".join(f"{k}={kv(v)}" for k, v in f.items()))

    def body():
        if not request.get_data():
            return {}
        data = request.get_json(force=True, silent=True)
        if data is None:
            raise ApiError(400, "JSON tidak valid")
        return data if isinstance(data, dict) else {}

    def user_of():
        a = request.headers.get("Authorization", "")
        if not a.startswith("Bearer "):
            return None
        uid = read_token(a[7:], secret)
        return db.get("SELECT id, username, role FROM users WHERE id = ?", [uid]) if uid else None

    def need_auth():
        u = user_of()
        if not u:
            raise ApiError(401, "unauthorized")
        return u

    @app.errorhandler(ApiError)
    def _api_error(e):
        return jsonify(error=e.msg), e.status

    @app.errorhandler(HTTPException)
    def _http_error(e):
        if request.path.startswith(("/api", "/admin")):
            return jsonify(error=e.description if e.code != 404 else "tidak ditemukan"), e.code
        return e

    @app.errorhandler(Exception)
    def _server_error(e):
        L("ERROR", "SERVER_ERROR", msg=str(e), ip=ip())
        return jsonify(error="kesalahan server"), 500

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", vuln=vuln)

    # ---- register dan login ----
    @app.post("/api/register")
    def register():
        b = body()
        u, p = str(b.get("username") or "").strip(), str(b.get("password") or "")
        if not u or len(u) > 50 or len(p) < 6:
            raise ApiError(400, "username/password tidak valid")
        if db.get("SELECT id FROM users WHERE username = ?", [u]):
            L("WARNING", "REGISTER_FAILED", user=u, ip=ip(), reason="username_taken")
            raise ApiError(409, "username sudah dipakai")
        r = db.run("INSERT INTO users (username, password_hash, role) VALUES (?,?, 'client')", [u, hash_password(p)])
        L("INFO", "REGISTER_OK", user=u, ip=ip())
        return jsonify(id=r["id"], username=u), 201

    @app.post("/api/login")
    def login():
        # Tanpa pembatasan percobaan: sasaran uji brute force.
        b = body()
        name = str(b.get("username") or "")
        u = db.get("SELECT * FROM users WHERE username = ?", [name])
        ua = request.headers.get("User-Agent", "-")
        if not u or not check_password_hash(u["password_hash"], str(b.get("password") or "")):
            # Alasan hanya masuk log (untuk analis), tidak dikirim ke klien.
            L("WARNING", "LOGIN_FAILED", user=name, ip=ip(), reason="bad_password" if u else "unknown_user", ua=ua)
            raise ApiError(401, "login gagal")
        L("INFO", "LOGIN_OK", user=u["username"], role=u["role"], ip=ip(), ua=ua)
        return jsonify(token=sign_token(u["id"], secret), role=u["role"], username=u["username"])

    # ---- katalog (publik) ----
    @app.get("/api/products")
    def products():
        return jsonify(db.all(f"SELECT {PRODUCT_COLS} FROM products ORDER BY id"))

    @app.get("/api/products/search")
    def search():
        q = request.args.get("q", "")
        L("INFO", "SEARCH", q=q, ip=ip())
        if vuln["VULN_SQLI"]:
            # RENTAN: string digabung langsung ke SQL (SQL injection).
            try:
                return jsonify(db.raw(f"SELECT {PRODUCT_COLS} FROM products WHERE name LIKE '%{q}%'"))
            except Exception as e:  # galat SQL bocor ke klien (sengaja)
                return jsonify(error=str(e)), 500
        return jsonify(db.all(f"SELECT {PRODUCT_COLS} FROM products WHERE name LIKE ? OR brand LIKE ?", [f"%{q}%", f"%{q}%"]))

    @app.get("/api/products/<int:pid>/reviews")
    def reviews(pid):
        return jsonify(db.all(
            "SELECT r.id, r.user_id, u.username, r.rating, r.comment FROM reviews r "
            "JOIN users u ON u.id = r.user_id WHERE r.product_id = ? ORDER BY r.id", [pid]))

    @app.post("/api/products/<int:pid>/reviews")
    def add_review(pid):
        user = need_auth()
        b = body()
        comment = str(b.get("comment") or "")
        if not vuln["VULN_XSS"]:
            comment = escape_html(comment)  # AMAN: HTML di-escape saat disimpan
        rating = min(5, max(1, parse_int(b.get("rating", 5), 5) or 5))
        r = db.run("INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?,?,?,?)",
                   [pid, user["id"], rating, comment])
        return jsonify(id=r["id"]), 201

    # ---- pesanan ----
    @app.post("/api/orders")
    def create_order():
        user = need_auth()
        raw_items = body().get("items") or []
        if not isinstance(raw_items, list):
            raw_items = []
        items, total = [], 0
        for it in raw_items:
            it = it if isinstance(it, dict) else {}
            p = db.get("SELECT id, price FROM products WHERE id = ?", [parse_int(it.get("product_id"))])
            qty, size = parse_int(it.get("qty")), parse_int(it.get("size"))
            if not p or qty < 1 or size < 36 or size > 46:
                raise ApiError(400, "item tidak valid (ukuran 36-46)")
            # RENTAN: harga dari klien dipercaya bila VULN_PRICE=1. AMAN: harga dari server.
            unit = parse_int(it["price"]) if vuln["VULN_PRICE"] and it.get("price") is not None else p["price"]
            items.append((p["id"], qty, size, unit))
            total += unit * qty
        if not items:
            raise ApiError(400, "keranjang kosong")
        o = db.run("INSERT INTO orders (user_id, total, status) VALUES (?,?, 'paid')", [user["id"], total])
        for pid, qty, size, unit in items:
            db.run("INSERT INTO order_items (order_id, product_id, qty, size, unit_price) VALUES (?,?,?,?,?)",
                   [o["id"], pid, qty, size, unit])
        L("INFO", "ORDER", id=o["id"], user=user["username"], total=total, ip=ip())
        return jsonify(id=o["id"], total=total), 201

    @app.get("/api/orders")
    def my_orders():
        user = need_auth()
        return jsonify(db.all("SELECT id, total, status FROM orders WHERE user_id = ? ORDER BY id DESC", [user["id"]]))

    @app.get("/api/orders/<int:oid>")
    def order(oid):
        user = need_auth()
        o = db.get("SELECT * FROM orders WHERE id = ?", [oid])
        if not o:
            raise ApiError(404, "tidak ditemukan")
        # RENTAN (IDOR): kepemilikan tidak dicek bila VULN_IDOR=1.
        if not vuln["VULN_IDOR"] and o["user_id"] != user["id"] and user["role"] != "admin":
            L("WARNING", "ORDER_ACCESS_DENIED", order=o["id"], user=user["username"], ip=ip())
            raise ApiError(403, "dilarang")
        items = db.all("SELECT product_id, qty, size, unit_price FROM order_items WHERE order_id = ?", [o["id"]])
        return jsonify(id=o["id"], user_id=o["user_id"], total=o["total"], status=o["status"], items=items)

    # ---- area admin: semua akses dicatat (diberikan maupun ditolak) ----
    def admin_guard():
        u = user_of()
        base = dict(path=request.path, method=request.method, ip=ip())
        g.actor = u["username"] if u else "anonymous"
        if vuln["VULN_ADMIN"]:  # RENTAN: tanpa autentikasi/otorisasi
            L("INFO", "ADMIN_ACCESS", **base, user=g.actor, result="GRANTED", note="vuln_mode")
            return
        if not u:
            L("WARNING", "ADMIN_ACCESS", **base, user=g.actor, result="DENIED", reason="unauthenticated")
            raise ApiError(401, "unauthorized")
        if u["role"] != "admin":
            L("WARNING", "ADMIN_ACCESS", **base, user=u["username"], result="DENIED", reason="not_admin")
            raise ApiError(403, "dilarang")
        L("INFO", "ADMIN_ACCESS", **base, user=u["username"], result="GRANTED")

    @app.get("/admin/stats")
    def stats():
        admin_guard()
        n = lambda sql: int((db.get(sql) or {}).get("n") or 0)
        return jsonify(
            users=n("SELECT COUNT(*) AS n FROM users"),
            products=n("SELECT COUNT(*) AS n FROM products"),
            orders=n("SELECT COUNT(*) AS n FROM orders"),
            low_stock=n("SELECT COUNT(*) AS n FROM products WHERE stock < 10"),
            revenue=n("SELECT COALESCE(SUM(total), 0) AS n FROM orders"),
        )

    @app.get("/admin/users")
    def admin_users():
        admin_guard()
        return jsonify(db.all("SELECT id, username, role FROM users"))

    @app.get("/admin/orders")
    def admin_orders():
        admin_guard()
        return jsonify(db.all("SELECT id, user_id, total, status FROM orders ORDER BY id DESC"))

    # CRUD produk (khusus admin)
    @app.post("/admin/products")
    def product_create():
        admin_guard()
        error, v = read_product(body())
        if error:
            raise ApiError(400, error)
        r = db.run("INSERT INTO products (name, brand, category, price, stock) VALUES (?,?,?,?,?)",
                   [v["name"], v["brand"], v["category"], v["price"], v["stock"]])
        L("INFO", "PRODUCT_CREATE", id=r["id"], name=v["name"], by=g.actor, ip=ip())
        return jsonify(id=r["id"], **v), 201

    @app.put("/admin/products/<int:pid>")
    def product_update(pid):
        admin_guard()
        if not db.get("SELECT id FROM products WHERE id = ?", [pid]):
            raise ApiError(404, "tidak ditemukan")
        error, v = read_product(body())
        if error:
            raise ApiError(400, error)
        db.run("UPDATE products SET name = ?, brand = ?, category = ?, price = ?, stock = ? WHERE id = ?",
               [v["name"], v["brand"], v["category"], v["price"], v["stock"], pid])
        L("INFO", "PRODUCT_UPDATE", id=pid, name=v["name"], price=v["price"], by=g.actor, ip=ip())
        return jsonify(id=pid, **v)

    @app.delete("/admin/products/<int:pid>")
    def product_delete(pid):
        admin_guard()
        p = db.get("SELECT id, name FROM products WHERE id = ?", [pid])
        if not p:
            raise ApiError(404, "tidak ditemukan")
        db.run("DELETE FROM products WHERE id = ?", [pid])
        L("WARNING", "PRODUCT_DELETE", id=pid, name=p["name"], by=g.actor, ip=ip())
        return jsonify(deleted=pid)

    # ---- berkas statis (HTML/CSS/JS) ----
    if public_dir:
        @app.get("/")
        def index():
            return send_from_directory(public_dir, "index.html")

        @app.get("/<path:name>")
        def static_file(name):
            return send_from_directory(public_dir, name)

    return app
