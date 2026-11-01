"""TAPAK: toko sepatu (Flask) untuk lab SOC PBL RKS-313.

PERINGATAN: aplikasi ini SENGAJA memuat kerentanan (toggle VULN_*) untuk diserang di
lingkungan lab terisolasi. JANGAN dipasang di jaringan produksi atau dibuka ke internet.
"""
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from tapak.config import CATEGORIES, MIGRATIONS_DIR, load_config
from tapak.errors import ApiError
from tapak.extensions import csrf, db, migrate
from tapak.logs import L, client_ip, make_logger
from tapak.util import rupiah


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    app.config.update(overrides or {})
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    app.extensions["tapak_log"] = app.config.get("LOG") or make_logger(app.config["LOG_FILE"])

    db.init_app(app)
    migrate.init_app(app, db, directory=MIGRATIONS_DIR)
    csrf.init_app(app)

    from tapak.blueprints import admin_api, admin_web, api, auth, shop
    for m in (api, admin_api):  # API memakai token Bearer, bukan cookie: tidak perlu CSRF
        app.register_blueprint(m.bp)
        csrf.exempt(m.bp)
    for m in (auth, shop, admin_web):
        app.register_blueprint(m.bp)

    app.jinja_env.filters["rupiah"] = rupiah

    @app.context_processor
    def inject():
        from flask import session
        from tapak.security import web_user
        return dict(me=web_user(), cart_count=len(session.get("cart", [])), categories=CATEGORIES, vuln=app.config["VULN"])

    def wants_json():
        return request.path.startswith(("/api", "/admin"))

    @app.errorhandler(ApiError)
    def _api_error(e):
        return jsonify(error=e.msg), e.status

    @app.errorhandler(HTTPException)
    def _http_error(e):
        if wants_json():
            return jsonify(error=e.description if e.code != 404 else "tidak ditemukan"), e.code
        return render_template("errors/error.html", code=e.code, name=e.name, desc=e.description), e.code

    @app.errorhandler(Exception)
    def _server_error(e):
        db.session.rollback()
        L("ERROR", "SERVER_ERROR", msg=str(e), ip=client_ip())
        if wants_json():
            return jsonify(error="kesalahan server"), 500
        return render_template("errors/error.html", code=500, name="Kesalahan server", desc="Terjadi kesalahan. Coba lagi nanti."), 500

    return app


def init_database(app):
    """Jalankan migrasi (idempoten) lalu isi data awal bila kosong. Dipanggil saat start (wsgi.py)."""
    from flask_migrate import upgrade
    from tapak.seed import seed
    with app.app_context():
        upgrade(directory=MIGRATIONS_DIR)
        return seed()
