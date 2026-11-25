from fastapi.testclient import TestClient

from app.main import CORS_ALLOW_ORIGINS, app

client = TestClient(app)

RENDER_FRONTEND_ORIGIN = "https://ecowatt-ai-pnki.onrender.com"


def test_local_and_render_origins_are_allowed() -> None:
    assert "http://localhost:5173" in CORS_ALLOW_ORIGINS
    assert "http://127.0.0.1:5173" in CORS_ALLOW_ORIGINS
    assert RENDER_FRONTEND_ORIGIN in CORS_ALLOW_ORIGINS


def test_render_frontend_can_read_health() -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": RENDER_FRONTEND_ORIGIN},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["access-control-allow-origin"] == RENDER_FRONTEND_ORIGIN


def test_render_frontend_preflight_allows_schedule_post() -> None:
    response = client.options(
        "/api/schedule",
        headers={
            "Origin": RENDER_FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == RENDER_FRONTEND_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


def test_local_vite_origin_remains_allowed() -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": "http://127.0.0.1:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
