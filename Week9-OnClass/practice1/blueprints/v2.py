from flask import Blueprint, request

from .users_data import add_user, get_user

bp = Blueprint("v2", __name__)


@bp.route("/<int:uid>")
def get(uid):
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {
        "id": uid,
        "first_name": u["first_name"],
        "last_name": u["last_name"],
        "email": u["email"],
    }


@bp.route("", methods=["POST"])
def create():
    data = request.get_json(silent=True) or {}
    missing = [f for f in ("first_name", "last_name", "email") if not data.get(f)]
    if missing:
        return {"error": "missing_fields", "fields": missing}, 400
    uid = add_user(data["first_name"], data["last_name"], data["email"])
    return {
        "id": uid,
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "email": data["email"],
    }, 201