# SSH Tunnel Setup for Distributed Robot Network

## Problem

Your robots are on separate Ethernet networks:
- **PC1** (192.168.1.100) can reach **Follower** (192.168.1.5)
- **PC2** (192.168.1.10) can reach **Leader** (192.168.1.2)
- PC1 and PC2 communicate via WiFi (192.168.2.x)

`lerobot-teleoperate` runs on PC1 and needs to access both robots.

## Solution

SSH tunnel from PC1 to PC2 forwards the leader robot's TCP port through the WiFi network.

```
PC1 (192.168.2.140 WiFi)
├── lerobot-teleoperate
├── → localhost:50001 (SSH tunnel)
│   └──→ PC2 (192.168.2.138 WiFi)
│       └──→ Leader (192.168.1.2:50001 Ethernet)
├── → 192.168.1.5:50001 (Direct Ethernet)
│   └──→ Follower
└── Cameras (USB)
```

## Manual Setup

### 1. Establish Tunnel

```bash
cd /home/tensi/tensi-trossen-studio/deployment
./ssh-tunnel-leader.sh
```

This creates an SSH tunnel:
- **Local**: `localhost:50001` on PC1
- **Remote**: `192.168.1.2:50001` (leader robot via PC2)

### 2. Verify Tunnel

```bash
nc -zv localhost 50001
# Should show: Connection to localhost 50001 port [tcp/*] succeeded!
```

### 3. Configuration

Your config at `~/.tensi_trossen_studio/config.json` should have:

```json
{
  "robot": {
    "leader_ip": "127.0.0.1",      // ← localhost (tunneled to PC2)
    "follower_ip": "192.168.1.5"   // ← direct Ethernet connection
  }
}
```

### 4. Start Teleoperation

From the Web UI, click "Start Teleoperation". It will:
- Connect to leader at `127.0.0.1:50001` (tunnel → PC2 → leader)
- Connect to follower at `192.168.1.5:50001` (direct)
- Access cameras via USB

## Automatic Startup (Optional)

### Install as Systemd Service

```bash
sudo cp /home/tensi/tensi-trossen-studio/deployment/ssh-tunnel-leader.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ssh-tunnel-leader
sudo systemctl start ssh-tunnel-leader
```

### Check Status

```bash
sudo systemctl status ssh-tunnel-leader
```

### View Logs

```bash
sudo journalctl -u ssh-tunnel-leader -f
```

## Troubleshooting

### Tunnel Not Connecting

```bash
# Check if tunnel process is running
ps aux | grep 'ssh.*50001:192.168.1.2'

# Test PC2 connectivity
ping 192.168.2.138

# Test SSH to PC2
ssh hadi@192.168.2.138 hostname

# Manually test leader robot from PC2
ssh hadi@192.168.2.138 'nc -zv 192.168.1.2 50001'
```

### Tunnel Established But Connection Fails

```bash
# Test local tunnel endpoint
nc -zv localhost 50001

# Check if port is listening
sudo lsof -i :50001

# Kill existing tunnel
pkill -f "ssh.*50001:192.168.1.2"

# Re-establish
./ssh-tunnel-leader.sh
```

### Teleoperation Can't Connect to Leader

1. Verify tunnel is active: `nc -zv localhost 50001`
2. Check config uses `127.0.0.1`: `cat ~/.tensi_trossen_studio/config.json`
3. Verify leader robot is powered on
4. Check PC2 can reach leader: `ssh hadi@192.168.2.138 'ping -c 3 192.168.1.2'`

## Limitations

- **UDP port 50000** cannot be tunneled through SSH
  - The Trossen driver should work with TCP only for control
  - If UDP is required, consider VPN or network bridge

- **Latency**: Commands go through WiFi (PC1 → PC2) then Ethernet (PC2 → Leader)
  - Typical latency: 1-5ms (acceptable for teleoperation)
  - Monitor with: `ping -c 100 192.168.2.138 | tail -5`

- **Network Reliability**: If WiFi disconnects, tunnel breaks
  - Systemd service will auto-reconnect
  - Manual reconnect: `./ssh-tunnel-leader.sh`

## Testing the Full Setup

### 1. Test Follower (Direct)

```bash
cd ~/lerobot_trossen
uv run python -c "
from trossen_arm import TrossenArmDriver
driver = TrossenArmDriver('192.168.1.5')
print('Follower connected!')
driver.close()
"
```

### 2. Test Leader (Tunneled)

```bash
cd ~/lerobot_trossen
uv run python -c "
from trossen_arm import TrossenArmDriver
driver = TrossenArmDriver('127.0.0.1')
print('Leader connected via tunnel!')
driver.close()
"
```

### 3. Test Cameras

```bash
cd ~/lerobot_trossen
uv run lerobot-find-cameras realsense
```

### 4. Test Full Teleoperation

1. Ensure tunnel is running: `nc -zv localhost 50001`
2. Start backend: `cd backend && uv run uvicorn app.main:app`
3. Start frontend: `cd frontend && npm run dev`
4. Open Web UI: `http://localhost:5173`
5. Click "Start Teleoperation"
6. Verify Rerun window opens with both robots

## Quick Commands

```bash
# Establish tunnel
./deployment/ssh-tunnel-leader.sh

# Check tunnel
nc -zv localhost 50001

# View tunnel process
ps aux | grep 'ssh.*50001'

# Kill tunnel
pkill -f "ssh.*50001:192.168.1.2"

# Test leader via tunnel
ssh hadi@192.168.2.138 'nc -zv 192.168.1.2 50001'

# Test follower direct
nc -zv 192.168.1.5 50001
```

## Architecture Summary

**Before (Not Working):**
```
PC1 → 192.168.1.2 ✗ (unreachable)
PC1 → 192.168.1.5 ✓
```

**After (With Tunnel):**
```
PC1 → localhost:50001 (tunnel) → PC2 → 192.168.1.2 ✓
PC1 → 192.168.1.5 ✓
```

Both robots now accessible from PC1!
