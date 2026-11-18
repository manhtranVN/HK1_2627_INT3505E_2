from flask import Blueprint

from .users_data import get_user

bp = Blueprint("v1", __name__)

SUNSET = "Thu, 31 Dec 2026 00:00:00 GMT"


@bp.route("/<int:uid>")
def get(uid):
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {
        "id": uid,
        "full_name": f"{u['first_name']} {u['last_name']}",
        "email": u["email"],
    }


@bp.after_request
def mark_deprecated(resp):
    resp.headers["Sunset"] = SUNSET
    resp.headers["Deprecation"] = "true"
    resp.headers["Link"] = '</api/v2/users>; rel="successor-version"'
    return resp