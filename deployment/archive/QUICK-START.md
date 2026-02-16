# Quick Start Guide - Distributed Teleoperation

## Prerequisites Checklist

On PC2:
- [ ] Leader iNerve connected through NetGear Switch 2
- [ ] `ping 192.168.1.2` succeeds from PC2
- [ ] iNerve LED is GREEN (not red)

On PC1:
- [ ] Follower iNerve connected through NetGear Switch 1
- [ ] Cameras plugged into PC1 USB
- [ ] WiFi connected (can reach 192.168.2.138)

## Startup Commands (PC1)

### Terminal 1: Start Tunnels
```bash
cd /home/tensi/tensi-trossen-studio
./deployment/start-all-tunnels.sh
```

**Expected output:**
```
✓ PC2 UDP relay running
✓ TCP tunnel created
✓ UDP relay tunnel created
✓ PC1 UDP wrapper running
Ready for teleoperation!
```

### Terminal 2: Start Backend
```bash
cd /home/tensi/tensi-trossen-studio/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Terminal 3: Start Frontend
```bash
cd /home/tensi/tensi-trossen-studio/frontend
npm run dev
```

**Expected output:**
```
➜  Local:   http://localhost:5173/
```

### Browser: Open Web UI
```
http://localhost:5173
```

## Quick Troubleshooting

### Leader LED is RED
```bash
# Power cycle the iNerve controller on PC2
# Wait for GREEN LED
```

### Can't reach Leader from PC2
```bash
ssh hadi@192.168.2.138 'ping -c 2 192.168.1.2'
# If fails: Check NetGear switch connection
```

### Tunnels not working
```bash
./deployment/stop-all-tunnels.sh
./deployment/start-all-tunnels.sh
```

### Cameras unavailable
```bash
pkill -f lerobot
# Restart backend
```

## Shutdown Commands

```bash
cd /home/tensi/tensi-trossen-studio
./deployment/stop-all-tunnels.sh

# Or kill everything:
pkill -f socat
pkill -f uvicorn
pkill -f "npm run dev"
ssh hadi@192.168.2.138 'pkill -f socat'
```

## Verification Commands

```bash
# Check all components are running
./deployment/test-setup.sh

# Manual checks
pgrep -af socat                           # PC1 UDP wrapper
ssh hadi@192.168.2.138 'pgrep -af socat'  # PC2 UDP relay
ps aux | grep ssh | grep 15000            # SSH tunnels
nc -zv localhost 50001                    # TCP tunnel
nc -zv localhost 15000                    # UDP tunnel wrapper
```

## Network Topology Quick Reference

```
PC1: WiFi 192.168.2.140, Ethernet 192.168.1.100
  ├── Follower: 192.168.1.5 (direct)
  └── Leader: 127.0.0.1 (tunneled → PC2)

PC2: WiFi 192.168.2.138, Ethernet 192.168.1.x
  └── Leader: 192.168.1.2 (direct through switch)

Tunnels (over WiFi):
  TCP 50001: Robot control
  TCP 15000: UDP relay wrapper
```

## Important Files

- Config: `~/.tensi_trossen_studio/config.json`
- PC1 logs: `/tmp/socat-pc1.log`
- PC2 logs: `ssh hadi@192.168.2.138 'cat /tmp/socat.log'`
- Full docs: `./deployment/SETUP-WITH-TWO-SWITCHES.md`
