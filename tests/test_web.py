import io
import re

from helpers import T

from tapak.extensions import db
from tapak.models import Order, Product, User

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64


def html(r):
    return r.get_data(as_text=True)


# ---- FR: register / login / hash ----
def test_register_validasi_server():
    t = T()
    c = t.web()
    bad = [dict(username="a", email="x@y.id", password="abcd1234", confirm="abcd1234"),
           dict(username="baru", email="bukan-email", password="abcd1234", confirm="abcd1234"),
           dict(username="baru", email="x@y.id", password="abcdefgh", confirm="abcdefgh"),
           dict(username="baru", email="x@y.id", password="abcd1234", confirm="beda1234")]
    for d in bad:
        assert c.post("/register", data=d).status_code == 200, d
    assert c.post("/register", data=dict(username="baru", email="x@y.id", password="abcd1234", confirm="abcd1234")).status_code == 302
    with t.app.app_context():
        u = db.session.scalars(db.select(User).filter_by(username="baru")).one()
        assert u.password_hash.startswith("scrypt:") and "abcd1234" not in u.password_hash
        assert u.role == "client" and u.is_active
    r = c.post("/register", data=dict(username="baru", email="x@y.id", password="abcd1234", confirm="abcd1234"))
    assert "sudah dipakai" in html(r)
    assert re.search(r"event=REGISTER_FAILED user=baru .*reason=username_taken", t.log_text)


def test_login_logout_web():
    t = T()
    c = t.web()
    assert "Username atau kata sandi salah" in html(c.post("/login", data=dict(username="budi", password="salah")))
    assert re.search(r"LOGIN_FAILED user=budi .*reason=bad_password", t.log_text)
    assert c.get("/orders").status_code == 302  # belum login -> ke halaman login
    c = t.web("budi", "password123")
    assert c.get("/orders").status_code == 200
    assert re.search(r"INFO event=LOGIN_OK user=budi role=client", t.log_text)
    assert c.post("/logout").status_code == 302
    assert c.get("/orders").status_code == 302


def test_open_redirect_ditolak():
    t = T()
    for nxt in ["https://evil.example/", "//evil.example/", "javascript:alert(1)"]:
        r = t.new_client().post(f"/login?next={nxt}", data=dict(username="budi", password="password123"))
        assert r.status_code == 302 and "evil" not in r.headers["Location"] and "javascript" not in r.headers["Location"]
    r = t.new_client().post("/login?next=/orders", data=dict(username="budi", password="password123"))
    assert r.headers["Location"] == "/orders"


def test_akun_nonaktif_tidak_bisa_masuk():
    t = T()
    a = t.web("admin", "Admin#2026")
    with t.app.app_context():
        uid = db.session.scalars(db.select(User).filter_by(username="sari")).one().id
    c = t.web("sari", "qwerty123")
    assert a.post(f"/panel/users/{uid}/toggle").status_code == 302
    assert c.get("/orders").status_code == 302  # sesi lama otomatis tidak berlaku
    assert t.new_client().post("/login", data=dict(username="sari", password="qwerty123")).status_code == 401
    assert t.login("sari", "qwerty123") is None  # API juga menolak
    assert re.search(r"LOGIN_FAILED user=sari .*reason=inactive", t.log_text)
    assert re.search(r"WARNING event=USER_STATUS target=sari active=0 by=admin", t.log_text)


# ---- FR: katalog + filter harga ----
def test_katalog_filter_harga():
    t = T()
    c = t.web()
    assert "24 produk ditemukan" in html(c.get("/products"))
    r = html(c.get("/products?min_price=500000&max_price=700000"))
    assert "Langkah Runner Pro" in r and "Rimba Trail X" in r and "Bayu Street Low" not in r
    assert "Harga maks harus" in html(c.get("/products?min_price=700000&max_price=500000"))
    assert "Rimba Trail X" in html(c.get("/products?q=rimba&category=gunung"))
    assert "0 produk ditemukan" in html(c.get("/products?q=%27+OR+%271%27%3D%271"))  # SQLi di web: tidak rentan (ORM)
    assert "Halaman 1 dari 2" in html(c.get("/products"))
    assert c.get("/").status_code == 200 and c.get("/products/1").status_code == 200
    assert c.get("/products/9999").status_code == 404


# ---- hak akses admin ----
def test_panel_admin_hak_akses():
    t = T()
    assert t.new_client().get("/panel/").status_code == 302
    assert t.web("budi", "password123").get("/panel/").status_code == 403
    assert t.web("admin", "Admin#2026").get("/panel/").status_code == 200
    assert re.search(r"WARNING event=ADMIN_ACCESS .*user=anonymous result=DENIED reason=unauthenticated", t.log_text)
    assert re.search(r"WARNING event=ADMIN_ACCESS .*user=budi result=DENIED reason=not_admin", t.log_text)
    assert re.search(r"INFO event=ADMIN_ACCESS .*user=admin result=GRANTED", t.log_text)


# ---- CRUD produk + unggah gambar ----
def test_panel_crud_produk_dan_gambar():
    t = T()
    a = t.web("admin", "Admin#2026")
    form = dict(name="Uji Web", brand="Bayu", category="lari", price="123000", stock="5", description="deskripsi")
    r = a.post("/panel/products/new", data={**form, "image": (io.BytesIO(PNG), "foto.png")}, content_type="multipart/form-data")
    assert r.status_code == 302
    with t.app.app_context():
        p = db.session.scalars(db.select(Product).filter_by(name="Uji Web")).one()
        pid, img = p.id, p.image
    assert img and img.endswith(".png")
    assert a.get(f"/uploads/products/{img}").data.startswith(b"\x89PNG")
    # berkas bukan gambar (nama .png tetapi isinya skrip) ditolak
    r = a.post("/panel/products/new", data={**form, "name": "Palsu", "image": (io.BytesIO(b"<?php echo 1;"), "x.png")}, content_type="multipart/form-data")
    assert r.status_code == 200 and "bukan gambar valid" in html(r)
    r = a.post("/panel/products/new", data={**form, "name": "Eks", "image": (io.BytesIO(PNG), "x.exe")}, content_type="multipart/form-data")
    assert r.status_code == 200
    for bad in [dict(price="-1"), dict(price="abc"), dict(category="roket"), dict(name="")]:
        assert a.post("/panel/products/new", data={**form, **bad}).status_code == 200, bad
    assert a.post(f"/panel/products/{pid}/edit", data={**form, "price": "99000"}).status_code == 302
    with t.app.app_context():
        assert db.session.get(Product, pid).price == 99000
    assert a.post(f"/panel/products/{pid}/delete").status_code == 302
    with t.app.app_context():
        assert db.session.get(Product, pid) is None
    assert re.search(r'event=PRODUCT_CREATE id=\d+ name="Uji Web" by=admin', t.log_text)
    assert re.search(r"WARNING event=PRODUCT_DELETE .*by=admin", t.log_text)
    assert t.web("budi", "password123").post("/panel/products/1/delete").status_code == 403


# ---- alur pembelian: keranjang -> pesanan -> bukti bayar -> verifikasi -> laporan ----
def test_alur_pembelian_dan_laporan():
    t = T()
    b = t.web("budi", "password123")
    assert b.post("/cart/add", data=dict(product_id=1, size=99, qty=1)).status_code == 302  # ukuran tak valid ditolak
    assert "Keranjang kosong" in html(b.get("/cart")) or "kosong" in html(b.get("/cart"))
    b.post("/cart/add", data=dict(product_id=1, size=40, qty=2))
    assert "Rp 1.098.000" in html(b.get("/cart"))
    r = b.post("/checkout")
    assert r.status_code == 302
    oid = int(r.headers["Location"].rsplit("/", 1)[1])
    with t.app.app_context():
        assert db.session.get(Order, oid).status == "pending"
    # bukti bukan gambar ditolak; gambar valid diterima
    b.post(f"/orders/{oid}/proof", data={"proof": (io.BytesIO(b"bukan gambar"), "b.png")}, content_type="multipart/form-data")
    with t.app.app_context():
        assert db.session.get(Order, oid).status == "pending"
    b.post(f"/orders/{oid}/proof", data={"proof": (io.BytesIO(PNG), "b.png")}, content_type="multipart/form-data")
    with t.app.app_context():
        assert db.session.get(Order, oid).status == "waiting"
    assert b.get(f"/orders/{oid}/proof").data.startswith(b"\x89PNG")
    # pengguna lain tidak boleh melihat pesanan maupun bukti
    s = t.web("sari", "qwerty123")
    assert s.get(f"/orders/{oid}").status_code == 403 and s.get(f"/orders/{oid}/proof").status_code == 403
    assert re.search(r"WARNING event=ORDER_ACCESS_DENIED order=\d+ user=sari", t.log_text)
    # klien biasa tidak bisa menyetujui; admin bisa
    assert b.post(f"/panel/orders/{oid}/approve").status_code == 403
    a = t.web("admin", "Admin#2026")
    assert "Menunggu verifikasi" in html(a.get("/panel/orders"))
    assert a.post(f"/panel/orders/{oid}/approve").status_code == 302
    with t.app.app_context():
        assert db.session.get(Order, oid).status == "paid"
    assert re.search(r"event=PAYMENT_DECISION order=\d+ result=paid by=admin", t.log_text)
    # laporan: rentang tanggal, CSV, XLSX
    rep = html(a.get("/panel/reports"))
    assert "<b>1</b> pesanan" in rep and "Rp 1.098.000" in rep
    assert "tidak ada data" in html(a.get("/panel/reports?date_from=2000-01-01&date_to=2000-01-02")).lower()
    assert "Tanggal akhir harus" in html(a.get("/panel/reports?date_from=2026-02-01&date_to=2026-01-01"))
    csv = a.get("/panel/reports/export?format=csv")
    assert csv.mimetype == "text/csv" and "TOTAL,1,1098000" in csv.get_data(as_text=True)
    assert a.get("/panel/reports/export?format=xlsx").data[:2] == b"PK"
    assert a.get("/panel/reports/export?date_from=bukan-tanggal").status_code == 400
    assert t.call("/admin/stats", token=t.login("admin", "Admin#2026"))[1]["revenue"] == 1098000


def test_tolak_pembayaran_dan_unggah_ulang():
    t = T()
    b = t.web("budi", "password123")
    b.post("/cart/add", data=dict(product_id=2, size=42, qty=1))
    oid = int(b.post("/checkout").headers["Location"].rsplit("/", 1)[1])
    b.post(f"/orders/{oid}/proof", data={"proof": (io.BytesIO(PNG), "b.png")}, content_type="multipart/form-data")
    a = t.web("admin", "Admin#2026")
    a.post(f"/panel/orders/{oid}/reject")
    with t.app.app_context():
        assert db.session.get(Order, oid).status == "rejected"
    b.post(f"/orders/{oid}/proof", data={"proof": (io.BytesIO(PNG), "c.png")}, content_type="multipart/form-data")
    with t.app.app_context():
        assert db.session.get(Order, oid).status == "waiting"
    assert a.post(f"/panel/orders/{oid}/hapus").status_code == 404


def test_hapus_pengguna():
    t = T()
    a = t.web("admin", "Admin#2026")
    with t.app.app_context():
        ids = {u.username: u.id for u in db.session.scalars(db.select(User))}
    b = t.web("budi", "password123")
    b.post("/cart/add", data=dict(product_id=1, size=40, qty=1))
    b.post("/checkout")
    a.post(f"/panel/users/{ids['budi']}/delete")      # punya pesanan -> ditolak
    a.post(f"/panel/users/{ids['admin']}/delete")     # diri sendiri -> ditolak
    a.post(f"/panel/users/{ids['andi']}/delete")      # boleh
    with t.app.app_context():
        names = {u.username for u in db.session.scalars(db.select(User))}
    assert names == {"admin", "budi", "sari"}
    assert re.search(r"WARNING event=USER_DELETE target=andi by=admin", t.log_text)


# ---- CSRF, XSS (flag), IP klien ----
def test_csrf_aktif_di_web_tapi_tidak_di_api():
    t = T()
    t.app.config["WTF_CSRF_ENABLED"] = True
    assert t.new_client().post("/login", data=dict(username="budi", password="password123")).status_code == 400
    assert t.login("budi", "password123")  # API (token Bearer) tidak terpengaruh


def test_xss_ulasan_web_mengikuti_flag():
    for flag, raw in [(False, False), (True, True)]:
        t = T(VULN_XSS=flag)
        b = t.web("budi", "password123")
        b.post("/products/1/reviews", data=dict(rating="5", comment="<script>alert(1)</script>"))
        assert ("<script>alert(1)</script>" in html(b.get("/products/1"))) == raw


def test_ip_klien_proksi_tepercaya():
    t = T()
    t.app.config["TRUSTED_PROXIES"] = ["172.16.0.0/12"]
    h = {"X-Real-IP": "203.0.113.9"}
    t.client.post("/api/login", json=dict(username="x", password="y"), headers=h, environ_overrides={"REMOTE_ADDR": "172.18.0.2"})
    t.client.post("/api/login", json=dict(username="y", password="y"), headers=h, environ_overrides={"REMOTE_ADDR": "198.51.100.7"})
    assert re.search(r"user=x ip=203.0.113.9 ", t.log_text)       # dari proksi tepercaya: header dipakai
    assert re.search(r"user=y ip=198.51.100.7 ", t.log_text)      # bukan proksi: header palsu diabaikan


def test_halaman_galat():
    t = T()
    r = t.new_client().get("/tidak-ada")
    assert r.status_code == 404 and "<html" in html(r)
    assert t.call("/api/tidak-ada")[0] == 404
