# Deployment

Scripts and documentation for deploying TENSI Trossen Studio, especially the distributed (two-PC) teleoperation setup.

## Current Architecture: Remote Leader

The distributed system uses a **split architecture** where each robot has its own dedicated PC with a local Trossen driver. A lightweight TCP service streams joint positions between them.

Full guide: **[REMOTE-LEADER-SETUP.md](./REMOTE-LEADER-SETUP.md)**

## Scripts

### Leader Service (Distributed Setup)

| Script | Run on | Purpose |
|--------|--------|---------|
| `start-leader-service.sh` | PC2 | Start `leader_service.py` locally |
| `start-remote-leader.sh` | PC1 | Start leader service on PC2 via SSH |

### Systemd Services

| File | Install on | Purpose |
|------|-----------|---------|
| `leader-service.service` | PC2 | Auto-start the leader service on boot |
| `tensi-backend.service` | PC1 | Auto-start the FastAPI backend on boot |
| `tensi-camera.service` | PC1 | Auto-start the camera streaming service on boot |

### Installing a Systemd Service

```bash
sudo cp <service-file> /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable <service-name>
sudo systemctl start <service-name>
```

## Quick Reference

### Start Everything (Distributed)

```bash
# On PC2 (or from web UI)
python3 -u ~/leader_service.py --ip 192.168.1.2 --port 5555 --fps 60

# On PC1
cd ~/tensi-trossen-studio/backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd ~/tensi-trossen-studio/frontend
npm run dev

# Open http://localhost:5173 and click Start Teleoperation
```

### Stop Everything

```bash
# From the web UI: click Stop, then Stop Leader
# Or manually:
curl -X POST http://localhost:8000/api/teleoperate/stop
curl -X POST http://localhost:8000/api/leader-service/stop
```

## Network Topology

```
PC1 (192.168.2.140 WiFi, 192.168.1.100 Ethernet)
  └── NetGear Switch 1
      ├── Follower iNerve (192.168.1.5)
      └── RealSense cameras (USB)

PC2 (192.168.2.138 WiFi, 192.168.1.x Ethernet)
  └── NetGear Switch 2
      └── Leader iNerve (192.168.1.2)

Communication: PC1 ← TCP:5555 over WiFi → PC2
```

## Pre-Deployment Testing

Before deploying changes to the robots, run the automated test suite:

```bash
# Backend (68 tests — config, CLI args, SSH logic, API integration)
cd backend && uv run pytest tests/ -v

# Frontend (46 tests — API client, all UI components)
cd frontend && npm test
```

Then run through the [Hardware Test Checklist](../docs/HARDWARE-TEST-CHECKLIST.md) for any changes affecting robot control, camera management, or the distributed system.

## Archived Documentation

The `archive/` subdirectory contains earlier documentation from the SSH tunnel / UDP relay approach that was superseded by the Remote Leader architecture. Kept for historical reference only.

---

Last updated: 2026-02-16
