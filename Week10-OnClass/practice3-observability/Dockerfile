FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

EXPOSE 8000
# 1 worker: default Prometheus registry is per-process; >1 worker needs multiprocess mode
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "app:app"]