import json
import pytest

def test_login_success(client):
    """Test POST /auth/login thành công, trả về cặp token và thông tin user an toàn"""
    res = client.post("/api/v1/auth/login", json={
        "email": "alice@example.com",
        "password": "AliceSecurePass123!"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900
    assert "posts:read" in data["scopes"]
    assert "posts:write" in data["scopes"]
    assert "profile:read" in data["scopes"]
    
    # Kiểm tra không bị rò rỉ password_hash (OWASP API3)
    user = data["user"]
    assert user["email"] == "alice@example.com"
    assert "password_hash" not in user
    assert "password" not in user

def test_login_wrong_password(client):
    """Test POST /auth/login sai mật khẩu -> 401 Unauthorized với thông báo chung"""
    res = client.post("/api/v1/auth/login", json={
        "email": "alice@example.com",
        "password": "WrongPassword999!"
    })
    assert res.status_code == 401
    assert res.headers.get("Content-Type") == "application/problem+json"
    data = res.get_json()
    assert data["status"] == 401
    assert data["code"] == "invalid_credentials"
    assert data["detail"] == "Invalid email or password."

def test_login_nonexistent_email(client):
    """Test POST /auth/login email không tồn tại -> 401 Unauthorized (thông báo giống hệt sai pass để chống enumeration)"""
    res = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "AnyPassword123!"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["status"] == 401
    assert data["code"] == "invalid_credentials"
    assert data["detail"] == "Invalid email or password."

def test_login_missing_fields(client):
    """Test POST /auth/login thiếu email hoặc password -> 400 Bad Request"""
    res1 = client.post("/api/v1/auth/login", json={"email": "alice@example.com"})
    assert res1.status_code == 400
    assert res1.get_json()["code"] == "missing_fields"

    res2 = client.post("/api/v1/auth/login", json={"password": "123"})
    assert res2.status_code == 400
    assert res2.get_json()["code"] == "missing_fields"

def test_login_invalid_email_format(client):
    """Test POST /auth/login email sai cú pháp -> 422 Unprocessable Entity"""
    res = client.post("/api/v1/auth/login", json={
        "email": "invalid-email-no-at-sign",
        "password": "Password123!"
    })
    assert res.status_code == 422
    data = res.get_json()
    assert data["code"] == "invalid_email_format"
    assert "invalid_params" in data

def test_refresh_token_via_header_success(client, alice_tokens):
    """Test POST /auth/refresh thành công qua header Authorization: Bearer <refresh_token>"""
    access_token, refresh_token = alice_tokens
    res = client.post("/api/v1/auth/refresh", headers={
        "Authorization": f"Bearer {refresh_token}"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900

def test_refresh_token_via_body_success(client, bob_tokens):
    """Test POST /auth/refresh thành công qua request body JSON"""
    _, refresh_token = bob_tokens
    res = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "access_token" in data

def test_refresh_rejects_access_token(client, alice_tokens):
    """Test POST /auth/refresh từ chối khi client gửi nhầm Access Token -> 403 Forbidden"""
    access_token, _ = alice_tokens
    res = client.post("/api/v1/auth/refresh", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert res.status_code == 403
    data = res.get_json()
    assert data["code"] == "invalid_token_type"

def test_refresh_token_rotation_and_revocation(client, alice_tokens):
    """Test cơ chế Token Rotation: token cũ bị thu hồi và không thể tái sử dụng"""
    _, refresh_token = alice_tokens
    
    # Lần 1: Dùng refresh token để xin access mới -> thành công
    res1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res1.status_code == 200
    
    # Lần 2: Cố tình dùng lại refresh token cũ đã bị xoay vòng -> 401 Unauthorized (token_revoked)
    res2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res2.status_code == 401
    data = res2.get_json()
    assert data["code"] == "token_revoked"

def test_refresh_fake_token(client):
    """Test POST /auth/refresh token giả mạo -> 401 Unauthorized"""
    res = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "fake.jwt.token.here"
    })
    assert res.status_code == 401
    assert res.get_json()["code"] == "invalid_token"
