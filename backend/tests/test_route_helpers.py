"""Tests for route helper functions in app.routes.process_routes."""

from unittest.mock import patch

import pytest

from app.config import AppConfig
from app.routes.process_routes import _robot_config, _dataset_config, _train_config, _replay_config


class TestRobotConfig:
    """_robot_config() builds the correct dict from AppConfig."""

    def test_local_mode(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _robot_config(use_top_camera_only=False)

        assert result["leader_ip"] == "10.0.0.1"
        assert result["follower_ip"] == "10.0.0.2"
        assert "left_wrist" in result["cameras"]
        assert "right_wrist" in result["cameras"]
        assert "top" in result["cameras"]
        assert "remote_leader" not in result

    def test_remote_mode(self, sample_remote_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_remote_config):
            result = _robot_config(use_top_camera_only=False)

        assert result["remote_leader"] is True
        assert result["remote_leader_host"] == "10.0.0.99"
        assert result["remote_leader_port"] == 7777

    def test_top_camera_only(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _robot_config(use_top_camera_only=True)

        assert list(result["cameras"].keys()) == ["wrist"]
        assert result["cameras"]["wrist"]["serial_number_or_name"] == "TOP_SERIAL"  # top mapped to wrist when use_top_camera_only

    def test_both_cameras(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _robot_config(use_top_camera_only=False)

        assert "left_wrist" in result["cameras"]
        assert "right_wrist" in result["cameras"]
        assert "top" in result["cameras"]
        assert result["cameras"]["left_wrist"]["serial_number_or_name"] == "LEFT_WRIST_SERIAL"
        assert result["cameras"]["right_wrist"]["serial_number_or_name"] == "RIGHT_WRIST_SERIAL"
        assert result["cameras"]["top"]["serial_number_or_name"] == "TOP_SERIAL"

    def test_uses_config_default_for_top_camera_only(self, sample_config):
        sample_config.robot.use_top_camera_only = True
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _robot_config()

        assert list(result["cameras"].keys()) == ["wrist"]

    def test_use_in_teleop_false_excludes_camera(self, sample_config):
        sample_config.robot.cameras["right_wrist"]["use_in_teleop"] = False
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _robot_config(use_top_camera_only=False)

        assert set(result["cameras"].keys()) == {"left_wrist", "top"}
        assert "use_in_teleop" not in result["cameras"]["top"]

    def test_use_in_teleop_false_all_gives_empty_cameras(self, sample_config):
        sample_config.robot.cameras["left_wrist"]["use_in_teleop"] = False
        sample_config.robot.cameras["right_wrist"]["use_in_teleop"] = False
        sample_config.robot.cameras["top"]["use_in_teleop"] = False
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _robot_config(use_top_camera_only=False)

        assert result["cameras"] == {}


class TestDatasetConfig:
    """_dataset_config() returns all dataset fields."""

    def test_returns_all_fields(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _dataset_config()

        assert result["repo_id"] == "test/dataset"
        assert result["num_episodes"] == 5
        assert result["episode_time_s"] == 30
        assert result["reset_time_s"] == 10
        assert result["single_task"] == "Pick up the block"
        assert result["push_to_hub"] is False


class TestTrainConfig:
    """_train_config() returns all train fields."""

    def test_returns_all_fields(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _train_config()

        assert result["dataset_repo_id"] == "test/dataset"
        assert result["policy_type"] == "act"
        assert result["output_dir"] == "outputs/test"
        assert result["job_name"] == "test_job"
        assert result["policy_repo_id"] == "test/policy"


class TestReplayConfig:
    """_replay_config() returns replay fields with optional overrides."""

    def test_defaults_from_config(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _replay_config()

        assert result["repo_id"] == "test/dataset"
        assert result["episode"] == 3

    def test_override_repo_id(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _replay_config(repo_id="other/data")

        assert result["repo_id"] == "other/data"
        assert result["episode"] == 3

    def test_override_episode(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _replay_config(episode=99)

        assert result["repo_id"] == "test/dataset"
        assert result["episode"] == 99

    def test_override_both(self, sample_config):
        with patch("app.routes.process_routes.load_config", return_value=sample_config):
            result = _replay_config(repo_id="a/b", episode=0)

        assert result["repo_id"] == "a/b"
        assert result["episode"] == 0
