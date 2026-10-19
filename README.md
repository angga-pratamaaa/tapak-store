# Sepatu RKS-313 (Flask + REST API + HTML/CSS/JS)

Web e-commerce sepatu untuk lab SOC PBL RKS-313. Backend Flask (REST API), frontend HTML/CSS/JavaScript
di `public/`, database MySQL di VM `db-primary`. **Sengaja rentan** (toggle `VULN_*`): hanya untuk lab terisolasi.

## Fitur wajib
Login (sukses/gagal dicatat; akses area admin dicatat), register, CRUD produk (admin), katalog, dashboard admin dasar.

## Endpoint
| Metode | Path | Keterangan |
|---|---|---|
| POST | /api/register, /api/login | register, login (token Bearer) |
| GET | /api/products, /api/products/search?q= | katalog, pencarian |
| GET/POST | /api/products/:id/reviews | ulasan (POST perlu login) |
| POST/GET | /api/orders, /api/orders/:id | pesanan (perlu login) |
| GET | /admin/stats, /admin/users, /admin/orders | dashboard admin |
| POST/PUT/DELETE | /admin/products(/:id) | CRUD produk (admin) |

## Uji lokal
```
pip install -r requirements-dev.txt
python -m pytest -q          # 20 tes
python server.py             # http://localhost:5000, SQLite ./dev.db
```

## Deploy di srv-web
```
cd ~ && unzip -o tapak-store.zip && cd tapak-store
cp .env.example .env && nano .env        # isi DATABASE_URL dan SECRET_KEY
sudo docker build -t tapak-store .
sudo docker rm -f toko 2>/dev/null
sudo docker run -d --name tapak --restart unless-stopped -p 5000:5000 --env-file .env -v /var/log/toko:/srv/logs tapak-store
sudo docker logs toko
```
Ubah `VULN_*` di `.env`, lalu `docker rm -f toko` dan `docker run` lagi (tanpa build ulang).

## Log (dibaca Wazuh Agent): /var/log/toko/app.log
Format `ISO-UTC LEVEL event=NAMA kunci=nilai`. Event: LOGIN_OK, LOGIN_FAILED, REGISTER_OK/FAILED,
ADMIN_ACCESS (GRANTED/DENIED), PRODUCT_CREATE/UPDATE/DELETE, ORDER, ORDER_ACCESS_DENIED, SEARCH, SERVER_ERROR.
Nilai dengan spasi/baris baru di-escape agar baris log tidak bisa dipalsukan.

## Akun awal (kata sandi sengaja lemah)
admin / Admin#2026, budi / password123, sari / qwerty123, andi / 123456
