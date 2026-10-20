import os
import json
import base64
from flask import Blueprint, request, jsonify
from sqlalchemy import select, func, and_, or_
from jsonschema import validate, ValidationError

from models import db, Book, Author, Category, BookAuthor, Review

bp = Blueprint("books", __name__)

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas", "book.json")
try:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        BOOK_SCHEMA = json.load(f)
except Exception:
    BOOK_SCHEMA = {}

ALLOWED_SORT_FIELDS = {
    "id": Book.id,
    "price": Book.price_vnd,
    "price_vnd": Book.price_vnd,
    "title": Book.title,
    "stock": Book.stock,
    "created_at": Book.created_at,
}

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def parse_sort(raw_sort: str):
    if not raw_sort:
        raw_sort = "-id"

    sort_specs = []
    has_id = False

    parts = [p.strip() for p in raw_sort.split(",") if p.strip()]
    if not parts:
        parts = ["-id"]

    for s in parts:
        desc = s.startswith("-")
        col_name = s.lstrip("-")

        if col_name not in ALLOWED_SORT_FIELDS:
            return None, None, f"Trường sắp xếp không hợp lệ: '{col_name}'. Cho phép: {list(ALLOWED_SORT_FIELDS.keys())}", 400

        col = ALLOWED_SORT_FIELDS[col_name]
        sort_specs.append((col_name, col, desc))
        if col_name == "id":
            has_id = True

    if not has_id:
        last_desc = sort_specs[-1][2] if sort_specs else True
        sort_specs.append(("id", Book.id, last_desc))

    order_by_cols = [
        col.desc() if desc else col.asc()
        for name, col, desc in sort_specs
    ]
    return sort_specs, order_by_cols, None, 200


def _enc(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode("utf-8")).decode("utf-8").rstrip("=")


def _dec(raw_cursor: str) -> dict:
    pad = "=" * (-len(raw_cursor) % 4)
    return json.loads(base64.urlsafe_b64decode(raw_cursor + pad).decode("utf-8"))


def apply_cursor(q, raw_cursor: str, sort_param: str, sort_specs: list):
    if not raw_cursor:
        return q, None, 200

    try:
        c = _dec(raw_cursor)
    except Exception:
        return None, {"error": "bad_cursor", "message": "Cursor không đúng định dạng base64 hợp lệ"}, 400

    if c.get("s") != sort_param:
        return None, {
            "error": "sort_chg",
            "message": f"Cursor có kiểu sort '{c.get('s')}' không khớp với query sort hiện tại '{sort_param}'"
        }, 400

    vals = c.get("v")
    if not isinstance(vals, list) or len(vals) != len(sort_specs):
        return None, {
            "error": "bad_cursor",
            "message": "Dữ liệu cursor không khớp với các tiêu chí sắp xếp"
        }, 400

    conditions = []
    for i in range(len(sort_specs)):
        prefix = [sort_specs[j][1] == vals[j] for j in range(i)]
        name_i, col_i, desc_i = sort_specs[i]
        op_cond = (col_i < vals[i]) if desc_i else (col_i > vals[i])
        conditions.append(and_(*prefix, op_cond))

    if conditions:
        q = q.filter(or_(*conditions))

    return q, None, 200


def build_cursor_response(items: list, limit: int, sort_param: str, sort_specs: list, has_more: bool, fields=None):
    next_cursor = None
    if items and has_more:
        last = items[-1]
        vals = []
        for name, col, desc in sort_specs:
            if name == "id":
                vals.append(last.id)
            elif name in ("price", "price_vnd"):
                vals.append(last.price_vnd)
            elif name == "title":
                vals.append(last.title)
            elif name == "stock":
                vals.append(last.stock)
            elif name == "created_at":
                vals.append(last.created_at.isoformat() if last.created_at else None)
            else:
                vals.append(getattr(last, col.key, None))

        next_cursor = _enc({
            "s": sort_param,
            "v": vals
        })

    return jsonify({
        "data": [b.to_dict(fields=fields) for b in items],
        "pagination": {
            "strategy": "cursor",
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more
        }
    })


def build_offset_response(items: list, offset: int, limit: int, total: int, fields=None):
    page_num = (offset // limit) + 1 if limit else 1
    total_pages = (total + limit - 1) // limit if limit and total > 0 else 1

    return jsonify({
        "data": [b.to_dict(fields=fields) for b in items],
        "pagination": {
            "strategy": "offset",
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_next": (offset + limit) < total,
            "has_prev": offset > 0,
            "page": page_num,
            "total_pages": total_pages
        }
    })


@bp.get("")
def list_books():
    strategy = request.args.get("strategy")
    sort_raw = request.args.get("sort", "-id")
    limit_raw = request.args.get("limit", DEFAULT_LIMIT, type=int)
    limit = min(max(1, limit_raw if limit_raw is not None else DEFAULT_LIMIT), MAX_LIMIT)
    fields = request.args.get("fields")

    if strategy is None:
        if "offset" in request.args or "page" in request.args:
            strategy = "offset"
        else:
            strategy = "cursor"

    if strategy not in ("offset", "cursor"):
        return jsonify({
            "error": "bad_strategy",
            "message": f"Chiến lược '{strategy}' không hợp lệ. Chỉ chấp nhận 'offset' hoặc 'cursor'."
        }), 400

    sort_specs, order_by_cols, sort_err, sort_code = parse_sort(sort_raw)
    if sort_err:
        return jsonify({"error": "bad_sort", "message": sort_err}), sort_code

    q = select(Book)

    genre_param = request.args.get("genre")
    category_param = request.args.get("category")

    if genre_param or category_param:
        target = (genre_param or category_param).strip()
        q = q.join(Category, Book.category_id == Category.id)
        if target.isdigit():
            q = q.filter(Book.category_id == int(target))
        else:
            q = q.filter(or_(
                Category.slug == target.lower(),
                Category.name.ilike(f"%{target}%")
            ))

    price_min = request.args.get("price_min", type=int)
    price_max = request.args.get("price_max", type=int)
    if price_min is not None:
        q = q.filter(Book.price_vnd >= price_min)
    if price_max is not None:
        q = q.filter(Book.price_vnd <= price_max)

    in_stock = request.args.get("in_stock")
    if in_stock is not None:
        if in_stock.lower() in ("true", "1", "yes"):
            q = q.filter(Book.stock > 0)
        elif in_stock.lower() in ("false", "0", "no"):
            q = q.filter(Book.stock == 0)

    if strategy == "offset":
        offset = request.args.get("offset", type=int)
        page = request.args.get("page", type=int)
        if offset is None:
            if page is not None and page >= 1:
                offset = (page - 1) * limit
            else:
                offset = 0
        offset = max(0, offset)

        count_q = select(func.count(Book.id))
        if genre_param or category_param:
            target = (genre_param or category_param).strip()
            count_q = count_q.join(Category, Book.category_id == Category.id)
            if target.isdigit():
                count_q = count_q.filter(Book.category_id == int(target))
            else:
                count_q = count_q.filter(or_(
                    Category.slug == target.lower(),
                    Category.name.ilike(f"%{target}%")
                ))
        if price_min is not None:
            count_q = count_q.filter(Book.price_vnd >= price_min)
        if price_max is not None:
            count_q = count_q.filter(Book.price_vnd <= price_max)
        if in_stock is not None:
            if in_stock.lower() in ("true", "1", "yes"):
                count_q = count_q.filter(Book.stock > 0)
            elif in_stock.lower() in ("false", "0", "no"):
                count_q = count_q.filter(Book.stock == 0)

        total = db.session.scalar(count_q) or 0

        q = q.order_by(*order_by_cols).offset(offset).limit(limit)
        rows = db.session.scalars(q).unique().all()
        return build_offset_response(rows, offset, limit, total, fields=fields)

    else:
        cursor_param = request.args.get("cursor")
        q = q.order_by(*order_by_cols)

        q, cursor_err, cursor_code = apply_cursor(q, cursor_param, sort_raw, sort_specs)
        if cursor_err:
            return jsonify(cursor_err), cursor_code

        rows = db.session.scalars(q.limit(limit + 1)).unique().all()
        has_more = len(rows) > limit
        items = rows[:limit]

        return build_cursor_response(items, limit, sort_raw, sort_specs, has_more, fields=fields)


@bp.post("")
def create_book():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "validation_failed", "message": "Body phải là định dạng JSON hợp lệ"}), 400

    if BOOK_SCHEMA:
        try:
            validate(payload, BOOK_SCHEMA)
        except ValidationError as e:
            return jsonify({
                "error": "validation_failed",
                "field": list(e.path),
                "message": e.message
            }), 400

    if payload.get("isbn"):
        existing = db.session.scalar(select(Book).where(Book.isbn == payload["isbn"]))
        if existing:
            return jsonify({
                "error": "conflict",
                "message": f"Cuốn sách với ISBN {payload['isbn']} đã tồn tại"
            }), 409

    cat_id = payload.get("category_id")
    if not cat_id and payload.get("genre"):
        cat = db.session.scalar(select(Category).where(Category.slug == payload["genre"].lower()))
        if cat:
            cat_id = cat.id

    payload["category_id"] = cat_id
    book = Book.from_payload(payload)
    db.session.add(book)
    db.session.flush()

    if "authors" in payload and isinstance(payload["authors"], list):
        for item in payload["authors"]:
            aid = item.get("author_id")
            role = item.get("role", "co")
            if aid:
                author_obj = db.session.get(Author, aid)
                if author_obj:
                    ba = BookAuthor(book_id=book.id, author_id=aid, role=role)
                    db.session.add(ba)

    db.session.commit()
    res = jsonify(book.to_dict())
    res.status_code = 201
    res.headers["Location"] = f"/api/v1/books/{book.id}"
    return res


@bp.get("/<int:book_id>")
def get_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy sách với ID {book_id}"}), 404
    fields = request.args.get("fields")
    return jsonify(book.to_dict(fields=fields)), 200


@bp.put("/<int:book_id>")
def update_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy sách với ID {book_id}"}), 404

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "bad_request", "message": "Body JSON không được để trống"}), 400

    if BOOK_SCHEMA:
        try:
            validate(payload, BOOK_SCHEMA)
        except ValidationError as e:
            return jsonify({
                "error": "validation_failed",
                "field": list(e.path),
                "message": e.message
            }), 400

    book.title = payload["title"]
    book.isbn = payload.get("isbn")
    if isinstance(payload.get("price"), dict):
        book.price_vnd = payload["price"].get("amount", book.price_vnd)
    elif "price_vnd" in payload:
        book.price_vnd = payload["price_vnd"]

    book.stock = payload.get("stock", book.stock)
    book.category_id = payload.get("category_id", book.category_id)

    db.session.commit()
    return jsonify(book.to_dict()), 200


@bp.patch("/<int:book_id>")
def patch_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy sách với ID {book_id}"}), 404

    payload = request.get_json(silent=True) or {}
    if "title" in payload:
        book.title = payload["title"]
    if "isbn" in payload:
        book.isbn = payload["isbn"]
    if "stock" in payload:
        book.stock = payload["stock"]
    if "category_id" in payload:
        book.category_id = payload["category_id"]
    if "price" in payload:
        if isinstance(payload["price"], dict):
            book.price_vnd = payload["price"].get("amount", book.price_vnd)
        else:
            book.price_vnd = int(payload["price"])
    elif "price_vnd" in payload:
        book.price_vnd = int(payload["price_vnd"])

    db.session.commit()
    return jsonify(book.to_dict()), 200


@bp.delete("/<int:book_id>")
def delete_book(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy sách với ID {book_id}"}), 404
    db.session.delete(book)
    db.session.commit()
    return "", 204


@bp.get("/<int:book_id>/authors")
def list_book_authors(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy sách với ID {book_id}"}), 404

    rows = (
        db.session.query(Author, BookAuthor.role)
        .join(Author, Author.id == BookAuthor.author_id)
        .filter(BookAuthor.book_id == book_id)
        .all()
    )
    return jsonify([
        {"id": a.id, "name": a.name, "role": r, "bio": a.bio}
        for a, r in rows
    ]), 200


@bp.post("/<int:book_id>/authors")
def add_book_author(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy sách với ID {book_id}"}), 404

    payload = request.get_json(silent=True) or {}
    if "author_id" not in payload:
        return jsonify({"error": "bad_request", "message": "author_id là bắt buộc"}), 400

    author_id = payload["author_id"]
    author = db.session.get(Author, author_id)
    if not author:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy tác giả với ID {author_id}"}), 404

    existing = db.session.get(BookAuthor, (book_id, author_id))
    role = payload.get("role", "co")
    if existing:
        existing.role = role
        db.session.commit()
        return jsonify(existing.to_dict()), 200

    ba = BookAuthor(book_id=book_id, author_id=author_id, role=role)
    db.session.add(ba)
    db.session.commit()
    return jsonify(ba.to_dict()), 201


@bp.delete("/<int:book_id>/authors/<int:author_id>")
def remove_book_author(book_id, author_id):
    ba = db.session.get(BookAuthor, (book_id, author_id))
    if not ba:
        return jsonify({"error": "not_found", "message": "Không tìm thấy quan hệ tác giả - sách này"}), 404

    db.session.delete(ba)
    db.session.commit()
    return "", 204


@bp.get("/<int:book_id>/reviews")
def list_book_reviews(book_id):
    book = db.session.get(Book, book_id)
    if not book:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy sách với ID {book_id}"}), 404

    reviews = db.session.scalars(
        select(Review).where(Review.book_id == book_id).order_by(Review.created_at.desc())
    ).all()
    return jsonify([r.to_dict() for r in reviews]), 200
