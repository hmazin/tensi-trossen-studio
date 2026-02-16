"""Shared fixtures for backend tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import AppConfig, RobotConfig, DatasetConfig, TrainConfig, ReplayConfig


@pytest.fixture()
def tmp_config_path(tmp_path: Path):
    """Patch get_config_path() to use a temp directory."""
    config_file = tmp_path / "config.json"
    with patch("app.config.get_config_path", return_value=config_file):
        yield config_file


@pytest.fixture()
def sample_config() -> AppConfig:
    """Return a fully-populated AppConfig with known test values."""
    return AppConfig(
        robot=RobotConfig(
            leader_ip="10.0.0.1",
            follower_ip="10.0.0.2",
            use_top_camera_only=False,
            cameras={
                "wrist": {
                    "type": "intelrealsense",
                    "serial_number_or_name": "WRIST_SERIAL",
                    "width": 640,
                    "height": 480,
                    "fps": 30,
                },
                "top": {
                    "type": "intelrealsense",
                    "serial_number_or_name": "TOP_SERIAL",
                    "width": 640,
                    "height": 480,
                    "fps": 30,
                },
            },
            remote_leader=False,
            remote_leader_host="10.0.0.99",
            remote_leader_port=7777,
        ),
        dataset=DatasetConfig(
            repo_id="test/dataset",
            num_episodes=5,
            episode_time_s=30,
            reset_time_s=10,
            single_task="Pick up the block",
            push_to_hub=False,
        ),
        train=TrainConfig(
            dataset_repo_id="test/dataset",
            policy_type="act",
            output_dir="outputs/test",
            job_name="test_job",
            policy_repo_id="test/policy",
        ),
        replay=ReplayConfig(repo_id="test/dataset", episode=3),
        lerobot_trossen_path="/tmp/fake_lerobot",
    )


@pytest.fixture()
def sample_remote_config(sample_config: AppConfig) -> AppConfig:
    """Same as sample_config but with remote_leader enabled."""
    cfg = sample_config.model_copy(deep=True)
    cfg.robot.remote_leader = True
    return cfg


@pytest.fixture(autouse=True)
def reset_process_manager_singleton():
    """Reset the ProcessManager singleton between tests to avoid state leaks."""
    from app.services.process_manager import ProcessManager

    ProcessManager._instance = None
    yield
    ProcessManager._instance = None


@pytest.fixture()
def mock_popen():
    """Provide a mocked subprocess.Popen that captures the command without spawning."""
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    mock_proc.poll.return_value = None
    mock_proc.stdout = MagicMock()
    mock_proc.stdout.readline.return_value = ""
    mock_proc.wait.return_value = 0

    with patch("app.services.process_manager.subprocess.Popen", return_value=mock_proc) as popen_cls:
        popen_cls._mock_proc = mock_proc
        yield popen_cls
