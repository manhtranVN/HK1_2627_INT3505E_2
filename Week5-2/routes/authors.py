from flask import Blueprint, request, jsonify
from sqlalchemy import select
from models import db, Author, Book, BookAuthor

bp = Blueprint("authors", __name__)

@bp.get("")
def list_authors():
    authors = db.session.scalars(select(Author).order_by(Author.id.asc())).all()
    return jsonify([a.to_dict() for a in authors]), 200

@bp.post("")
def create_author():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "bad_request", "message": "name là bắt buộc"}), 400

    author = Author(name=data["name"], bio=data.get("bio"))
    db.session.add(author)
    db.session.commit()
    return jsonify(author.to_dict()), 201

@bp.get("/<int:author_id>")
def get_author(author_id):
    author = db.session.get(Author, author_id)
    if not author:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy tác giả ID {author_id}"}), 404
    return jsonify(author.to_dict()), 200

@bp.get("/<int:author_id>/books")
def list_author_books(author_id):
    author = db.session.get(Author, author_id)
    if not author:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy tác giả ID {author_id}"}), 404

    books = (
        db.session.query(Book)
        .join(BookAuthor, Book.id == BookAuthor.book_id)
        .filter(BookAuthor.author_id == author_id)
        .all()
    )
    return jsonify([b.to_dict() for b in books]), 200
