"""Tests for app.config — Pydantic models and config I/O."""

import json

import pytest
from pydantic import ValidationError

from app.config import (
    AppConfig,
    CameraConfig,
    DatasetConfig,
    ReplayConfig,
    RobotConfig,
    TrainConfig,
    load_config,
    save_config,
)


class TestPydanticDefaults:
    """Pydantic models produce the expected default values."""

    def test_robot_config_defaults(self):
        cfg = RobotConfig()
        assert cfg.leader_ip == "192.168.1.2"
        assert cfg.follower_ip == "192.168.1.5"
        assert cfg.use_top_camera_only is True
        assert cfg.remote_leader is False
        assert cfg.remote_leader_host == "192.168.2.138"
        assert cfg.remote_leader_port == 5555
        assert "wrist" in cfg.cameras
        assert "top" in cfg.cameras

    def test_dataset_config_defaults(self):
        cfg = DatasetConfig()
        assert cfg.repo_id == "tensi/test_dataset"
        assert cfg.num_episodes == 10
        assert cfg.episode_time_s == 45
        assert cfg.reset_time_s == 15
        assert cfg.single_task == "Grab the cube"
        assert cfg.push_to_hub is False

    def test_train_config_defaults(self):
        cfg = TrainConfig()
        assert cfg.dataset_repo_id == "tensi/test_dataset"
        assert cfg.policy_type == "act"
        assert cfg.output_dir == "outputs/train/act_trossen"
        assert cfg.job_name == "act_trossen"
        assert cfg.policy_repo_id == "tensi/my_policy"

    def test_replay_config_defaults(self):
        cfg = ReplayConfig()
        assert cfg.repo_id == "tensi/test_dataset"
        assert cfg.episode == 0

    def test_app_config_defaults(self):
        cfg = AppConfig()
        assert isinstance(cfg.robot, RobotConfig)
        assert isinstance(cfg.dataset, DatasetConfig)
        assert isinstance(cfg.train, TrainConfig)
        assert isinstance(cfg.replay, ReplayConfig)
        assert "lerobot_trossen" in cfg.lerobot_trossen_path


class TestPydanticValidation:
    """Pydantic models reject invalid input."""

    def test_invalid_num_episodes_type(self):
        with pytest.raises(ValidationError):
            DatasetConfig(num_episodes="not_a_number")

    def test_invalid_port_type(self):
        with pytest.raises(ValidationError):
            RobotConfig(remote_leader_port="not_a_port")

    def test_extra_fields_ignored_by_default(self):
        cfg = RobotConfig(leader_ip="1.2.3.4", unknown_field="ignored")
        assert cfg.leader_ip == "1.2.3.4"


class TestRemoteLeaderFields:
    """Remote leader fields propagate correctly."""

    def test_remote_leader_enabled(self):
        cfg = RobotConfig(
            remote_leader=True,
            remote_leader_host="10.0.0.99",
            remote_leader_port=9999,
        )
        assert cfg.remote_leader is True
        assert cfg.remote_leader_host == "10.0.0.99"
        assert cfg.remote_leader_port == 9999

    def test_remote_leader_in_app_config(self):
        cfg = AppConfig(
            robot=RobotConfig(remote_leader=True, remote_leader_host="1.2.3.4")
        )
        assert cfg.robot.remote_leader is True
        assert cfg.robot.remote_leader_host == "1.2.3.4"


class TestLoadConfig:
    """load_config() reads from disk or falls back to defaults."""

    def test_load_no_file_returns_defaults(self, tmp_config_path):
        cfg = load_config()
        assert cfg.robot.leader_ip == "192.168.1.2"
        assert cfg.robot.follower_ip == "192.168.1.5"

    def test_load_valid_json(self, tmp_config_path):
        data = {
            "robot": {"leader_ip": "10.0.0.1", "follower_ip": "10.0.0.2"},
            "dataset": {"repo_id": "myuser/mydata"},
        }
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(json.dumps(data))
        cfg = load_config()
        assert cfg.robot.leader_ip == "10.0.0.1"
        assert cfg.dataset.repo_id == "myuser/mydata"

    def test_load_fills_missing_camera_slots(self, tmp_config_path):
        data = {"robot": {"cameras": {}}}
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text(json.dumps(data))
        cfg = load_config()
        assert "wrist" in cfg.robot.cameras
        assert "top" in cfg.robot.cameras

    def test_load_corrupt_json_falls_back(self, tmp_config_path):
        tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_config_path.write_text("{invalid json!!!")
        cfg = load_config()
        assert cfg.robot.leader_ip == "192.168.1.2"


class TestSaveConfig:
    """save_config() persists to disk and round-trips correctly."""

    def test_save_creates_file(self, tmp_config_path):
        cfg = AppConfig(robot=RobotConfig(leader_ip="99.99.99.99"))
        save_config(cfg)
        assert tmp_config_path.exists()
        data = json.loads(tmp_config_path.read_text())
        assert data["robot"]["leader_ip"] == "99.99.99.99"

    def test_save_load_round_trip(self, tmp_config_path):
        original = AppConfig(
            robot=RobotConfig(leader_ip="1.1.1.1", remote_leader=True),
            dataset=DatasetConfig(repo_id="rt/test", num_episodes=42),
        )
        save_config(original)
        loaded = load_config()
        assert loaded.robot.leader_ip == "1.1.1.1"
        assert loaded.robot.remote_leader is True
        assert loaded.dataset.repo_id == "rt/test"
        assert loaded.dataset.num_episodes == 42
