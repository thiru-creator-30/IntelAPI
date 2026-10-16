from fastapi.testclient import TestClient


def test_live_returns_alive():
    from app.main import app
    c = TestClient(app)
    r = c.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_v1_404_is_structured():
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/nope")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"


def test_me_requires_auth():
    from app.main import app
    c = TestClient(app)
    r = c.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
