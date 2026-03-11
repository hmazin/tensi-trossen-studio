"""Config API routes."""

from fastapi import APIRouter, HTTPException

from app.config import AppConfig, load_config, load_launcher_config, save_config, save_launcher_config

router = APIRouter(tags=["config"])


@router.get("")
def get_config() -> dict:
    """Load and return current configuration, including launcher-backed runtime values."""
    config = load_config()
    launcher = load_launcher_config()
    return {**config.model_dump(), "launcher": launcher}


@router.post("")
def post_config(config: dict) -> dict:
    """Save configuration. Validates and persists to disk. Syncs launcher-backed network fields."""
    try:
        app_config = AppConfig.model_validate(config)
        save_config(app_config)
        robot = config.get("robot", {})
        launcher_updates = {}
        if robot.get("leader_ip") and str(robot["leader_ip"]).strip():
            launcher_updates["leader_ip"] = str(robot["leader_ip"]).strip()
        if robot.get("follower_ip") and str(robot["follower_ip"]).strip():
            launcher_updates["follower_ip"] = str(robot["follower_ip"]).strip()
        if robot.get("remote_leader_host") and str(robot["remote_leader_host"]).strip():
            launcher_updates["pc2_wifi_ip"] = str(robot["remote_leader_host"]).strip()
        if robot.get("remote_leader_ssh_user") and str(robot["remote_leader_ssh_user"]).strip():
            launcher_updates["pc2_ssh_user"] = str(robot["remote_leader_ssh_user"]).strip()
        if launcher_updates:
            save_launcher_config(launcher_updates)
        out = {**load_config().model_dump(), "launcher": load_launcher_config()}
        return {"status": "saved", "config": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
