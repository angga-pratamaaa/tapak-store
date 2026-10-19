"""Lapisan database: MySQL (PyMySQL, produksi lab) atau SQLite (uji lokal tanpa MySQL).

URL: mysql://user:pass@host:3306/nama  atau  sqlite:./dev.db  atau  sqlite::memory:
Kata sandi di URL MySQL boleh di-URL-encode (mis. %40 untuk '@').
"""
import sqlite3
import threading
from urllib.parse import unquote, urlparse


class Db:
    def __init__(self, url="sqlite::memory:"):
        self.lock = threading.RLock()
        if url.startswith("mysql://"):
            import pymysql
            from pymysql.cursors import DictCursor
            u = urlparse(url)
            self._kw = dict(
                host=u.hostname, port=u.port or 3306, user=unquote(u.username or ""),
                password=unquote(u.password or ""), database=(u.path or "/").lstrip("/"),
                charset="utf8mb4", autocommit=True, cursorclass=DictCursor, connect_timeout=10,
            )
            self.dialect = "mysql"
            self._pymysql = pymysql
            self.conn = pymysql.connect(**self._kw)
        else:
            self.dialect = "sqlite"
            f = url.removeprefix("sqlite:") or ":memory:"
            self.conn = sqlite3.connect(f, check_same_thread=False, isolation_level=None)
            self.conn.row_factory = sqlite3.Row

    # -- internal --
    def _cur(self):
        if self.dialect == "mysql":
            self.conn.ping(reconnect=True)
            return self.conn.cursor()
        return self.conn.cursor()

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.dialect == "mysql" else sql

    @staticmethod
    def _clean(p):
        return tuple(None if v is None else v for v in p)

    # -- API --
    def all(self, sql, params=()):
        with self.lock:
            c = self._cur()
            try:
                c.execute(self._sql(sql), self._clean(params))
                return [dict(r) for r in c.fetchall()]
            finally:
                c.close()

    def get(self, sql, params=()):
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def run(self, sql, params=()):
        with self.lock:
            c = self._cur()
            try:
                c.execute(self._sql(sql), self._clean(params))
                return {"id": c.lastrowid}
            finally:
                c.close()

    def raw(self, sql):
        """Dipakai endpoint rentan SQLi: SQL dieksekusi apa adanya (tanpa parameter)."""
        with self.lock:
            c = self._cur()
            try:
                c.execute(sql)
                return [dict(r) for r in c.fetchall()]
            finally:
                c.close()

    def exec(self, sql):
        with self.lock:
            c = self._cur()
            try:
                c.execute(sql)
            finally:
                c.close()

    def close(self):
        with self.lock:
            self.conn.close()


def open_db(url="sqlite::memory:"):
    return Db(url)


def migrate(db):
    pk = "INT AUTO_INCREMENT PRIMARY KEY" if db.dialect == "mysql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    for s in [
        f"CREATE TABLE IF NOT EXISTS users (id {pk}, username VARCHAR(50) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL DEFAULT 'client')",
        f"CREATE TABLE IF NOT EXISTS products (id {pk}, name VARCHAR(120) NOT NULL, brand VARCHAR(60) NOT NULL DEFAULT '', category VARCHAR(30) NOT NULL DEFAULT '', price INT NOT NULL, stock INT NOT NULL DEFAULT 0)",
        f"CREATE TABLE IF NOT EXISTS orders (id {pk}, user_id INT NOT NULL, total INT NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'paid')",
        f"CREATE TABLE IF NOT EXISTS order_items (id {pk}, order_id INT NOT NULL, product_id INT NOT NULL, qty INT NOT NULL, size INT NOT NULL DEFAULT 0, unit_price INT NOT NULL)",
        f"CREATE TABLE IF NOT EXISTS reviews (id {pk}, product_id INT NOT NULL, user_id INT NOT NULL, rating INT NOT NULL, comment TEXT NOT NULL)",
    ]:
        db.exec(s)
