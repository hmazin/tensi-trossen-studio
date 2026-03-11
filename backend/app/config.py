"""Configuration models and persistence for TENSI Trossen Studio."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def get_config_path() -> Path:
    """Return path to persisted config file."""
    return Path.home() / ".tensi_trossen_studio" / "config.json"


def get_launcher_config_path() -> Path:
    """Return path to launcher config (shared with launcher.py)."""
    return Path.home() / ".tensi_trossen_studio" / "launcher.json"


def load_launcher_config() -> dict:
    """Load launcher config from launcher.json. Used for Leader Service Host etc."""
    default = {
        "pc1_wifi_ip": "",
        "pc1_ethernet_ip": "",
        "follower_ip": "192.168.1.5",
        "pc2_wifi_ip": "192.168.2.138",
        "pc2_ethernet_ip": "192.168.1.200",
        "leader_ip": "192.168.1.2",
        "pc2_ssh_user": "",
    }
    path = get_launcher_config_path()
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text())
        return {**default, **data}
    except Exception:
        return default


def save_launcher_config(updates: dict) -> None:
    """Merge updates into launcher.json and save."""
    path = get_launcher_config_path()
    current = load_launcher_config()
    current.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2))


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
        description="Camera config dict, e.g. {left_wrist: {...}, right_wrist: {...}, top: {...}}",
        default_factory=lambda: {
            "left_wrist": {
                "type": "intelrealsense",
                "serial_number_or_name": "218622276325",
                "width": 640,
                "height": 480,
                "fps": 30,
            },
            "right_wrist": {
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
    "left_wrist": {
        "type": "intelrealsense",
        "serial_number_or_name": "218622276325",
        "width": 640,
        "height": 480,
        "fps": 30,
    },
    "right_wrist": {
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


def _ensure_camera_slots(cfg: AppConfig) -> AppConfig:
    """Ensure left_wrist, right_wrist, and top camera slots exist for Camera Viewer. Migrate old 'wrist' to right_wrist and drop wrist."""
    cameras = cfg.robot.cameras or {}
    if "wrist" in cameras and "right_wrist" not in cameras:
        cameras = {**cameras, "right_wrist": {**cameras["wrist"]}}
    # Remove legacy "wrist" key so it does not show as redundant in the UI
    if "wrist" in cameras:
        cameras = {k: v for k, v in cameras.items() if k != "wrist"}
    for key in ("left_wrist", "right_wrist", "top"):
        if key not in cameras:
            cameras = {**cameras, key: DEFAULT_CAMERAS[key].copy()}
    cfg.robot.cameras = cameras
    return cfg


def _apply_launcher_overrides(cfg: AppConfig) -> AppConfig:
    """Use launcher.json as the source of truth for runtime network settings."""
    if not get_launcher_config_path().exists():
        return cfg
    launcher = load_launcher_config()
    if launcher.get("leader_ip"):
        cfg.robot.leader_ip = str(launcher["leader_ip"]).strip()
    if launcher.get("follower_ip"):
        cfg.robot.follower_ip = str(launcher["follower_ip"]).strip()
    if launcher.get("pc2_wifi_ip"):
        cfg.robot.remote_leader_host = str(launcher["pc2_wifi_ip"]).strip()
    if launcher.get("pc2_ssh_user"):
        cfg.robot.remote_leader_ssh_user = str(launcher["pc2_ssh_user"]).strip()
    return cfg


def load_config() -> AppConfig:
    """Load config from disk, or return defaults if not found."""
    path = get_config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            cfg = AppConfig.model_validate(data)
            return _apply_launcher_overrides(_ensure_camera_slots(cfg))
        except Exception:
            pass
    return _apply_launcher_overrides(_ensure_camera_slots(AppConfig()))


def save_config(config: AppConfig) -> None:
    """Save config to disk."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2))
