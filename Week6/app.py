import os
import sys
import re
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt, decode_token
)
from config import Config
import database
from auth import (
    verify_credentials_constant_time, get_role_scopes,
    make_problem_response, require_scopes, check_post_access
)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
app.config.from_object(Config)

jwt = JWTManager(app)

# In-memory rate limiting tracker (chống brute-force)
# Format: {ip_or_email: [(timestamp, is_fail)]}
RATE_LIMIT_STORE = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_PERIOD_SECONDS = 60

# -------------------------------------------------------------
# JWT Error Handlers (RFC 7807)
# -------------------------------------------------------------
@jwt.token_in_blocklist_loader
def check_if_token_revoked(_header, payload):
    jti = payload.get("jti")
    if not jti:
        return False
    return database.is_token_revoked(jti, db_path=app.config["DATABASE_PATH"])

@jwt.unauthorized_loader
def handle_unauthorized_error(err_str):
    return make_problem_response(
        status=401,
        title="Unauthorized",
        detail="Missing or malformed Authorization header. Bearer token required.",
        code="missing_token"
    )

@jwt.invalid_token_loader
def handle_invalid_token_error(err_str):
    return make_problem_response(
        status=401,
        title="Unauthorized",
        detail="Signature verification failed or token is malformed.",
        code="invalid_token"
    )

@jwt.expired_token_loader
def handle_expired_token_error(_header, _payload):
    return make_problem_response(
        status=401,
        title="Unauthorized",
        detail="The token has expired. Please refresh your token or log in again.",
        code="token_expired"
    )

@jwt.revoked_token_loader
def handle_revoked_token_error(_header, _payload):
    return make_problem_response(
        status=401,
        title="Unauthorized",
        detail="The token has been revoked.",
        code="token_revoked"
    )

# -------------------------------------------------------------
# Rate Limiting Helper (Chống Brute Force)
# -------------------------------------------------------------
def check_rate_limit(key: str) -> bool:
    """Trả về True nếu bị chặn do quá số lần thử đăng nhập sai"""
    now = datetime.now(timezone.utc).timestamp()
    history = RATE_LIMIT_STORE.get(key, [])
    # Chỉ giữ lại các lần thử trong khoảng LOCKOUT_PERIOD_SECONDS
    history = [ts for ts in history if now - ts < LOCKOUT_PERIOD_SECONDS]
    RATE_LIMIT_STORE[key] = history
    return len(history) >= MAX_FAILED_ATTEMPTS

def record_failed_attempt(key: str):
    now = datetime.now(timezone.utc).timestamp()
    history = RATE_LIMIT_STORE.get(key, [])
    history.append(now)
    RATE_LIMIT_STORE[key] = history

def clear_rate_limit(key: str):
    RATE_LIMIT_STORE.pop(key, None)

# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------

@app.post("/api/v1/auth/login")
@app.post("/auth/login")
def login():
    """
    POST /auth/login
    Xác thực người dùng và cấp cặp token JWT (Access Token + Refresh Token).
    - Scope yêu cầu: None (Public endpoint)
    - Xử lý lỗi: 400 (Bad Request), 401 (Unauthorized), 422 (Validation), 429 (Rate Limit), 500 (Server Error)
    """
    if not request.is_json:
        return make_problem_response(
            status=400,
            title="Bad Request",
            detail="Request body must be JSON.",
            code="malformed_json"
        )
    
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    # Kiểm tra thiếu trường bắt buộc (400)
    if not email or not password:
        return make_problem_response(
            status=400,
            title="Bad Request",
            detail="Fields 'email' and 'password' are required.",
            code="missing_fields"
        )
    
    # Kiểm tra định dạng email RFC 5322 (422)
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not isinstance(email, str) or not re.match(email_regex, email.strip()):
        return make_problem_response(
            status=422,
            title="Unprocessable Entity",
            detail="Field 'email' is not a valid email address.",
            code="invalid_email_format",
            invalid_params=[{"name": "email", "reason": "Must be valid email format."}]
        )
        
    client_ip = request.remote_addr or "127.0.0.1"
    rate_key = f"{client_ip}:{email.lower().strip()}"
    
    # Kiểm tra rate limit (429)
    if check_rate_limit(rate_key):
        resp = make_problem_response(
            status=429,
            title="Too Many Requests",
            detail=f"Too many failed login attempts. Please try again after {LOCKOUT_PERIOD_SECONDS} seconds.",
            code="rate_limit_exceeded"
        )
        resp.headers["Retry-After"] = str(LOCKOUT_PERIOD_SECONDS)
        return resp
    
    # Xác thực mật khẩu với Constant-Time Dummy Hash chống Timing Attack
    user = verify_credentials_constant_time(
        email=email,
        password=password,
        db_path=app.config["DATABASE_PATH"]
    )
    
    if not user:
        record_failed_attempt(rate_key)
        # Thông báo lỗi chung không tiết lộ email có tồn tại hay không
        return make_problem_response(
            status=401,
            title="Unauthorized",
            detail="Invalid email or password.",
            code="invalid_credentials"
        )
    
    clear_rate_limit(rate_key)
    
    uid_str = str(user["id"])
    role = user["role"]
    scopes = get_role_scopes(role)
    
    # Access Token chứa claims: roles, scopes
    claims = {
        "roles": [role],
        "scopes": scopes
    }
    
    access_token = create_access_token(
        identity=uid_str,
        additional_claims=claims,
        expires_delta=app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    )
    
    # Refresh Token có claim type: "refresh"
    refresh_token = create_refresh_token(
        identity=uid_str,
        additional_claims={"type": "refresh"},
        expires_delta=app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    )
    
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
        "refresh_expires_in": int(app.config["JWT_REFRESH_TOKEN_EXPIRES"].total_seconds()),
        "scopes": scopes,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "avatar_url": user["avatar_url"],
            "role": user["role"]
        }
    }), 200

@app.post("/api/v1/auth/refresh")
@app.post("/auth/refresh")
def refresh():
    """
    POST /auth/refresh
    Gia hạn Access Token bằng Refresh Token (hỗ trợ cả header Authorization hoặc body JSON).
    Áp dụng Refresh Token Rotation.
    - Scope yêu cầu: Yêu cầu Refresh Token hợp lệ (claim type: "refresh")
    - Xử lý lỗi: 400 (Bad Request), 401 (Unauthorized / Revoked), 403 (Invalid Token Type), 500
    """
    token_str = None
    
    # 1. Trích xuất token từ Authorization header nếu có
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token_str = auth_header[7:].strip()
    
    # 2. Nếu không có ở header, kiểm tra body JSON
    if not token_str and request.is_json:
        data = request.get_json(silent=True) or {}
        token_str = data.get("refresh_token")
        
    if not token_str:
        return make_problem_response(
            status=400,
            title="Bad Request",
            detail="Refresh token is required via 'Authorization: Bearer <token>' header or 'refresh_token' body field.",
            code="missing_refresh_token"
        )
    
    # Giải mã và kiểm tra token
    try:
        decoded = decode_token(token_str)
    except Exception as e:
        return make_problem_response(
            status=401,
            title="Unauthorized",
            detail=f"Invalid or expired refresh token: {str(e)}",
            code="invalid_token"
        )
    
    # Kiểm tra loại token: Bắt buộc phải là Refresh Token
    token_type = decoded.get("type")
    if token_type != "refresh":
        return make_problem_response(
            status=403,
            title="Forbidden",
            detail="Invalid token type. You must provide a Refresh Token, not an Access Token.",
            code="invalid_token_type"
        )
        
    # Kiểm tra token đã bị đưa vào blocklist chưa
    jti = decoded.get("jti")
    if database.is_token_revoked(jti, db_path=app.config["DATABASE_PATH"]):
        return make_problem_response(
            status=401,
            title="Unauthorized",
            detail="This refresh token has been revoked.",
            code="token_revoked"
        )
        
    uid_str = decoded.get("sub")
    user = database.find_user_by_id(int(uid_str), db_path=app.config["DATABASE_PATH"])
    if not user or not user["is_active"]:
        return make_problem_response(
            status=403,
            title="Forbidden",
            detail="User account is deactivated or no longer exists.",
            code="account_suspended"
        )
        
    # Thu hồi Refresh Token cũ (Refresh Token Rotation)
    database.revoke_token(jti, db_path=app.config["DATABASE_PATH"])
    
    # Nạp quyền hiện tại của người dùng
    scopes = get_role_scopes(user["role"])
    claims = {
        "roles": [user["role"]],
        "scopes": scopes
    }
    
    # Cấp Access Token mới
    new_access_token = create_access_token(
        identity=uid_str,
        additional_claims=claims,
        expires_delta=app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    )
    
    # Cấp Refresh Token mới xoay vòng
    new_refresh_token = create_refresh_token(
        identity=uid_str,
        additional_claims={"type": "refresh"},
        expires_delta=app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    )
    
    return jsonify({
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "expires_in": int(app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds())
    }), 200

@app.get("/api/v1/posts/<int:id>")
@app.get("/posts/<int:id>")
@jwt_required()
@require_scopes("posts:read")
@check_post_access("id")
def get_post(id: int, _cached_post=None):
    """
    GET /posts/{id}
    Lấy thông tin bài viết theo ID.
    Bảo vệ 3 lớp:
    1. AuthN: @jwt_required()
    2. AuthZ Scope: @require_scopes("posts:read")
    3. Object-Level Ownership (Chống BOLA): @check_post_access("id")
    """
    # Lấy post đã được cache an toàn trong decorator check_post_access
    post = _cached_post
    if not post:
        post = database.get_post_with_author(id, db_path=app.config["DATABASE_PATH"])
        
    return jsonify(post), 200

# -------------------------------------------------------------
# Swagger UI & OpenAPI Specification Routes
# -------------------------------------------------------------

@app.get("/api/v1/openapi.yaml")
@app.get("/openapi.yaml")
def get_openapi_yaml():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, "openapi.yaml", mimetype="text/yaml")

@app.get("/api/v1/docs")
@app.get("/docs")
def swagger_ui():
    """Giao diện Swagger UI tương tác hiển thị đặc tả OpenAPI 3.0.3"""
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Social Network API - Swagger UI</title>
      <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
      <style>
        body { margin: 0; background: #fafafa; font-family: sans-serif; }
        .topbar { display: none; }
      </style>
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
      <script>
        window.onload = () => {
          window.ui = SwaggerUIBundle({
            url: '/openapi.yaml',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            layout: "BaseLayout"
          });
        };
      </script>
    </body>
    </html>
    """
    return render_template_string(template)

@app.get("/health")
def health_check():
    return jsonify({"status": "healthy", "service": "social-network-api", "version": "1.0.0"}), 200

# -------------------------------------------------------------
# Global Error Handlers (RFC 7807)
# -------------------------------------------------------------
@app.errorhandler(404)
def handle_not_found(e):
    return make_problem_response(
        status=404,
        title="Not Found",
        detail="The requested URL was not found on the server.",
        code="endpoint_not_found"
    )

@app.errorhandler(405)
def handle_method_not_allowed(e):
    return make_problem_response(
        status=405,
        title="Method Not Allowed",
        detail="The method is not allowed for the requested URL.",
        code="method_not_allowed"
    )

@app.errorhandler(500)
def handle_server_error(e):
    return make_problem_response(
        status=500,
        title="Internal Server Error",
        detail="An internal server error occurred.",
        code="internal_error"
    )

if __name__ == "__main__":
    database.init_db()
    print("[*] Starting Social Network API service on http://127.0.0.1:5000 ...")
    print("[*] Swagger UI documentation available at: http://127.0.0.1:5000/docs")
    app.run(host="127.0.0.1", port=5000, debug=True)
