# Pre-Flight Checklist - When NetGear Switch Arrives

## Hardware Setup

### Physical Connections
- [ ] NetGear Switch 2 powered on
- [ ] Leader iNerve → NetGear Switch 2 (CAT6)
- [ ] NetGear Switch 2 → PC2 Ethernet port (CAT6)
- [ ] Leader iNerve powered on
- [ ] Leader iNerve LED is GREEN (not red)
  - If red: Press power button to cycle, wait for green

### Network Verification (PC2)
```bash
# SSH into PC2
ssh hadi@192.168.2.138

# Test 1: Ping leader robot
ping -c 3 192.168.1.2
# ✓ Expected: 0% packet loss, <1ms latency

# Test 2: TCP port reachable
nc -zv 192.168.1.2 50001
# ✓ Expected: Connection to 192.168.1.2 50001 port [tcp/*] succeeded!

# Test 3: UDP port reachable
nc -zvu 192.168.1.2 50000
# ✓ Expected: Connection to 192.168.1.2 50000 port [udp/*] succeeded!

# Exit PC2
exit
```

**If any test fails:** Check physical connections, switch power, iNerve power

---

## PC1 Setup

### Terminal 1: Start Tunnels
```bash
cd /home/tensi/tensi-trossen-studio

# Start all tunneling infrastructure
./deployment/start-all-tunnels.sh
```

**Expected Output:**
```
=== Starting Distributed Teleoperation Setup ===

Step 1: Setting up UDP relay on PC2...
✓ PC2 UDP relay running (PID: XXXX)

Step 2: Creating SSH tunnels...
✓ TCP tunnel created
✓ UDP relay tunnel created

Step 3: Setting up UDP wrapper on PC1...
✓ PC1 UDP wrapper running

=== Verification ===
PC2 socat (TCP→UDP relay):
XXXX socat TCP4-LISTEN:15000,reuseaddr,fork UDP4:192.168.1.2:50000

PC1 socat (UDP→TCP wrapper):
XXXX socat UDP4-LISTEN:50000,reuseaddr,fork TCP4:localhost:15000

SSH tunnels:
XXXX ssh ... 50001 ... 15000

Port tests:
  TCP 50001 (robot control): ✓
  TCP 15000 (UDP relay): ✓

=== Setup Complete ===
Ready for teleoperation!
```

**Troubleshooting:**
- If script hangs: Ctrl+C, check PC2 connectivity, run `./deployment/stop-all-tunnels.sh`, retry
- If ports already in use: Run `./deployment/stop-all-tunnels.sh` first

### Terminal 2: Start Backend
```bash
cd /home/tensi/tensi-trossen-studio/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO: Will watch for changes in these directories: ['/home/tensi/tensi-trossen-studio/backend']
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO: Started reloader process [XXXX] using WatchFiles
INFO: Started server process [XXXX]
INFO: Waiting for application startup.
INFO: Application startup complete.
```

**Wait for:** "Application startup complete"

### Terminal 3: Start Frontend
```bash
cd /home/tensi/tensi-trossen-studio/frontend
npm run dev
```

**Expected Output:**
```
> tensi-trossen-studio-frontend@0.1.0 dev
> vite

  VITE v5.4.21  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Wait for:** "ready in XXX ms"

---

## Web UI Testing

### Step 1: Open Browser
```
http://localhost:5173
```

### Step 2: Check Camera Status
- [ ] Top camera shows live feed (or detected status)
- [ ] Wrist camera shows live feed (or detected status)
- [ ] No "Camera unavailable" errors
  - If unavailable: Click "Detect Cameras" or refresh page

### Step 3: Check Configuration
- [ ] Leader IP shows: 127.0.0.1
- [ ] Follower IP shows: 192.168.1.5
- [ ] Cameras configured correctly

---

## Teleoperation Test

### Pre-Teleoperation Checks
- [ ] Leader iNerve LED is GREEN on PC2
- [ ] Follower iNerve LED is GREEN on PC1
- [ ] No cameras in use (check "Camera unavailable" messages)
- [ ] Backend logs show no errors

### Start Teleoperation
1. Click **"Start Teleoperation"** button in web UI
2. Watch for process status change

### Success Indicators
- [ ] Process status shows "Running: true"
- [ ] Process status shows "Mode: teleoperate"
- [ ] Leader iNerve LED stays GREEN (not red)
- [ ] Follower iNerve LED stays GREEN
- [ ] Moving leader arm causes follower to mirror
- [ ] No error logs in backend terminal

### Expected Logs (Backend Terminal)
```
INFO: 127.0.0.1:XXXXX - "POST /api/teleoperate/start?display_data=true HTTP/1.1" 200 OK
INFO 2026-02-XX XX:XX:XX eoperate.py:187 {'display_data': True, ...}
INFO 2026-02-XX XX:XX:XX ai_leader.py:46 Connecting to the arm controller's TCP server at 127.0.0.1:50001
INFO 2026-02-XX XX:XX:XX ai_leader.py:46 Connecting to the arm controller's UDP server at 127.0.0.1:50000
INFO 2026-02-XX XX:XX:XX ai_leader.py:46 Driver version: 'v1.9.0'
INFO 2026-02-XX XX:XX:XX ai_leader.py:46 Controller firmware version: 'v1.9.1'
[2026-02-XX...] INFO egui_wgpu Starting GUI...
```

**No errors like:**
- ❌ "Connection refused"
- ❌ "Connection reset by peer"
- ❌ "Failed to receive initial joint outputs"
- ❌ "Invalid robot command indicator"

### Failure Indicators
If you see any of these, stop and troubleshoot:

**Leader LED turns RED:**
- Stop teleoperation
- Power cycle Leader iNerve
- Wait for GREEN LED
- Retry

**"Connection reset by peer" error:**
- Verify: `ssh hadi@192.168.2.138 'nc -zv 192.168.1.2 50001'`
- Check Leader iNerve physical connection to switch
- Check switch power

**"Failed to receive initial joint outputs":**
- Check UDP tunnel: `tail -f /tmp/socat-pc1.log`
- Check PC2 relay: `ssh hadi@192.168.2.138 'tail -f /tmp/socat.log'`
- Restart tunnels: `./deployment/stop-all-tunnels.sh && ./deployment/start-all-tunnels.sh`

**"Connection refused" on UDP 50000:**
- Check PC1 socat: `pgrep -af "UDP4-LISTEN:50000"`
- Restart: `pkill -f socat ; ./deployment/start-all-tunnels.sh`

---

## Monitoring During Teleoperation

### Terminal 4: Monitor PC1 UDP Wrapper
```bash
tail -f /tmp/socat-pc1.log
```

**Expected:**
- Lines showing "accepting UDP connection"
- Lines showing "successfully connected to localhost:15000"
- Lines showing "starting data transfer loop"

### Terminal 5: Monitor PC2 UDP Relay
```bash
ssh hadi@192.168.2.138 'tail -f /tmp/socat.log'
```

**Expected:**
- Lines showing "accepting connection from AF=2 127.0.0.1"
- Lines showing "successfully connected from local address"
- Lines showing "starting data transfer loop"

---

## Stop Teleoperation

### From Web UI
1. Click **"Stop Teleoperation"** button

### Verify Stop
- [ ] Process status shows "Running: false"
- [ ] Cameras become available again
- [ ] Both iNerve LEDs stay GREEN

---

## Shutdown Sequence

### Stop Backend & Frontend
```bash
# Ctrl+C in Terminal 2 (backend)
# Ctrl+C in Terminal 3 (frontend)
```

### Stop Tunnels
```bash
cd /home/tensi/tensi-trossen-studio
./deployment/stop-all-tunnels.sh
```

**Expected Output:**
```
Stopping all tunnel processes...
✓ Killed PC1 socat processes
✓ Killed SSH tunnel processes
✓ Killed PC2 socat processes
All tunnel processes stopped
```

### Verify Cleanup
```bash
pgrep -af "socat|ssh.*192.168.2.138|uvicorn|vite"
# Should return nothing or only system processes
```

---

## Success Criteria

✅ **System is working if:**
1. Leader iNerve stays green during teleoperation
2. No connection errors in logs
3. Leader arm movements mirror to follower
4. Cameras stream properly
5. Can start/stop teleoperation multiple times without issues

---

## Documentation Reference

- **Full Setup Guide:** `./deployment/SETUP-WITH-TWO-SWITCHES.md`
- **Quick Start:** `./deployment/QUICK-START.md`
- **Implementation Summary:** `./deployment/IMPLEMENTATION-SUMMARY.md`
- **UDP Architecture:** `./deployment/UDP-ARCHITECTURE.md`
- **This Checklist:** `./deployment/PRE-FLIGHT-CHECKLIST.md`

---

## Emergency Commands

### Kill Everything
```bash
pkill -9 -f socat
pkill -9 -f "ssh.*192.168.2.138"
pkill -9 -f uvicorn
pkill -9 -f vite
ssh hadi@192.168.2.138 'pkill -9 -f socat'
```

### Check What's Running
```bash
pgrep -af "socat|ssh|uvicorn|vite" | grep -v grep
```

### Test Network from PC1
```bash
# WiFi to PC2
ping -c 2 192.168.2.138

# Ethernet to Follower
ping -c 2 192.168.1.5

# Tunneled to Leader
nc -zv localhost 50001
nc -zv localhost 15000
```

---

**Ready to test when switch arrives! 🚀**
