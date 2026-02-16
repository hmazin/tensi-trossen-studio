"""Integration tests using FastAPI TestClient — full request/response cycles."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig
from app.services.process_manager import ProcessManager, ProcessMode, ProcessStatus


@pytest.fixture()
def client(tmp_config_path, sample_config):
    """TestClient with patched config path and mocked singletons."""
    from app.config import save_config

    save_config(sample_config)

    with (
        patch("app.services.camera_manager.CameraManager.get_instance") as mock_cam,
        patch("app.routes.process_routes.CameraManager") as mock_cam_routes,
    ):
        mock_cam_inst = MagicMock()
        mock_cam.return_value = mock_cam_inst
        mock_cam_routes.get_instance.return_value = mock_cam_inst
        mock_cam_inst.cameras = {}
        mock_cam_inst.get_camera_status.return_value = {"status": "not_initialized"}

        from app.main import app

        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    """GET /health returns ok."""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestConfigEndpoints:
    """GET/POST /api/config round-trips configuration."""

    def test_get_config(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "robot" in data
        assert "dataset" in data
        assert data["robot"]["leader_ip"] == "10.0.0.1"

    def test_post_config_saves(self, client):
        resp = client.get("/api/config")
        cfg = resp.json()
        cfg["robot"]["leader_ip"] = "99.99.99.99"
        resp2 = client.post("/api/config", json=cfg)
        assert resp2.status_code == 200
        assert resp2.json()["config"]["robot"]["leader_ip"] == "99.99.99.99"

        resp3 = client.get("/api/config")
        assert resp3.json()["robot"]["leader_ip"] == "99.99.99.99"

    def test_post_invalid_config(self, client):
        resp = client.post("/api/config", json={"robot": {"cameras": "not_a_dict"}})
        assert resp.status_code == 400


class TestProcessEndpoints:
    """Process control endpoints with mocked ProcessManager."""

    def test_process_status_idle(self, client):
        resp = client.get("/api/process/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "idle"
        assert data["running"] is False

    @patch("app.routes.process_routes.ProcessManager")
    def test_teleoperate_start(self, MockPM, client):
        mock_pm = MagicMock()
        MockPM.return_value = mock_pm

        resp = client.post("/api/teleoperate/start?display_data=true")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"
        assert resp.json()["mode"] == "teleoperate"

    @patch("app.routes.process_routes.ProcessManager")
    def test_process_stop(self, MockPM, client):
        mock_pm = MagicMock()
        MockPM.return_value = mock_pm

        resp = client.post("/api/process/stop")
        assert resp.status_code == 200
        assert resp.json()["status"] == "stopped"
        mock_pm.stop.assert_called_once()

    @patch("app.routes.process_routes.ProcessManager")
    def test_record_start(self, MockPM, client):
        mock_pm = MagicMock()
        MockPM.return_value = mock_pm

        resp = client.post("/api/record/start?repo_id=test/data&num_episodes=3")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "record"

    @patch("app.routes.process_routes.ProcessManager")
    def test_train_start(self, MockPM, client):
        mock_pm = MagicMock()
        MockPM.return_value = mock_pm

        resp = client.post("/api/train/start?dataset_repo_id=test/data")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "train"

    @patch("app.routes.process_routes.ProcessManager")
    def test_replay_start(self, MockPM, client):
        mock_pm = MagicMock()
        MockPM.return_value = mock_pm

        resp = client.post("/api/replay/start?repo_id=test/data&episode=5")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "replay"


class TestCameraEndpoints:
    """Camera endpoints with mocked CameraManager."""

    def test_camera_status(self, client):
        resp = client.get("/api/cameras/status")
        assert resp.status_code == 200
        assert "cameras" in resp.json()

    def test_camera_shutdown(self, client):
        resp = client.post("/api/cameras/shutdown")
        assert resp.status_code == 200
        assert resp.json()["status"] == "shutdown"
