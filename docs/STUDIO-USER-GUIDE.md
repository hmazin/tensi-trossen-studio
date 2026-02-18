# TENSI Trossen Studio — User & Operator Guide

This guide documents how to run, configure, and use the Studio: launcher, networks, cameras (including the operator view USB camera), and opening the app from another PC.

---

## Table of contents

1. [Two networks (IP addresses)](#1-two-networks-ip-addresses)
2. [Launcher (PC1)](#2-launcher-pc1)
3. [Backend and frontend (manual start)](#3-backend-and-frontend-manual-start)
4. [Opening the Studio (local and from PC2)](#4-opening-the-studio-local-and-from-pc2)
5. [Network info in the UI](#5-network-info-in-the-ui)
6. [Cameras: Wrist, Top, Operator view](#6-cameras-wrist-top-operator-view)
7. [Finding the operator view camera index](#7-finding-the-operator-view-camera-index)
8. [Config files and paths](#8-config-files-and-paths)
9. [Troubleshooting](#9-troubleshooting)
10. [Related documentation](#10-related-documentation)

---

## 1. Two networks (IP addresses)

Each machine has **two IP ranges**. Use the correct one for each purpose.

| Domain        | Interface | Use |
|---------------|-----------|-----|
| **192.168.1.x** | Ethernet  | Netgate, robot arms (leader/follower). **Leader IP** and **Follower IP** in Settings use these. |
| **192.168.2.x** | WiFi       | Internet and internal LAN. Opening the Studio from another PC; **Leader Service Host** (PC2) for distributed teleop. |

**Do not mix them:** robot arms and Netgate are on 192.168.1.x; PC-to-PC and web access use 192.168.2.x.

- **Follower IP** / **Leader IP** in Settings → **192.168.1.x**
- **Leader Service Host** (when using Remote Leader Mode) → PC2’s **192.168.2.x**
- To open the Studio from PC2 → use PC1’s **192.168.2.x** in the browser (e.g. `http://192.168.2.140:5173`).

---

## 2. Launcher (PC1)

A desktop GUI on PC1 to start/stop the backend and frontend and to view/edit PC1/PC2 IPs.

### Run the launcher

```bash
cd tensi-trossen-studio
python launcher.py
```

On Debian/Ubuntu, if the window does not open: `sudo apt install python3-tk`.

### What the launcher does

| Section | Description |
|--------|-------------|
| **1. Backend** | Status (Running/Stopped). **Start backend** runs `uv run uvicorn` in `backend/`. **Stop backend** stops the process and frees port 8000. |
| **2. Frontend** | Status (Running/Stopped). **Start frontend** runs `npm run dev` in `frontend/`. **Stop frontend** stops that process. |
| **3. PC1 IPs** | WiFi (192.168.2.x) and Ethernet (192.168.1.x). Defaults are auto-detected; you can edit and save. |
| **4. PC2 IPs** | WiFi and Ethernet for PC2 (defaults: 192.168.2.138, 192.168.1.2). Editable; click **Save IPs** to persist. |
| **Open Studio in browser** | Opens `http://127.0.0.1:5173`. |

### Port 8000 already in use

If you click **Start backend** and port 8000 is in use, the launcher asks: **Free the port and start backend?**  
- **Yes** — runs `fuser -k 8000/tcp`, waits 1.5 s, then starts the backend.  
- **No** — do nothing (stop the other process yourself or use **Stop backend** first if the launcher had started it).

### Backend / frontend exited (error dialog)

If the backend or frontend process exits, the launcher shows a **copyable error window**:

- **Copy to clipboard** — copies the full message.
- **Open log file** — opens the full log (e.g. `~/.tensi_trossen_studio/backend_stderr.log`) in your default editor.
- You can also select text in the window and copy with Ctrl+C.

### Launcher config

Saved to `~/.tensi_trossen_studio/launcher.json` (PC1/PC2 IPs). Backend and frontend are not auto-started on boot unless you set that up separately (e.g. systemd).

---

## 3. Backend and frontend (manual start)

If you prefer not to use the launcher:

**Backend (port 8000):**

```bash
cd tensi-trossen-studio/backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (port 5173, or 5174 if 5173 is busy):**

```bash
cd tensi-trossen-studio/frontend
npm install
npm run dev
```

The frontend is built with Vite and uses `--host` so it is reachable on the LAN (e.g. from PC2).

---

## 4. Opening the Studio (local and from PC2)

- **On PC1:** `http://localhost:5173` (or the port Vite reports, e.g. 5174).
- **From PC2 (or another machine on the same WiFi):** `http://<PC1_192.168.2.x>:5173`  
  Example: if PC1’s WiFi IP is 192.168.2.140, use `http://192.168.2.140:5173`.

Ensure the firewall on PC1 allows ports **5173** (frontend) and **8000** (backend), e.g.:

```bash
sudo ufw allow 5173/tcp
sudo ufw allow 8000/tcp
sudo ufw status
```

---

## 5. Network info in the UI

- **ℹ (info) button** (top bar, next to the gear): opens a panel with the two-networks summary and the **“Open from another PC”** URL (if **Studio host for other PCs** is set in Settings).
- **Copy** copies that URL; **Open Settings →** opens the Settings panel.
- **Settings → Network**: same two-networks table and the field **“Studio host for other PCs (this PC’s 192.168.2.x)”**. Set this to PC1’s WiFi IP (e.g. 192.168.2.140) so the ℹ panel shows the correct URL for PC2. Save with **Save Settings**.

---

## 6. Cameras: Wrist, Top, Operator view

| Camera        | Type       | Use |
|---------------|------------|-----|
| **Wrist**     | RealSense  | Teleop/recording (LeRobot). Configure with serial number in Settings. |
| **Top**       | RealSense  | Teleop/recording. Configure with serial number in Settings. |
| **Operator view** | USB (OpenCV) | HMI only; **not** used for teleop or recording. Stays on when you start teleop/record. |

- Wrist and Top: set in **Settings → Cameras** (Wrist camera serial, Top camera serial). Use **Detect cameras** in the Camera Feed area to verify serials.
- Operator view: **Settings → Cameras** → enable **Operator view camera (USB)** and set **Device index** (e.g. 12 for a typical USB webcam). See [§7](#7-finding-the-operator-view-camera-index).

The operator view stream is served at `/api/cameras/stream/operator` and is excluded from teleop/record shutdown logic.

---

## 7. Finding the operator view camera index

The operator view camera is a USB video device. Its **device index** (0, 1, 2, …) is what you set in Settings.

### From the Studio UI

1. Open **Settings** → **Cameras**.
2. Enable **Operator view camera (USB)**.
3. In the **“Identify USB camera index”** block, click **Detect USB cameras**.
4. A list appears (e.g. “Index 12: /dev/video12 — Full HD webcam”). Click **Use** next to the device that is your operator camera; the **Device index** field updates.
5. Click **Save Settings**.

### From the terminal (Linux)

```bash
# List video devices with index and name
for n in /sys/class/video4linux/video*; do
  [ -d "$n" ] || continue
  name=$(cat "$n/name" 2>/dev/null || echo "")
  echo "$(basename $n): $name"
done
```

Match the device name (e.g. “Full HD webcam”) to the index (e.g. video12 → index **12**). Enter that index in Settings → Operator view camera → Device index.

---

## 8. Config files and paths

| What | Path |
|------|------|
| Main app config (robot, dataset, train, replay, paths, operator_camera, etc.) | `~/.tensi_trossen_studio/config.json` |
| Launcher IPs (PC1/PC2 WiFi and Ethernet) | `~/.tensi_trossen_studio/launcher.json` |
| Backend stderr log (when backend exits from launcher) | `~/.tensi_trossen_studio/backend_stderr.log` |
| Frontend stderr log (when frontend exits from launcher) | `~/.tensi_trossen_studio/frontend_stderr.log` |

All of these are created or updated automatically when you use the app and the launcher.

---

## 9. Troubleshooting

| Issue | What to do |
|-------|------------|
| **Port 8000 in use** | In the launcher, when prompted, choose “Free the port and start backend”. Or run `fuser -k 8000/tcp` and start the backend again. |
| **Backend process exited (code 1)** | Open the log file from the error window or run the backend in a terminal: `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` to see the traceback. |
| **Cannot see cameras** | Ensure config has wrist/top (and operator_camera if you use it). Reload the page; check that the backend is running and that camera serials (and operator device index) are correct. Use **Detect cameras** / **Detect USB cameras** in Settings. |
| **PC2 cannot open Studio** | Use PC1’s **192.168.2.x** in the browser (e.g. `http://192.168.2.140:5173`). Check firewall on PC1 for 5173 and 8000. Ensure the frontend was started with `npm run dev` (Vite with `--host`). |
| **Operator view black or wrong camera** | Change **Device index** in Settings (e.g. try 12 or 13). Use **Detect USB cameras** to see all devices and pick the right one. |

---

## 10. Related documentation

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Project overview, quick start, features. |
| [deployment/REMOTE-LEADER-SETUP.md](../deployment/REMOTE-LEADER-SETUP.md) | Distributed teleop (leader on PC2, follower on PC1). |
| [deployment/README.md](../deployment/README.md) | Network topology, scripts, systemd. |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and components. |
| [docs/TROSSEN_LEROBOT_REFERENCE.md](TROSSEN_LEROBOT_REFERENCE.md) | LeRobot CLI and camera format reference. |
| [docs/HARDWARE-TEST-CHECKLIST.md](HARDWARE-TEST-CHECKLIST.md) | Manual hardware test checklist. |

---

*Last updated: 2026-02.*
