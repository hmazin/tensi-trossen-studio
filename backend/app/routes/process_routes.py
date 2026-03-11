"""Process control API routes."""

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import load_config
from app.services.camera_manager import CameraManager
from app.services.process_manager import ProcessManager, ProcessStatus

router = APIRouter(prefix="/api", tags=["process"])
logger = logging.getLogger(__name__)


def _reset_realsense_cameras() -> None:
    """Hardware-reset RealSense cameras so lerobot gets a clean connection."""
    try:
        import pyrealsense2 as rs
        import time
        ctx = rs.context()
        devices = ctx.query_devices()
        if len(devices) == 0:
            return
        for dev in devices:
            sn = dev.get_info(rs.camera_info.serial_number)
            dev.hardware_reset()
            logger.info(f"Hardware-reset RealSense {sn}")
        time.sleep(3)
    except Exception as e:
        logger.warning(f"Camera reset failed (non-fatal): {e}")


def _shutdown_cameras_for_process(teleop_keys: set[str] | None = None) -> None:
    """Shutdown only the given teleop camera keys (or all configured if None). Operator camera stays on."""
    if teleop_keys is None:
        config = load_config()
        teleop_keys = set(config.robot.cameras or {})
    CameraManager.get_instance().shutdown_cameras_for_teleop(teleop_keys)

    # Hardware-reset RealSense only when we are handing cameras to the process (avoid disrupting Studio viewer)
    if teleop_keys:
        _reset_realsense_cameras()

    # If remote camera service is configured, shutdown remote cameras
    camera_service_url = os.getenv("CAMERA_SERVICE_URL")
    if camera_service_url:
        try:
            import requests
            response = requests.post(
                f"{camera_service_url}/api/cameras/shutdown",
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Remote cameras shutdown successfully: {response.json()}")
        except Exception as e:
            logger.warning(f"Failed to shutdown remote cameras at {camera_service_url}: {e}")
            # Continue anyway - cameras might not be in use


def _robot_config(use_top_camera_only: bool | None = None) -> dict:
    """Get robot config as dict for process manager. Only cameras with use_in_teleop != False are sent to Trossen."""
    cfg = load_config()
    use_top_only = use_top_camera_only if use_top_camera_only is not None else getattr(cfg.robot, "use_top_camera_only", True)
    cameras = cfg.robot.cameras or {}
    # Only include cameras that are selected for teleoperation (default True)
    cameras = {k: v for k, v in cameras.items() if v.get("use_in_teleop", True)}
    if use_top_only and "top" in cameras:
        # Pass top camera as "wrist" key - widowxai_follower may expect wrist slot
        cameras = {"wrist": cameras["top"]}
    # Strip use_in_teleop so lerobot does not see it
    cameras_clean = {
        k: {kk: vv for kk, vv in v.items() if kk != "use_in_teleop"}
        for k, v in cameras.items()
    }
    result = {"leader_ip": cfg.robot.leader_ip, "follower_ip": cfg.robot.follower_ip, "cameras": cameras_clean}
    if cfg.robot.remote_leader:
        result["remote_leader"] = True
        result["remote_leader_host"] = cfg.robot.remote_leader_host
        result["remote_leader_port"] = cfg.robot.remote_leader_port
    return result


def _dataset_config() -> dict:
    """Get dataset config as dict."""
    cfg = load_config()
    return cfg.dataset.model_dump()


def _train_config() -> dict:
    """Get train config as dict."""
    cfg = load_config()
    return cfg.train.model_dump()


def _replay_config(repo_id: str | None = None, episode: int | None = None) -> dict:
    """Get replay config as dict, with optional overrides."""
    cfg = load_config()
    return {
        "repo_id": repo_id if repo_id is not None else cfg.replay.repo_id,
        "episode": episode if episode is not None else cfg.replay.episode,
    }


@router.post("/teleoperate/start")
def start_teleoperate(display_data: bool = True, use_top_camera_only: bool | None = None) -> dict:
    """Start lerobot-teleoperate."""
    robot_cfg = _robot_config(use_top_camera_only=use_top_camera_only)
    if not robot_cfg["cameras"]:
        raise HTTPException(
            status_code=400,
            detail="At least one camera must be used in teleoperation. Enable 'Use in teleoperation' for left wrist, right wrist, or top camera in Settings.",
        )
    # Only release cameras that we send to Trossen; others stay available in Studio
    _shutdown_cameras_for_process(teleop_keys=set(robot_cfg["cameras"].keys()))

    pm = ProcessManager()
    config = load_config()
    pm.set_lerobot_path(Path(config.lerobot_trossen_path))
    pm.start_teleoperate(robot_cfg, display_data=display_data)
    return {"status": "started", "mode": "teleoperate"}


@router.post("/teleoperate/stop")
def stop_teleoperate() -> dict:
    """Stop teleoperate process."""
    ProcessManager().stop()
    return {"status": "stopped"}


@router.post("/record/start")
def start_record(
    repo_id: str | None = None,
    num_episodes: int | None = None,
    episode_time_s: int | None = None,
    single_task: str | None = None,
    push_to_hub: bool | None = None,
    use_top_camera_only: bool | None = None,
) -> dict:
    """Start lerobot-record."""
    robot_cfg = _robot_config(use_top_camera_only=use_top_camera_only)
    if not robot_cfg["cameras"]:
        raise HTTPException(
            status_code=400,
            detail="At least one camera must be used in recording. Enable 'Use in teleoperation' for left wrist, right wrist, or top camera in Settings.",
        )
    _shutdown_cameras_for_process(teleop_keys=set(robot_cfg["cameras"].keys()))

    pm = ProcessManager()
    config = load_config()
    pm.set_lerobot_path(Path(config.lerobot_trossen_path))
    dataset = _dataset_config()
    if repo_id is not None:
        dataset["repo_id"] = repo_id
    if num_episodes is not None:
        dataset["num_episodes"] = num_episodes
    if episode_time_s is not None:
        dataset["episode_time_s"] = episode_time_s
    if single_task is not None:
        dataset["single_task"] = single_task
    if push_to_hub is not None:
        dataset["push_to_hub"] = push_to_hub
    pm.start_record(robot_cfg, dataset)
    return {"status": "started", "mode": "record"}


@router.post("/record/stop")
def stop_record() -> dict:
    """Stop record process."""
    ProcessManager().stop()
    return {"status": "stopped"}


@router.post("/train/start")
def start_train(
    dataset_repo_id: str | None = None,
    policy_type: str | None = None,
    output_dir: str | None = None,
    job_name: str | None = None,
) -> dict:
    """Start lerobot-train."""
    pm = ProcessManager()
    config = load_config()
    pm.set_lerobot_path(Path(config.lerobot_trossen_path))
    train = _train_config()
    if dataset_repo_id is not None:
        train["dataset_repo_id"] = dataset_repo_id
    if policy_type is not None:
        train["policy_type"] = policy_type
    if output_dir is not None:
        train["output_dir"] = output_dir
    if job_name is not None:
        train["job_name"] = job_name
    pm.start_train(train)
    return {"status": "started", "mode": "train"}


@router.post("/train/stop")
def stop_train() -> dict:
    """Stop train process."""
    ProcessManager().stop()
    return {"status": "stopped"}


@router.post("/replay/start")
def start_replay(repo_id: str | None = None, episode: int | None = None) -> dict:
    """Start lerobot-replay."""
    pm = ProcessManager()
    config = load_config()
    pm.set_lerobot_path(Path(config.lerobot_trossen_path))
    pm.start_replay(_robot_config(), _replay_config(repo_id=repo_id, episode=episode))
    return {"status": "started", "mode": "replay"}


@router.post("/replay/stop")
def stop_replay() -> dict:
    """Stop replay process."""
    ProcessManager().stop()
    return {"status": "stopped"}


@router.post("/process/stop")
def stop_process() -> dict:
    """Stop any running process."""
    ProcessManager().stop()
    return {"status": "stopped"}


@router.get("/process/status")
def get_process_status() -> dict:
    """Get current process status and logs."""
    status: ProcessStatus = ProcessManager().get_status()
    return {
        "mode": status.mode.value,
        "running": status.running,
        "pid": status.pid,
        "logs": status.logs,
        "error": status.error,
    }
