# Distributed Teleoperation Implementation Summary

**Date:** 2026-02-13  
**Status:** Ready for testing when second NetGear switch arrives

---

## What We Built

A complete distributed teleoperation system that allows operating Trossen robots across two physically separated PCs connected via WiFi, with UDP tunneling over SSH to bypass network isolation.

### Architecture Overview

**PC1 (Operator Station):**
- FastAPI backend server
- React/Vite frontend UI
- Direct control of Follower robot (192.168.1.5)
- Camera streaming from RealSense cameras
- SSH tunnel client + UDP-to-TCP wrapper

**PC2 (Leader Robot Station):**
- SSH tunnel server
- TCP-to-UDP relay for leader robot
- Direct connection to Leader robot (192.168.1.2)

**Communication Path:**
```
PC1 lerobot process
  ↓ TCP: localhost:50001 → [SSH tunnel] → PC2 → Leader:50001 (direct)
  ↓ UDP: localhost:50000 → [socat] → TCP:15000 → [SSH tunnel] → PC2:15000 → [socat] → Leader UDP:50000
```

---

## Key Technical Solutions Implemented

### 1. UDP-over-SSH Tunneling (Dual-socat Architecture)

**Problem:** SSH `-L` flag only tunnels TCP, but robots require UDP for state communication.

**Solution:** 
- PC1: `socat` converts UDP:50000 → TCP:15000 (wrapper)
- SSH tunnel: Forwards TCP:15000 from PC1 to PC2
- PC2: `socat` converts TCP:15000 → UDP:50000 to robot (relay)

**Implementation:**
- `/home/tensi/tensi-trossen-studio/deployment/setup-pc1-udp-wrapper.sh`
- `/home/tensi/tensi-trossen-studio/deployment/setup-pc2-udp-relay.sh`
- `/home/tensi/tensi-trossen-studio/deployment/ssh-tunnel-complete.sh`

### 2. Camera Manager Singleton

**Problem:** RealSense cameras allow only one process at a time; conflicts when streaming and teleoperation run simultaneously.

**Solution:** Implemented `CameraManager` singleton that:
- Provides persistent camera lifecycle management
- Auto-releases cameras before teleoperation starts
- Restarts camera streams after teleoperation ends
- Thread-safe frame capture with connection pooling

**Files:**
- `/home/tensi/tensi-trossen-studio/backend/app/services/camera_manager.py`
- `/home/tensi/tensi-trossen-studio/backend/app/routes/camera_routes.py`
- `/home/tensi/tensi-trossen-studio/backend/app/routes/process_routes.py`

### 3. Automated Startup Scripts

**Scripts created:**
- `start-all-tunnels.sh` - Complete setup automation
- `stop-all-tunnels.sh` - Clean shutdown
- `test-setup.sh` - Verification suite

**Location:** `/home/tensi/tensi-trossen-studio/deployment/`

### 4. Configuration Management

**Updated config.json:**
- `leader_ip: "127.0.0.1"` - Routes through SSH tunnel
- `follower_ip: "192.168.1.5"` - Direct Ethernet connection
- Camera serial numbers and configurations preserved

**File:** `~/.tensi_trossen_studio/config.json`

---

## What's Working Now

✅ SSH key authentication PC1 → PC2  
✅ SSH tunnel infrastructure (TCP + UDP wrapper)  
✅ socat UDP-over-SSH relay architecture  
✅ Camera streaming from PC1  
✅ Backend/Frontend web UI  
✅ Configuration management  
✅ Automated startup/shutdown scripts  
✅ Follower robot connectivity on PC1  

---

## What's Blocked (Hardware Required)

❌ **Leader robot connectivity on PC2**

**Root Cause:** Leader iNerve controller is directly connected to PC2 Ethernet port, which does not provide the proper network infrastructure that the iNerve requires.

**Evidence:**
- `ping 192.168.1.2` from PC2 fails (Destination Host Unreachable)
- TCP port 50001 connection resets immediately
- iNerve LED goes red (fault) when teleoperation attempted

**Solution Required:** Connect Leader iNerve through a NetGear switch (same model as used on PC1 side).

---

## Hardware Needed

**NetGear GS305E switch** (ordered, ETA: 2 days)

**Proper setup after switch arrives:**

```
PC2 Ethernet → NetGear Switch 2 → Leader iNerve
```

This will provide:
- Proper network infrastructure for iNerve
- Stable connection to 192.168.1.2
- Bidirectional TCP/UDP communication

---

## Testing Plan (When Switch Arrives)

### Step 1: Hardware Connection
1. Connect Leader iNerve → NetGear 2 → PC2 Ethernet
2. Power on iNerve controller
3. Wait for GREEN LED

### Step 2: Network Verification
On PC2:
```bash
ping 192.168.1.2           # Must succeed
nc -zv 192.168.1.2 50001   # TCP must succeed
nc -zvu 192.168.1.2 50000  # UDP must succeed
```

### Step 3: Start System
On PC1:
```bash
cd /home/tensi/tensi-trossen-studio

# Start tunnels
./deployment/start-all-tunnels.sh

# Verify
./deployment/test-setup.sh

# Start backend (Terminal 1)
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (Terminal 2)
cd frontend
npm run dev

# Open browser
http://localhost:5173
```

### Step 4: Test Teleoperation
1. Click "Start Teleoperation" in web UI
2. Verify:
   - No "Connection refused" errors
   - No "Failed to receive initial joint outputs"
   - Leader iNerve stays GREEN (not red)
   - Leader arm responds to movements
   - Follower arm mirrors leader

### Step 5: Monitor Logs
```bash
# PC1 socat log
tail -f /tmp/socat-pc1.log

# PC2 socat log
ssh hadi@192.168.2.138 'tail -f /tmp/socat.log'

# Backend logs
# Check terminal running uvicorn
```

---

## Known Issues & Limitations

### 1. Direct iNerve Connection Doesn't Work
- **Issue:** iNerve controllers require network switch infrastructure
- **Status:** Documented, will be resolved with second switch

### 2. WiFi Dependency
- **Issue:** SSH tunnels run over WiFi; unstable WiFi breaks connection
- **Mitigation:** Use stable 192.168.2.x WiFi network
- **Future:** Consider Ethernet bridge if WiFi unreliable

### 3. Manual Startup Process
- **Issue:** Requires running multiple scripts/commands
- **Status:** Automated via `start-all-tunnels.sh`
- **Future:** Create systemd services for auto-start on boot

### 4. socat Fork Process Multiplication
- **Issue:** `fork` option creates child processes for each connection
- **Impact:** Multiple socat processes visible in `ps` (normal behavior)
- **Status:** Documented; not an error

---

## Documentation Created

1. **SETUP-WITH-TWO-SWITCHES.md** - Complete setup guide
2. **QUICK-START.md** - Quick reference for daily use
3. **UDP-ARCHITECTURE.md** - Technical details of UDP tunneling
4. **QUICKSTART-TUNNELS.md** - Tunnel-specific guide
5. **README.md** - Updated with distributed setup info

**Location:** `/home/tensi/tensi-trossen-studio/deployment/`

---

## Technical Achievements

### Problem 1: UDP over SSH
**Challenge:** SSH cannot tunnel UDP natively

**Solution:** Dual-socat architecture
- Wrapper converts UDP→TCP for tunnel
- Relay converts TCP→UDP for robot
- Bidirectional communication maintained

### Problem 2: Camera Access Conflicts
**Challenge:** RealSense allows single process only

**Solution:** Singleton CameraManager
- Centralized lifecycle management
- Auto-release before teleoperation
- Thread-safe operations

### Problem 3: Distributed Camera Service (Initial Plan)
**Challenge:** Cameras physically on PC1, not PC2

**Resolution:** Simplified architecture - cameras stay local to PC1

### Problem 4: Network Isolation
**Challenge:** PC1 and PC2 have separate 192.168.1.x Ethernet networks

**Solution:** SSH tunnels over WiFi (192.168.2.x) network

### Problem 5: Leader Robot Unreachable
**Challenge:** Direct PC2↔Leader connection fails

**Root Cause:** iNerve requires network switch
**Status:** Blocked pending hardware (NetGear switch)

---

## Next Steps

1. **Wait for NetGear switch delivery** (2 days)
2. **Physical setup:**
   - Connect Leader iNerve through switch
   - Verify network connectivity from PC2
3. **Test distributed teleoperation:**
   - Run startup scripts
   - Verify tunnel operations
   - Test full leader-follower control
4. **Optional enhancements** (after successful test):
   - Create systemd services for auto-startup
   - Add monitoring dashboard
   - Implement connection health checks

---

## Key Learnings

1. **iNerve controllers need proper network infrastructure** - direct PC connection insufficient
2. **UDP tunneling requires creative solutions** - socat dual-relay architecture
3. **Camera resource management critical** - singleton pattern prevents conflicts
4. **Network topology matters** - switch-based vs. direct connections behave differently
5. **Distributed systems need robust automation** - manual steps error-prone

---

## Commands Reference

### Start Everything
```bash
cd /home/tensi/tensi-trossen-studio
./deployment/start-all-tunnels.sh
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
cd frontend && npm run dev
```

### Stop Everything
```bash
./deployment/stop-all-tunnels.sh
pkill -f uvicorn
pkill -f "npm run dev"
```

### Verify Setup
```bash
./deployment/test-setup.sh
```

### Check Logs
```bash
tail -f /tmp/socat-pc1.log                      # PC1 UDP wrapper
ssh hadi@192.168.2.138 'tail -f /tmp/socat.log' # PC2 UDP relay
```

---

## Contact Points

**User:** tensi  
**PC1:** tensi@192.168.2.140 (tensi-trossen-studio)  
**PC2:** hadi@192.168.2.138  
**Project:** /home/tensi/tensi-trossen-studio  

---

**End of Summary**
