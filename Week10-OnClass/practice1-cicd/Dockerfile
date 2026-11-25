# Builder: dependencies trong venv
FROM python:3.12-slim AS build
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime: cùng Python ABI, non-root
FROM python:3.12-slim
ENV PATH="/opt/venv/bin:$PATH"
COPY --from=build /opt/venv /opt/venv
WORKDIR /app
COPY . .
USER 65532:65532
EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]