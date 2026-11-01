"""Titik masuk: `gunicorn wsgi:app` (Docker) atau `python wsgi.py` (uji lokal)."""
import os

from tapak import create_app, init_database

app = create_app()
print("seed selesai" if init_database(app) else "data sudah ada, seed dilewati", flush=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
