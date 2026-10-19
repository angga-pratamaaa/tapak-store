import json
import re

import pytest

from app import create_app, seed
from db import open_db

OFF = dict(VULN_SQLI=False, VULN_IDOR=False, VULN_XSS=False, VULN_PRICE=False, VULN_ADMIN=False)


class T:
    def __init__(self, **vuln):
        self.db = open_db("sqlite::memory:")
        seed(self.db)
        self.logs = []
        self.client = create_app(self.db, vuln={**OFF, **vuln}, secret="tes", log=self.logs.append).test_client()

    def call(self, path, method="GET", body=None, token=None, raw=None):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        kw = {}
        if raw is not None:
            kw = dict(data=raw, content_type="application/json")
        elif body is not None:
            kw = dict(json=body)
        r = self.client.open(path, method=method, headers=h, **kw)
        return r.status_code, r.get_json(silent=True)

    def login(self, u, p):
        return (self.call("/api/login", "POST", {"username": u, "password": p})[1] or {}).get("token")

    @property
    def log_text(self):
        return "\n".join(self.logs)


def test_health_dan_produk():
    t = T()
    assert t.call("/api/health")[1]["status"] == "ok"
    assert len(t.call("/api/products")[1]) == 24


def test_login():
    t = T()
    assert t.call("/api/login", "POST", {"username": "budi", "password": "salah"})[0] == 401
    assert t.login("budi", "password123")


def test_sqli():
    q = "/api/products/search?q=" + "%27%20OR%20%271%27%3D%271"
    assert len(T(VULN_SQLI=False).call(q)[1]) == 0
    assert len(T(VULN_SQLI=True).call(q)[1]) == 24


def test_idor():
    for flag, want in [(False, 403), (True, 200)]:
        t = T(VULN_IDOR=flag)
        b = t.login("budi", "password123")
        oid = t.call("/api/orders", "POST", {"items": [{"product_id": 1, "qty": 1, "size": 40}]}, b)[1]["id"]
        assert t.call(f"/api/orders/{oid}", token=t.login("sari", "qwerty123"))[0] == want


def test_harga():
    body = {"items": [{"product_id": 4, "qty": 1, "size": 42, "price": 1}]}
    for flag, want in [(False, 799000), (True, 1)]:
        t = T(VULN_PRICE=flag)
        assert t.call("/api/orders", "POST", body, t.login("budi", "password123"))[1]["total"] == want


def test_xss():
    body = {"rating": 5, "comment": "<script>alert(1)</script>"}
    for flag, has in [(False, False), (True, True)]:
        t = T(VULN_XSS=flag)
        t.call("/api/products/1/reviews", "POST", body, t.login("budi", "password123"))
        assert ("<script>" in t.call("/api/products/1/reviews")[1][0]["comment"]) == has


def test_admin_akses():
    t = T(VULN_ADMIN=False)
    assert t.call("/admin/users")[0] == 401
    assert t.call("/admin/users", token=t.login("budi", "password123"))[0] == 403
    assert t.call("/admin/users", token=t.login("admin", "Admin#2026"))[0] == 200
    assert T(VULN_ADMIN=True).call("/admin/users")[0] == 200


def test_token_rusak():
    t = T()
    assert t.call("/api/orders", token=t.login("budi", "password123") + "x")[0] == 401


def test_ukuran_sepatu():
    t = T()
    b = t.login("budi", "password123")
    for size in [0, 20, 99, None]:
        it = {"product_id": 1, "qty": 1}
        if size is not None:
            it["size"] = size
        assert t.call("/api/orders", "POST", {"items": [it]}, b)[0] == 400
    st, j = t.call("/api/orders", "POST", {"items": [{"product_id": 1, "qty": 2, "size": 41}]}, b)
    assert st == 201 and j["total"] == 549000 * 2
    assert t.call(f"/api/orders/{j['id']}", token=b)[1]["items"][0]["size"] == 41


def test_cari_merek():
    assert len(T().call("/api/products/search?q=Rimba")[1]) == 2


def test_json_rusak():
    t = T()
    assert t.call("/api/login", "POST", raw="{bukan json")[0] == 400


# ---------- logging ----------
def test_log_login():
    t = T()
    t.call("/api/login", "POST", {"username": "budi", "password": "SALAH-RAHASIA"})
    t.call("/api/login", "POST", {"username": "tidakada", "password": "x"})
    t.login("budi", "password123")
    a = t.log_text
    assert re.search(r"WARNING event=LOGIN_FAILED user=budi .*reason=bad_password", a)
    assert re.search(r"WARNING event=LOGIN_FAILED user=tidakada .*reason=unknown_user", a)
    assert re.search(r"INFO event=LOGIN_OK user=budi role=client", a)
    assert "SALAH-RAHASIA" not in a and "password123" not in a


def test_log_tidak_bisa_dipalsukan():
    t = T()
    evil = "x\n2026-01-01T00:00:00Z INFO event=LOGIN_OK user=admin"
    t.call("/api/login", "POST", {"username": evil, "password": "x"})
    line = next(l for l in t.logs if "LOGIN_FAILED" in l)
    assert "\n" not in line
    assert not any(re.match(r"^\S+ INFO event=LOGIN_OK", l) for l in t.log_text.split("\n"))
    assert 'user="x\\n2026-01-01T00:00:00Z INFO event=LOGIN_OK user=admin"' in line


def test_log_admin():
    t = T()
    t.call("/admin/users")
    t.call("/admin/users", token=t.login("budi", "password123"))
    t.call("/admin/users", token=t.login("admin", "Admin#2026"))
    a = t.log_text
    assert re.search(r"WARNING event=ADMIN_ACCESS .*user=anonymous result=DENIED reason=unauthenticated", a)
    assert re.search(r"WARNING event=ADMIN_ACCESS .*user=budi result=DENIED reason=not_admin", a)
    assert re.search(r"INFO event=ADMIN_ACCESS .*user=admin result=GRANTED", a)


def test_log_register():
    t = T()
    for _ in range(2):
        t.call("/api/register", "POST", {"username": "baru", "password": "rahasia1"})
    assert "event=REGISTER_OK user=baru" in t.log_text
    assert re.search(r"event=REGISTER_FAILED user=baru .*reason=username_taken", t.log_text)


def test_timestamp_iso():
    t = T()
    t.call("/api/login", "POST", {"username": "x", "password": "y"})
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z WARNING event=LOGIN_FAILED", t.logs[0])


# ---------- CRUD produk dan dashboard ----------
def test_crud_produk():
    t = T()
    a = t.login("admin", "Admin#2026")
    body = dict(name="Uji Sepatu", brand="Bayu", category="kasual", price=123000, stock=5)
    st, c = t.call("/admin/products", "POST", body, a)
    assert st == 201
    pid = c["id"]
    assert any(p["id"] == pid and p["name"] == "Uji Sepatu" for p in t.call("/api/products")[1])
    assert t.call(f"/admin/products/{pid}", "PUT", {**body, "price": 99000, "stock": 3}, a)[0] == 200
    assert next(p for p in t.call("/api/products")[1] if p["id"] == pid)["price"] == 99000
    assert t.call(f"/admin/products/{pid}", "DELETE", token=a)[0] == 200
    assert not any(p["id"] == pid for p in t.call("/api/products")[1])
    assert t.call(f"/admin/products/{pid}", "DELETE", token=a)[0] == 404
    x = t.log_text
    assert re.search(r'event=PRODUCT_CREATE id=\d+ name="Uji Sepatu" by=admin', x)
    assert re.search(r"event=PRODUCT_UPDATE .*price=99000 by=admin", x)
    assert re.search(r"WARNING event=PRODUCT_DELETE .*by=admin", x)


def test_validasi_produk():
    t = T()
    a = t.login("admin", "Admin#2026")
    ok = dict(name="A", brand="B", category="lari", price=1000, stock=1)
    for bad in [{"name": ""}, {"category": "roket"}, {"price": -1}, {"price": 1.5}, {"stock": -5}, {"price": "abc"}]:
        assert t.call("/admin/products", "POST", {**ok, **bad}, a)[0] == 400, json.dumps(bad)
    assert t.call("/admin/products", "POST", ok, a)[0] == 201
    assert t.call("/admin/products/9999", "PUT", ok, a)[0] == 404


def test_crud_hak_akses():
    body = dict(name="X", brand="B", category="lari", price=1000, stock=1)
    t = T(VULN_ADMIN=False)
    assert t.call("/admin/products", "POST", body)[0] == 401
    b = t.login("budi", "password123")
    assert t.call("/admin/products", "POST", body, b)[0] == 403
    assert t.call("/admin/products/1", "DELETE", token=b)[0] == 403
    assert t.call("/admin/products/1", "PUT", body, b)[0] == 403
    assert len(t.call("/api/products")[1]) == 24
    t = T(VULN_ADMIN=True)
    assert t.call("/admin/products", "POST", body)[0] == 201
    assert re.search(r"event=PRODUCT_CREATE .*by=anonymous", t.log_text)


def test_dashboard():
    t = T()
    b = t.login("budi", "password123")
    t.call("/api/orders", "POST", {"items": [{"product_id": 1, "qty": 2, "size": 40}]}, b)
    assert t.call("/admin/stats", token=b)[0] == 403
    assert t.call("/admin/stats")[0] == 401
    st, j = t.call("/admin/stats", token=t.login("admin", "Admin#2026"))
    assert st == 200
    assert j == dict(users=4, products=24, orders=1, low_stock=0, revenue=549000 * 2)
