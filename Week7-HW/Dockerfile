# Multi-stage Dockerfile for production deployment
# ─── stage 1: builder ───
FROM python:3.12-slim AS builder
WORKDIR /build

COPY pyproject.toml requirements.txt ./
COPY src ./src

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

# ─── stage 2: runtime ───
FROM python:3.12-slim
WORKDIR /app

RUN groupadd -r app && \
    useradd -r -g app -d /app app

# Copy virtual environment from builder stage
COPY --from=builder --chown=app:app /opt/venv /opt/venv

# Copy entrypoint, configuration and application source code
COPY --chown=app:app wsgi.py gunicorn.conf.py openapi.yaml ./
COPY --chown=app:app src ./src

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

USER app
EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]

