FROM python:3.13-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY wsgi.py ./
COPY tapak ./tapak
COPY migrations ./migrations
ENV UPLOAD_DIR=/srv/uploads LOG_FILE=/srv/logs/app.log
EXPOSE 5000
# 1 worker + banyak thread: migrasi/seed saat start tidak berebut (cukup untuk lab).
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "1", "--threads", "8", "--timeout", "60", "wsgi:app"]
