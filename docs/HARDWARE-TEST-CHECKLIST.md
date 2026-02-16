# Hardware Test Checklist

Manual tests that require physical robots and cameras. Run this checklist before releases or after significant changes to robot control, camera management, or the distributed teleoperation system.

## Pre-conditions

- [ ] Both leader and follower robots powered on
- [ ] iNerve controller LEDs are green (not red or off)
- [ ] Robots connected to their respective NetGear switches via Ethernet
- [ ] RealSense cameras connected via USB to PC1
- [ ] Backend running: `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Frontend running: `npm run dev`
- [ ] Web UI accessible at http://localhost:5173

---

## Single-PC Tests

These tests assume leader and follower are both on the same Ethernet switch connected to one PC.

### Teleoperation

- [ ] Click **Start Teleoperation** in the web UI
- [ ] Process Log shows the lerobot process starting without errors
- [ ] Move the leader arm -- follower arm mirrors movements in real-time
- [ ] Gripper open/close on leader is mirrored on follower
- [ ] Click **Stop** -- process terminates cleanly
- [ ] Leader arm returns to sleep position after stop
- [ ] Follower arm returns to sleep position after stop
- [ ] StatusBar shows "Idle" after stopping

### Recording

- [ ] Set dataset name, episodes, and task description
- [ ] Click **Start Recording**
- [ ] Perform a demonstration -- move the leader arm
- [ ] Episode completes and data is saved (check terminal output)
- [ ] Click **Stop** when done
- [ ] Verify dataset files exist at expected path

### Training

- [ ] Enter a valid dataset repo ID
- [ ] Click **Start Training**
- [ ] Process Log shows training progress (loss values, etc.)
- [ ] Click **Stop** -- training process terminates

### Replay

- [ ] Enter a dataset repo ID and episode number with existing data
- [ ] Click **Start Replay**
- [ ] Follower robot executes the recorded trajectory
- [ ] Process completes or can be stopped

---

## Camera Tests

### Streaming

- [ ] Camera feed shows live image for configured cameras (wrist, top)
- [ ] Image updates smoothly (not frozen)
- [ ] "Detect cameras" button shows correct serial numbers
- [ ] Camera status shows "running" in the diagnostics panel

### Camera-process handoff

- [ ] Start teleoperation -- cameras should release (stream shows placeholder or unavailable)
- [ ] Stop teleoperation -- camera streams should recover automatically
- [ ] No "camera in use" errors when starting teleoperation

### Error recovery

- [ ] Disconnect a camera USB cable -- UI shows error state
- [ ] Reconnect the camera -- stream recovers (may need to click "Detect cameras")

---

## Distributed Tests (Two PCs)

These tests require PC1 (follower + cameras) and PC2 (leader) on separate networks.

### Pre-conditions (distributed)

- [ ] PC1 and PC2 on same WiFi network (can ping each other)
- [ ] SSH access from PC1 to PC2: `ssh hadi@<PC2_IP>` works without password prompt
- [ ] `leader_service.py` is present on PC2 at `~/leader_service.py`
- [ ] `trossen_arm` Python package is installed on PC2
- [ ] Remote Leader Mode enabled in web UI Settings
- [ ] Leader Service Host and Port correctly configured

### Leader Service Management

- [ ] Click **Start Leader** in the web UI -- Leader Service card turns green ("Running")
- [ ] Verify on PC2: `ps aux | grep leader_service` shows the process
- [ ] Verify on PC2: `tail /tmp/leader_service.log` shows "listening on :5555"
- [ ] Click **Stop Leader** -- Leader Service card turns to "Stopped"
- [ ] Verify on PC2: process is no longer running

### Distributed Teleoperation

- [ ] Start the Leader Service (green indicator)
- [ ] Click **Start Teleoperation**
- [ ] Process Log shows "Connecting to remote leader" or similar
- [ ] Move the leader arm on PC2 -- follower on PC1 mirrors movements
- [ ] Latency is acceptable (no noticeable delay on LAN, <200ms on WAN)

### Graceful Disconnect

- [ ] While teleoperating, click **Stop** in the web UI
- [ ] Follower arm stops and returns to sleep position
- [ ] Leader arm on PC2 returns to staged position, then sleep position
- [ ] Leader service remains running (ready for next session)
- [ ] Leader Service card still shows "Running"

### Unexpected Disconnect

- [ ] While teleoperating, kill the backend on PC1: `pkill -f uvicorn`
- [ ] Check PC2 logs: leader service should detect disconnect
- [ ] Leader arm on PC2 should return to safe (sleep) position
- [ ] Leader iNerve LED should return to green (not stay blue)

### Network Interruption

- [ ] While teleoperating, briefly disconnect PC1 from WiFi
- [ ] Follower should stop moving (no more position updates)
- [ ] Reconnect WiFi -- check if teleoperation can be restarted

---

## StatusBar Indicators

- [ ] Idle state: StatusBar shows "Idle" with gray pill
- [ ] Teleoperating: StatusBar shows "Teleoperating" with green pulsing pill
- [ ] Recording: StatusBar shows "Recording" with blue pulsing pill
- [ ] Leader Service running: Leader Svc chip shows green dot
- [ ] Leader Service stopped: Leader Svc chip shows red dot

---

## Settings Panel

- [ ] Gear icon opens the settings panel (slides in from right)
- [ ] All fields are editable (IPs, ports, camera serials)
- [ ] Remote Leader Mode checkbox toggles the leader config fields
- [ ] Click **Save Settings** -- config persists (refresh page and verify)
- [ ] Click **Cancel** -- changes are discarded

---

## Failure Signatures

Common issues to watch for during testing:

| Symptom | Likely cause |
|---------|-------------|
| iNerve LED turns red immediately | Robot needs power cycle; or direct PC connection (needs switch) |
| "Failed to receive initial joint outputs" | Robot controller not ready; power cycle and wait for green LED |
| "ConnectionRefusedError" on remote leader | Leader service not running on PC2 |
| "No route to host" on 192.168.1.x | Trying to reach robot on wrong PC's Ethernet network |
| Camera "hardware timeout" | USB bandwidth issue; try different USB port |
| Process Log shows nothing | Backend may have crashed; check terminal output |

---

Last updated: 2026-02-16
