# TAPAK — toko sepatu (Flask) untuk lab SOC PBL RKS-313

Web e-commerce sepatu: **Flask + blueprint + OOP (SQLAlchemy) + migrasi (Flask-Migrate) + Jinja2 + WTForms**,
database MySQL di VM `db-primary`. Selain halaman web, tersedia **REST API** yang dipakai skenario serangan lab.
**Sengaja rentan** (toggle `VULN_*`): hanya untuk lab terisolasi, jangan dibuka ke internet.

## Struktur kode
```
wsgi.py                  titik masuk (gunicorn wsgi:app): migrasi + seed lalu layani
tapak/
  __init__.py            application factory create_app(), error handler, init_database()
  config.py              konfigurasi dari .env           extensions.py  db, migrate, csrf
  models.py              model ORM (User, Product, Order, OrderItem, Review)
  security.py            hash scrypt, token API, sesi web  logs.py  log berformat + IP klien
  services.py            login/register/pesanan (dipakai API dan web)
  forms.py               form WTForms (validasi server)    uploads.py  validasi & simpan gambar
  blueprints/            api.py, admin_api.py (JSON) · auth.py, shop.py, admin_web.py (HTML)
  templates/ static/     Jinja2, CSS, JS (validasi sisi klien)
migrations/              Alembic (0001 baseline idempoten, 0002 kolom fitur web)
tests/                   pytest (36 tes)
```

## Fitur
| Area | Rute web |
|---|---|
| Register / login / logout (hash scrypt, CSRF, validasi server + klien) | `/register` `/login` `/logout` |
| Beranda, katalog (cari, kategori, **rentang harga**, halaman), detail + ulasan | `/` `/products` `/products/<id>` |
| Keranjang, checkout, pesanan saya, **unggah bukti bayar** | `/cart` `/checkout` `/orders` `/orders/<id>` |
| **Panel admin**: dashboard, CRUD produk + **foto**, pengguna (aktif/nonaktif/hapus), **verifikasi pembayaran**, **laporan penjualan** (rentang tanggal, ekspor CSV/Excel) | `/panel/...` |

REST API (token Bearer, tidak berubah dari versi awal): `/api/health|register|login|products|products/search|products/:id/reviews|orders`, `/admin/stats|users|orders|products`.

## Uji lokal
```
pip install -r requirements-dev.txt
python -m pytest -q                   # 36 tes
DATABASE_URL=sqlite:./dev.db python wsgi.py   # http://localhost:5000
```

## Deploy di srv-web (Docker)
```
cd ~/tapak-store && git pull
cp .env.example .env && nano .env        # DATABASE_URL, SECRET_KEY, VULN_*
sudo mkdir -p /var/log/toko /var/lib/toko-uploads
sudo docker build -t tapak-store .
sudo docker rm -f tapak 2>/dev/null
sudo docker run -d --name tapak --restart unless-stopped -p 5000:5000 --env-file .env \
  -v /var/log/toko:/srv/logs -v /var/lib/toko-uploads:/srv/uploads tapak-store
sudo docker logs tapak
```
**Migrasi pertama di MySQL lama** memakai `ALTER TABLE`, jadi beri hak sementara di `db-primary`, jalankan container sekali,
lalu cabut lagi:
```
GRANT ALTER, CREATE, INDEX ON toko.* TO 'toko'@'192.168.10.10';   -- sebelum docker run
REVOKE ALTER, CREATE, INDEX ON toko.* FROM 'toko'@'192.168.10.10'; -- setelah log menulis "seed ..." dan web hidup
```
Data lama (pengguna, produk, pesanan) tidak diubah; kolom baru diisi nilai bawaan.

## Log (dibaca Wazuh Agent): /var/log/toko/app.log
Format `ISO-UTC LEVEL event=NAMA kunci=nilai`. Event: LOGIN_OK, LOGIN_FAILED (bad_password/unknown_user/inactive), LOGOUT,
REGISTER_OK/FAILED, ADMIN_ACCESS (GRANTED/DENIED; API dan panel web), PRODUCT_CREATE/UPDATE/DELETE, ORDER, ORDER_ACCESS_DENIED,
PAYMENT_PROOF_UPLOADED, PAYMENT_DECISION, USER_STATUS, USER_DELETE, REPORT_EXPORT, SEARCH, SERVER_ERROR.
Nilai dengan spasi/baris baru di-escape agar baris log tidak bisa dipalsukan.

**IP klien**: `X-Real-IP`/`X-Forwarded-For` hanya dipercaya bila koneksi datang dari alamat di `TRUSTED_PROXIES`
(isi dengan alamat WAF/nginx setelah Backlog 5). Tanpa itu, log memakai alamat koneksi langsung (tidak bisa dipalsukan klien).

## Perilaku VULN_* (tetap sama)
`VULN_SQLI` pencarian `/api/products/search` memakai SQL mentah · `VULN_IDOR` `/api/orders/:id` tanpa cek pemilik ·
`VULN_XSS` ulasan disimpan apa adanya · `VULN_PRICE` harga dari klien dipercaya · `VULN_ADMIN` `/admin/*` (API JSON) tanpa autentikasi.
Halaman web (`/products`, `/panel`) memakai ORM dan **tidak** rentan SQLi/akses admin; hanya tampilan ulasan yang mengikuti `VULN_XSS`.

## Akun awal (kata sandi sengaja lemah)
admin / Admin#2026, budi / password123, sari / qwerty123, andi / 123456
