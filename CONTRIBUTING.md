# Panduan kontribusi TAPAK

Repositori ini **private**. Aplikasi sengaja rentan untuk lab SOC, jadi jangan dibagikan ke luar tim.

## Aturan
1. Jangan push langsung ke `main` (kecuali ketua).
2. Satu perubahan = satu cabang = satu pull request. Nama cabang: `nama/topik`, contoh `louisa/isi-produk`.
3. Louisa dan Fauziah hanya mengubah: `public/index.html` (teks), `public/style.css` (tampilan), dan berkas laporan uji. Jangan mengubah `app.py`, `db.py`, `logger.py`, atau `Dockerfile`.
4. Jangan pernah mengunggah `.env`, kata sandi, atau token.
5. Ketua meninjau dan menggabungkan semua pull request.

## Mengedit lewat browser (tanpa terminal)
1. Buka berkas di GitHub, klik ikon pensil (Edit this file).
2. Ubah isinya, lalu klik **Commit changes**.
3. Pilih **Create a new branch for this commit**, beri nama cabang, klik **Propose changes**.
4. Klik **Create pull request**, tulis satu kalimat apa yang diubah, lalu minta ketua meninjau.
