from unittest.mock import patch
from sqlalchemy.exc import OperationalError


def test_liveness_probe(client):
    """Test that /healthz returns 200 without checking DB."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.get_json()
    assert data == {"status": "ok"}


def test_readiness_probe_healthy(client):
    """Test that /ready returns 200 when DB is connected."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["checks"]["db"] == "ok"


def test_readiness_probe_degraded_when_db_down(client):
    """Test that /ready returns 503 degraded when DB connection fails."""
    with patch("product_api.api.health.db.session.execute") as mock_exec:
        mock_exec.side_effect = OperationalError("connection refused", {}, None)
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.get_json()
        assert data["status"] == "degraded"
        assert data["checks"]["db"] == "err"
