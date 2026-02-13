# Distributed Teleoperation Setup with Two NetGear Switches

## Overview

This guide describes how to set up distributed teleoperation across two PCs when you have the second NetGear switch.

## Hardware Requirements

- **PC1** (Operator station): Ubuntu PC with WiFi and Ethernet
- **PC2** (Leader robot station): Ubuntu PC with WiFi and Ethernet
- **2x NetGear GS305E switches**
- **2x Trossen robots with iNerve Arm Controllers**
- **2x RealSense cameras**
- **WiFi network** (for PC-to-PC communication)
- **CAT6 Ethernet cables**

## Physical Network Topology

```
PC1 Side (192.168.2.140 WiFi, 192.168.1.100 Ethernet):
  ├── WiFi: 192.168.2.140 (connects to PC2 via WiFi)
  └── Ethernet → NetGear Switch 1
       ├── Follower iNerve (192.168.1.5)
       └── RealSense Cameras (USB)

PC2 Side (192.168.2.138 WiFi, 192.168.1.x Ethernet):
  ├── WiFi: 192.168.2.138 (connects to PC1 via WiFi)
  └── Ethernet → NetGear Switch 2
       └── Leader iNerve (192.168.1.2)

SSH Tunnels over WiFi:
  - TCP 50001: PC1 → PC2 (robot control)
  - TCP 15000: PC1 → PC2 (UDP relay wrapper)

UDP-over-SSH via socat:
  - PC1: UDP:50000 → TCP:15000 (wrapper)
  - PC2: TCP:15000 → UDP:50000 → Leader (relay)
```

## Critical Prerequisites

### On PC2:
1. **Leader iNerve MUST be connected through NetGear Switch 2**
   - Direct connection PC2 ↔ Leader will NOT work
   - The iNerve controller requires proper network infrastructure
   
2. **Verify Leader connectivity from PC2:**
   ```bash
   ping 192.168.1.2
   nc -zv 192.168.1.2 50001  # TCP port
   nc -zvu 192.168.1.2 50000 # UDP port
   ```
   All must succeed before proceeding.

3. **iNerve LED must be GREEN** (not red/fault state)
   - If red: Power cycle the iNerve controller
   - Wait for green LED before attempting teleoperation

### On PC1:
1. **Follower iNerve connected through NetGear Switch 1**
2. **Cameras connected via USB to PC1**
3. **SSH key access to PC2 configured** (see below)

## Initial Setup

### 1. SSH Key Setup (One-time)

On PC1:
```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "pc1-to-pc2"

# Copy public key to PC2
ssh-copy-id hadi@192.168.2.138

# Test passwordless SSH
ssh hadi@192.168.2.138 'hostname'
```

### 2. Install Dependencies

On both PC1 and PC2:
```bash
# Install socat (for UDP tunneling)
sudo apt-get update
sudo apt-get install -y socat

# Install netcat (for testing)
sudo apt-get install -y netcat

# Verify installations
which socat
which nc
```

### 3. Configure Leader IP in config.json

On PC1:
```bash
# Edit config to use tunneled leader
nano ~/.tensi_trossen_studio/config.json
```

Change:
```json
{
  "robot": {
    "leader_ip": "127.0.0.1",  // ← Use localhost (tunneled)
    "follower_ip": "192.168.1.5",
    ...
  }
}
```

## Running the System

### Option A: Automated Startup (Recommended)

On PC1, run the all-in-one script:

```bash
cd /home/tensi/tensi-trossen-studio

# Start all tunnels and relays
./deployment/start-all-tunnels.sh

# Verify setup
./deployment/test-setup.sh

# Start backend (Terminal 1)
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (Terminal 2)
cd frontend
npm run dev

# Open browser: http://localhost:5173
```

### Option B: Manual Step-by-Step

If the automated script hangs, run each component manually:

#### Step 1: Setup PC2 UDP Relay
```bash
# On PC1, execute on PC2
ssh hadi@192.168.2.138 'bash -s' << 'EOF'
pkill -f socat
nohup socat -d -d TCP4-LISTEN:15000,reuseaddr,fork UDP4:192.168.1.2:50000 > /tmp/socat.log 2>&1 &
sleep 1
pgrep -af socat
EOF
```

#### Step 2: Create SSH Tunnels
```bash
# On PC1
ssh -f -N \
  -L 50001:192.168.1.2:50001 \
  -L 15000:localhost:15000 \
  -o ServerAliveInterval=60 \
  -o ServerAliveCountMax=3 \
  hadi@192.168.2.138

# Verify
ps aux | grep -E 'ssh.*(50001|15000)' | grep -v grep
```

#### Step 3: Setup PC1 UDP Wrapper
```bash
# On PC1
socat -d -d UDP4-LISTEN:50000,reuseaddr,fork TCP4:localhost:15000 > /tmp/socat-pc1.log 2>&1 &

# Verify
pgrep -af socat
```

#### Step 4: Verify Complete Setup
```bash
echo "=== PC2 socat ==="
ssh hadi@192.168.2.138 'pgrep -af socat'

echo "=== PC1 socat ==="
pgrep -af socat | grep "UDP4-LISTEN:50000"

echo "=== SSH tunnels ==="
ps aux | grep -E 'ssh.*(50001|15000)' | grep -v grep

echo "=== Port tests ==="
nc -zv localhost 50001
nc -zv localhost 15000
```

#### Step 5: Start Backend & Frontend
```bash
# Terminal 1: Backend
cd /home/tensi/tensi-trossen-studio/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
cd /home/tensi/tensi-trossen-studio/frontend
npm run dev

# Terminal 3: Monitor logs
tail -f /tmp/socat-pc1.log
```

## Stopping the System

```bash
cd /home/tensi/tensi-trossen-studio

# Stop all tunnels and processes
./deployment/stop-all-tunnels.sh

# Or manually:
pkill -f socat
pkill -f "ssh.*192.168.2.138"
ssh hadi@192.168.2.138 'pkill -f socat'
```

## Troubleshooting

### Leader shows RED LED immediately
**Cause:** iNerve controller has pre-existing fault

**Solution:**
1. Power cycle the Leader's iNerve controller
2. Wait for GREEN LED
3. Retry teleoperation

### "Failed to receive initial joint outputs"
**Cause:** Leader robot not responding on network

**Check:**
```bash
# From PC2, test direct connectivity
ssh hadi@192.168.2.138 'ping -c 3 192.168.1.2'
ssh hadi@192.168.2.138 'nc -zv 192.168.1.2 50001'
```

**If ping fails:** Leader iNerve is not connected properly through the switch

### "Connection reset by peer" on TCP 50001
**Cause:** Leader iNerve not accepting connections

**Possible reasons:**
- iNerve not connected through switch (must use NetGear, not direct)
- Another process already connected to leader
- Robot not initialized properly

### Cameras show "Camera unavailable"
**Cause:** Cameras in use by another process

**Solution:**
```bash
# Check what's using cameras
lsusb | grep Intel
pgrep -af "lerobot|realsense"

# Release cameras
pkill -f lerobot
# Then restart backend
```

### SSH tunnel drops/timeouts
**Check WiFi connectivity:**
```bash
ping -c 5 192.168.2.138
```

**Restart tunnel:**
```bash
pkill -f "ssh.*192.168.2.138"
./deployment/start-all-tunnels.sh
```

### socat not forwarding packets
**Check logs:**
```bash
# PC1
tail -f /tmp/socat-pc1.log

# PC2
ssh hadi@192.168.2.138 'tail -f /tmp/socat.log'
```

**Restart socat:**
```bash
pkill -f socat
ssh hadi@192.168.2.138 'pkill -f socat'
./deployment/start-all-tunnels.sh
```

## Network Data Flow

### TCP Port 50001 (Robot Control)
```
lerobot → TCP:127.0.0.1:50001 → SSH tunnel → PC2 → Leader:50001
```

### UDP Port 50000 (Robot Communication)
```
lerobot → UDP:127.0.0.1:50000 
  → socat(PC1) → TCP:localhost:15000 
  → SSH tunnel → PC2:localhost:15000 
  → socat(PC2) → UDP:192.168.1.2:50000 
  → Leader iNerve
```

## Component Responsibilities

### PC1 (Operator Station)
- **Frontend:** React web UI (port 5173)
- **Backend:** FastAPI server (port 8000)
- **Cameras:** Manages RealSense cameras directly
- **Follower:** Direct Ethernet connection (192.168.1.5)
- **Leader (tunneled):** Via SSH to PC2 (127.0.0.1)
- **socat wrapper:** Converts UDP→TCP for SSH tunnel

### PC2 (Leader Robot Station)
- **Leader:** Direct Ethernet connection through switch (192.168.1.2)
- **socat relay:** Converts TCP→UDP from tunnel to robot
- **SSH server:** Accepts tunnel connections from PC1

## Key Files

- `/home/tensi/tensi-trossen-studio/deployment/start-all-tunnels.sh` - Start everything
- `/home/tensi/tensi-trossen-studio/deployment/stop-all-tunnels.sh` - Stop everything
- `/home/tensi/tensi-trossen-studio/deployment/test-setup.sh` - Verify setup
- `~/.tensi_trossen_studio/config.json` - Robot/camera configuration
- `/tmp/socat-pc1.log` - PC1 socat logs
- `/tmp/socat.log` (on PC2) - PC2 socat logs

## Important Notes

1. **NetGear Switch is REQUIRED on PC2 side**
   - Direct iNerve ↔ PC2 connection will NOT work
   - The iNerve controllers need proper network infrastructure

2. **WiFi must be stable**
   - SSH tunnels run over WiFi (192.168.2.x network)
   - Unstable WiFi = dropped connections

3. **socat uses `fork` option**
   - This allows bidirectional UDP communication
   - Each UDP "connection" spawns a child process (normal behavior)

4. **Leader IP is 127.0.0.1 in config**
   - This routes through the SSH tunnel
   - Do NOT use 192.168.1.2 directly from PC1

5. **Green LED = Ready**
   - Always ensure iNerve LED is green before teleoperation
   - Red LED = Fault (power cycle to clear)

## Next Steps After Getting Second Switch

1. Connect Leader iNerve → NetGear 2 → PC2 Ethernet
2. On PC2: `ping 192.168.1.2` (must succeed)
3. On PC1: Run `./deployment/start-all-tunnels.sh`
4. Start backend and frontend
5. Test teleoperation!
