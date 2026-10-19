FROM python:3.13-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py db.py logger.py server.py wsgi.py ./
COPY public ./public
EXPOSE 5000
# 1 worker + banyak thread: seed dan koneksi database tidak berebut (cukup untuk lab).
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "1", "--threads", "8", "--timeout", "60", "wsgi:app"]
