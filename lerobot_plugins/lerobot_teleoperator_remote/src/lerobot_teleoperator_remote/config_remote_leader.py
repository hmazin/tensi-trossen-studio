from dataclasses import dataclass, field

import numpy as np
from lerobot.teleoperators.config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("remote_leader_teleop")
@dataclass
class RemoteLeaderTeleopConfig(TeleoperatorConfig):
    """Configuration for the Remote Leader Teleoperator.

    Instead of connecting to a leader robot directly (which requires sub-millisecond
    latency), this teleoperator connects to a Leader Service running on the remote PC.
    The Leader Service handles the real-time robot communication locally, and streams
    joint positions over TCP.

    This enables teleoperation across buildings, cities, or even continents.
    """

    # IP address of the PC running leader_service.py (e.g. PC2's WiFi IP)
    host: str = "192.168.2.138"

    # TCP port of the leader service
    port: int = 5555

    # Connection timeout in seconds
    timeout: float = 10.0

    # Joint names (must match the leader robot)
    joint_names: list[str] = field(
        default_factory=lambda: [
            "joint_0",
            "joint_1",
            "joint_2",
            "joint_3",
            "joint_4",
            "joint_5",
            "left_carriage_joint",
        ]
    )

    # Staged positions for reference (actual staging is done by the leader service)
    staged_positions: list[float] = field(
        default_factory=lambda: [0, np.pi / 3, np.pi / 6, np.pi / 5, 0, 0, 0]
    )
