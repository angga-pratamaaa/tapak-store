import tempfile

from tapak import create_app
from tapak.extensions import db
from tapak.seed import seed

OFF = dict(VULN_SQLI=False, VULN_IDOR=False, VULN_XSS=False, VULN_PRICE=False, VULN_ADMIN=False)


class T:
    """App uji dengan SQLite memori. `call` = klien JSON (API); `web` = klien HTML (sesi cookie)."""

    def __init__(self, **vuln):
        self.logs = []
        self.app = create_app({
            "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "SECRET_KEY": "tes", "LOG": self.logs.append,
            "VULN": {**OFF, **vuln}, "WTF_CSRF_ENABLED": False, "UPLOAD_DIR": tempfile.mkdtemp(prefix="tapak-up-")})
        with self.app.app_context():
            db.create_all()
            seed()
        self.client = self.app.test_client()

    def new_client(self):
        return self.app.test_client()

    def call(self, path, method="GET", body=None, token=None, raw=None):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        kw = {}
        if raw is not None:
            kw = dict(data=raw, content_type="application/json")
        elif body is not None:
            kw = dict(json=body)
        r = self.client.open(path, method=method, headers=h, **kw)
        return r.status_code, r.get_json(silent=True)

    def login(self, u, p):
        return (self.call("/api/login", "POST", {"username": u, "password": p})[1] or {}).get("token")

    def web(self, user=None, password=None):
        """Klien web; bila user diberikan, login lewat form."""
        c = self.new_client()
        if user:
            r = c.post("/login", data={"username": user, "password": password})
            assert r.status_code == 302, r.get_data(as_text=True)[:300]
        return c

    @property
    def log_text(self):
        return "\n".join(self.logs)
