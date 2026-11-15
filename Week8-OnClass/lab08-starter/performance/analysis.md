# Lab 4 — Phân tích kết quả

## Môi trường đo (đọc trước khi tin vào con số)

- Ngày đo: 2026-11-11, máy cá nhân `LAPTOP-B871DQ0U`.
- Server: **Flask development server** (Werkzeug, `threaded=True`, 1 process) + **SQLite** file `instance/books.db`.
- Công cụ: Locust 2.47.0, Python 3.14.3. Lệnh: `bash run_lab4.sh` (xem `reports/locust-lab4.log`).
- `performance/locustfile.py`: 4 task có trọng số — `list_books`(3), `read_book`(2), `create_book`(1), `search_by_year`(2); `wait_time = between(1, 3)`.
- **Lỗi 1% ở `search_by_year` là `response.failure()` phía client (giả lập 500), KHÔNG phải HTTP 500 do server trả.** Server vẫn trả 200; Locust chỉ đánh dấu failed trong thống kê.
- DB bắt đầu rỗng và lớn dần qua A → B → C (mỗi kịch bản nối tiếp, không reset giữa chừng).

## Bảng kết quả — hàng `Aggregated` trong `reports/{A,B,C}_stats.csv`

| Kịch bản | Users | Spawn rate | Duration | p95 (ms) | Failure rate | RPS |
|---|---:|---:|---:|---:|---:|---:|
| A | 10 | 2 | 30s | 20 | 0.00% (0/139) | 4.80 |
| B | 50 | 5 | 60s | 19 | 0.36% (5/1385) | 23.38 |
| C | 200 | 50 | 30s | 88 | 0.18% (5/2826) | 97.01 |

p95 theo từng endpoint (ms):

| Endpoint | A | B | C |
|---|---:|---:|---:|
| GET /books | 19 | 18 | 97 |
| GET /books/{id} | 19 | 17 | 88 |
| GET /books?year= | 29 | 17 | 68 |
| POST /books | 28 | 29 | 110 |

### p95 theo số user (1 █ ≈ 5 ms)

```
10u  | ████ 20 ms
50u  | ████ 19 ms
200u | ██████████████████ 88 ms
```

A → B gần như phẳng (20 → 19 ms); B → C nhảy ~4.6× (19 → 88 ms). Đúng dạng **tăng phi tuyến sau một ngưỡng** nằm giữa 50 và 200 user.

## Trả lời câu hỏi

**1. Kịch bản có p95 cao nhất? Vì sao?**
Kịch bản **C (200 user)**: p95 aggregated **88 ms**, so với A = 20 ms và B = 19 ms. Ở 200 user, Flask dev server (1 process, bị GIL chặn) + SQLite phải xếp hàng nhiều request đồng thời nên thời gian chờ tăng vọt; POST /books chịu nặng nhất (p95 **110 ms**, max 249 ms) vì ghi SQLite bị tuần tự hoá. A và B còn dưới ngưỡng bão hoà nên p95 gần như không đổi.

**2. Endpoint nào tăng failure rate? Phân biệt lỗi HTTP thật và lỗi đánh dấu trong Locust.**
Chỉ `GET /books?year=` có failure: A 0/38 (0%), B 5/340 (1.47%), C 5/740 (0.68%). Đây **toàn bộ là lỗi giả lập client-side** (`CatchResponseError('Simulated 500 ...')` trong `reports/*_failures.csv`), dao động quanh 1% do xác suất cố định + nhiễu mẫu nhỏ — **không thực sự tăng theo số user**. `reports/*_exceptions.csv` rỗng ở cả 3 kịch bản → **không có HTTP 500 thật**, không có lỗi "database is locked". Ứng viên cho lỗi thật khi tải nặng hơn là **POST /books** (khoá ghi SQLite có thể ném `OperationalError` → 500 vì `app.py` chỉ bắt `IntegrityError`), nhưng nó chưa xuất hiện trong phép đo này. Kết luận trung thực: tải này làm **tăng latency (p95)**, chưa làm tăng failure rate thật.

**3. SLO giả định p95 < 300 ms — kịch bản nào đạt? Baseline cho CI gate.**
Cả **A, B, C đều đạt** p95 < 300 ms (kể cả max của C = 249 ms). Nhưng đây là dev server + SQLite trên máy cá nhân nên **không suy ra SLO production**. Đề xuất CI gate:
- Chạy một baseline **cố định, tái lập được** (ví dụ A: 10 user / 30s, seed dữ liệu cố định) trên **WSGI server thật** (gunicorn/waitress, số worker cố định) và runner chuẩn — không dùng dev server.
- Gate theo **p95 aggregated < 300 ms** kèm biên an toàn (báo động sớm ở > 150–200 ms để bắt regression), và **real-error rate < 0.1%** sau khi **loại trừ 1% injection đã biết**.
- Pin phiên bản Locust, dataset, duration để số liệu so sánh được. Kịch bản C chỉ dùng làm spike test định kỳ, không nên là gate mỗi PR vì nhiễu cao.

**4. (Bonus) Connection pool giới hạn ở 5, 200 user đồng thời — điều gì xảy ra? Xác nhận bằng Locust thế nào?**
Với `QueuePool(pool_size=5, max_overflow=0)`, chỉ 5 kết nối DB được phục vụ cùng lúc; 200 request đồng thời → ~195 request xếp hàng chờ connection. Nếu chờ quá `pool_timeout` (mặc định 30s) → `TimeoutError: QueuePool limit of size 5 overflow 0 reached` → không được bắt → **HTTP 500 thật**. Hệ quả: p95 tăng lên hàng giây, RPS bị chặn ở mức 5 connection phục vụ nổi, failure rate **tăng thật theo số user**.
Cách xác nhận bằng Locust:
- Cấu hình engine `pool_size=5, max_overflow=0, pool_timeout=5` (timeout nhỏ để lộ lỗi nhanh), chạy kịch bản C (200u/50r). Quan sát `reports/C_failures.csv` xuất hiện lỗi 500 (QueuePool timeout), p95 vọt, RPS plateau.
- Lặp lại với `pool_size=20` cùng kịch bản → failure giảm, p95 giảm → chứng minh pool chính là nút thắt.
- Lưu ý cô lập biến: Flask dev server và bản thân SQLite (ghi tuần tự) cũng là nút thắt; muốn quy kết riêng cho pool thì chạy WSGI server đủ worker/thread và DB server (Postgres/MySQL), vì với SQLite ghi vẫn tuần tự bất kể pool size.

## Giới hạn của phép đo

- Flask **development server** + **SQLite** trên máy cá nhân: chỉ để thực hành, không đại diện production.
- `wait_time` 1–3s giới hạn tải offered; RPS đo được (4.8 / 23.4 / 97) thấp hơn khả năng thật của server.
- Duration ngắn (30–60s) và percentile của Locust là **xấp xỉ**; DB lớn dần qua A→B→C là một yếu tố gây nhiễu.
- 1% failure là **giả lập client-side**, không phải lỗi server; không dùng nó để kết luận về độ tin cậy của API.

> Không điền số liệu giả định vào bảng. Không khẳng định hiệu năng production
> từ SQLite + Flask development server trên máy cá nhân.