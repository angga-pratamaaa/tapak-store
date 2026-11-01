"""Unggah berkas gambar (foto produk, bukti pembayaran) dengan pemeriksaan isi berkas."""
import os
import uuid

from flask import current_app

ALLOWED = ("jpg", "jpeg", "png", "webp")


def sniff(head):
    """Jenis gambar dari byte awal berkas (bukan dari nama berkas yang bisa dipalsukan)."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(storage, subdir):
    """Simpan gambar; kembalikan nama berkas acak, atau None bila bukan gambar valid / terlalu besar."""
    if not storage or not storage.filename:
        return None
    data = storage.read(current_app.config["MAX_IMAGE_BYTES"] + 1)
    if not data or len(data) > current_app.config["MAX_IMAGE_BYTES"]:
        return None
    kind = sniff(data[:16])
    if not kind:
        return None
    name = f"{uuid.uuid4().hex}.{kind}"
    folder = os.path.join(current_app.config["UPLOAD_DIR"], subdir)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), "wb") as f:
        f.write(data)
    return name


def remove_image(subdir, name):
    if name:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_DIR"], subdir, os.path.basename(name)))
        except OSError:
            pass
