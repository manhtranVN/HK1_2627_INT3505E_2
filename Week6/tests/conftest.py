import os
import sys
import tempfile
import pytest

# Thêm thư mục Week6 vào PYTHONPATH
week6_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if week6_dir not in sys.path:
    sys.path.insert(0, week6_dir)

from app import app as flask_app
import database
import seed

@pytest.fixture
def app_instance():
    # Sử dụng file sqlite tạm thời cho test suite
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    
    flask_app.config["DATABASE_PATH"] = db_path
    flask_app.config["TESTING"] = True
    flask_app.config["JWT_SECRET_KEY"] = "test-secret-key-entropy-256-bits-xyz123456789"
    
    seed.seed_database(db_path)
    
    yield flask_app
    
    try:
        os.remove(db_path)
    except OSError:
        pass

@pytest.fixture
def client(app_instance):
    return app_instance.test_client()

@pytest.fixture
def alice_tokens(client):
    """Lấy cặp token của Alice (user thông thường)"""
    res = client.post("/api/v1/auth/login", json={
        "email": "alice@example.com",
        "password": "AliceSecurePass123!"
    })
    assert res.status_code == 200
    data = res.get_json()
    return data["access_token"], data["refresh_token"]

@pytest.fixture
def bob_tokens(client):
    """Lấy cặp token của Bob (bạn của Alice)"""
    res = client.post("/api/v1/auth/login", json={
        "email": "bob@example.com",
        "password": "BobSecurePass123!"
    })
    assert res.status_code == 200
    data = res.get_json()
    return data["access_token"], data["refresh_token"]

@pytest.fixture
def charlie_tokens(client):
    """Lấy cặp token của Charlie (người lạ, không phải bạn của Alice)"""
    res = client.post("/api/v1/auth/login", json={
        "email": "charlie@example.com",
        "password": "CharliePass123!"
    })
    assert res.status_code == 200
    data = res.get_json()
    return data["access_token"], data["refresh_token"]

@pytest.fixture
def admin_tokens(client):
    """Lấy cặp token của Admin (toàn quyền)"""
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminSecretPass2026!"
    })
    assert res.status_code == 200
    data = res.get_json()
    return data["access_token"], data["refresh_token"]
