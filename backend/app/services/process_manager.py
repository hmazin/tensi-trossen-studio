"""Process manager for spawning and controlling LeRobot CLI subprocesses."""

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

LEROBOT_TROSSEN_PATH = Path.home() / "lerobot_trossen"
DEBUG_LOG_PATH = Path(__file__).resolve().parents[3] / ".cursor" / "debug.log"
_FALLBACK_LOG_PATH = Path.home() / ".tensi_trossen_studio" / "debug.log"


def _debug_log(location: str, message: str, data: dict, hypothesis_id: str) -> None:
    # #region agent log
    payload = {"timestamp": int(time.time() * 1000), "location": location, "message": message, "data": data, "hypothesisId": hypothesis_id}
    entry = json.dumps(payload, default=str) + "\n"
    for path in (DEBUG_LOG_PATH, _FALLBACK_LOG_PATH):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as f:
                f.write(entry)
            break
        except Exception:
            continue
    # #endregion


class ProcessMode(str, Enum):
    IDLE = "idle"
    TELEOPERATE = "teleoperate"
    RECORD = "record"
    TRAIN = "train"
    REPLAY = "replay"
    VISUALIZE = "visualize"


@dataclass
class ProcessStatus:
    """Current process status."""

    mode: ProcessMode = ProcessMode.IDLE
    running: bool = False
    pid: int | None = None
    logs: list[str] = field(default_factory=list)
    error: str | None = None


class ProcessManager:
    """Singleton process manager."""

    _instance: "ProcessManager | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "ProcessManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._process: subprocess.Popen | None = None
        self._status = ProcessStatus()
        self._log_buffer: list[str] = []
        self._reader_thread: threading.Thread | None = None
        self._lerobot_path = LEROBOT_TROSSEN_PATH
        self._initialized = True

    def set_lerobot_path(self, path: Path) -> None:
        """Set path to lerobot_trossen repository."""
        self._lerobot_path = Path(path)

    def _read_output(self, pipe, callback: Callable[[str], None] | None = None) -> None:
        """Read from pipe and append to log buffer."""
        try:
            for line in iter(pipe.readline, ""):
                if line:
                    self._log_buffer.append(line.rstrip())
                    if callback:
                        callback(line.rstrip())
        except Exception:
            pass

    def start_teleoperate(self, robot_config: dict, display_data: bool = True) -> None:
        """Start lerobot-teleoperate subprocess."""
        # #region agent log
        _debug_log("process_manager.py:start_teleoperate:entry", "entry", {"hit": True}, "H2")
        # #endregion
        self.stop()
        cameras = robot_config.get("cameras", {})
        # #region agent log
        _debug_log("process_manager.py:start_teleoperate", "teleoperate params", {"cameras_keys": list(cameras.keys()), "cameras_json_len": len(json.dumps(cameras))}, "H2")
        # #endregion
        cmd = [
            "uv",
            "run",
            "lerobot-teleoperate",
            "--robot.type=widowxai_follower_robot",
            f"--robot.ip_address={robot_config.get('follower_ip', '192.168.1.5')}",
            "--robot.id=follower",
            f"--robot.cameras={json.dumps(cameras)}",
            "--teleop.type=widowxai_leader_teleop",
            f"--teleop.ip_address={robot_config.get('leader_ip', '192.168.1.2')}",
            "--teleop.id=leader",
            f"--display_data={str(display_data).lower()}",
        ]
        self._spawn(cmd, ProcessMode.TELEOPERATE)

    def start_record(
        self,
        robot_config: dict,
        dataset_config: dict,
        display_data: bool = True,
    ) -> None:
        """Start lerobot-record subprocess."""
        self.stop()
        cameras = robot_config.get("cameras", {})
        cmd = [
            "uv",
            "run",
            "lerobot-record",
            "--robot.type=widowxai_follower_robot",
            f"--robot.ip_address={robot_config.get('follower_ip', '192.168.1.5')}",
            "--robot.id=follower",
            f"--robot.cameras={json.dumps(cameras)}",
            "--teleop.type=widowxai_leader_teleop",
            f"--teleop.ip_address={robot_config.get('leader_ip', '192.168.1.2')}",
            "--teleop.id=leader",
            f"--display_data={str(display_data).lower()}",
            f"--dataset.repo_id={dataset_config.get('repo_id', 'tensi/test_dataset')}",
            f"--dataset.num_episodes={dataset_config.get('num_episodes', 10)}",
            f"--dataset.episode_time_s={dataset_config.get('episode_time_s', 45)}",
            f"--dataset.reset_time_s={dataset_config.get('reset_time_s', 15)}",
            f"--dataset.single_task={dataset_config.get('single_task', 'Grab the cube')!r}",
            f"--dataset.push_to_hub={str(dataset_config.get('push_to_hub', False)).lower()}",
        ]
        self._spawn(cmd, ProcessMode.RECORD)

    def start_train(
        self,
        train_config: dict,
    ) -> None:
        """Start lerobot-train subprocess."""
        self.stop()
        cmd = [
            "uv",
            "run",
            "lerobot-train",
            f"--dataset.repo_id={train_config.get('dataset_repo_id', 'tensi/test_dataset')}",
            f"--policy.type={train_config.get('policy_type', 'act')}",
            f"--output_dir={train_config.get('output_dir', 'outputs/train/act_trossen')}",
            f"--job_name={train_config.get('job_name', 'act_trossen')}",
            "--policy.device=cuda",
            "--wandb.enable=false",
            f"--policy.repo_id={train_config.get('policy_repo_id', 'tensi/my_policy')}",
        ]
        self._spawn(cmd, ProcessMode.TRAIN)

    def start_replay(self, robot_config: dict, replay_config: dict) -> None:
        """Start lerobot-replay subprocess."""
        self.stop()
        cmd = [
            "uv",
            "run",
            "lerobot-replay",
            "--robot.type=widowxai_follower_robot",
            f"--robot.ip_address={robot_config.get('follower_ip', '192.168.1.5')}",
            "--robot.id=follower",
            f"--dataset.repo_id={replay_config.get('repo_id', 'tensi/test_dataset')}",
            f"--dataset.episode={replay_config.get('episode', 0)}",
        ]
        self._spawn(cmd, ProcessMode.REPLAY)

    def _spawn(self, cmd: list[str], mode: ProcessMode) -> None:
        """Spawn subprocess with cwd set to lerobot_trossen."""
        self._log_buffer = []
        self._status = ProcessStatus(mode=mode, running=True, logs=[])

        cwd = str(self._lerobot_path)
        # #region agent log
        env_before = dict(os.environ)
        _debug_log("process_manager.py:_spawn", "pre-spawn env and cwd", {"VIRTUAL_ENV": env_before.get("VIRTUAL_ENV"), "PYTHONPATH": env_before.get("PYTHONPATH"), "LD_LIBRARY_PATH": env_before.get("LD_LIBRARY_PATH"), "cwd": cwd, "cmd": cmd, "lerobot_path_exists": Path(self._lerobot_path).exists()}, "H1,H3,H5")
        # #endregion

        env = dict(os.environ)
        env.pop("VIRTUAL_ENV", None)
        env.pop("PYTHONPATH", None)

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._status.pid = self._process.pid

            def read_loop() -> None:
                if self._process and self._process.stdout:
                    self._read_output(self._process.stdout)
                    self._process.wait()

            self._reader_thread = threading.Thread(target=read_loop, daemon=True)
            self._reader_thread.start()
        except Exception as e:
            self._status.running = False
            self._status.error = str(e)
            self._log_buffer.append(f"Error: {e}")

    def stop(self) -> None:
        """Stop current process if running."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._log_buffer.append("[Studio] Process stopped.")
        self._process = None
        if self._status.running:
            self._status.running = False
            self._status.pid = None

    def get_status(self) -> ProcessStatus:
        """Get current process status and latest logs."""
        if self._process and self._process.poll() is not None:
            self._status.running = False
            self._status.pid = None
        self._status.logs = self._log_buffer[-500:]  # Keep last 500 lines
        return self._status
