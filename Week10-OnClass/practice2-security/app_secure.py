import os
from functools import wraps

import jwt
from flask import Flask, g, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

app = Flask(__name__)

# (1) Secrets từ environment
JWT_SECRET = os.environ["JWT_SECRET"]
DB_URL = os.environ["DATABASE_URL"]

# (2) HTTPS / security headers (FORCE_HTTPS=0 để test curl qua HTTP local)
Talisman(
    app,
    force_https=os.environ.get("FORCE_HTTPS", "1") != "0",
    strict_transport_security=True,
    content_security_policy={"default-src": "'none'"},
)
app.config["DEBUG"] = False


# (3) Rate-limit: user đã verify hoặc IP
def client_key():
    a = request.headers.get("Authorization", "")
    if a.startswith("Bearer "):
        try:
            c = jwt.decode(a[7:], JWT_SECRET, algorithms=["HS256"], options={"require": ["sub", "exp"]})
            return "u:" + c["sub"]
        except (jwt.PyJWTError, KeyError):
            pass
    return "ip:" + get_remote_address()


limiter = Limiter(
    client_key,
    app=app,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)


# (4) Decorator: reject invalid JWT
def jwt_required(f):
    @wraps(f)
    def w(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify(err="missing token"), 401
        try:
            g.user = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"], options={"require": ["sub", "exp"]})
        except jwt.PyJWTError:
            return jsonify(err="invalid token"), 401
        return f(*args, **kwargs)

    return w


@app.errorhandler(429)
def too_many(e):
    return jsonify(err="too many requests"), 429


@app.post("/items")
@limiter.limit("10/minute")
@jwt_required
def create_item():
    body = request.get_json(silent=True)
    name = body.get("name") if isinstance(body, dict) else None
    if not isinstance(name, str) or not 1 <= len(name) <= 64:
        return {"err": "invalid name"}, 400
    return {"id": 42, "name": name}, 201


if __name__ == "__main__":
    app.run(port=8000)