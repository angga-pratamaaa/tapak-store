"""Log berformat `waktu LEVEL event=NAMA kunci=nilai ...` (dibaca Wazuh Agent).

Nilai yang mengandung spasi, kutip, atau baris baru di-escape (JSON) agar pengguna
tidak bisa memalsukan baris log.
"""
import ipaddress
import json
import os
import re
import sys
import threading
from datetime import datetime, timezone

from flask import current_app, request


def make_logger(file=None):
    """Tulis ke stdout (docker logs) dan ke berkas (dibaca Wazuh Agent)."""
    lock = threading.Lock()
    stream = None
    if file:
        os.makedirs(os.path.dirname(os.path.abspath(file)), exist_ok=True)
        stream = open(file, "a", encoding="utf-8", buffering=1)

    def log(line):
        with lock:
            print(line, file=sys.stdout, flush=True)
            if stream:
                stream.write(line + "\n")
    return log


def kv(v):
    s = "-" if v is None else str(v)
    return s if re.fullmatch(r"[\w.:@/-]+", s, re.ASCII) else json.dumps(s, ensure_ascii=False)


def L(level, event, **fields):
    ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    current_app.extensions["tapak_log"](f"{ts} {level} event={event} " + " ".join(f"{k}={kv(v)}" for k, v in fields.items()))


def _trusted(addr):
    for net in current_app.config["TRUSTED_PROXIES"]:
        try:
            if ipaddress.ip_address(addr) in ipaddress.ip_network(net, strict=False):
                return True
        except ValueError:
            continue
    return False


def client_ip():
    """IP klien. Header proksi dipercaya hanya bila permintaan datang dari TRUSTED_PROXIES."""
    addr = request.remote_addr or "-"
    if _trusted(addr):
        real = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        return real or addr
    return addr
