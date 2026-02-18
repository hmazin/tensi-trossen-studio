# TENSI Trossen Studio - System Architecture

## Overview

TENSI Trossen Studio is a web-based control system for Trossen WidowX AI robotic arms. It wraps the [LeRobot](https://github.com/huggingface/lerobot) framework with a FastAPI backend and React frontend, enabling teleoperation, data recording, policy training, and replay through a browser interface.

The system supports two deployment modes:
- **Single PC** — both robots on one Ethernet switch, one machine
- **Distributed** — leader and follower robots on separate PCs connected over WiFi or WAN

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Web Browser                               │
│                      http://localhost:5173                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   StatusBar          ActionPanel         CameraViewer   ConfigForm  │
│   ┌──────────┐      ┌──────────────┐    ┌───────────┐  ┌────────┐  │
│   │ Mode     │      │ Leader Svc   │    │ MJPEG     │  │Settings│  │
│   │ Status   │      │ Teleoperate  │    │ Streams   │  │ Drawer │  │
│   │ IPs      │      │ Record       │    │           │  │        │  │
│   │          │      │ Train/Replay │    │           │  │        │  │
│   └──────────┘      └──────────────┘    └───────────┘  └────────┘  │
│                              │                 │              │      │
│   React + TypeScript + Tailwind CSS + Vite                          │
└──────────────────────────────┼─────────────────┼──────────────┼─────┘
                               │ REST API        │ MJPEG        │
                               ▼                 ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (:8000)                          │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐ │
│   │  Process Routes  │  │  Camera Routes  │  │  Config Routes     │ │
│   │  /api/teleoperate│  │  /api/cameras/  │  │  /api/config       │ │
│   │  /api/record     │  │    stream/      │  │                    │ │
│   │  /api/train      │  │    detect       │  │                    │ │
│   │  /api/replay     │  │    status       │  │                    │ │
│   │  /api/process    │  │    shutdown     │  │                    │ │
│   └────────┬────────┘  └────────┬────────┘  └────────┬───────────┘ │
│            │                    │                     │             │
│   ┌────────▼────────┐  ┌───────▼─────────┐  ┌───────▼───────────┐ │
│   │ ProcessManager  │  │ CameraManager   │  │ Config (Pydantic) │ │
│   │ (singleton)     │  │ (singleton)     │  │                   │ │
│   │                 │  │                 │  │ ~/.tensi_trossen_  │ │
│   │ Spawns lerobot  │  │ Background      │  │   studio/         │ │
│   │ CLI as sub-     │  │ capture threads │  │   config.json     │ │
│   │ process         │  │ per camera      │  │                   │ │
│   └────────┬────────┘  └────────┬────────┘  └───────────────────┘ │
│            │                    │                                   │
│   ┌────────▼────────┐  ┌───────▼─────────┐                        │
│   │ Leader Service  │  │                 │                         │
│   │ Routes          │  │ pyrealsense2    │                         │
│   │ /api/leader-    │  │ + OpenCV        │                         │
│   │   service/      │  │                 │                         │
│   │   start|stop|   │  │ RealSense USB   │                         │
│   │   status|logs   │  │ cameras         │                         │
│   │ (SSH to PC2)    │  │                 │                         │
│   └─────────────────┘  └─────────────────┘                        │
│                                                                     │
│   Python 3.10+ / FastAPI / uvicorn / Pydantic                       │
└─────────────────────────────────────────────────────────────────────┘
                               │
                   Spawns as subprocess
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LeRobot CLI (subprocess)                          │
│                                                                     │
│   lerobot-teleoperate / lerobot-record / lerobot-train / replay     │
│                                                                     │
│   ┌───────────────────────┐    ┌──────────────────────────────────┐ │
│   │ Follower Robot Plugin │    │ Teleoperator Plugin              │ │
│   │ widowxai_follower     │    │                                  │ │
│   │                       │    │  LOCAL: widowxai_leader_teleop   │ │
│   │ Connects to follower  │    │    → direct Ethernet to leader   │ │
│   │ via Ethernet          │    │                                  │ │
│   │ TCP:50001 + UDP:50000 │    │  REMOTE: remote_leader_teleop   │ │
│   │                       │    │    → TCP to leader_service.py    │ │
│   └───────────┬───────────┘    └──────────────┬───────────────────┘ │
│               │                                │                    │
│   ~/lerobot_trossen (uv project)                                    │
└───────────────┼────────────────────────────────┼────────────────────┘
                │                                │
                ▼                                ▼
        ┌───────────────┐          ┌──────────────────────────┐
        │ Follower Robot│          │ Leader Robot              │
        │ iNerve        │          │ (local or remote)        │
        │ 192.168.1.5   │          │                          │
        │               │          │ LOCAL: 192.168.1.2       │
        │ Ethernet via  │          │   direct Ethernet        │
        │ NetGear switch│          │                          │
        └───────────────┘          │ REMOTE: via TCP:5555     │
                                   │   to leader_service.py   │
                                   └──────────────────────────┘
```

---

## Distributed Architecture (Two-PC)

When leader and follower robots are on separate networks:

```
  PC2 (Leader Side)                                PC1 (Follower Side)
  e.g. Toronto                                     e.g. Montreal
┌──────────────────────────────┐                 ┌────────────────────────────────────┐
│                              │                 │                                    │
│  ┌────────────────────────┐  │                 │  ┌──────────────────────────────┐  │
│  │ Leader Robot            │  │                 │  │ Follower Robot                │  │
│  │ 192.168.1.2             │  │                 │  │ 192.168.1.5                   │  │
│  └──────────┬─────────────┘  │                 │  └──────────┬───────────────────┘  │
│             │ Ethernet       │                 │             │ Ethernet              │
│             │ TCP:50001      │                 │             │ TCP:50001              │
│             │ UDP:50000      │                 │             │ UDP:50000              │
│             │                │                 │             │                       │
│  ┌──────────▼─────────────┐  │                 │  ┌──────────▼───────────────────┐  │
│  │ trossen_arm driver      │  │                 │  │ trossen_arm driver            │  │
│  │ (local, < 1ms latency) │  │                 │  │ (local, < 1ms latency)       │  │
│  └──────────┬─────────────┘  │                 │  └──────────▲───────────────────┘  │
│             │                │                 │             │                       │
│  ┌──────────▼─────────────┐  │     WiFi /      │  ┌──────────┴───────────────────┐  │
│  │ leader_service.py       │  │      WAN        │  │ lerobot-teleoperate          │  │
│  │                         │  │    ~2 KB/s      │  │ + RemoteLeaderTeleop plugin  │  │
│  │ Reads joint positions   │  │                 │  │                              │  │
│  │ at 60 Hz                ├──┼── TCP:5555 ────►│  │ Receives joint positions     │  │
│  │                         │  │                 │  │ Sends to follower driver     │  │
│  │ Streams 7 floats as     │  │                 │  │                              │  │
│  │ newline-delimited JSON  │  │                 │  └──────────────────────────────┘  │
│  └─────────────────────────┘  │                 │                                    │
│                              │                 │  ┌──────────────────────────────┐  │
│  Python 3.10 + trossen_arm   │                 │  │ FastAPI Backend (:8000)       │  │
│                              │                 │  │ React Frontend (:5173)        │  │
│                              │                 │  │ RealSense Cameras (USB)       │  │
│                              │                 │  └──────────────────────────────┘  │
│                              │                 │                                    │
└──────────────────────────────┘                 └────────────────────────────────────┘

        NetGear Switch 2                                  NetGear Switch 1
     (192.168.1.x Ethernet)                            (192.168.1.x Ethernet)
```

### Key Design Decision

The Trossen iNerve controller uses a proprietary protocol (TCP:50001 + UDP:50000) that requires sub-millisecond latency. This protocol **cannot** be relayed over WiFi or WAN. The solution is to run the `trossen_arm` driver **locally** on each robot's PC and only stream high-level joint positions (7 floats) over the network.

| | Raw iNerve Protocol | Leader Service Protocol |
|---|---|---|
| Latency tolerance | < 1ms | 50-200ms |
| Protocol | TCP:50001 + UDP:50000 | Single TCP:5555 |
| Bandwidth | Driver-dependent | ~2 KB/s |
| NAT/Firewall | Not friendly (UDP) | Friendly (single TCP port) |
| WAN capable | No | Yes |

---

## Component Details

### Frontend (React + TypeScript)

```
frontend/src/
├── App.tsx                 # Dashboard layout: StatusBar + grid + ProcessLog
├── api/client.ts           # REST client for all backend APIs
├── index.css               # Tailwind + shared component styles
└── components/
    ├── StatusBar.tsx        # Sticky header: mode pill, connection indicators, settings gear
    ├── ActionPanel.tsx      # Workflow cards: Leader Svc, Teleoperate, Record, Train, Replay
    ├── CameraViewer.tsx     # Live MJPEG camera feed viewer with diagnostics
    ├── ConfigForm.tsx       # Slide-over settings panel (robot, cameras, paths)
    └── ProcessLog.tsx       # Real-time subprocess output with auto-scroll
```

**Data flow**: The frontend polls `/api/process/status` every 1.5s (when a process is running) or 3s (idle). It polls `/api/leader-service/status` every 5s when remote leader mode is enabled. Camera feeds are MJPEG streams fetched as `<img>` tags pointing at `/api/cameras/stream/<key>`.

### Backend (FastAPI)

```
backend/app/
├── main.py                 # FastAPI app, CORS, lifespan, router registration
├── config.py               # Pydantic models, load/save to ~/.tensi_trossen_studio/config.json
├── routes/
│   ├── config_routes.py    # GET/POST /api/config
│   ├── process_routes.py   # Start/stop teleoperate, record, train, replay
│   ├── camera_routes.py    # Camera stream, detect, status, shutdown
│   └── leader_service_routes.py  # Start/stop/status/logs of remote leader via SSH
└── services/
    ├── process_manager.py  # Singleton — spawns lerobot CLI as subprocess, captures stdout
    ├── camera_manager.py   # Singleton — manages RealSense cameras with background threads
    └── camera_streamer.py  # MJPEG streaming response generator
```

**Singletons**:
- `ProcessManager` — ensures only one lerobot process runs at a time. Captures subprocess stdout into a rolling 500-line log buffer. Cleans subprocess environment (removes `VIRTUAL_ENV`, `PYTHONPATH`) so `uv run` resolves correctly.
- `CameraManager` — manages `ManagedCamera` instances, each with a background capture thread. Thread-safe frame access. Cameras are automatically released before teleoperation/recording (since the lerobot process needs exclusive USB access) and restarted after.

### LeRobot Integration

The backend spawns lerobot CLI tools as subprocesses:

| CLI Command | Backend Route | Purpose |
|---|---|---|
| `lerobot-teleoperate` | `/api/teleoperate/start` | Real-time leader-follower control |
| `lerobot-record` | `/api/record/start` | Record demonstration episodes |
| `lerobot-train` | `/api/train/start` | Train ACT/Diffusion policy |
| `lerobot-replay` | `/api/replay/start` | Replay recorded episodes |

Commands are run via `uv run` inside the `~/lerobot_trossen` project directory. The `ProcessManager` dynamically constructs CLI arguments from the config:

- **Local mode**: `--teleop.type=widowxai_leader_teleop --teleop.ip_address=192.168.1.2`
- **Remote mode**: `--teleop.type=remote_leader_teleop --teleop.host=192.168.2.138 --teleop.port=5555`

### Leader Service (`leader_service.py`)

A standalone Python script that runs on PC2 (the leader robot's PC). It:

1. Connects to the leader robot locally using `trossen_arm.TrossenArmDriver()`
2. Accepts one TCP client connection at a time
3. On `configure` command: moves leader to staged position, enables gravity compensation
4. Streams joint positions (7 floats) as newline-delimited JSON at 60 Hz
5. On `disconnect` command or client drop: moves leader to staged → sleep → releases driver

**Protocol** (newline-delimited JSON over TCP):

```
Client → Server:
  {"cmd": "configure"}          Start and configure the leader
  {"cmd": "disconnect"}         Graceful disconnect
  {"cmd": "ping"}               Health check

Server → Client:
  {"type": "configured", "joints": 7}     Leader ready
  {"type": "positions", "v": [...], "t": N}  Joint positions (7 floats)
  {"type": "disconnected"}                 Leader disconnected
  {"type": "pong"}                         Health check response
  {"type": "error", "msg": "..."}          Error occurred
```

### RemoteLeaderTeleop (LeRobot Plugin)

A custom LeRobot teleoperator plugin (`remote_leader_teleop`) in the `lerobot_teleoperator_trossen` package:

- `config_remote_leader.py` — `RemoteLeaderTeleopConfig` dataclass registered as `"remote_leader_teleop"`
- `remote_leader.py` — `RemoteLeaderTeleop` class that connects to `leader_service.py` over TCP, runs a background receiver thread, and returns the latest joint positions via `get_action()`

### Leader Service Management (SSH)

The backend manages the leader service on PC2 remotely via SSH:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/leader-service/status` | GET | Check if `leader_service.py` is running on PC2 |
| `/api/leader-service/start` | POST | Start `leader_service.py` on PC2 via `nohup` + SSH |
| `/api/leader-service/stop` | POST | Kill `leader_service.py` on PC2 via SSH |
| `/api/leader-service/logs` | GET | Fetch `/tmp/leader_service.log` from PC2 via SSH |

Requires passwordless SSH access (`ssh-copy-id`) from PC1 to PC2.

---

## Data Flow: Teleoperation (Distributed)

```
1. User clicks "Start Leader" in web UI
   Browser → POST /api/leader-service/start → SSH → PC2: nohup leader_service.py

2. User clicks "Start Teleoperation"
   Browser → POST /api/teleoperate/start
     → ProcessManager.start_teleoperate()
       → CameraManager.shutdown_all() (release USB cameras)
       → subprocess: uv run lerobot-teleoperate
           --robot.type=widowxai_follower_robot
           --robot.ip_address=192.168.1.5
           --teleop.type=remote_leader_teleop
           --teleop.host=192.168.2.138
           --teleop.port=5555

3. RemoteLeaderTeleop connects to leader_service.py on PC2
   PC1:RemoteLeaderTeleop → TCP:5555 → PC2:leader_service.py
     → sends {"cmd": "configure"}
     → receives {"type": "configured", "joints": 7}

4. Streaming loop (60 Hz):
   PC2: leader_service.py reads leader joints via trossen_arm driver
     → sends {"type": "positions", "v": [0.1, 0.5, ...], "t": 42}
   PC1: RemoteLeaderTeleop receives positions
     → lerobot control loop reads via get_action()
     → sends to follower robot via local trossen_arm driver

5. User clicks "Stop"
   Browser → POST /api/process/stop
     → ProcessManager.stop() → SIGTERM to lerobot process
     → RemoteLeaderTeleop sends {"cmd": "disconnect"} to leader_service.py
     → leader_service.py moves leader to staged → sleep → releases driver
```

---

## Network Topology

```
┌─────────────────────────────────────────────────────┐
│                  WiFi Network (192.168.2.x)          │
│                                                     │
│   PC1: 192.168.2.140              PC2: 192.168.2.138│
│     │                               │               │
│     │  TCP:5555 (leader service)     │               │
│     │  SSH:22 (management)           │               │
│     ◄────────────────────────────────►               │
└─────────────────────────────────────────────────────┘

┌──────────────────────┐       ┌──────────────────────┐
│ Ethernet 192.168.1.x │       │ Ethernet 192.168.1.x │
│ (NetGear Switch 1)   │       │ (NetGear Switch 2)   │
│                      │       │                      │
│ PC1: 192.168.1.100   │       │ PC2: 192.168.1.x     │
│ Follower: 192.168.1.5│       │ Leader: 192.168.1.2  │
│ (+ Leader 2: .1.3)   │       │                      │
└──────────────────────┘       └──────────────────────┘
```

- Each Ethernet network is isolated (no routing between them)
- WiFi carries only the leader service TCP stream (~2 KB/s) and SSH management
- The iNerve controllers require a network switch (direct PC-to-iNerve fails)

---

## Configuration Model

```
AppConfig
├── robot: RobotConfig
│   ├── leader_ip: str                    # Direct leader IP (local mode)
│   ├── follower_ip: str                  # Follower robot IP
│   ├── remote_leader: bool               # Enable remote leader mode
│   ├── remote_leader_host: str           # PC2 WiFi IP
│   ├── remote_leader_port: int           # Leader service TCP port
│   ├── use_top_camera_only: bool         # Skip wrist camera
│   ├── cameras: dict[str, CameraConfig]  # Camera definitions
│   ├── camera_service_url: str | None    # Remote camera service URL
│   └── enable_local_cameras: bool        # Whether this PC manages cameras
├── dataset: DatasetConfig
│   ├── repo_id, num_episodes, episode_time_s, reset_time_s
│   ├── single_task, push_to_hub
├── train: TrainConfig
│   ├── dataset_repo_id, policy_type, output_dir, job_name, policy_repo_id
├── replay: ReplayConfig
│   ├── repo_id, episode
└── lerobot_trossen_path: str             # Path to ~/lerobot_trossen
```

Persisted at `~/.tensi_trossen_studio/config.json`. Loaded on every API request (no restart needed).

---

## API Reference

### Config
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Get current configuration |
| POST | `/api/config` | Save configuration |

### Process Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/teleoperate/start` | Start teleoperation |
| POST | `/api/teleoperate/stop` | Stop teleoperation |
| POST | `/api/record/start` | Start recording |
| POST | `/api/record/stop` | Stop recording |
| POST | `/api/train/start` | Start training |
| POST | `/api/train/stop` | Stop training |
| POST | `/api/replay/start` | Start replay |
| POST | `/api/replay/stop` | Stop replay |
| POST | `/api/process/stop` | Stop any running process |
| GET | `/api/process/status` | Get process mode, running state, PID, logs |

### Cameras
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cameras/stream/{key}` | MJPEG stream for a camera (`wrist`, `top`, `operator`) |
| GET | `/api/cameras/detect` | Detect connected RealSense cameras |
| GET | `/api/cameras/usb-devices` | List USB video devices (index, path, name) for operator view camera |
| GET | `/api/cameras/status` | Get status of all configured cameras (including operator if set) |
| POST | `/api/cameras/shutdown` | Release only teleop cameras; operator camera stays on |

### Leader Service (Remote)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/leader-service/status` | Check if leader service is running on PC2 |
| POST | `/api/leader-service/start` | Start leader service on PC2 via SSH |
| POST | `/api/leader-service/stop` | Stop leader service on PC2 via SSH |
| GET | `/api/leader-service/logs` | Get recent logs from PC2 |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Backend health check |

---

## Operator view camera (USB)

A separate USB camera (e.g. webcam) can be configured as **operator view**: it is streamed in the UI but **not** used for teleoperation or recording and is **not** shut down when starting teleop/record. Config key: `robot.operator_camera` (optional). Backend uses `ManagedUSBCamera` (OpenCV) and stream key `operator`. The frontend shows an "Operator view" tile when `operator_camera` is set. Device index can be discovered via **Detect USB cameras** in Settings or via `GET /api/cameras/usb-devices`. See [docs/STUDIO-USER-GUIDE.md](STUDIO-USER-GUIDE.md).

---

## Launcher (PC1)

`launcher.py` at repo root is a tkinter GUI that starts/stops the backend and frontend, and lets the user view/edit PC1 and PC2 IPs (WiFi and Ethernet). Config: `~/.tensi_trossen_studio/launcher.json`. If port 8000 is in use, the launcher can free it and start the backend. See [docs/STUDIO-USER-GUIDE.md](STUDIO-USER-GUIDE.md).

---

## Testing Architecture

The project uses a layered test strategy matching the test pyramid:

```
    ┌───────────────────────┐
    │  Manual Hardware E2E  │  docs/HARDWARE-TEST-CHECKLIST.md
    │  (robots + cameras)   │  Run before releases
    ├───────────────────────┤
    │  Backend API           │  test_api.py (12 tests)
    │  Integration           │  FastAPI TestClient, mocked services
    ├───────────────────────┤
    │  Backend Unit          │  test_config.py (16), test_process_manager.py (17)
    │  Tests                 │  test_route_helpers.py (11), test_leader_service.py (12)
    ├───────────────────────┤
    │  Frontend Unit         │  client.test.ts (21), 5 component tests (25)
    │  Tests                 │  vitest + @testing-library/react + jsdom
    └───────────────────────┘
```

**Total: 114 automated tests** (68 backend + 46 frontend)

### Backend Test Infrastructure

```
backend/tests/
├── conftest.py                    # Shared fixtures
│   ├── tmp_config_path            # Patches get_config_path() to temp dir
│   ├── sample_config              # Known AppConfig with test values
│   ├── sample_remote_config       # Same + remote_leader=True
│   ├── reset_process_manager      # Auto-resets singleton between tests
│   └── mock_popen                 # Captures subprocess commands
├── test_config.py                 # Pydantic models, load/save, validation
├── test_process_manager.py        # CLI arg building, stop/kill logic
├── test_route_helpers.py          # _robot_config, _dataset_config helpers
├── test_leader_service_routes.py  # SSH command construction and parsing
└── test_api.py                    # Full HTTP request/response cycles
```

**Strategy**: All hardware and network I/O is mocked. `subprocess.Popen` is patched to capture CLI commands without spawning processes. `subprocess.run` is patched for SSH tests. Config persistence uses temp directories. The `ProcessManager` singleton is reset between every test.

**Run**: `cd backend && uv run pytest tests/ -v`

### Frontend Test Infrastructure

```
frontend/
├── vitest.config.ts               # jsdom environment, globals, setup
├── src/
│   ├── test-setup.ts              # @testing-library/jest-dom matchers
│   ├── api/client.test.ts         # Mock fetch, test all 20+ API functions
│   └── components/
│       ├── StatusBar.test.tsx     # Title, mode pill, indicators
│       ├── ActionPanel.test.tsx   # Cards, leader service, running state
│       ├── ProcessLog.test.tsx    # Logs, line count, error footer
│       ├── ConfigForm.test.tsx    # Slide-over, fields, remote toggle
│       └── CameraViewer.test.tsx  # Camera labels, no-cameras state
```

**Strategy**: `globalThis.fetch` is mocked to return controlled responses. `vi.mock('../api/client')` is used in component tests to isolate rendering from API calls. All tests run in jsdom (no browser required).

**Run**: `cd frontend && npm test`

### Manual Hardware Checklist

`docs/HARDWARE-TEST-CHECKLIST.md` provides a structured checklist for tests requiring physical robots and cameras:

- **Single-PC**: teleoperation mirroring, recording episodes, training, replay
- **Camera**: streaming, camera-process handoff (release for lerobot), error recovery
- **Distributed**: leader service start/stop from web UI, cross-PC teleoperation, graceful and unexpected disconnects, network interruption
- **UI verification**: StatusBar indicators, settings panel persistence

---

## Dependencies

### Backend (Python)
- `fastapi` + `uvicorn` — web framework and ASGI server
- `pydantic` — configuration validation
- `pyrealsense2` — Intel RealSense camera SDK
- `opencv-python-headless` — image encoding (JPEG)
- `numpy` — array operations
- `requests` / `httpx` — HTTP client for remote camera service

### Backend Testing
- `pytest` >= 8.0 — test runner
- `pytest-asyncio` >= 0.23 — async test support
- `httpx` >= 0.27 — async HTTP client (FastAPI TestClient)
- `coverage` >= 7.0 — code coverage reporting

### Frontend (Node.js)
- `react` + `react-dom` — UI framework
- `vite` — dev server and bundler
- `tailwindcss` + `postcss` + `autoprefixer` — styling
- `typescript` — type safety

### Frontend Testing
- `vitest` — test runner (Vite-native)
- `@testing-library/react` — component rendering and queries
- `@testing-library/jest-dom` — DOM assertion matchers
- `@testing-library/user-event` — user interaction simulation
- `jsdom` — browser environment for Node.js

### External
- `lerobot` + `lerobot_teleoperator_trossen` — robot control framework and Trossen plugin
- `trossen_arm` — Trossen robot driver (required on both PCs for distributed setup)
- `uv` — Python package manager (runs lerobot CLI)
