import sqlite3

import pytest
from sqlalchemy import create_engine, inspect

from tapak import create_app, init_database

LEGACY = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(50) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL DEFAULT 'client')",
    "CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(120) NOT NULL, brand VARCHAR(60) NOT NULL DEFAULT '', category VARCHAR(30) NOT NULL DEFAULT '', price INT NOT NULL, stock INT NOT NULL DEFAULT 0)",
    "CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT NOT NULL, total INT NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'paid')",
    "CREATE TABLE order_items (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INT NOT NULL, product_id INT NOT NULL, qty INT NOT NULL, size INT NOT NULL DEFAULT 0, unit_price INT NOT NULL)",
    "CREATE TABLE reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INT NOT NULL, user_id INT NOT NULL, rating INT NOT NULL, comment TEXT NOT NULL)",
    "INSERT INTO users (username, password_hash, role) VALUES ('lama', 'scrypt:dummy', 'client')",
    "INSERT INTO products (name, brand, category, price, stock) VALUES ('Sepatu Lama', 'Bayu', 'lari', 100000, 3)",
    "INSERT INTO orders (user_id, total, status) VALUES (1, 100000, 'paid')",
]


def make(path):
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{path}", "LOG": lambda _l: None})


def test_migrasi_db_kosong_idempoten(tmp_path):
    app = make(tmp_path / "baru.db")
    assert init_database(app) is True
    assert init_database(app) is False  # dijalankan lagi: tidak error, seed dilewati
    cols = {c["name"] for c in inspect(create_engine(f"sqlite:///{tmp_path/'baru.db'}")).get_columns("users")}
    assert {"email", "is_active", "created_at"} <= cols


def test_migrasi_db_lama_mempertahankan_data(tmp_path):
    f = tmp_path / "lama.db"
    con = sqlite3.connect(f)
    for s in LEGACY:
        con.execute(s)
    con.commit()
    con.close()
    app = make(f)
    assert init_database(app) is False  # sudah ada pengguna -> tidak di-seed
    con = sqlite3.connect(f)
    assert con.execute("SELECT username, role, is_active FROM users").fetchall() == [("lama", "client", 1)]
    assert con.execute("SELECT name, price FROM products").fetchall() == [("Sepatu Lama", 100000)]
    assert con.execute("SELECT status, payment_proof FROM orders").fetchall() == [("paid", None)]
    assert "image" in {r[1] for r in con.execute("PRAGMA table_info(products)")}
    assert con.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0002"
