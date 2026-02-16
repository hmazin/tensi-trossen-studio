# Remote Leader Setup (Distributed Teleoperation)

## Overview

This setup enables teleoperation where the **leader** and **follower** robots are on different
networks — different floors, buildings, or even cities (e.g., Montreal ↔ Toronto).

Instead of trying to relay the Trossen iNerve's raw TCP/UDP protocol over the network
(which fails due to sub-millisecond latency requirements), we run a **Leader Service** on
the PC physically connected to the leader robot. This service:

1. Connects to the leader locally (direct Ethernet, zero latency)
2. Reads joint positions at 60 Hz
3. Streams them over a simple TCP connection to the remote PC

The remote PC (with the follower) uses a **RemoteLeaderTeleop** plugin that receives
these positions over the network instead of talking to the robot directly.

## Architecture

```
PC2 (Leader Side - e.g., Toronto)         PC1 (Follower Side - e.g., Montreal)
┌──────────────────────────────┐          ┌──────────────────────────────────┐
│                              │          │                                  │
│  Leader Robot                │          │  Follower Robot                  │
│  (192.168.1.2)               │          │  (192.168.1.5)                   │
│       │                      │          │       │                          │
│       │ Ethernet (< 1ms)     │          │       │ Ethernet (< 1ms)         │
│       │                      │          │       │                          │
│  ┌────▼─────────────┐       │          │  ┌────▼──────────────────────┐   │
│  │  leader_service   │       │          │  │  lerobot-teleoperate      │   │
│  │  (python3)        │       │          │  │  + RemoteLeaderTeleop     │   │
│  │                   │       │   WiFi/  │  │                           │   │
│  │  TCP:5555 ────────┼───────┼── WAN ──►│  │  Reads positions from     │   │
│  │  Streams 7 floats │       │  ~1.7KB/s│  │  network, sends to        │   │
│  │  @ 60 Hz          │       │          │  │  follower robot            │   │
│  └───────────────────┘       │          │  └───────────────────────────┘   │
│                              │          │                                  │
└──────────────────────────────┘          └──────────────────────────────────┘
```

## Why This Works Over WAN

| Aspect | Raw iNerve Protocol | Leader Service |
|--------|---------------------|----------------|
| Latency tolerance | < 1ms | 50-200ms OK |
| Protocol | TCP:50001 + UDP:50000 | Single TCP:5555 |
| Bandwidth | Depends on driver | ~1.7 KB/s |
| NAT-friendly | No (UDP) | Yes (TCP only) |
| Firewall-friendly | No | Yes (single port) |

## Prerequisites

### PC2 (Leader Side)
- Python 3.10+ with `trossen_arm` package installed
- Leader robot connected via NetGear switch (Ethernet)
- Network connectivity to PC1 (WiFi, LAN, or internet)

### PC1 (Follower Side)
- Full TENSI Trossen Studio setup (backend, frontend, lerobot)
- Follower robot connected via NetGear switch (Ethernet)
- Cameras connected via USB
- Network connectivity to PC2

## Quick Start

### Step 1: Enable Remote Leader in the Web UI

1. Open http://localhost:5173
2. Click the **gear icon** (top-right) to open Settings
3. Enable **Remote Leader Mode**
4. Set **Leader Service Host** to PC2's WiFi IP (e.g., `192.168.2.138`)
5. Set **Leader Service Port** to `5555`
6. Click **Save Settings**

Or edit `~/.tensi_trossen_studio/config.json` directly:
```json
{
  "robot": {
    "remote_leader": true,
    "remote_leader_host": "192.168.2.138",
    "remote_leader_port": 5555,
    "follower_ip": "192.168.1.5"
  }
}
```

### Step 2: Start the Leader Service

**Option A: From the web UI (recommended):**

The dashboard shows a **Leader Service** card at the top of the actions panel. Click **Start Leader** to launch `leader_service.py` on PC2 via SSH. The card shows live status (Running/Stopped).

**Option B: From PC1 terminal (via SSH):**
```bash
cd ~/tensi-trossen-studio
./deployment/start-remote-leader.sh
```

**Option C: Directly on PC2:**
```bash
python3 -u ~/leader_service.py --ip 192.168.1.2 --port 5555 --fps 60
```

**Option D: As a systemd service on PC2 (auto-start on boot):**
```bash
# One-time setup on PC2:
sudo cp leader-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable leader-service
sudo systemctl start leader-service
```

### Step 3: Start Teleoperation

1. Verify the Leader Service card shows **Running** (green indicator)
2. Click **Start Teleoperation**
3. The system connects to the leader service on PC2 automatically
4. Move the leader arm — the follower mirrors in real-time

## Web UI Controls

The dashboard provides full control over the distributed system:

- **Status bar** (top) — shows mode (Idle/Teleoperating/Recording), follower IP, and leader service connection status with color-coded indicators
- **Leader Service card** — Start/Stop the leader service on PC2 with one click, shows live Running/Stopped status
- **Action cards** — Teleoperate, Record, Train, Replay — each with its own controls. Teleoperate and Record are disabled until the leader service is running.
- **Settings panel** (gear icon) — configure IPs, remote leader mode, cameras
- **Process Log** — real-time output from running processes

## Monitoring

### From the Web UI

The Leader Service card shows real-time status. The backend polls PC2 via SSH every 5 seconds.

### Leader Service Logs (on PC2)
```bash
tail -f /tmp/leader_service.log
```

### Expected Log Output
```
[INFO] Leader service listening on :5555
[INFO] Leader robot IP: 192.168.1.2
[INFO] Waiting for client connection...
[INFO] Client connected from ('192.168.2.140', 54321)
[INFO] Configuring leader at 192.168.1.2...
[INFO] Leader configured and ready (gravity compensation active).
```

## Stopping

### From the Web UI (recommended)

1. Click **Stop** on the running process (teleoperate/record)
2. Click **Stop Leader** on the Leader Service card

The leader service performs a graceful shutdown: it moves the leader arm to its staged position, then sleep position, and releases the driver. If the client disconnects unexpectedly, the same cleanup runs automatically.

### From the Terminal

```bash
# Stop teleoperation
curl -X POST http://localhost:8000/api/teleoperate/stop

# Stop leader service via the backend API
curl -X POST http://localhost:8000/api/leader-service/stop

# Or directly via SSH
ssh hadi@192.168.2.138 'pkill -f leader_service.py'
```

## Troubleshooting

### "Cannot reach Leader Service"
- Check PC2 is running `leader_service.py`
- Check network: `ping 192.168.2.138`
- Check port: `nc -zv 192.168.2.138 5555`
- Check firewall on PC2: `sudo ufw allow 5555/tcp`

### Leader iNerve LED is RED
- Power cycle the leader iNerve controller
- Wait for GREEN LED
- Restart leader_service.py

### Positions feel laggy
- Check WiFi latency: `ping 192.168.2.138`
- For WAN: 50-100ms is normal and acceptable
- Reduce streaming FPS if bandwidth is limited: `--fps 30`

### "No position data received"
- Leader service may have crashed — check logs on PC2
- Network may have dropped — restart leader_service.py

## For WAN Deployment (Different Cities)

For Montreal ↔ Toronto deployment:

1. **VPN or port forwarding** — PC2 needs TCP port 5555 accessible from PC1
2. **Set host to WAN IP** — Use PC2's public IP or VPN IP
3. **Consider latency** — Expect 20-50ms over WAN (perfectly acceptable)
4. **Consider security** — Use VPN (WireGuard/Tailscale) for encrypted tunnel

### Using Tailscale (Recommended for WAN)
```bash
# Install on both PCs
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# PC2's Tailscale IP (e.g., 100.x.y.z)
# Set remote_leader_host to this IP in config
```

## Files

| File | Location | Purpose |
|------|----------|---------|
| `leader_service.py` | PC2: `~/leader_service.py` | Streams leader positions |
| `remote_leader.py` | lerobot_teleoperator_trossen plugin | RemoteLeaderTeleop class |
| `config_remote_leader.py` | lerobot_teleoperator_trossen plugin | Config for remote leader |
| `start-remote-leader.sh` | PC1: `deployment/` | Launch leader service via SSH |
| `leader-service.service` | PC2: `/etc/systemd/system/` | Systemd auto-start |
