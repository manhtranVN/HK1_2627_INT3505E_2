import app as app_module


def test_healthz():
    client = app_module.app.test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"