"""
Remote Leader Teleoperator - connects to a Leader Service over the network.

Instead of talking to the Trossen iNerve controller directly (which requires
sub-ms latency), this teleoperator reads joint positions from a remote
Leader Service that runs on the PC physically connected to the leader robot.

This makes distributed teleoperation possible over WiFi, LAN, or WAN.
"""

import json
import logging
import socket
import threading
import time

from lerobot.utils.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError
from lerobot.teleoperators.teleoperator import Teleoperator

from lerobot_teleoperator_remote.config_remote_leader import RemoteLeaderTeleopConfig

logger = logging.getLogger(__name__)


class RemoteLeaderTeleop(Teleoperator):
    """
    Teleoperator that reads joint positions from a remote Leader Service.
    See leader_service.py for the server side.
    """

    config_class = RemoteLeaderTeleopConfig
    name = "remote_leader_teleop"

    def __init__(self, config: RemoteLeaderTeleopConfig):
        super().__init__(config)
        self.config = config
        self._sock: socket.socket | None = None
        self._connected = False
        self._latest_positions: list[float] | None = None
        self._positions_lock = threading.Lock()
        self._receiver_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._recv_buf = bytearray()

    @property
    def action_features(self) -> dict[str, type]:
        return {f"{joint_name}.pos": float for joint_name in self.config.joint_names}

    @property
    def feedback_features(self) -> dict[str, type]:
        return {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, calibrate: bool = True) -> None:
        if self._connected:
            raise DeviceAlreadyConnectedError(f"{self} already connected")

        logger.info(f"Connecting to Leader Service at {self.config.host}:{self.config.port}...")

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock.settimeout(self.config.timeout)

        try:
            self._sock.connect((self.config.host, self.config.port))
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            self._sock.close()
            self._sock = None
            raise ConnectionError(
                f"Cannot reach Leader Service at {self.config.host}:{self.config.port}. "
                f"Make sure leader_service.py is running on the remote PC. Error: {e}"
            ) from e

        self._send_json({"cmd": "configure"})

        response = self._recv_json_blocking()
        if response is None:
            self._sock.close()
            self._sock = None
            raise ConnectionError("No response from Leader Service after configure command.")

        if response.get("type") == "error":
            msg = response.get("msg", "unknown error")
            self._sock.close()
            self._sock = None
            raise ConnectionError(f"Leader Service configure error: {msg}")

        if response.get("type") != "configured":
            self._sock.close()
            self._sock = None
            raise ConnectionError(f"Unexpected response: {response}")

        num_joints = response.get("joints", 0)
        logger.info(f"Leader Service configured with {num_joints} joints.")

        self._connected = True
        self._stop_event.clear()
        self._receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._receiver_thread.start()

        logger.info(f"{self} connected to remote leader.")

    def _receiver_loop(self) -> None:
        """Background thread that reads position updates from the leader service."""
        buf = bytearray()
        while not self._stop_event.is_set():
            try:
                self._sock.setblocking(False)
                try:
                    chunk = self._sock.recv(65536)
                    if not chunk:
                        logger.warning("Leader Service disconnected.")
                        self._connected = False
                        break
                    buf.extend(chunk)
                except BlockingIOError:
                    pass
                finally:
                    self._sock.setblocking(True)

                while b"\n" in buf:
                    idx = buf.index(b"\n")
                    line = buf[:idx]
                    del buf[: idx + 1]
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if msg.get("type") == "positions":
                        with self._positions_lock:
                            self._latest_positions = msg["v"]

                    elif msg.get("type") == "error":
                        logger.error(f"Leader Service error: {msg.get('msg')}")

                    elif msg.get("type") == "disconnected":
                        logger.info("Leader Service confirmed disconnect.")
                        self._connected = False
                        return

            except (ConnectionResetError, OSError) as e:
                logger.warning(f"Connection lost: {e}")
                self._connected = False
                break

            time.sleep(0.001)

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    def get_action(self) -> dict[str, float]:
        if not self._connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        start = time.perf_counter()

        with self._positions_lock:
            positions = self._latest_positions

        if positions is None:
            retries = 0
            while positions is None and retries < 200:
                time.sleep(0.005)
                with self._positions_lock:
                    positions = self._latest_positions
                retries += 1
            if positions is None:
                raise RuntimeError(
                    "No position data received from Leader Service. "
                    "Check network connectivity and leader_service.py logs."
                )

        action_dict = {
            f"{joint_name}.pos": val
            for joint_name, val in zip(self.config.joint_names, positions, strict=True)
        }

        dt_ms = (time.perf_counter() - start) * 1e3
        logger.debug(f"{self} remote action: {dt_ms:.1f}ms")
        return action_dict

    def send_feedback(self, feedback: dict[str, float]) -> None:
        raise NotImplementedError

    def disconnect(self) -> None:
        if not self._connected and self._sock is None:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        logger.info(f"Disconnecting {self} from remote leader...")

        self._stop_event.set()

        if self._sock:
            try:
                self._send_json({"cmd": "disconnect"})
                time.sleep(0.5)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

        if self._receiver_thread and self._receiver_thread.is_alive():
            self._receiver_thread.join(timeout=2.0)

        self._connected = False
        self._latest_positions = None
        logger.info(f"{self} disconnected.")

    def _send_json(self, obj: dict) -> None:
        """Send a JSON message followed by newline."""
        if self._sock is None:
            raise DeviceNotConnectedError("Socket not connected")
        data = json.dumps(obj, separators=(",", ":")) + "\n"
        self._sock.sendall(data.encode("utf-8"))

    def _recv_json_blocking(self) -> dict | None:
        """Read a single JSON line from socket (blocking, with timeout)."""
        buf = bytearray()
        deadline = time.time() + self.config.timeout
        while time.time() < deadline:
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    return None
                buf.extend(chunk)
            except socket.timeout:
                return None

            idx = buf.find(b"\n")
            if idx != -1:
                line = buf[:idx]
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    return None
        return None
