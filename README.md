# TENSI Trossen Studio

> **Web-based control interface for LeRobot Trossen robots with distributed teleoperation support**

A comprehensive system for teleoperating, recording, training, and replaying Trossen robotic arms using LeRobot, featuring UDP-over-SSH tunneling for distributed multi-PC setups.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

### Core Functionality
- 🎮 **Teleoperation** - Real-time leader-follower robot control
- 📹 **Recording** - Capture demonstration episodes with camera feeds
- 🧠 **Training** - Train AI policies on collected data
- ▶️ **Replay** - Test learned behaviors on physical robots
- 📷 **Camera Streaming** - Live RealSense camera feeds in web UI

### Advanced Features
- 🌐 **Distributed Teleoperation** - Operate robots across multiple PCs over network
- 🔒 **UDP-over-SSH Tunneling** - Secure robot communication through SSH
- 🎥 **Camera Manager** - Conflict-free camera access between streaming and teleoperation
- 🔧 **Web Configuration** - Easy setup through browser interface
- 📊 **Real-time Monitoring** - Live process logs and status updates

## 📋 Table of Contents

- [Quick Start (Single PC)](#quick-start-single-pc)
- [Distributed Setup (Multi-PC)](#distributed-setup-multi-pc)
- [Configuration](#configuration)
- [Usage](#usage)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start (Single PC)

### Prerequisites

- **lerobot_trossen**: Clone and install at `~/lerobot_trossen`. See [Trossen LeRobot docs](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin.html)
- **uv**: Python package manager - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Node.js & npm**: For the frontend - [nodejs.org](https://nodejs.org/)
- **RealSense cameras**: Connected via USB
- **Trossen robots**: Leader and follower with iNerve controllers

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/hmazin/tensi-trossen-studio.git
   cd tensi-trossen-studio
   ```

2. **Start the backend**
   ```bash
   cd backend
   uv sync
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the frontend** (in a new terminal)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Open in browser**
   ```
   http://localhost:5173
   ```

### First-Time Configuration

1. Open the web UI
2. Configure robot IPs (default: Leader `192.168.1.2`, Follower `192.168.1.5`)
3. Set camera serial numbers (find with `uv run lerobot-find-cameras realsense`)
4. Verify LeRobot Trossen path (default: `~/lerobot_trossen`)
5. Click **Save Config**

## 🌐 Distributed Setup (Multi-PC)

**Use case:** Operate leader and follower robots from separate computers connected via WiFi.

### Architecture Overview

```
PC1 (Operator Station)          PC2 (Leader Robot Station)
├─ Backend + Frontend          ├─ Leader Robot
├─ Follower Robot              └─ UDP Relay (socat)
├─ RealSense Cameras           
└─ SSH Tunnel Client ─WiFi────> SSH Tunnel Server
         UDP-over-SSH tunneling
```

### Prerequisites

- **2 PCs** with WiFi and Ethernet
- **2 NetGear switches** (one per PC)
- **SSH access** between PCs
- **socat** installed on both PCs

### Quick Setup

1. **Hardware Connection**
   ```
   PC1 Ethernet → NetGear 1 → Follower iNerve + Cameras
   PC2 Ethernet → NetGear 2 → Leader iNerve
   Both PCs connected via WiFi
   ```

2. **On PC1, start tunnels**
   ```bash
   cd tensi-trossen-studio
   ./deployment/start-all-tunnels.sh
   ```

3. **Start backend and frontend** (same as single PC setup)

4. **Verify and test**
   ```bash
   ./deployment/test-setup.sh
   ```

### Documentation

Complete distributed setup guide: [`deployment/SETUP-WITH-TWO-SWITCHES.md`](deployment/SETUP-WITH-TWO-SWITCHES.md)

Quick reference: [`deployment/QUICK-START.md`](deployment/QUICK-START.md)

Pre-flight checklist: [`deployment/PRE-FLIGHT-CHECKLIST.md`](deployment/PRE-FLIGHT-CHECKLIST.md)

## ⚙️ Configuration

Configuration is stored in `~/.tensi_trossen_studio/config.json` with the following structure:

```json
{
  "robot": {
    "leader_ip": "192.168.1.2",
    "follower_ip": "192.168.1.5",
    "cameras": {
      "wrist": { "serial_number_or_name": "218622275782" },
      "top": { "serial_number_or_name": "218622278263" }
    }
  },
  "dataset": {
    "repo_id": "username/dataset_name",
    "num_episodes": 10
  },
  "lerobot_trossen_path": "/home/user/lerobot_trossen"
}
```

**For distributed setup**, set `leader_ip` to `127.0.0.1` to route through SSH tunnel.

## 📖 Usage

### Teleoperation

1. Click **"Start Teleoperation"**
2. Move the leader robot arm
3. Follower robot mirrors movements
4. Click **"Stop"** when done

### Recording Episodes

1. Set dataset name and number of episodes
2. Define task description
3. Click **"Start Recording"**
4. Perform demonstrations
5. Episodes saved to LeRobot dataset

### Training

1. Select dataset repository ID
2. Configure policy type (ACT, Diffusion, etc.)
3. Click **"Start Training"**
4. Monitor training progress

### Replay

1. Select dataset and episode number
2. Click **"Start Replay"**
3. Robot executes learned behavior

## 🏗️ Architecture

### System Components

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │ HTTP
┌────────▼────────┐
│  Frontend (UI)  │  React + Vite + Tailwind
└────────┬────────┘
         │ REST API
┌────────▼────────┐
│ Backend (API)   │  FastAPI + uvicorn
├─────────────────┤
│ Camera Manager  │  Singleton pattern
│ Process Manager │  Subprocess control
│ Config Manager  │  Pydantic models
└────────┬────────┘
         │
┌────────▼────────┐
│  lerobot_trossen │  LeRobot CLI tools
└─────────────────┘
```

### Key Technologies

- **Backend**: FastAPI, Python 3.12+, uvicorn
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Camera**: pyrealsense2, OpenCV
- **Networking**: SSH tunneling, socat (for UDP-over-SSH)
- **Robot Control**: LeRobot Trossen plugin

### Camera Manager

Singleton pattern ensures only one process accesses cameras at a time:
- Automatically releases cameras before teleoperation
- Restarts streaming after teleoperation ends
- Thread-safe frame capture

### UDP-over-SSH Tunneling

For distributed setups, UDP robot communication is tunneled over SSH:

```
PC1: UDP:50000 → socat → TCP:15000 → SSH → PC2:TCP:15000 → socat → UDP:50000 → Robot
```

Technical details: [`deployment/UDP-ARCHITECTURE.md`](deployment/UDP-ARCHITECTURE.md)

## 📚 Documentation

### Setup Guides
- [`deployment/SETUP-WITH-TWO-SWITCHES.md`](deployment/SETUP-WITH-TWO-SWITCHES.md) - Complete distributed setup
- [`deployment/QUICK-START.md`](deployment/QUICK-START.md) - Quick reference
- [`deployment/PRE-FLIGHT-CHECKLIST.md`](deployment/PRE-FLIGHT-CHECKLIST.md) - Testing checklist

### Technical Documentation
- [`deployment/UDP-ARCHITECTURE.md`](deployment/UDP-ARCHITECTURE.md) - UDP tunneling details
- [`deployment/IMPLEMENTATION-SUMMARY.md`](deployment/IMPLEMENTATION-SUMMARY.md) - Technical implementation
- [`deployment/README.md`](deployment/README.md) - Deployment overview

### Scripts
- `deployment/start-all-tunnels.sh` - Start distributed system
- `deployment/stop-all-tunnels.sh` - Stop all processes
- `deployment/test-setup.sh` - Verify configuration

## 🐛 Troubleshooting

### Common Issues

**Camera shows "Camera unavailable"**
```bash
# Check if another process is using cameras
pgrep -af lerobot

# Kill processes and restart backend
pkill -f lerobot
```

**Leader robot not responding (distributed setup)**
```bash
# Verify network connectivity
ssh user@pc2 'ping -c 2 192.168.1.2'

# Check tunnels are running
./deployment/test-setup.sh
```

**iNerve controller shows red LED**
- Power cycle the iNerve controller
- Wait for green LED before attempting teleoperation
- Ensure proper connection through network switch (not direct PC connection)

**SSH tunnel drops**
```bash
# Restart tunnels
./deployment/stop-all-tunnels.sh
./deployment/start-all-tunnels.sh
```

### Logs

- **Backend logs**: Check terminal running uvicorn
- **PC1 socat logs**: `/tmp/socat-pc1.log`
- **PC2 socat logs**: `ssh user@pc2 'cat /tmp/socat.log'`

## 🛠️ Project Structure

```
tensi-trossen-studio/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Main application
│   │   ├── config.py          # Configuration models
│   │   ├── routes/            # API endpoints
│   │   │   ├── camera_routes.py
│   │   │   ├── process_routes.py
│   │   │   └── config_routes.py
│   │   └── services/          # Business logic
│   │       ├── camera_manager.py
│   │       └── process_manager.py
│   ├── camera_service.py      # Standalone camera service
│   └── pyproject.toml         # Python dependencies
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.tsx            # Main app component
│   │   ├── api/               # API client
│   │   └── components/        # React components
│   ├── .env.development       # Local dev config
│   ├── .env.production        # Distributed config
│   └── package.json           # Node dependencies
└── deployment/                 # Deployment scripts & docs
    ├── start-all-tunnels.sh   # Start script
    ├── stop-all-tunnels.sh    # Stop script
    ├── test-setup.sh          # Verification script
    └── *.md                   # Documentation
```

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

- **Author**: Hooman
- **Email**: hooman.mazin@gmail.com
- **GitHub**: [@hmazin](https://github.com/hmazin)

## 🙏 Acknowledgments

- [LeRobot](https://github.com/huggingface/lerobot) by Hugging Face
- [Trossen Robotics](https://www.trossenrobotics.com/) for WidowX robotic arms
- Intel RealSense SDK

## 🔗 Related Projects

- [lerobot_trossen](https://docs.trossenrobotics.com/trossen_arm/main/tutorials/lerobot_plugin.html) - Trossen plugin for LeRobot
- [LeRobot](https://github.com/huggingface/lerobot) - Robot learning toolkit

---

**⭐ Star this repo if you find it useful!**
