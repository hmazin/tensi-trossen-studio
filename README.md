# TENSI Trossen Studio

> Web-based control interface for LeRobot Trossen robots with distributed teleoperation support

A system for teleoperating, recording, training, and replaying Trossen WidowX AI robotic arms using [LeRobot](https://github.com/huggingface/lerobot). Supports distributed setups where leader and follower robots are on separate networks — different rooms, floors, or even cities.

## Features

- **Teleoperation** — Real-time leader-follower robot control, local or remote
- **Recording** — Capture demonstration episodes with camera feeds
- **Training** — Train ACT/Diffusion policies on collected data
- **Replay** — Execute learned behaviors on the physical robot
- **Camera streaming** — Live RealSense camera feeds in the web UI
- **Distributed teleoperation** — Operate robots across PCs over WiFi or WAN
- **Leader service management** — Start/stop the remote leader service from the web UI
- **Web configuration** — All settings configurable through the browser

## Architecture

### Single PC

Both robots on the same Ethernet switch, everything runs on one machine.

```
Browser → Frontend (React) → Backend (FastAPI) → lerobot-teleoperate → Robots
```

### Distributed (two PCs)

Leader and follower robots on separate PCs. A lightweight Leader Service on PC2 streams joint positions over TCP to PC1.

```
PC2 (Leader Side)                      PC1 (Follower Side)
┌─────────────────────────┐            ┌─────────────────────────────┐
│  Leader Robot            │            │  Follower Robot              │
│  (192.168.1.2)           │            │  (192.168.1.5)               │
│       │ Ethernet         │            │       │ Ethernet             │
│  leader_service.py       │            │  lerobot-teleoperate         │
│  TCP:5555 ───────────────┼── WiFi ──► │  + RemoteLeaderTeleop plugin │
│  Streams 7 floats @60Hz  │   ~2KB/s  │                              │
└─────────────────────────┘            │  Backend + Frontend + Cameras │
                                       └─────────────────────────────┘
```

This works over WiFi (LAN) and WAN (internet via VPN) because it only needs a single TCP connection at ~2 KB/s, tolerating 50-200ms latency.

## Quick Start

### Prerequisites

- **lerobot_trossen** — cloned and installed at `~/lerobot_trossen` ([Trossen docs](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin.html))
- **uv** — Python package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js 18+** and npm ([nodejs.org](https://nodejs.org/))
- **Trossen WidowX AI robots** — leader and follower with iNerve controllers
- **Intel RealSense cameras** (optional, for recording)

### Installation

```bash
git clone https://github.com/hmazin/tensi-trossen-studio.git
cd tensi-trossen-studio
```

### Start the Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

### Open the UI

```
http://localhost:5173
```

### First-Time Configuration

1. Click the gear icon (top-right) to open Settings
2. Set **Follower IP** (default: `192.168.1.5`)
3. For single-PC: set **Leader IP** (default: `192.168.1.2`)
4. For distributed: enable **Remote Leader Mode** and set the host/port
5. Configure camera serial numbers
6. Click **Save Settings**

## Distributed Setup

For operating leader and follower robots on separate PCs.

See the full guide: [deployment/REMOTE-LEADER-SETUP.md](deployment/REMOTE-LEADER-SETUP.md)

### TL;DR

1. Copy `leader_service.py` to PC2 (the leader robot's PC)
2. Install `trossen_arm` on PC2
3. Start the leader service on PC2:
   ```bash
   python3 -u ~/leader_service.py --ip 192.168.1.2 --port 5555 --fps 60
   ```
   Or start it from the web UI (uses SSH under the hood).
4. Enable **Remote Leader Mode** in the web UI Settings
5. Click **Start Teleoperation**

## Configuration

Configuration is stored at `~/.tensi_trossen_studio/config.json`:

```json
{
  "robot": {
    "leader_ip": "192.168.1.2",
    "follower_ip": "192.168.1.5",
    "remote_leader": true,
    "remote_leader_host": "192.168.2.138",
    "remote_leader_port": 5555,
    "use_top_camera_only": true,
    "cameras": {
      "wrist": { "type": "intelrealsense", "serial_number_or_name": "218622275782", "width": 640, "height": 480, "fps": 30 },
      "top":   { "type": "intelrealsense", "serial_number_or_name": "218622278263", "width": 640, "height": 480, "fps": 30 }
    }
  },
  "dataset": {
    "repo_id": "tensi/test_dataset",
    "num_episodes": 10,
    "episode_time_s": 45,
    "single_task": "Grab the cube"
  },
  "lerobot_trossen_path": "/home/user/lerobot_trossen"
}
```

All fields are editable through the web UI Settings panel.

## Usage

### Teleoperation

1. (If distributed) Start the leader service — either from the web UI or manually on PC2
2. Click **Start Teleoperation**
3. Move the leader arm — the follower mirrors in real-time
4. Click **Stop** when done

### Recording

1. Set dataset name, number of episodes, and task description
2. Click **Start Recording**
3. Perform demonstrations — each episode is captured with camera frames
4. Dataset is saved locally in LeRobot format

### Training

1. Enter the dataset repo ID
2. Click **Start Training** — trains an ACT policy
3. Monitor progress in the Process Log

### Replay

1. Select dataset and episode number
2. Click **Start Replay** — the robot executes the recorded actions

## Testing

The project has a comprehensive automated test suite covering backend and frontend, plus a manual hardware checklist.

### Run Backend Tests

```bash
cd backend
uv sync --extra test
uv run pytest tests/ -v
```

68 tests covering config models, process manager CLI arg building, route helpers, leader service SSH logic, and full API integration.

### Run Frontend Tests

```bash
cd frontend
npm install
npm test
```

46 tests covering the API client, and all 5 UI components (StatusBar, ActionPanel, ProcessLog, ConfigForm, CameraViewer).

### Manual Hardware Tests

See [docs/HARDWARE-TEST-CHECKLIST.md](docs/HARDWARE-TEST-CHECKLIST.md) for the structured checklist covering single-PC teleoperation, camera streaming, distributed leader service management, and graceful/unexpected disconnect scenarios.

## Project Structure

```
tensi-trossen-studio/
├── backend/                        # FastAPI backend
│   ├── app/
│   │   ├── main.py                 # Application entry point
│   │   ├── config.py               # Pydantic config models
│   │   ├── routes/
│   │   │   ├── config_routes.py    # GET/POST /api/config
│   │   │   ├── process_routes.py   # Start/stop teleoperate, record, train, replay
│   │   │   ├── camera_routes.py    # Camera streaming and detection
│   │   │   └── leader_service_routes.py  # Remote leader start/stop/status via SSH
│   │   └── services/
│   │       ├── process_manager.py  # Subprocess lifecycle for lerobot CLI
│   │       ├── camera_manager.py   # Singleton camera access manager
│   │       └── camera_streamer.py  # MJPEG streaming
│   ├── tests/                      # Backend test suite (pytest)
│   │   ├── conftest.py             # Shared fixtures
│   │   ├── test_config.py          # Config models + I/O
│   │   ├── test_process_manager.py # CLI arg building, stop logic, singleton
│   │   ├── test_route_helpers.py   # _robot_config, _dataset_config, etc.
│   │   ├── test_leader_service_routes.py # SSH command logic
│   │   └── test_api.py             # Full API integration (TestClient)
│   └── pyproject.toml
├── frontend/                       # React + TypeScript + Tailwind
│   ├── vitest.config.ts            # Vitest test runner configuration
│   ├── src/
│   │   ├── App.tsx                 # Dashboard layout
│   │   ├── api/
│   │   │   ├── client.ts           # REST API client
│   │   │   └── client.test.ts      # API client unit tests
│   │   └── components/
│   │       ├── StatusBar.tsx        # Header with mode + connection indicators
│   │       ├── StatusBar.test.tsx
│   │       ├── ActionPanel.tsx      # Workflow cards + leader service control
│   │       ├── ActionPanel.test.tsx
│   │       ├── CameraViewer.tsx     # Live camera feed viewer
│   │       ├── CameraViewer.test.tsx
│   │       ├── ConfigForm.tsx       # Settings slide-over panel
│   │       ├── ConfigForm.test.tsx
│   │       ├── ProcessLog.tsx       # Real-time process output
│   │       └── ProcessLog.test.tsx
│   └── package.json
├── deployment/                     # Deployment guides and scripts
│   ├── REMOTE-LEADER-SETUP.md     # Distributed teleoperation guide
│   ├── leader-service.service     # Systemd unit for leader service
│   ├── start-leader-service.sh    # Start leader locally on PC2
│   ├── start-remote-leader.sh     # Start leader on PC2 via SSH
│   ├── tensi-backend.service      # Systemd unit for backend
│   └── tensi-camera.service       # Systemd unit for camera service
├── docs/
│   ├── ARCHITECTURE.md            # System architecture deep-dive
│   ├── HARDWARE-TEST-CHECKLIST.md # Manual hardware test checklist
│   └── TROSSEN_LEROBOT_REFERENCE.md  # Trossen LeRobot plugin reference
└── README.md
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, FastAPI, uvicorn, Pydantic |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend testing | pytest, httpx, coverage |
| Frontend testing | vitest, @testing-library/react, jsdom |
| Cameras | pyrealsense2, OpenCV |
| Robot control | LeRobot + Trossen plugin (`trossen_arm`) |
| Networking | TCP sockets (leader service), SSH (remote management) |
| Package management | uv (Python), npm (Node.js) |

## Troubleshooting

### Camera shows "Camera unavailable"

```bash
# Check for stuck processes
pgrep -af lerobot
pkill -f lerobot
# Restart the backend
```

### Leader iNerve LED is red

- Power cycle the iNerve controller
- Wait for the LED to turn green before retrying
- The controller needs a network switch (direct PC connection does not work)

### "Cannot reach Leader Service" (distributed)

```bash
# Check network
ping 192.168.2.138

# Check port
nc -zv 192.168.2.138 5555

# Check if leader_service.py is running on PC2
ssh hadi@192.168.2.138 'ps aux | grep leader_service'

# Check firewall
ssh hadi@192.168.2.138 'sudo ufw allow 5555/tcp'
```

### Positions feel laggy (distributed)

- Check WiFi latency: `ping <PC2_IP>` — under 50ms is ideal
- For WAN: 50-100ms is normal and acceptable
- Reduce FPS if bandwidth is limited: `--fps 30`

## License

MIT License

## Contact

- **Author**: Hooman
- **Email**: hooman.mazin@gmail.com
- **GitHub**: [@hmazin](https://github.com/hmazin)

## Acknowledgments

- [LeRobot](https://github.com/huggingface/lerobot) by Hugging Face
- [Trossen Robotics](https://www.trossenrobotics.com/) for WidowX robotic arms
- Intel RealSense SDK
