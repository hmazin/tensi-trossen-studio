#!/usr/bin/env python3
"""
Remote Leader Service - runs on the PC physically connected to the leader robot.

Connects to the leader arm locally (direct Ethernet, zero latency) and streams
joint positions to a remote client over TCP. This enables distributed teleoperation
where leader and follower can be in different buildings or cities.

Protocol (newline-delimited JSON over TCP):

  Client -> Server:
    {"cmd": "configure"}                     Start the leader, move to staged positions
    {"cmd": "disconnect"}                    Disconnect the leader, return to sleep
    {"cmd": "ping"}                          Health check

  Server -> Client:
    {"type": "configured", "joints": 7}      Leader is ready
    {"type": "positions", "v": [...], "t": 0} Joint positions (streamed at ~fps Hz)
    {"type": "disconnected"}                  Leader disconnected
    {"type": "pong"}                          Health check response
    {"type": "error", "msg": "..."}          Error occurred

Usage:
    python3 leader_service.py --ip 192.168.1.3 --port 5555

    # Or for the older leader:
    python3 leader_service.py --ip 192.168.1.2 --port 5555
"""

import argparse
import json
import logging
import socket
import threading
import time

import trossen_arm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("leader_service")

STAGED_POSITIONS = [0, 1.0471975511965976, 0.5235987755982988, 0.6283185307179586, 0, 0, 0]
JOINT_NAMES = ["joint_0", "joint_1", "joint_2", "joint_3", "joint_4", "joint_5", "left_carriage_joint"]


class LeaderService:
    def __init__(self, leader_ip: str, listen_port: int, fps: int = 60):
        self.leader_ip = leader_ip
        self.listen_port = listen_port
        self.fps = fps
        self.driver = trossen_arm.TrossenArmDriver()
        self._configured = False
        self._streaming = False
        self._lock = threading.Lock()

    def configure_leader(self) -> None:
        """Connect and configure the leader robot (local Ethernet)."""
        logger.info(f"Configuring leader at {self.leader_ip}...")
        self.driver.configure(
            model=trossen_arm.Model.wxai_v0,
            end_effector=trossen_arm.StandardEndEffector.wxai_v0_leader,
            serv_ip=self.leader_ip,
            clear_error=True,
        )
        self.driver.set_all_modes(trossen_arm.Mode.position)
        self.driver.set_all_positions(STAGED_POSITIONS, goal_time=2.0, blocking=True)
        self.driver.set_all_modes(trossen_arm.Mode.external_effort)
        self.driver.set_all_external_efforts(
            [0.0] * len(JOINT_NAMES), goal_time=0.0, blocking=True,
        )
        self._configured = True
        logger.info("Leader configured and ready (gravity compensation active).")

    def disconnect_leader(self) -> None:
        """Disconnect the leader robot gracefully."""
        if not self._configured:
            return
        logger.info("Disconnecting leader...")
        try:
            self.driver.set_all_modes(trossen_arm.Mode.position)
            self.driver.set_all_positions(STAGED_POSITIONS, goal_time=2.0, blocking=True)
            self.driver.set_all_positions([0.0] * len(JOINT_NAMES), goal_time=2.0, blocking=True)
            self.driver.cleanup()
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")
        self._configured = False
        logger.info("Leader disconnected.")

    def get_positions(self) -> list[float]:
        """Read current joint positions from leader."""
        return list(self.driver.get_all_positions())

    def _send_json(self, sock: socket.socket, obj: dict) -> bool:
        """Send a JSON message followed by newline. Returns False on error."""
        try:
            data = json.dumps(obj, separators=(",", ":")) + "\n"
            sock.sendall(data.encode("utf-8"))
            return True
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False

    def _recv_json(self, sock: socket.socket, buf: bytearray) -> dict | None:
        """Read a JSON line from socket. Non-blocking, returns None if no complete message."""
        try:
            sock.setblocking(False)
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    return {"cmd": "_disconnected"}
                buf.extend(chunk)
            except BlockingIOError:
                pass
            finally:
                sock.setblocking(True)
        except (ConnectionResetError, OSError):
            return {"cmd": "_disconnected"}

        idx = buf.find(b"\n")
        if idx == -1:
            return None
        line = buf[:idx]
        del buf[: idx + 1]
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None

    def handle_client(self, client_sock: socket.socket, addr: tuple) -> None:
        """Handle a single client connection."""
        logger.info(f"Client connected from {addr}")
        buf = bytearray()
        streaming = False

        try:
            while True:
                msg = self._recv_json(client_sock, buf)

                if msg and msg.get("cmd") == "_disconnected":
                    logger.info(f"Client {addr} disconnected")
                    break

                if msg:
                    cmd = msg.get("cmd")
                    if cmd == "configure":
                        try:
                            if not self._configured:
                                self.configure_leader()
                            self._send_json(client_sock, {
                                "type": "configured",
                                "joints": len(JOINT_NAMES),
                                "joint_names": JOINT_NAMES,
                            })
                            streaming = True
                        except Exception as e:
                            logger.error(f"Configure failed: {e}")
                            self._send_json(client_sock, {"type": "error", "msg": str(e)})
                            break

                    elif cmd == "disconnect":
                        streaming = False
                        self.disconnect_leader()
                        self._send_json(client_sock, {"type": "disconnected"})
                        break

                    elif cmd == "ping":
                        self._send_json(client_sock, {"type": "pong"})

                if streaming and self._configured:
                    try:
                        positions = self.get_positions()
                        ok = self._send_json(client_sock, {
                            "type": "positions",
                            "v": positions,
                            "t": time.time(),
                        })
                        if not ok:
                            break
                    except Exception as e:
                        logger.error(f"Position read error: {e}")
                        self._send_json(client_sock, {"type": "error", "msg": str(e)})
                        break

                    time.sleep(1.0 / self.fps)
                else:
                    time.sleep(0.01)

        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            client_sock.close()
            if self._configured:
                logger.info(f"Client {addr} gone — returning leader to safe state...")
                self.disconnect_leader()
            logger.info(f"Client {addr} session ended.")

    def run(self) -> None:
        """Run the leader service TCP server."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", self.listen_port))
        server.listen(1)
        logger.info(f"Leader service listening on :{self.listen_port}")
        logger.info(f"Leader robot IP: {self.leader_ip}")
        logger.info(f"Streaming rate: {self.fps} Hz")
        logger.info("Waiting for client connection...")

        try:
            while True:
                client_sock, addr = server.accept()
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.handle_client(client_sock, addr)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            if self._configured:
                self.disconnect_leader()
            server.close()


def main():
    parser = argparse.ArgumentParser(description="Remote Leader Service")
    parser.add_argument("--ip", required=True, help="Leader robot IP address (e.g. 192.168.1.3)")
    parser.add_argument("--port", type=int, default=5555, help="TCP port to listen on (default: 5555)")
    parser.add_argument("--fps", type=int, default=60, help="Position streaming rate in Hz (default: 60)")
    args = parser.parse_args()

    service = LeaderService(leader_ip=args.ip, listen_port=args.port, fps=args.fps)
    service.run()


if __name__ == "__main__":
    main()
