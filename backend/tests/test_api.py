"""Smoke tests. Run with the simulated device + synthetic camera, no hardware."""

import os

os.environ.setdefault("HOMERUN_SERIAL_ENABLED", "false")
os.environ.setdefault("HOMERUN_CAMERA_BACKEND", "synthetic")
os.environ.setdefault("HOMERUN_OLLAMA_ENABLED", "false")
os.environ.setdefault("HOMERUN_DB_PATH", "./data/test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_system_status():
    with TestClient(app) as client:
        response = client.get("/api/system")
        assert response.status_code == 200
        body = response.json()
        assert "state" in body
        assert body["camera"]["mode"] == "manual"


def test_climate_roundtrip():
    with TestClient(app) as client:
        response = client.post(
            "/api/climate",
            json={"power": "on", "mode": "cool", "temp": 23, "fan": "2"},
        )
        assert response.status_code == 200
        assert response.json()["temp"] == 23

        current = client.get("/api/climate").json()
        assert current["mode"] == "cool"
        assert current["temp"] == 23


def test_climate_rejects_bad_temp():
    with TestClient(app) as client:
        response = client.post(
            "/api/climate",
            json={"power": "on", "mode": "cool", "temp": 99, "fan": "auto"},
        )
        assert response.status_code in (400, 422)


def test_watering_and_plants():
    with TestClient(app) as client:
        response = client.post("/api/plants/water", json={"seconds": 5})
        assert response.status_code == 200
        assert response.json()["seconds"] == 5

        plants = client.get("/api/plants").json()
        assert plants["zone"] == 1
        assert len(plants["soil"]) == 5


def test_camera_mode_switch():
    with TestClient(app) as client:
        response = client.post("/api/camera/mode", json={"mode": "motion"})
        assert response.status_code == 200
        assert response.json()["mode"] == "motion"


def test_chat_unavailable_without_ollama():
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "hello"})
        assert response.status_code == 503
