"""Logger sederhana: tulis ke stdout (docker logs) dan ke berkas (dibaca Wazuh Agent)."""
import os
import sys
import threading


def make_logger(file=None):
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
