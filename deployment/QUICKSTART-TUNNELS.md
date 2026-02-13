# Quick Start: Distributed Teleoperation with UDP Tunneling

## Your Setup

**PC1** (192.168.2.140 WiFi, 192.168.1.100 Ethernet):
- Follower robot at 192.168.1.5 (direct Ethernet)
- RealSense cameras (USB)
- Web UI + Backend
- lerobot-teleoperate runs here

**PC2** (192.168.2.138 WiFi, 192.168.1.10 Ethernet):
- Leader robot at 192.168.1.2 (Ethernet)
- No cameras

**Problem**: PC1 cannot reach leader (192.168.1.2) directly
**Solution**: UDP-over-SSH tunneling via socat

## Start Teleoperation

### One-Command Start

```bash
cd /home/tensi/tensi-trossen-studio
./deployment/start-all-tunnels.sh
```

This will:
1. Set up PC2 socat (TCP→UDP relay)
2. Create SSH tunnels (TCP:50001 and TCP:15000)
3. Set up PC1 socat (UDP→TCP wrapper)
4. Verify all components

### Then Start Services

```bash
# Terminal 1: Backend
cd /home/tensi/tensi-trossen-studio/backend
uv run uvicorn app.main:app --reload

# Terminal 2: Frontend
cd /home/tensi/tensi-trossen-studio/frontend
npm run dev

# Browser: http://localhost:5173
# Click "Start Teleoperation"
```

## Stop Tunnels

```bash
cd /home/tensi/tensi-trossen-studio
./deployment/stop-all-tunnels.sh
```

## Verify Setup

```bash
# Should show all green checkmarks
pgrep -af socat  # PC1 UDP wrapper
ssh hadi@192.168.2.138 'pgrep -af socat'  # PC2 UDP relay
ps aux | grep 'ssh -f -N -L'  # SSH tunnels
nc -zv localhost 50001  # TCP test
nc -zv localhost 15000  # UDP relay test
```

## Components

```
PC1: lerobot → UDP:50000 → socat → TCP:15000 → SSH → PC2
PC2: SSH → TCP:15000 → socat → UDP → Leader:50000
```

## Troubleshooting

**"Connection refused" on UDP port 50000:**
```bash
# Check PC1 socat
pgrep -af "socat.*UDP4-LISTEN:50000"

# If missing, restart:
socat UDP4-LISTEN:50000,reuseaddr,fork TCP4:localhost:15000 &
```

**SSH tunnel disconnected:**
```bash
./deployment/stop-all-tunnels.sh
./deployment/start-all-tunnels.sh
```

**Complete reset:**
```bash
./deployment/stop-all-tunnels.sh
sleep 2
./deployment/start-all-tunnels.sh
```

## Configuration

File: `~/.tensi_trossen_studio/config.json`

```json
{
  "robot": {
    "leader_ip": "127.0.0.1",      // ← Tunneled
    "follower_ip": "192.168.1.5"   // ← Direct
  }
}
```

## Scripts

- `deployment/start-all-tunnels.sh` - Start everything
- `deployment/stop-all-tunnels.sh` - Stop everything
- `deployment/setup-pc1-udp-wrapper.sh` - PC1 socat only
- `deployment/setup-pc2-udp-relay.sh` - PC2 socat only
- `deployment/ssh-tunnel-complete.sh` - SSH tunnels only

## Full Documentation

- `deployment/UDP-ARCHITECTURE.md` - Complete architecture details
- `deployment/SSH-TUNNEL-GUIDE.md` - SSH tunneling guide
- `deployment/UDP-FORWARDING-GUIDE.md` - UDP forwarding background
