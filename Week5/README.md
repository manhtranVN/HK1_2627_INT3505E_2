### Mục 1: Phân trang theo Offset (`?strategy=offset`)

#### 1.1. Lấy trang đầu tiên (`offset=0&limit=3`)
- **Mô tả:** Lấy 3 cuốn sách đầu tiên bắt đầu từ vị trí 0. Trả về metadata: `total`, `offset`, `limit`, `page`, `has_next`, `has_prev`.
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?strategy=offset&offset=0&limit=3"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      {
        "authors": [],
        "category": { "id": 5, "name": "Tâm lý & Kỹ năng", "slug": "psychology" },
        "createdAt": "2026-09-26T10:50:47Z",
        "genre": "psychology",
        "id": "book_25",
        "inStock": true,
        "isbn": "9781455586691",
        "price": { "amount": 230000, "currency": "VND" },
        "raw_id": 25,
        "stock": 16,
        "title": "Deep Work"
      },
      {
        "authors": [],
        "category": { "id": 5, "name": "Tâm lý & Kỹ năng", "slug": "psychology" },
        "createdAt": "2026-09-27T10:50:47Z",
        "genre": "psychology",
        "id": "book_24",
        "inStock": true,
        "isbn": "9780735211292",
        "price": { "amount": 210000, "currency": "VND" },
        "raw_id": 24,
        "stock": 60,
        "title": "Atomic Habits"
      },
      {
        "authors": [],
        "category": { "id": 5, "name": "Tâm lý & Kỹ năng", "slug": "psychology" },
        "createdAt": "2026-09-28T10:50:47Z",
        "genre": "psychology",
        "id": "book_23",
        "inStock": true,
        "isbn": "9780374533557",
        "price": { "amount": 290000, "currency": "VND" },
        "raw_id": 23,
        "stock": 28,
        "title": "Thinking, Fast and Slow"
      }
    ],
    "pagination": {
      "has_next": true,
      "has_prev": false,
      "limit": 3,
      "offset": 0,
      "page": 1,
      "strategy": "offset",
      "total": 25,
      "total_pages": 9
    }
  }
  ```

#### 1.2. Nhảy tới trang kế tiếp bằng `offset=3&limit=3` hoặc `page=2`
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?strategy=offset&offset=3&limit=3"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      {
        "id": "book_22",
        "title": "21 Lessons for the 21st Century",
        "price": { "amount": 310000, "currency": "VND" },
        "genre": "business"
      },
      {
        "id": "book_21",
        "title": "Homo Deus: A Brief History of Tomorrow",
        "price": { "amount": 330000, "currency": "VND" },
        "genre": "business"
      },
      {
        "id": "book_20",
        "title": "Sapiens: A Brief History of Humankind",
        "price": { "amount": 320000, "currency": "VND" },
        "genre": "business"
      }
    ],
    "pagination": {
      "has_next": true,
      "has_prev": true,
      "limit": 3,
      "offset": 3,
      "page": 2,
      "strategy": "offset",
      "total": 25,
      "total_pages": 9
    }
  }
  ```

---

### Mục 2: Phân trang theo Cursor (`?strategy=cursor`)

#### 2.1. Lấy trang đầu tiên với Cursor
- **Mô tả:** Truy vấn trang 1 với kích thước 3 bản ghi. Server trả về token `next_cursor` mã hoá base64url thông tin mốc sắp xếp cuối cùng.
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?strategy=cursor&limit=3"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      { "id": "book_25", "title": "Deep Work" },
      { "id": "book_24", "title": "Atomic Habits" },
      { "id": "book_23", "title": "Thinking, Fast and Slow" }
    ],
    "pagination": {
      "has_more": true,
      "limit": 3,
      "next_cursor": "eyJzIjogIi1pZCIsICJ2IjogWzIzXX0",
      "strategy": "cursor"
    }
  }
  ```
  *(Chuỗi `next_cursor` giải mã là: `{"s": "-id", "v": [23]}`)*

#### 2.2. Lấy trang kế tiếp sử dụng `next_cursor`
- **Mô tả:** Truyền `cursor=eyJzIjogIi1pZCIsICJ2IjogWzIzXX0` lên server để lấy 3 cuốn sách tiếp theo. Dữ liệu liên tục và tuyệt đối không trùng lặp các ID của trang trước.
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?strategy=cursor&limit=3&cursor=eyJzIjogIi1pZCIsICJ2IjogWzIzXX0"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      { "id": "book_22", "title": "21 Lessons for the 21st Century" },
      { "id": "book_21", "title": "Homo Deus: A Brief History of Tomorrow" },
      { "id": "book_20", "title": "Sapiens: A Brief History of Humankind" }
    ],
    "pagination": {
      "has_more": true,
      "limit": 3,
      "next_cursor": "eyJzIjogIi1pZCIsICJ2IjogWzIwXX0",
      "strategy": "cursor"
    }
  }
  ```

---

### Mục 3: Lọc dữ liệu (`?genre=...`, `?price_min`, `?price_max`, `?in_stock`)

#### 3.1. Lọc theo thể loại Công nghệ thông tin (`?genre=tech`)
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?genre=tech&strategy=offset&limit=3"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      {
        "id": "book_9",
        "title": "The Clean Coder",
        "genre": "tech",
        "price": { "amount": 350000, "currency": "VND" }
      },
      {
        "id": "book_8",
        "title": "Extreme Programming Explained",
        "genre": "tech",
        "price": { "amount": 300000, "currency": "VND" }
      },
      {
        "id": "book_7",
        "title": "Clean Craftsmanship",
        "genre": "tech",
        "inStock": false,
        "price": { "amount": 350000, "currency": "VND" }
      }
    ],
    "pagination": {
      "has_next": true,
      "has_prev": false,
      "limit": 3,
      "offset": 0,
      "page": 1,
      "strategy": "offset",
      "total": 9,
      "total_pages": 3
    }
  }
  ```

#### 3.2. Lọc theo khoảng giá và tình trạng kho (`?price_min=200000&price_max=300000&in_stock=true`)
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?price_min=200000&price_max=300000&in_stock=true&strategy=offset"
  ```

---

### Mục 4: Sắp Xếp Đa Khóa (Multi-key Sort) & Tie-breaking

#### 4.1. Sắp xếp đa khóa `?sort=-price,title` (Giá giảm dần, nếu cùng giá thì tiêu đề tăng dần)
- **Mô tả:** Kiểm tra sắp xếp nhiều tiêu chí. Cột `price` giảm dần (có dấu `-`), khi hai cuốn sách có giá bằng nhau thì sắp xếp theo `title` theo thứ tự chữ cái A-Z (không dấu `-`).
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?sort=-price,title&limit=5&strategy=offset"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      { "id": "book_6", "title": "Patterns of Enterprise Application Architecture", "price": { "amount": 520000, "currency": "VND" } },
      { "id": "book_5", "title": "Domain-Driven Design", "price": { "amount": 480000, "currency": "VND" } },
      { "id": "book_4", "title": "Refactoring", "price": { "amount": 450000, "currency": "VND" } },
      { "id": "book_2", "title": "Clean Architecture", "price": { "amount": 420000, "currency": "VND" } },
      { "id": "book_1", "title": "Clean Code", "price": { "amount": 350000, "currency": "VND" } }
    ],
    "pagination": {
      "limit": 5,
      "offset": 0,
      "page": 1,
      "strategy": "offset",
      "total": 25,
      "total_pages": 5
    }
  }
  ```

#### 4.2. Phân trang Cursor với Sắp xếp đa khóa (`?sort=-price,title`)
- **Mô tả:** Hệ thống tự động bổ sung khóa `id` làm tie-breaker: `(price_vnd, title, id)` đảm bảo thứ tự luôn cố định (deterministic) ngay cả khi có nhiều sách trùng giá và trùng tên.
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?strategy=cursor&limit=4&sort=-price,title"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      { "id": "book_6", "title": "Patterns of Enterprise Application Architecture", "price": { "amount": 520000, "currency": "VND" } },
      { "id": "book_5", "title": "Domain-Driven Design", "price": { "amount": 480000, "currency": "VND" } },
      { "id": "book_4", "title": "Refactoring", "price": { "amount": 450000, "currency": "VND" } },
      { "id": "book_2", "title": "Clean Architecture", "price": { "amount": 420000, "currency": "VND" } }
    ],
    "pagination": {
      "has_more": true,
      "limit": 4,
      "next_cursor": "eyJzIjogIi1wcmljZSx0aXRsZSIsICJ2IjogWzQyMDAwMCwgIkNsZWFuIEFyY2hpdGVjdHVyZSIsIDJdfQ",
      "strategy": "cursor"
    }
  }
  ```
  *(Giá trị cursor chứa đầy đủ: `{"s": "-price,title", "v": [420000, "Clean Architecture", 2]}`)*

---

### Mục 5: Field Selection (Sparse Fieldsets: `?fields=...`)

- **Mô tả:** Client yêu cầu chỉ trả về các trường mong muốn (`id`, `title`, `price`), cắt giảm các trường dài như `isbn`, `createdAt`, `authors` để tiết kiệm băng thông.
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?fields=id,title,price&limit=2"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  {
    "data": [
      {
        "id": "book_25",
        "price": { "amount": 230000, "currency": "VND" },
        "raw_id": 25,
        "title": "Deep Work"
      },
      {
        "id": "book_24",
        "price": { "amount": 210000, "currency": "VND" },
        "raw_id": 24,
        "title": "Atomic Habits"
      }
    ],
    "pagination": {
      "has_more": true,
      "limit": 2,
      "next_cursor": "eyJzIjogIi1pZCIsICJ2IjogWzI0XX0",
      "strategy": "cursor"
    }
  }
  ```

---

### Mục 6: Xử Lý Lỗi và An Toàn Truy Vấn (Error Handling)

#### 6.1. Sắp xếp trường không nằm trong whitelist (`?sort=invalid_col`)
- **Mô tả:** Ngăn chặn lỗi SQL Injection bằng whitelist các cột được phép. Trả về mã lỗi 400 Bad Request rõ ràng.
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?sort=invalid_col"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 400 BAD REQUEST
  Content-Type: application/json
  
  {
    "error": "bad_sort",
    "message": "Trường sắp xếp không hợp lệ: 'invalid_col'. Cho phép: ['id', 'price', 'price_vnd', 'title', 'stock', 'created_at']"
  }
  ```

#### 6.2. Thay đổi tiêu chí sắp xếp khi đang dùng cursor (`sort_chg`)
- **Mô tả:** Client gửi kèm cursor được tạo từ `sort=-id` nhưng query lại yêu cầu `sort=-price`. Server phát hiện sai lệch mốc và từ chối xử lý bằng mã lỗi 400.
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books?strategy=cursor&sort=-price&cursor=eyJzIjogIi1pZCIsICJ2IjogWzIzXX0"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 400 BAD REQUEST
  Content-Type: application/json
  
  {
    "error": "sort_chg",
    "message": "Cursor có kiểu sort '-id' không khớp với query sort hiện tại '-price'"
  }
  ```

---

### Mục 7: JSON Schema Validation khi tạo sách mới (`POST /api/v1/books`)

#### 7.1. Tạo sách thành công với Schema hợp lệ
- **Lệnh test (PowerShell):**
  ```powershell
  curl.exe -i -X POST "http://127.0.0.1:5000/api/v1/books" -H "Content-Type: application/json" -d "{\`"title\`": \`"Building Microservices\`", \`"isbn\`": \`"9781491950357\`", \`"price\`": {\`"amount\`": 590000, \`"currency\`": \`"VND\`"}, \`"stock\`": 10, \`"category_id\`": 1}"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 201 CREATED
  Location: /api/v1/books/26
  Content-Type: application/json
  
  {
    "authors": [],
    "category": { "id": 1, "name": "Công nghệ thông tin", "slug": "tech" },
    "createdAt": "2026-10-20T10:54:58Z",
    "genre": "tech",
    "id": "book_26",
    "inStock": true,
    "isbn": "9781491950357",
    "price": { "amount": 590000, "currency": "VND" },
    "raw_id": 26,
    "stock": 10,
    "title": "Building Microservices"
  }
  ```

#### 7.2. Lỗi validation khi thiếu trường bắt buộc (`price`)
- **Lệnh test (PowerShell):**
  ```powershell
  curl.exe -i -X POST "http://127.0.0.1:5000/api/v1/books" -H "Content-Type: application/json" -d "{\`"title\`": \`"Incomplete Book\`"}"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 400 BAD REQUEST
  Content-Type: application/json
  
  {
    "error": "validation_failed",
    "field": [],
    "message": "'price' is a required property"
  }
  ```

---

### Mục 8: Quản Lý Quan Hệ N:M Tác Giả - Sách (Sub-resources)

#### 8.1. Lấy danh sách tác giả của một cuốn sách (`GET /books/1/authors`)
- **Lệnh test:**
  ```powershell
  curl.exe -i "http://127.0.0.1:5000/api/v1/books/1/authors"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: application/json
  
  [
    {
      "bio": "Tác giả nổi tiếng về Clean Code và Clean Architecture.",
      "id": 1,
      "name": "Robert C. Martin",
      "role": "lead"
    }
  ]
  ```

#### 8.2. Thêm tác giả đồng hành (`POST /books/1/authors`)
- **Lệnh test (PowerShell):**
  ```powershell
  curl.exe -i -X POST "http://127.0.0.1:5000/api/v1/books/1/authors" -H "Content-Type: application/json" -d "{\`"author_id\`": 2, \`"role\`": \`"co\`"}"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 201 CREATED
  Content-Type: application/json
  
  {
    "author_id": 2,
    "author_name": "Martin Fowler",
    "book_id": 1,
    "role": "co"
  }
  ```

#### 8.3. Gỡ tác giả khỏi sách (`DELETE /books/1/authors/2`)
- **Lệnh test (PowerShell):**
  ```powershell
  curl.exe -i -X DELETE "http://127.0.0.1:5000/api/v1/books/1/authors/2"
  ```
- **Kết quả HTTP Response:**
  ```http
  HTTP/1.1 204 NO CONTENT
  ```

---

## 6. Kết Quả Kiểm Thử Tự Động Toàn Diện (`pytest`)

Tất cả 20 bài kiểm thử đơn vị và tích hợp trong `tests/test_pagination.py` đều đạt kết quả **PASSED (100%)**:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0
rootdir: F:\học\uet\kthdv\HK1_2627_INT3505E_2\Week5
collected 20 items

tests/test_pagination.py::test_offset_pagination_page_1 PASSED           [  5%]
tests/test_pagination.py::test_offset_pagination_page_2 PASSED           [ 10%]
tests/test_pagination.py::test_offset_pagination_page_param PASSED       [ 15%]
tests/test_pagination.py::test_cursor_pagination_basic PASSED            [ 20%]
tests/test_pagination.py::test_cursor_pagination_sequential_navigation PASSED [ 25%]
tests/test_pagination.py::test_filter_by_genre_tech PASSED               [ 30%]
tests/test_pagination.py::test_filter_by_genre_fiction PASSED            [ 35%]
tests/test_pagination.py::test_filter_by_price_range PASSED              [ 40%]
tests/test_pagination.py::test_filter_in_stock PASSED                    [ 45%]
tests/test_pagination.py::test_sort_single_key_asc_desc PASSED           [ 50%]
tests/test_pagination.py::test_sort_multi_key PASSED                     [ 55%]
tests/test_pagination.py::test_cursor_with_multi_key_and_duplicate_prices PASSED [ 60%]
tests/test_pagination.py::test_bad_sort_returns_400 PASSED               [ 65%]
tests/test_pagination.py::test_cursor_sort_changed_returns_400 PASSED    [ 70%]
tests/test_pagination.py::test_bad_cursor_returns_400 PASSED             [ 75%]
tests/test_pagination.py::test_bad_strategy_returns_400 PASSED           [ 80%]
tests/test_pagination.py::test_field_selection PASSED                    [ 85%]
tests/test_pagination.py::test_post_book_schema_validation_success PASSED [ 90%]
tests/test_pagination.py::test_post_book_schema_validation_failure PASSED [ 95%]
tests/test_pagination.py::test_book_authors_nested_lifecycle PASSED      [100%]

============================= 20 passed in 4.67s ==============================
```

---
