# Rencana isu GitHub (pembagian kerja ATS)

Satu isu = satu cabang `nama/topik` = satu PR yang ditinjau ketua. Kode dasar refaktor ada di cabang `ats/refactor`;
anggota mengerjakan di atasnya dan **membuat commit sendiri** (agar riwayat Git menunjukkan keterlibatan tiap anggota).

| Isu | Isi | Berkas utama | Pemilik (usulan) |
|---|---|---|---|
| #1 Refaktor struktur Flask | blueprint, factory, SQLAlchemy, migrasi | `tapak/`, `migrations/` | Angga |
| #2 Tampilan beranda & katalog | teks, gambar, tata letak, filter harga | `templates/home.html`, `catalog.html`, `style.css` | Louisa |
| #3 Halaman login/register & pesan galat | teks, validasi sisi klien | `templates/auth/`, `static/app.js` | Fauziah |
| #4 Panel admin: tampilan produk/pengguna/pesanan | template admin | `templates/admin/` | Louisa |
| #5 Uji unit: web & migrasi | tambah kasus uji | `tests/test_web.py`, `tests/test_migrations.py` | Guruh |
| #6 Laporan penjualan & ekspor | cek hasil CSV/Excel, perbaikan format | `blueprints/admin_web.py` (`reports`) | Zainsty |
| #7 Dokumen: panduan deploy & uji manual | README, skenario uji per FR | `README.md`, `docs/` | Fauziah |
| #8 Deploy & verifikasi di srv-web | build image, migrasi MySQL, bukti | VM `srv-web`, `db-primary` | Angga |

Aturan: jangan commit `.env`; hanya ketua yang mengubah `tapak/*.py` inti dan `migrations/` (lihat CONTRIBUTING.md).
