import sys
import os
import json
import pytest

# Thêm thư mục Week5 vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Book, Category, Author

@pytest.fixture
def client():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })
    with app.test_client() as client:
        with app.app_context():
            from seed import seed_database
            seed_database()
        yield client


# --- 1. OFFSET PAGINATION TESTS ---

def test_offset_pagination_page_1(client):
    """Kiểm tra phân trang offset trang đầu tiên"""
    res = client.get("/api/v1/books?strategy=offset&offset=0&limit=5")
    assert res.status_code == 200
    body = res.get_json()
    assert "data" in body
    assert len(body["data"]) == 5
    pag = body["pagination"]
    assert pag["strategy"] == "offset"
    assert pag["offset"] == 0
    assert pag["limit"] == 5
    assert pag["total"] == 25
    assert pag["has_next"] is True
    assert pag["has_prev"] is False
    assert pag["page"] == 1


def test_offset_pagination_page_2(client):
    """Kiểm tra phân trang offset trang thứ hai qua offset=5"""
    res = client.get("/api/v1/books?strategy=offset&offset=5&limit=5")
    assert res.status_code == 200
    body = res.get_json()
    assert len(body["data"]) == 5
    pag = body["pagination"]
    assert pag["offset"] == 5
    assert pag["has_prev"] is True
    assert pag["page"] == 2


def test_offset_pagination_page_param(client):
    """Kiểm tra phân trang offset bằng param page=2"""
    res = client.get("/api/v1/books?strategy=offset&page=2&limit=5")
    assert res.status_code == 200
    body = res.get_json()
    assert body["pagination"]["offset"] == 5
    assert body["pagination"]["page"] == 2


# --- 2. CURSOR PAGINATION TESTS ---

def test_cursor_pagination_basic(client):
    """Kiểm tra phân trang cursor trang đầu"""
    res = client.get("/api/v1/books?strategy=cursor&limit=5")
    assert res.status_code == 200
    body = res.get_json()
    assert len(body["data"]) == 5
    pag = body["pagination"]
    assert pag["strategy"] == "cursor"
    assert pag["has_more"] is True
    assert pag["next_cursor"] is not None


def test_cursor_pagination_sequential_navigation(client):
    """Kiểm tra di chuyển sang trang tiếp theo bằng cursor không bị trùng lặp phần tử"""
    # Trang 1
    res1 = client.get("/api/v1/books?strategy=cursor&limit=5&sort=-id")
    body1 = res1.get_json()
    ids1 = [item["id"] for item in body1["data"]]
    next_cursor = body1["pagination"]["next_cursor"]
    assert next_cursor is not None

    # Trang 2 với cursor
    res2 = client.get(f"/api/v1/books?strategy=cursor&limit=5&sort=-id&cursor={next_cursor}")
    assert res2.status_code == 200
    body2 = res2.get_json()
    ids2 = [item["id"] for item in body2["data"]]

    # Đảm bảo không có bản ghi nào bị lặp
    assert set(ids1).isdisjoint(set(ids2))


# --- 3. FILTERING TESTS ---

def test_filter_by_genre_tech(client):
    """Kiểm tra filter theo thể loại tech (?genre=tech)"""
    res = client.get("/api/v1/books?genre=tech&strategy=offset")
    assert res.status_code == 200
    body = res.get_json()
    assert body["pagination"]["total"] == 9
    for book in body["data"]:
        assert book["genre"] == "tech"


def test_filter_by_genre_fiction(client):
    """Kiểm tra filter theo thể loại fiction (?genre=fiction)"""
    res = client.get("/api/v1/books?genre=fiction&strategy=offset")
    assert res.status_code == 200
    body = res.get_json()
    assert body["pagination"]["total"] == 4
    for book in body["data"]:
        assert book["genre"] == "fiction"


def test_filter_by_price_range(client):
    """Kiểm tra filter theo khoảng giá ?price_min=...&price_max=..."""
    res = client.get("/api/v1/books?price_min=200000&price_max=300000&strategy=offset")
    assert res.status_code == 200
    body = res.get_json()
    for book in body["data"]:
        assert 200000 <= book["price"]["amount"] <= 300000


def test_filter_in_stock(client):
    """Kiểm tra filter sách còn hàng ?in_stock=true"""
    res = client.get("/api/v1/books?in_stock=true&strategy=offset")
    assert res.status_code == 200
    body = res.get_json()
    for book in body["data"]:
        assert book["inStock"] is True
        assert book["stock"] > 0


# --- 4. SORTING TESTS ---

def test_sort_single_key_asc_desc(client):
    """Kiểm tra sort đơn khóa: tăng dần và giảm dần theo giá"""
    # Tăng dần
    res_asc = client.get("/api/v1/books?sort=price&limit=10&strategy=offset")
    body_asc = res_asc.get_json()
    prices_asc = [b["price"]["amount"] for b in body_asc["data"]]
    assert prices_asc == sorted(prices_asc)

    # Giảm dần
    res_desc = client.get("/api/v1/books?sort=-price&limit=10&strategy=offset")
    body_desc = res_desc.get_json()
    prices_desc = [b["price"]["amount"] for b in body_desc["data"]]
    assert prices_desc == sorted(prices_desc, reverse=True)


def test_sort_multi_key(client):
    """Kiểm tra sắp xếp đa khóa ?sort=-price,title"""
    res = client.get("/api/v1/books?sort=-price,title&limit=25&strategy=offset")
    assert res.status_code == 200
    body = res.get_json()
    books = body["data"]

    for i in range(len(books) - 1):
        b1 = books[i]
        b2 = books[i + 1]
        p1 = b1["price"]["amount"]
        p2 = b2["price"]["amount"]
        if p1 == p2:
            # Nếu cùng giá thì title phải sắp xếp tăng dần theo chữ cái
            assert b1["title"] <= b2["title"]
        else:
            assert p1 > p2


def test_cursor_with_multi_key_and_duplicate_prices(client):
    """Kiểm tra cursor pagination hoạt động chính xác với sort multi-key và giá trùng nhau (tie-break = id)"""
    # Lấy toàn bộ sách bằng cursor từng trang 5 cuốn với sort=-price,title
    collected = []
    cursor = None
    while True:
        url = "/api/v1/books?strategy=cursor&limit=5&sort=-price,title"
        if cursor:
            url += f"&cursor={cursor}"
        res = client.get(url)
        assert res.status_code == 200
        body = res.get_json()
        items = body["data"]
        collected.extend(items)
        if not body["pagination"]["has_more"]:
            break
        cursor = body["pagination"]["next_cursor"]

    assert len(collected) == 25
    collected_ids = [b["id"] for b in collected]
    # Toàn bộ 25 id đều độc nhất, không bỏ sót cuốn nào và không bị trùng lặp
    assert len(set(collected_ids)) == 25


# --- 5. ERROR HANDLING & VALIDATION ---

def test_bad_sort_returns_400(client):
    """Sort không nằm trong whitelist phải trả về 400 Bad Request"""
    res = client.get("/api/v1/books?sort=invalid_col")
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"] == "bad_sort"


def test_cursor_sort_changed_returns_400(client):
    """Cursor sort bị đổi giữa chừng phải trả về 400 sort_chg theo Slide 24"""
    # Tạo cursor từ sort=-id
    res1 = client.get("/api/v1/books?strategy=cursor&limit=2&sort=-id")
    c = res1.get_json()["pagination"]["next_cursor"]

    # Gửi cursor kèm sort khác (-price)
    res2 = client.get(f"/api/v1/books?strategy=cursor&limit=2&sort=-price&cursor={c}")
    assert res2.status_code == 400
    body = res2.get_json()
    assert body["error"] == "sort_chg"


def test_bad_cursor_returns_400(client):
    """Cursor rác phải trả về 400 bad_cursor"""
    res = client.get("/api/v1/books?strategy=cursor&cursor=not_a_valid_base64_json")
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"] == "bad_cursor"


def test_bad_strategy_returns_400(client):
    """Strategy không hợp lệ trả về 400 bad_strategy"""
    res = client.get("/api/v1/books?strategy=invalid_strat")
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"] == "bad_strategy"


# --- 6. FIELD SELECTION & JSON SCHEMA VALIDATION ---

def test_field_selection(client):
    """Kiểm tra sparse fieldsets ?fields=id,title,price"""
    res = client.get("/api/v1/books?fields=id,title,price&limit=2")
    assert res.status_code == 200
    body = res.get_json()
    item = body["data"][0]
    assert "id" in item
    assert "title" in item
    assert "price" in item
    assert "isbn" not in item
    assert "createdAt" not in item


def test_post_book_schema_validation_success(client):
    """POST /books tạo thành công với JSON Schema hợp lệ trả về 201 Created"""
    payload = {
        "title": "Designing Data-Intensive Applications",
        "isbn": "9781449373320",
        "price": {
            "amount": 650000,
            "currency": "VND"
        },
        "stock": 25,
        "genre": "tech"
    }
    res = client.post("/api/v1/books", json=payload)
    assert res.status_code == 201
    assert "Location" in res.headers
    body = res.get_json()
    assert body["title"] == payload["title"]
    assert body["price"]["amount"] == 650000


def test_post_book_schema_validation_failure(client):
    """POST /books thiếu trường bắt buộc (price) trả về 400 validation_failed"""
    payload = {
        "title": "Incomplete Book"
    }
    res = client.post("/api/v1/books", json=payload)
    assert res.status_code == 400
    body = res.get_json()
    assert body["error"] == "validation_failed"


# --- 7. NESTED SUB-RESOURCE AUTHOR TESTS ---

def test_book_authors_nested_lifecycle(client):
    """Kiểm tra CRUD quan hệ N:M Book-Author dạng sub-resource theo Slide 11"""
    # 1. GET authors của sách 1
    res1 = client.get("/api/v1/books/1/authors")
    assert res1.status_code == 200
    assert len(res1.get_json()) > 0

    # 2. POST thêm tác giả mới vào sách 1
    res2 = client.post("/api/v1/books/1/authors", json={"author_id": 2, "role": "co"})
    assert res2.status_code in (200, 201)

    # 3. DELETE gỡ tác giả khỏi sách 1
    res3 = client.delete("/api/v1/books/1/authors/2")
    assert res3.status_code == 204
