"""Titik masuk: `python server.py` (uji lokal) atau `gunicorn wsgi:app` (Docker)."""
import os

from app import create_app, seed
from db import open_db
from logger import make_logger

here = os.path.dirname(os.path.abspath(__file__))
db = open_db(os.environ.get("DATABASE_URL") or "sqlite:./dev.db")
print("seed selesai" if seed(db) else "data sudah ada, seed dilewati", flush=True)
log = make_logger(os.environ.get("LOG_FILE") or os.path.join(here, "logs", "app.log"))
app = create_app(db, public_dir=os.path.join(here, "public"), log=log)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
