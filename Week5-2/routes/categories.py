from flask import Blueprint, request, jsonify
from sqlalchemy import select
from models import db, Category

bp = Blueprint("categories", __name__)

@bp.get("")
def list_categories():
    cats = db.session.scalars(select(Category).order_by(Category.id.asc())).all()
    return jsonify([c.to_dict() for c in cats]), 200

@bp.post("")
def create_category():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("slug"):
        return jsonify({"error": "bad_request", "message": "name và slug là bắt buộc"}), 400

    existing = db.session.scalar(select(Category).where(Category.slug == data["slug"].lower()))
    if existing:
        return jsonify({"error": "conflict", "message": f"Thể loại slug '{data['slug']}' đã tồn tại"}), 409

    cat = Category(name=data["name"], slug=data["slug"].lower())
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201

@bp.get("/<int:cat_id>")
def get_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        return jsonify({"error": "not_found", "message": f"Không tìm thấy thể loại ID {cat_id}"}), 404
    return jsonify(cat.to_dict()), 200
