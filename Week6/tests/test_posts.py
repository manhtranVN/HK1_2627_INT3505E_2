import pytest
from flask_jwt_extended import create_access_token

def test_get_post_without_token(client):
    """Test GET /posts/{id} không có Bearer token -> 401 Unauthorized"""
    res = client.get("/api/v1/posts/101")
    assert res.status_code == 401
    assert res.headers.get("Content-Type") == "application/problem+json"
    data = res.get_json()
    assert data["code"] == "missing_token"

def test_get_post_insufficient_scope(client, app_instance):
    """Test GET /posts/{id} có token nhưng thiếu scope 'posts:read' -> 403 Forbidden"""
    with app_instance.app_context():
        # Tạo token giả lập chỉ có scope profile:read, thiếu posts:read
        token_no_scope = create_access_token(
            identity="1",
            additional_claims={"roles": ["user"], "scopes": ["profile:read"]}
        )
    
    res = client.get("/api/v1/posts/101", headers={
        "Authorization": f"Bearer {token_no_scope}"
    })
    assert res.status_code == 403
    data = res.get_json()
    assert data["code"] == "insufficient_scope"

def test_get_public_post_success(client, charlie_tokens):
    """Test GET /posts/{id} bài viết public (101) -> Người lạ (Charlie) đọc thành công (200 OK)"""
    access_token, _ = charlie_tokens
    res = client.get("/api/v1/posts/101", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["id"] == 101
    assert data["visibility"] == "public"
    assert data["author"]["username"] == "alice"
    # Kiểm tra DTO không leak hash mật khẩu (OWASP API3)
    assert "password_hash" not in data["author"]

def test_get_friends_only_post(client, alice_tokens, bob_tokens, charlie_tokens):
    """
    Test GET /posts/{id} bài viết friends_only (102 của Alice):
    - Alice (tác giả) đọc được (200)
    - Bob (bạn của Alice) đọc được (200)
    - Charlie (người lạ) bị từ chối 403 Forbidden
    """
    alice_acc, _ = alice_tokens
    bob_acc, _ = bob_tokens
    charlie_acc, _ = charlie_tokens
    
    # 1. Tác giả đọc bài của chính mình -> OK
    res_author = client.get("/api/v1/posts/102", headers={"Authorization": f"Bearer {alice_acc}"})
    assert res_author.status_code == 200
    
    # 2. Bạn bè (Bob) đọc bài của Alice -> OK
    res_friend = client.get("/api/v1/posts/102", headers={"Authorization": f"Bearer {bob_acc}"})
    assert res_friend.status_code == 200
    
    # 3. Người lạ (Charlie) cố tình đọc -> 403 Forbidden
    res_stranger = client.get("/api/v1/posts/102", headers={"Authorization": f"Bearer {charlie_acc}"})
    assert res_stranger.status_code == 403
    assert res_stranger.get_json()["code"] == "friends_only_restriction"

def test_get_private_post_bola_protection(client, alice_tokens, bob_tokens, charlie_tokens, admin_tokens):
    """
    Kiểm thử phòng vệ BOLA (Broken Object Level Authorization - OWASP API1:2023):
    Bài viết riêng tư (103 của Alice):
    - Alice (chính tác giả) xem được (200 OK)
    - Charlie (người dùng khác) KHÔNG xem được (404 Not Found chống enumeration)
    - Bob (kể cả bạn bè cũng không xem được private) (404 Not Found)
    - Admin (có quyền kiểm duyệt/quản trị) xem được (200 OK)
    """
    alice_acc, _ = alice_tokens
    bob_acc, _ = bob_tokens
    charlie_acc, _ = charlie_tokens
    admin_acc, _ = admin_tokens
    
    # 1. Tác giả Alice đọc private post của mình -> 200 OK
    res_alice = client.get("/api/v1/posts/103", headers={"Authorization": f"Bearer {alice_acc}"})
    assert res_alice.status_code == 200
    assert res_alice.get_json()["id"] == 103
    
    # 2. Kẻ tấn công Charlie cố đọc ID 103 -> Bị chặn, trả 404 để chống enumeration
    res_charlie = client.get("/api/v1/posts/103", headers={"Authorization": f"Bearer {charlie_acc}"})
    assert res_charlie.status_code == 404
    assert res_charlie.get_json()["code"] == "post_not_found"
    
    # 3. Bob (bạn thân) cũng không thể đọc private diary -> Bị chặn 404
    res_bob = client.get("/api/v1/posts/103", headers={"Authorization": f"Bearer {bob_acc}"})
    assert res_bob.status_code == 404
    
    # 4. Admin có role admin -> 200 OK
    res_admin = client.get("/api/v1/posts/103", headers={"Authorization": f"Bearer {admin_acc}"})
    assert res_admin.status_code == 200
    assert res_admin.get_json()["id"] == 103

def test_get_nonexistent_post(client, alice_tokens):
    """Test GET /posts/{id} với ID không tồn tại -> 404 Not Found"""
    access_token, _ = alice_tokens
    res = client.get("/api/v1/posts/9999", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 404
    assert res.get_json()["code"] == "post_not_found"
