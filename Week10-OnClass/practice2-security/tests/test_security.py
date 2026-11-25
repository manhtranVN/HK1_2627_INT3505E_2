import os
import time

import jwt

os.environ.setdefault("JWT_SECRET", "test-secret-0123456789abcdef0123456789")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

import app_secure as m

HTTPS = "https://localhost"


def token(sub="alice", exp_delta=3600, secret=None):
    payload = {"sub": sub, "exp": int(time.time()) + exp_delta}
    return jwt.encode(payload, secret or m.JWT_SECRET, algorithm="HS256")


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def client():
    return m.app.test_client()


def test_missing_token_401():
    r = client().post("/items", json={"name": "book"}, base_url=HTTPS)
    assert r.status_code == 401


def test_invalid_signature_401():
    r = client().post("/items", json={"name": "book"}, headers=auth(token(secret="wrong-secret-0123456789abcdef0123456789")), base_url=HTTPS)
    assert r.status_code == 401


def test_expired_token_401():
    r = client().post("/items", json={"name": "book"}, headers=auth(token(sub="exp-user", exp_delta=-10)), base_url=HTTPS)
    assert r.status_code == 401


def test_valid_201():
    r = client().post("/items", json={"name": "book"}, headers=auth(token(sub="ok-user")), base_url=HTTPS)
    assert r.status_code == 201
    assert r.get_json()["name"] == "book"


def test_invalid_name_400():
    r = client().post("/items", json={"name": ""}, headers=auth(token(sub="name-user")), base_url=HTTPS)
    assert r.status_code == 400


def test_security_headers_present():
    r = client().post("/items", json={"name": "book"}, headers=auth(token(sub="hdr-user")), base_url=HTTPS)
    assert "Strict-Transport-Security" in r.headers
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in r.headers


def test_rate_limit_429():
    c = client()
    h = auth(token(sub="limit-user"))
    codes = [c.post("/items", json={"name": "book"}, headers=h, base_url=HTTPS).status_code for _ in range(11)]
    assert codes[:10] == [201] * 10
    assert codes[10] == 429


def test_force_https_redirect():
    r = client().post("/items", json={"name": "book"}, base_url="http://localhost")
    assert r.status_code in (301, 302)