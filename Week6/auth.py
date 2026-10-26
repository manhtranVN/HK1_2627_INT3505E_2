from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt, get_jwt_identity
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timezone
import database

# PasswordHasher Argon2id (Memory-hard 64MB, time_cost=3, parallelism=4)
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    type=Type.ID
)

# Hash giả lập để cân bằng thời gian xử lý khi email không tồn tại (chống timing attack)
DUMMY_ARGON2_HASH = ph.hash("dummy-hash-to-balance-timing-for-invalid-users")

def hash_password(password: str) -> str:
    """Băm mật khẩu bằng Argon2id kèm salt ngẫu nhiên"""
    return ph.hash(password)

def verify_password_safe(stored_hash: str, password: str) -> bool:
    """Xác minh mật khẩu an toàn"""
    try:
        ph.verify(stored_hash, password)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False

def verify_credentials_constant_time(email: str, password: str, db_path=None):
    """Xác thực thông tin đăng nhập với thời gian phản hồi đồng nhất"""
    user = database.find_user_by_email(email, db_path=db_path)
    if user:
        if verify_password_safe(user["password_hash"], password):
            return user
        return None
    else:
        # Chạy dummy hash nếu email không tồn tại để san bằng độ trễ
        verify_password_safe(DUMMY_ARGON2_HASH, password)
        return None

def get_role_scopes(role: str) -> list:
    """Gán scopes mặc định theo vai trò"""
    role_scope_map = {
        "user": ["posts:read", "posts:write", "profile:read"],
        "moderator": ["posts:read", "posts:write", "posts:moderate", "profile:read"],
        "admin": ["posts:read", "posts:write", "posts:moderate", "profile:read", "admin"]
    }
    return role_scope_map.get(role, ["posts:read"])

def make_problem_response(status: int, title: str, detail: str, code: str = None, invalid_params: list = None):
    """Tạo phản hồi lỗi chuẩn RFC 7807 (Problem Details)"""
    type_url = f"https://api.socialnetwork.example.com/errors/{code or status}"
    problem = {
        "type": type_url,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.path,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if code:
        problem["code"] = code
    if invalid_params:
        problem["invalid_params"] = invalid_params
    
    response = jsonify(problem)
    response.status_code = status
    response.headers["Content-Type"] = "application/problem+json"
    return response

def require_scopes(*needed_scopes):
    """Kiểm tra token có đủ tất cả scopes yêu cầu (AND)"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            granted_scopes = set(claims.get("scopes", []))
            needed_set = set(needed_scopes)
            
            if not needed_set.issubset(granted_scopes):
                return make_problem_response(
                    status=403,
                    title="Forbidden",
                    detail=f"Insufficient permissions. Required scope(s): {list(needed_scopes)}",
                    code="insufficient_scope"
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def require_roles(*allowed_roles):
    """Kiểm tra token có ít nhất một role được phép (OR)"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_roles = set(claims.get("roles", []))
            allowed_set = set(allowed_roles)
            
            if not (user_roles & allowed_set):
                return make_problem_response(
                    status=403,
                    title="Forbidden",
                    detail=f"Access denied. User role must be one of: {list(allowed_roles)}",
                    code="forbidden_role"
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def check_post_access(id_param="id"):
    """Kiểm tra quyền truy cập theo đối tượng (BOLA protection)"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            post_id = kwargs.get(id_param)
            if post_id is None or post_id <= 0:
                return make_problem_response(
                    status=400,
                    title="Bad Request",
                    detail="Invalid post ID format. Must be a positive integer.",
                    code="invalid_id"
                )
            
            db_path = current_app.config.get("DATABASE_PATH")
            post = database.get_post_with_author(post_id, db_path=db_path)
            if not post:
                return make_problem_response(
                    status=404,
                    title="Not Found",
                    detail=f"Post with ID {post_id} not found.",
                    code="post_not_found"
                )
            
            current_user_id = int(get_jwt_identity())
            claims = get_jwt()
            user_roles = claims.get("roles", ["user"])
            is_admin = "admin" in user_roles or "moderator" in user_roles
            
            author_id = post["author"]["id"]
            visibility = post["visibility"]
            
            # Kiểm tra quyền truy cập theo visibility
            if visibility == "public":
                pass
            elif visibility == "friends_only":
                is_friend = database.are_friends(author_id, current_user_id, db_path=db_path)
                if not (author_id == current_user_id or is_friend or is_admin):
                    return make_problem_response(
                        status=403,
                        title="Forbidden",
                        detail="This post is restricted to friends of the author.",
                        code="friends_only_restriction"
                    )
            elif visibility == "private":
                if not (author_id == current_user_id or is_admin):
                    # Trả 404 để tránh lộ sự tồn tại của bài viết riêng tư
                    return make_problem_response(
                        status=404,
                        title="Not Found",
                        detail=f"Post with ID {post_id} not found.",
                        code="post_not_found"
                    )
            
            kwargs["_cached_post"] = post
            return fn(*args, **kwargs)
        return wrapper
    return decorator
