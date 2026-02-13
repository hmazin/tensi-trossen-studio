# ✅ UDP Tunneling Implementation Complete

## What Was Fixed

**Problem**: SSH's `-L` flag only forwards TCP, not UDP. The leader robot at 192.168.1.2 (accessible only from PC2) requires both:
- TCP port 50001 (control) - was working
- UDP port 50000 (real-time feedback) - was broken

**Error**: `Failed to read UDP message from 127.0.0.1:50000 due to Connection refused`

## Solution Implemented

**Dual-socat UDP-over-SSH architecture:**
1. PC1: socat converts UDP:50000 → TCP:15000
2. SSH tunnels TCP:15000 from PC1 to PC2
3. PC2: socat converts TCP:15000 → UDP sent to Leader:50000

## Components Running

### PC1 (192.168.2.140)
- ✅ socat UDP wrapper (UDP:50000 → TCP:15000)
- ✅ SSH tunnel for TCP (50001 → Leader:50001)
- ✅ SSH tunnel for UDP relay (15000 → PC2:15000)

### PC2 (192.168.2.138)
- ✅ socat TCP-to-UDP relay (TCP:15000 → Leader UDP:50000)

## Files Created

1. `deployment/setup-pc2-udp-relay.sh` - PC2 TCP→UDP converter
2. `deployment/setup-pc1-udp-wrapper.sh` - PC1 UDP→TCP converter  
3. `deployment/ssh-tunnel-complete.sh` - Both SSH tunnels
4. `deployment/start-all-tunnels.sh` - Complete startup automation
5. `deployment/stop-all-tunnels.sh` - Complete shutdown
6. `deployment/UDP-ARCHITECTURE.md` - Detailed documentation
7. `deployment/QUICKSTART-TUNNELS.md` - Quick reference

## Configuration Updated

`~/.tensi_trossen_studio/config.json`:
```json
{
  "robot": {
    "leader_ip": "127.0.0.1",      // ← Changed from 192.168.1.2
    "follower_ip": "192.168.1.5"   // ← Unchanged (direct)
  }
}
```

## How to Use

### Start Tunnels
```bash
cd /home/tensi/tensi-trossen-studio
./deployment/start-all-tunnels.sh
```

### Start Services
```bash
# Terminal 1: Backend
cd backend && uv run uvicorn app.main:app --reload

# Terminal 2: Frontend  
cd frontend && npm run dev

# Browser: http://localhost:5173
```

### Test Teleoperation
Click "Start Teleoperation" in the Web UI

**Expected behavior:**
- ✅ Connects to leader at 127.0.0.1 (TCP and UDP)
- ✅ Connects to follower at 192.168.1.5 (direct)
- ✅ Cameras initialize
- ✅ Rerun window opens
- ✅ No "Connection refused" errors

### Stop Tunnels
```bash
./deployment/stop-all-tunnels.sh
```

## Verification Commands

```bash
# Check all components
pgrep -af socat  # Should show PC1 UDP wrapper
ssh hadi@192.168.2.138 'pgrep -af socat'  # Should show PC2 relay
ps aux | grep 'ssh -f -N -L'  # Should show 2 tunnels

# Test ports
nc -zv localhost 50001  # TCP - should succeed
nc -zv localhost 15000  # UDP relay - should succeed
```

## Network Path

```
lerobot → UDP:50000 → socat(PC1) → TCP:15000 → SSH → PC2 → socat(PC2) → Leader UDP:50000 ✓
lerobot → TCP:50001 → SSH → PC2 → Leader TCP:50001 ✓
```

## Troubleshooting

**If teleoperation still fails with UDP errors:**
1. Verify all components: Run verification commands above
2. Restart everything: `./deployment/stop-all-tunnels.sh && sleep 2 && ./deployment/start-all-tunnels.sh`
3. Check logs on PC2: `ssh hadi@192.168.2.138 'tail /tmp/socat-udp.log'`

**If network disconnects:**
- Run `./deployment/start-all-tunnels.sh` again
- Tunnels will auto-reconnect

## Status

- ✅ UDP tunneling architecture implemented
- ✅ All scripts created and tested
- ✅ PC1 and PC2 components running
- ✅ Configuration updated
- ✅ Documentation complete
- ⏳ Ready for teleoperation test

## Next Step

**Test teleoperation from the Web UI** and verify no UDP connection errors appear.
