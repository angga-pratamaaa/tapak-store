# Pemetaan fitur ke persyaratan dosen (ATS)

| Persyaratan kode | Letak |
|---|---|
| Blueprint | `tapak/blueprints/` (5 blueprint) |
| OOP | model ORM `tapak/models.py`, form kelas `tapak/forms.py` |
| Migration | `migrations/` (Flask-Migrate/Alembic) |
| Logging | `tapak/logs.py` (berkas `app.log`) |
| SQLAlchemy | `tapak/models.py`, `tapak/extensions.py` |
| Template engine | Jinja2, `tapak/templates/` |
| Validasi klien + server | atribut HTML5 + `static/app.js`; WTForms `tapak/forms.py` |
| Hashing | scrypt (`tapak/security.py`) |

| Fitur | Rute | Uji |
|---|---|---|
| Login, register, logout | `/login` `/register` `/logout` | `test_web.py::test_register_validasi_server`, `test_login_logout_web` |
| Beranda | `/` | `test_katalog_filter_harga` |
| Katalog + filter rentang harga | `/products?min_price=&max_price=` | `test_katalog_filter_harga` |
| CRUD produk (+foto) | `/panel/products...` | `test_panel_crud_produk_dan_gambar` |
| Dashboard admin | `/panel/` | `test_panel_admin_hak_akses` |
| Kelola pengguna (aktif/nonaktif/hapus) | `/panel/users` | `test_akun_nonaktif_tidak_bisa_masuk`, `test_hapus_pengguna` |
| Keranjang, checkout, bukti bayar | `/cart` `/checkout` `/orders/<id>` | `test_alur_pembelian_dan_laporan` |
| Verifikasi pembayaran admin | `/panel/orders` | `test_tolak_pembayaran_dan_unggah_ulang` |
| Laporan penjualan + ekspor | `/panel/reports` | `test_alur_pembelian_dan_laporan` |

Cocokkan baris ini dengan nomor FR-001..011 pada lembar checklist dosen; ubah/hapus baris yang tidak diwajibkan.
