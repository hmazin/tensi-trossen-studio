"""Tests for app.services.process_manager — CLI arg building, stop logic, singleton."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.process_manager import ProcessManager, ProcessMode, ProcessStatus


class TestProcessModeAndStatus:
    """Pure-logic enums and dataclass."""

    def test_process_mode_values(self):
        assert ProcessMode.IDLE.value == "idle"
        assert ProcessMode.TELEOPERATE.value == "teleoperate"
        assert ProcessMode.RECORD.value == "record"
        assert ProcessMode.TRAIN.value == "train"
        assert ProcessMode.REPLAY.value == "replay"

    def test_process_status_defaults(self):
        s = ProcessStatus()
        assert s.mode == ProcessMode.IDLE
        assert s.running is False
        assert s.pid is None
        assert s.logs == []
        assert s.error is None


class TestSingleton:
    """ProcessManager is a singleton; reset between tests via fixture."""

    def test_singleton_returns_same_instance(self):
        a = ProcessManager()
        b = ProcessManager()
        assert a is b

    def test_set_lerobot_path(self):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/custom/path"))
        assert pm._lerobot_path == Path("/custom/path")


class TestTeleoperateArgs:
    """start_teleoperate() builds the correct CLI command."""

    def test_local_mode_args(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        robot_cfg = {
            "leader_ip": "10.0.0.1",
            "follower_ip": "10.0.0.2",
            "cameras": {"wrist": {"type": "test"}},
        }
        pm.start_teleoperate(robot_cfg, display_data=True)

        cmd = mock_popen.call_args[0][0]
        assert "lerobot-teleoperate" in cmd
        assert "--teleop.type=widowxai_leader_teleop" in cmd
        assert "--teleop.ip_address=10.0.0.1" in cmd
        assert "--robot.ip_address=10.0.0.2" in cmd
        assert "--display_data=true" in cmd

    def test_remote_mode_args(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        robot_cfg = {
            "follower_ip": "10.0.0.2",
            "cameras": {},
            "remote_leader": True,
            "remote_leader_host": "10.0.0.99",
            "remote_leader_port": 7777,
        }
        pm.start_teleoperate(robot_cfg)

        cmd = mock_popen.call_args[0][0]
        assert "--teleop.type=remote_leader_teleop" in cmd
        assert "--teleop.host=10.0.0.99" in cmd
        assert "--teleop.port=7777" in cmd
        assert "--teleop.ip_address" not in " ".join(cmd)

    def test_cameras_serialized_as_json(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        cams = {"top": {"type": "intelrealsense", "serial_number_or_name": "ABC"}}
        pm.start_teleoperate({"follower_ip": "10.0.0.2", "cameras": cams})

        cmd = mock_popen.call_args[0][0]
        cameras_arg = [a for a in cmd if a.startswith("--robot.cameras=")][0]
        parsed = json.loads(cameras_arg.split("=", 1)[1])
        assert parsed == cams


class TestRecordArgs:
    """start_record() builds the correct CLI command with dataset params."""

    def test_record_includes_dataset_params(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        robot_cfg = {"follower_ip": "10.0.0.2", "cameras": {}}
        dataset_cfg = {
            "repo_id": "user/data",
            "num_episodes": 5,
            "episode_time_s": 30,
            "reset_time_s": 10,
            "single_task": "Pick cube",
            "push_to_hub": True,
        }
        pm.start_record(robot_cfg, dataset_cfg)

        cmd = mock_popen.call_args[0][0]
        assert "lerobot-record" in cmd
        assert "--dataset.repo_id=user/data" in cmd
        assert "--dataset.num_episodes=5" in cmd
        assert "--dataset.episode_time_s=30" in cmd
        assert "--dataset.push_to_hub=true" in cmd

    def test_record_remote_mode(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        robot_cfg = {
            "follower_ip": "10.0.0.2",
            "cameras": {},
            "remote_leader": True,
            "remote_leader_host": "10.0.0.99",
            "remote_leader_port": 7777,
        }
        pm.start_record(robot_cfg, {"repo_id": "x/y"})

        cmd = mock_popen.call_args[0][0]
        assert "--teleop.type=remote_leader_teleop" in cmd
        assert "--teleop.host=10.0.0.99" in cmd


class TestTrainArgs:
    """start_train() builds the correct CLI command."""

    def test_train_args(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        pm.start_train({
            "dataset_repo_id": "user/data",
            "policy_type": "diffusion",
            "output_dir": "outputs/test",
            "job_name": "test_job",
            "policy_repo_id": "user/policy",
        })

        cmd = mock_popen.call_args[0][0]
        assert "lerobot-train" in cmd
        assert "--dataset.repo_id=user/data" in cmd
        assert "--policy.type=diffusion" in cmd
        assert "--output_dir=outputs/test" in cmd
        assert "--job_name=test_job" in cmd
        assert "--policy.device=cuda" in cmd


class TestReplayArgs:
    """start_replay() builds the correct CLI command."""

    def test_replay_args(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        robot_cfg = {"follower_ip": "10.0.0.2", "cameras": {}}
        replay_cfg = {"repo_id": "user/data", "episode": 7}
        pm.start_replay(robot_cfg, replay_cfg)

        cmd = mock_popen.call_args[0][0]
        assert "lerobot-replay" in cmd
        assert "--dataset.repo_id=user/data" in cmd
        assert "--dataset.episode=7" in cmd
        assert "--robot.ip_address=10.0.0.2" in cmd


class TestStopLogic:
    """stop() sends SIGTERM and escalates to SIGKILL."""

    def test_stop_calls_terminate(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        pm.start_teleoperate({"follower_ip": "x", "cameras": {}})

        proc = mock_popen._mock_proc
        proc.poll.return_value = None

        pm.stop()
        proc.terminate.assert_called_once()

    def test_stop_escalates_to_kill_on_timeout(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        pm.start_teleoperate({"follower_ip": "x", "cameras": {}})

        proc = mock_popen._mock_proc
        proc.poll.return_value = None
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

        pm.stop()
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()

    def test_stop_on_idle_is_noop(self):
        pm = ProcessManager()
        pm.stop()


class TestGetStatus:
    """get_status() returns current state and log buffer."""

    def test_idle_status(self):
        pm = ProcessManager()
        s = pm.get_status()
        assert s.mode == ProcessMode.IDLE
        assert s.running is False
        assert s.logs == []

    def test_status_with_logs(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        pm.start_teleoperate({"follower_ip": "x", "cameras": {}})
        pm._log_buffer = [f"line_{i}" for i in range(600)]

        s = pm.get_status()
        assert len(s.logs) == 500
        assert s.logs[0] == "line_100"

    def test_start_stops_existing_process(self, mock_popen):
        pm = ProcessManager()
        pm.set_lerobot_path(Path("/tmp/fake"))
        pm.start_teleoperate({"follower_ip": "x", "cameras": {}})

        proc = mock_popen._mock_proc
        proc.poll.return_value = None

        pm.start_teleoperate({"follower_ip": "y", "cameras": {}})
        proc.terminate.assert_called()
