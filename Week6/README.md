# BÀI TẬP VỀ NHÀ BUỔI 06: AUTHENTICATION & AUTHORIZATION TRONG REST API
## Đề tài: Social Network API (OpenAPI 3.0 Spec & Security Audit)

---
Trả lời các câu hỏi:

### Câu hỏi 1: Mỗi endpoint cần scope nào?

| Endpoint | Giao thức & Bảo mật | Scope yêu cầu | Cơ chế kiểm tra |
|:---|:---|:---|:---|
| **`POST /auth/login`** | Public (Không cần Token) | `None` | Endpoint công khai để người dùng gửi credentials (`email` + `password`). Sau khi xác thực thành công, server cấp token chứa danh sách `scopes` dựa theo vai trò (User: `["posts:read", "posts:write", "profile:read"]`; Admin: thêm `posts:moderate`, `admin`). |
| **`POST /auth/refresh`** | `refreshBearerAuth` | `refresh` (Token Claim `type: "refresh"`) | Yêu cầu Refresh Token hợp lệ (truyền qua header `Authorization: Bearer <refresh_token>` hoặc request body JSON). **Từ chối nếu gửi Access Token** (trả `403 Forbidden - invalid_token_type`). |
| **`GET /posts/{id}`** | `bearerAuth` / `oauth2` | **`posts:read`** | Yêu cầu JWT Access Token hợp lệ có scope `posts:read`. Đồng thời áp dụng **lớp kiểm tra quyền đối tượng (Ownership / BOLA Check)** theo 3 cấp độ: `public`, `friends_only`, `private`. |

---

### Câu hỏi 2: Lỗi nào có thể xảy ra?

Mọi phản hồi lỗi đều tuân thủ chuẩn **RFC 7807 (Problem Details for HTTP APIs)** với `Content-Type: application/problem+json`:

1. **`POST /auth/login`**:
   - `400 Bad Request`: Body không phải JSON hoặc thiếu `email` / `password` (`missing_fields`).
   - `401 Unauthorized`: Sai email hoặc mật khẩu (`invalid_credentials`), tài khoản bị khóa (`account_disabled`). Luôn trả thông báo chung không phân biệt email tồn tại hay không.
   - `422 Unprocessable Content`: Email sai định dạng RFC 5322 (`invalid_email_format`) hoặc mật khẩu không đạt độ dài tối thiểu.
   - `429 Too Many Requests`: Vượt quá số lần thử sai (Rate limit: tối đa 5 lần thử / phút) để chống Brute-force & Credential Stuffing.
   - `500 Internal Server Error`: Sự cố cơ sở dữ liệu hoặc máy chủ nội bộ.

2. **`POST /auth/refresh`**:
   - `400 Bad Request`: Thiếu refresh token trong header hoặc request body (`missing_refresh_token`).
   - `401 Unauthorized`: Refresh token hết hạn (`token_expired`), chữ ký giả mạo (`invalid_token`), hoặc token đã bị đưa vào blocklist thu hồi (`token_revoked`).
   - `403 Forbidden`: Gửi nhầm Access Token thay vì Refresh Token (`invalid_token_type`), hoặc tài khoản người dùng đã bị khóa (`account_suspended`).
   - `429 Too Many Requests`: Gọi refresh liên tục vượt ngưỡng rate limit.
   - `500 Internal Server Error`: Lỗi máy chủ nội bộ.

3. **`GET /posts/{id}`**:
   - `400 Bad Request`: Tham số `{id}` không hợp lệ (không phải số nguyên dương).
   - `401 Unauthorized`: Thiếu header Authorization (`missing_token`), token hết hạn (`token_expired`), hoặc token đã bị thu hồi (`token_revoked`).
   - `403 Forbidden`: Token thiếu scope `posts:read` (`insufficient_scope`), HOẶC người dùng không có quyền xem bài viết `friends_only` (không phải bạn bè) hoặc bài viết `private` (không phải tác giả và không có quyền admin) — vi phạm **BOLA (OWASP API1:2023)**.
   - `404 Not Found`: Bài viết không tồn tại (`post_not_found`), hoặc trả về 404 thay cho 403 đối với bài viết private để chống brute-force ID rò rỉ sự tồn tại của bài viết.
   - `429 Too Many Requests`: Gửi request vượt giới hạn tần suất.
   - `500 Internal Server Error`: Lỗi máy chủ nội bộ.

---

### Câu hỏi 3: Status code nào được trả?

* **`POST /auth/login`**: `200 OK`, `400 Bad Request`, `401 Unauthorized`, `422 Unprocessable Content`, `429 Too Many Requests`, `500 Internal Server Error`.
* **`POST /auth/refresh`**: `200 OK`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `429 Too Many Requests`, `500 Internal Server Error`.
* **`GET /posts/{id}`**: `200 OK`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `429 Too Many Requests`, `500 Internal Server Error`.

---
