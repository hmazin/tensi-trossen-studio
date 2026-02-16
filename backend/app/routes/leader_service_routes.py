"""Leader Service API routes - manage the remote leader service on PC2 via SSH."""

import logging
import subprocess
import time

from fastapi import APIRouter

from app.config import load_config

router = APIRouter(prefix="/api/leader-service", tags=["leader-service"])
logger = logging.getLogger(__name__)


def _ssh_run(user: str, host: str, command: str, timeout: int = 10) -> tuple[int, str]:
    """Run a command on the remote PC via SSH. Returns (exit_code, output)."""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "ConnectTimeout=5",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                f"{user}@{host}",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "SSH command timed out"
    except Exception as e:
        return -1, str(e)


def _get_remote_config() -> tuple[str, str, str, int]:
    """Get SSH user, host, leader IP, and port from config."""
    cfg = load_config()
    host = cfg.robot.remote_leader_host
    port = cfg.robot.remote_leader_port
    leader_ip = cfg.robot.leader_ip
    user = getattr(cfg.robot, "remote_leader_ssh_user", None) or "hadi"
    return user, host, leader_ip, port


@router.get("/status")
def get_leader_service_status() -> dict:
    """Check if the leader service is running on PC2."""
    user, host, leader_ip, port = _get_remote_config()

    exit_code, output = _ssh_run(
        user, host,
        "ps aux | grep 'leader_service.py' | grep -v grep | head -1"
    )

    if exit_code != 0 or not output.strip():
        exit_code2, _ = _ssh_run(user, host, f"ss -tlnp | grep :{port}")
        if exit_code2 == 0:
            return {"status": "running", "host": host, "port": port}
        return {"status": "stopped", "host": host, "port": port}

    return {"status": "running", "host": host, "port": port}


@router.post("/start")
def start_leader_service() -> dict:
    """Start the leader service on PC2 via SSH."""
    user, host, leader_ip, port = _get_remote_config()

    exit_code, output = _ssh_run(
        user, host,
        "ps aux | grep 'leader_service.py' | grep -v grep"
    )
    if exit_code == 0 and output.strip():
        return {"status": "already_running", "host": host, "port": port}

    exit_code, _ = _ssh_run(user, host, f"ping -c 1 -W 2 {leader_ip}")
    if exit_code != 0:
        return {
            "status": "error",
            "message": f"Cannot reach leader robot at {leader_ip} from PC2. Is it powered on?",
        }

    start_cmd = (
        f"nohup python3 -u ~/leader_service.py "
        f"--ip {leader_ip} --port {port} --fps 60 "
        f"> /tmp/leader_service.log 2>&1 & "
        f"echo $!"
    )
    exit_code, output = _ssh_run(user, host, start_cmd, timeout=15)
    if exit_code != 0:
        return {"status": "error", "message": f"Failed to start: {output}"}

    pid = output.strip().split("\n")[-1]

    time.sleep(2)
    exit_code, check_output = _ssh_run(
        user, host,
        "ps aux | grep 'leader_service.py' | grep -v grep | head -1"
    )
    if exit_code != 0 or not check_output.strip():
        _, log_output = _ssh_run(user, host, "tail -20 /tmp/leader_service.log")
        return {
            "status": "error",
            "message": f"Leader service exited immediately. Log: {log_output}",
        }

    return {"status": "started", "host": host, "port": port, "pid": pid}


@router.post("/stop")
def stop_leader_service() -> dict:
    """Stop the leader service on PC2 via SSH."""
    user, host, _, port = _get_remote_config()

    exit_code, output = _ssh_run(
        user, host,
        "ps aux | grep 'leader_service.py' | grep -v grep | awk '{print $2}'"
    )

    if exit_code != 0 or not output.strip():
        return {"status": "not_running"}

    pids = output.strip().split("\n")
    for pid in pids:
        pid = pid.strip()
        if pid:
            _ssh_run(user, host, f"kill {pid}")

    time.sleep(3)

    exit_code, output = _ssh_run(
        user, host,
        "ps aux | grep 'leader_service.py' | grep -v grep"
    )
    if exit_code == 0 and output.strip():
        for pid in pids:
            pid = pid.strip()
            if pid:
                _ssh_run(user, host, f"kill -9 {pid}")
        return {"status": "force_killed"}

    return {"status": "stopped"}


@router.get("/logs")
def get_leader_service_logs(lines: int = 30) -> dict:
    """Get recent logs from the leader service on PC2."""
    user, host, _, _ = _get_remote_config()
    exit_code, output = _ssh_run(user, host, f"tail -{lines} /tmp/leader_service.log 2>/dev/null")
    if exit_code != 0:
        return {"logs": [], "error": output}
    return {"logs": output.split("\n") if output else []}
