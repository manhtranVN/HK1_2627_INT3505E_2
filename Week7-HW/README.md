# BÀI TẬP VỀ NHÀ BUỔI 07: BACKEND SERVICE IMPLEMENTATION
## Môn học: Kiến trúc hướng dịch vụ (SOA - INT3505E)
### Đề tài: E-Commerce Product & Order Service (Production-Ready REST API)

---

## 1. Tổng quan kiến trúc & Yêu cầu bài tập

Hệ thống Backend Service quản lý Sản phẩm (Product) và Đơn hàng (Order) được thiết kế theo tiêu chuẩn công nghiệp (Production-Grade), bao gồm:
1. **CRUD Product Service**:
   - Quản lý sản phẩm đầy đủ với các trường `sku`, `name`, `price_cents`, `stock_quantity`, `category`, `status`.
   - Cơ chế trừ kho (Atomic Inventory Reservation) với giao dịch đảm bảo tính toàn vẹn (ACID) và chống Race Condition.
2. **Order & OrderItem Resource**:
   - Quản lý vòng đời đơn hàng (`PENDING` $\to$ `PAID` $\to$ `CANCELLED` $\to$ `FULFILLED`).
   - Tự động trừ tồn kho khi tạo đơn hàng, tự động hoàn trả tồn kho khi hủy đơn.
   - Giải quyết triệt để bài toán **$N+1$ Query Problem** bằng kỹ thuật Eager Loading (`selectinload` và `joinedload`).
3. **Tiêu chuẩn Production & Cloud-Native Readiness**:
   - **Multi-Probe Health Checks**: `/healthz` (Liveness Probe) và `/ready` (Readiness Probe kiểm tra kết nối CSDL).
   - **Chuẩn hóa lỗi RFC 7807**: Phản hồi lỗi đồng nhất với `Content-Type: application/problem+json`.
   - **12-Factor App**: Quản lý cấu hình linh hoạt qua biến môi trường (`.env`).
   - **Database Migration**: Quản lý phiên bản CSDL bằng Alembic / Flask-Migrate.
   - **Containerization**: Multi-stage `Dockerfile` (Non-root user) và `docker-compose.yml` tích hợp PostgreSQL với cơ chế Healthcheck tự động.
   - **Kiểm thử tự động (Automated Testing)**: 33/33 test case passed 100% bằng `pytest`.

---

## 2. Cấu trúc thư mục

```text
Week7-HW/
├── Dockerfile                  # Multi-stage build tối ưu kích thước image, chạy non-root
├── docker-compose.yml          # Triển khai backend + PostgreSQL với healthcheck
├── gunicorn.conf.py            # Cấu hình WSGI Production server
├── pyproject.toml              # Quản lý project & cấu hình pytest
├── requirements.txt            # Thư viện phụ thuộc
├── openapi.yaml                # OpenAPI 3.0.3 specification
├── seed.py                     # Script nạp dữ liệu mẫu ban đầu
├── app.py / wsgi.py            # Entrypoint khởi chạy ứng dụng
│
├── migrations/                 # Lịch sử migration cơ sở dữ liệu (Alembic)
│   └── versions/
│       └── dde988142fa2_initial_schema_products_orders.py
│
├── src/product_api/            # Mã nguồn chính của dịch vụ
│   ├── api/
│   │   ├── health.py           # Health checks (/healthz, /ready)
│   │   ├── products.py         # Endpoints CRUD Product & Reserve kho
│   │   └── orders.py           # Endpoints Order & OrderItem
│   ├── models/                 # SQLAlchemy ORM Models (Product, Order, OrderItem)
│   ├── schemas/                # Marshmallow Schemas (Validation & Serialization)
│   ├── config.py               # 12-factor configuration
│   ├── errors.py               # RFC 7807 error handlers
│   ├── extensions.py           # Khởi tạo db, migrate, api
│   ├── factory.py              # Application factory pattern
│   └── logging_config.py       # Structured JSON logging
│
└── tests/                      # Bộ kiểm thử toàn diện 33 test cases
    ├── test_health.py          # Kiểm tra Liveness & Readiness probe
    ├── test_products.py        # Kiểm tra CRUD sản phẩm & xác thực schema
    ├── test_orders.py          # Kiểm tra tạo đơn, trừ kho, hủy đơn
    └── test_n_plus_one.py      # Kiểm tra chặn lỗi N+1 Query bằng SQL query counter
```

---

## 3. Danh sách Endpoint API

| Nhóm | Phương thức | Đường dẫn | Chức năng | Mã trạng thái |
|:---|:---|:---|:---|:---|
| **Health** | `GET` | `/healthz` | Liveness probe (kiểm tra service còn sống) | `200` |
| | `GET` | `/ready` | Readiness probe (kiểm tra DB đã sẵn sàng nhận traffic) | `200`, `503` |
| **Product** | `GET` | `/products` | Danh sách sản phẩm (có lọc category, search, phân trang) | `200` |
| | `POST` | `/products` | Tạo sản phẩm mới | `201`, `400`, `422` |
| | `GET` | `/products/{id}` | Xem thông tin chi tiết 1 sản phẩm | `200`, `404` |
| | `PUT` | `/products/{id}` | Cập nhật thông tin sản phẩm | `200`, `400`, `404` |
| | `DELETE` | `/products/{id}` | Xóa sản phẩm | `204`, `404` |
| | `POST` | `/products/{id}/reserve` | Trừ kho an toàn (Atomic Stock Reservation) | `200`, `400`, `409` |
| **Order** | `GET` | `/orders` | Danh sách đơn hàng | `200` |
| | `POST` | `/orders` | Tạo đơn hàng mới & tự động trừ kho nguyên tử | `201`, `400`, `409` |
| | `GET` | `/orders/{id}` | Xem chi tiết đơn hàng cùng các items (Eager loading) | `200`, `404` |
| | `POST` | `/orders/{id}/cancel` | Hủy đơn hàng và hoàn trả lại số lượng kho | `200`, `400`, `404` |

---

## 4. Hướng dẫn chạy và kiểm thử

### Cách 1: Chạy trực tiếp với Python
```powershell
# Chuyển vào thư mục Week7-HW
cd Week7-HW

# Cài đặt thư viện
pip install -r requirements.txt

# Nạp dữ liệu mẫu
python seed.py

# Khởi chạy server development
python app.py
```
* API chạy tại: `http://127.0.0.1:5000`
* Swagger UI tài liệu API: `http://127.0.0.1:5000/swagger-ui`

---

### Cách 2: Chạy Production qua Docker Compose
```powershell
# Build và chạy ngầm container backend + PostgreSQL
docker compose up -d --build

# Kiểm tra trạng thái containers & healthcheck
docker compose ps
```

---

### Cách 3: Chạy bộ kiểm thử tự động (Pytest)
```powershell
pytest tests -v
```
Kết quả kiểm thử: **33/33 passed** (100% bao gồm cả kiểm tra race condition trừ kho và tối ưu số lượng câu truy vấn SQL).
