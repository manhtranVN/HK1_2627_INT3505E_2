from flask import Blueprint, jsonify
from sqlalchemy import text
from ..extensions import db

health_bp = Blueprint("health", __name__, url_prefix="")


@health_bp.get("/healthz")
def liveness():
    """Liveness probe: verifies the service process is running without checking dependencies."""
    return jsonify({"status": "ok"}), 200


@health_bp.get("/ready")
def readiness():
    """Readiness probe: verifies backend dependencies (database connection) are operational."""
    checks = {}
    try:
        db.session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = "err"

    ok = all(status == "ok" for status in checks.values())
    return (
        jsonify(
            {
                "status": "ok" if ok else "degraded",
                "checks": checks,
            }
        ),
        200 if ok else 503,
    )

