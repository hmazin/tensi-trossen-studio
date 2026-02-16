"""Tests for app.routes.leader_service_routes — SSH command logic."""

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest


def _patch_config():
    """Return a patch for load_config that provides known remote leader settings."""
    from app.config import AppConfig, RobotConfig

    cfg = AppConfig(
        robot=RobotConfig(
            remote_leader=True,
            remote_leader_host="10.0.0.99",
            remote_leader_port=7777,
            leader_ip="10.0.0.1",
        )
    )
    return patch("app.routes.leader_service_routes.load_config", return_value=cfg)


class TestSshRun:
    """_ssh_run() constructs SSH commands and handles errors."""

    def test_success(self):
        from app.routes.leader_service_routes import _ssh_run

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output line\n"
        mock_result.stderr = ""

        with patch("app.routes.leader_service_routes.subprocess.run", return_value=mock_result) as mock_run:
            code, output = _ssh_run("user", "10.0.0.99", "echo hello")

        assert code == 0
        assert output == "output line"
        args = mock_run.call_args[0][0]
        assert "ssh" in args
        assert "user@10.0.0.99" in args
        assert "echo hello" in args

    def test_timeout(self):
        from app.routes.leader_service_routes import _ssh_run

        with patch(
            "app.routes.leader_service_routes.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=10),
        ):
            code, output = _ssh_run("user", "host", "cmd")

        assert code == -1
        assert "timed out" in output.lower()

    def test_exception(self):
        from app.routes.leader_service_routes import _ssh_run

        with patch(
            "app.routes.leader_service_routes.subprocess.run",
            side_effect=OSError("Connection refused"),
        ):
            code, output = _ssh_run("user", "host", "cmd")

        assert code == -1
        assert "Connection refused" in output


class TestGetLeaderServiceStatus:
    """get_leader_service_status() returns running/stopped based on SSH checks."""

    def test_running_via_ps(self):
        from app.routes.leader_service_routes import get_leader_service_status

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
        ):
            mock_ssh.return_value = (0, "hadi  12345  ... python3 leader_service.py")
            result = get_leader_service_status()

        assert result["status"] == "running"
        assert result["host"] == "10.0.0.99"
        assert result["port"] == 7777

    def test_stopped(self):
        from app.routes.leader_service_routes import get_leader_service_status

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
        ):
            mock_ssh.side_effect = [
                (1, ""),
                (1, ""),
            ]
            result = get_leader_service_status()

        assert result["status"] == "stopped"

    def test_running_via_ss_fallback(self):
        from app.routes.leader_service_routes import get_leader_service_status

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
        ):
            mock_ssh.side_effect = [
                (1, ""),
                (0, "LISTEN 0 128 *:7777"),
            ]
            result = get_leader_service_status()

        assert result["status"] == "running"


class TestStartLeaderService:
    """start_leader_service() handles already-running, unreachable, and success."""

    def test_already_running(self):
        from app.routes.leader_service_routes import start_leader_service

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
        ):
            mock_ssh.return_value = (0, "hadi 12345 python3 leader_service.py")
            result = start_leader_service()

        assert result["status"] == "already_running"

    def test_robot_unreachable(self):
        from app.routes.leader_service_routes import start_leader_service

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
        ):
            mock_ssh.side_effect = [
                (1, ""),
                (1, "packet loss"),
            ]
            result = start_leader_service()

        assert result["status"] == "error"
        assert "Cannot reach leader robot" in result["message"]

    def test_successful_start(self):
        from app.routes.leader_service_routes import start_leader_service

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
            patch("app.routes.leader_service_routes.time.sleep"),
        ):
            mock_ssh.side_effect = [
                (1, ""),
                (0, ""),
                (0, "99999"),
                (0, "hadi 99999 python3 leader_service.py"),
            ]
            result = start_leader_service()

        assert result["status"] == "started"
        assert result["pid"] == "99999"


class TestStopLeaderService:
    """stop_leader_service() kills PIDs and verifies."""

    def test_not_running(self):
        from app.routes.leader_service_routes import stop_leader_service

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
        ):
            mock_ssh.return_value = (1, "")
            result = stop_leader_service()

        assert result["status"] == "not_running"

    def test_stopped_successfully(self):
        from app.routes.leader_service_routes import stop_leader_service

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
            patch("app.routes.leader_service_routes.time.sleep"),
        ):
            mock_ssh.side_effect = [
                (0, "12345"),
                (0, ""),
                (1, ""),
            ]
            result = stop_leader_service()

        assert result["status"] == "stopped"

    def test_force_killed(self):
        from app.routes.leader_service_routes import stop_leader_service

        with (
            _patch_config(),
            patch("app.routes.leader_service_routes._ssh_run") as mock_ssh,
            patch("app.routes.leader_service_routes.time.sleep"),
        ):
            mock_ssh.side_effect = [
                (0, "12345"),
                (0, ""),
                (0, "hadi 12345 python3 leader_service.py"),
                (0, ""),
            ]
            result = stop_leader_service()

        assert result["status"] == "force_killed"
