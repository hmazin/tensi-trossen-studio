"""Configuration models and persistence for TENSI Trossen Studio."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def get_config_path() -> Path:
    """Return path to persisted config file."""
    return Path.home() / ".tensi_trossen_studio" / "config.json"


class CameraConfig(BaseModel):
    """Single camera configuration."""

    type: str = "intelrealsense"
    serial_number_or_name: str
    width: int = 640
    height: int = 480
    fps: int = 30


class RobotConfig(BaseModel):
    """Robot and teleop configuration."""

    leader_ip: str = Field(description="Leader arm IP address", default="192.168.1.2")
    follower_ip: str = Field(description="Follower arm IP address", default="192.168.1.5")
    use_top_camera_only: bool = Field(
        description="Use only the top camera (bypass wrist camera if it fails)",
        default=True,
    )
    cameras: dict[str, dict[str, Any]] = Field(
        description="Camera config dict, e.g. {wrist: {...}, top: {...}}",
        default_factory=lambda: {
            "wrist": {
                "type": "intelrealsense",
                "serial_number_or_name": "218622275782",
                "width": 640,
                "height": 480,
                "fps": 30,
            },
            "top": {
                "type": "intelrealsense",
                "serial_number_or_name": "218622278263",
                "width": 640,
                "height": 480,
                "fps": 30,
            },
        },
    )
    operator_camera: dict[str, Any] | None = Field(
        description="Optional USB operator (HMI) camera; not used for teleop/recording",
        default=None,
    )
    remote_leader: bool = Field(
        description="Enable remote leader mode: leader runs on a separate PC with leader_service.py",
        default=False,
    )
    remote_leader_host: str = Field(
        description="IP/hostname of the PC running leader_service.py (e.g., PC2's WiFi IP)",
        default="192.168.2.138",
    )
    remote_leader_port: int = Field(
        description="TCP port of the leader service",
        default=5555,
    )
    remote_leader_ssh_user: str = Field(
        description="SSH username for the PC running the leader service",
        default="hadi",
    )
    camera_service_url: str | None = Field(
        description="URL of remote camera service (e.g., http://192.168.1.5:8001) for distributed setup",
        default=None,
    )
    enable_local_cameras: bool = Field(
        description="Whether this instance manages cameras directly (true) or proxies to remote service (false)",
        default=True,
    )
    studio_host_for_remote: str | None = Field(
        description="This PC's WiFi IP (192.168.2.x) for opening Studio from another PC; used in UI for 'Open from other PCs' link",
        default=None,
    )


class DatasetConfig(BaseModel):
    """Dataset recording configuration."""

    repo_id: str = Field(description="Dataset repo ID", default="tensi/test_dataset")
    num_episodes: int = Field(description="Number of episodes", default=10)
    episode_time_s: int = Field(description="Episode duration in seconds", default=45)
    reset_time_s: int = Field(description="Reset phase duration", default=15)
    single_task: str = Field(description="Task description", default="Grab the cube")
    push_to_hub: bool = Field(description="Upload to HuggingFace Hub", default=False)


class TrainConfig(BaseModel):
    """Training configuration."""

    dataset_repo_id: str = Field(description="Dataset repo ID", default="tensi/test_dataset")
    policy_type: str = Field(description="Policy type", default="act")
    output_dir: str = Field(description="Output directory", default="outputs/train/act_trossen")
    job_name: str = Field(description="Job name", default="act_trossen")
    policy_repo_id: str = Field(description="Policy repo ID on Hub", default="tensi/my_policy")


class ReplayConfig(BaseModel):
    """Replay configuration."""

    repo_id: str = Field(description="Dataset repo ID", default="tensi/test_dataset")
    episode: int = Field(description="Episode index to replay", default=0)


class AppConfig(BaseModel):
    """Full application configuration."""

    robot: RobotConfig = Field(default_factory=RobotConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    train: TrainConfig = Field(default_factory=TrainConfig)
    replay: ReplayConfig = Field(default_factory=ReplayConfig)
    lerobot_trossen_path: str = Field(
        description="Path to lerobot_trossen repository",
        default_factory=lambda: str(Path.home() / "lerobot_trossen"),
    )


DEFAULT_CAMERAS = {
    "wrist": {
        "type": "intelrealsense",
        "serial_number_or_name": "218622275782",
        "width": 640,
        "height": 480,
        "fps": 30,
    },
    "top": {
        "type": "intelrealsense",
        "serial_number_or_name": "218622278263",
        "width": 640,
        "height": 480,
        "fps": 30,
    },
}


def load_config() -> AppConfig:
    """Load config from disk, or return defaults if not found."""
    path = get_config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            cfg = AppConfig.model_validate(data)
            # Ensure both wrist and top camera slots exist for Camera Viewer
            cameras = cfg.robot.cameras or {}
            for key in ("wrist", "top"):
                if key not in cameras:
                    cameras = {**cameras, key: DEFAULT_CAMERAS[key].copy()}
            cfg.robot.cameras = cameras
            return cfg
        except Exception:
            pass
    return AppConfig()


def save_config(config: AppConfig) -> None:
    """Save config to disk."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2))
