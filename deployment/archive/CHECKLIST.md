# Pre-Deployment Verification Checklist

Use this checklist before deploying the distributed setup to ensure all prerequisites are met.

## Hardware Prerequisites

### PC1 (Leader Side)
- [ ] Leader robot physically connected via USB
- [ ] USB cable securely connected
- [ ] Leader robot powered on
- [ ] Leader robot firmware up to date

### PC2 (Follower Side)
- [ ] Follower robot network cable connected
- [ ] Follower robot at IP address 192.168.1.5 (or configured IP)
- [ ] Follower robot powered on
- [ ] RealSense cameras connected via USB
- [ ] Cameras connected to powered USB hub (if needed)
- [ ] Verify cameras with `rs-enumerate-devices`

### Network
- [ ] Both PCs on same local network
- [ ] PC1 can ping PC2: `ping 192.168.1.5`
- [ ] No firewall blocking port 8001
- [ ] Network latency < 50ms: `ping -c 10 192.168.1.5`

## Software Prerequisites

### Both PCs
- [ ] Ubuntu/Debian Linux (tested on Ubuntu 22.04+)
- [ ] Python 3.10 or higher: `python3 --version`
- [ ] `uv` installed: `uv --version`
- [ ] Git installed: `git --version`
- [ ] Repository cloned to `/home/tensi/tensi-trossen-studio`

### PC1 Only
- [ ] Node.js 18+ installed: `node --version`
- [ ] npm installed: `npm --version`

### PC2 Only
- [ ] RealSense SDK installed: `rs-enumerate-devices`
- [ ] OpenCV installed: `python3 -c "import cv2; print(cv2.__version__)"`

## Pre-Deployment Tests

### PC2 Camera Tests
```bash
# Test camera detection
cd ~/lerobot_trossen
uv run lerobot-find-cameras realsense

# Should show both cameras
# 218622275782 (wrist)
# 218622278263 (top)
```

### PC1 Leader Robot Test
```bash
# Test leader connection
cd ~/lerobot_trossen
# Try reading joint positions (specific command depends on your setup)
```

### PC2 Follower Robot Test
```bash
# From PC1, test follower connectivity
ping 192.168.1.5

# Test follower robot (if accessible via network tools)
```

## Configuration Files Ready

### PC1
- [ ] `~/.tensi_trossen_studio/config.json` exists with correct camera serials
- [ ] Leader IP is correct (192.168.1.2 or actual)
- [ ] Follower IP is correct (192.168.1.5 or actual)

### PC2
- [ ] `~/.tensi_trossen_studio/config.json` exists with correct camera serials
- [ ] Camera serials match detected cameras

## Deployment File Checks

- [ ] Deployment scripts exist:
  - `/home/tensi/tensi-trossen-studio/deployment/deploy-pc1.sh`
  - `/home/tensi/tensi-trossen-studio/deployment/deploy-pc2.sh`
- [ ] Scripts are executable: `ls -l deployment/*.sh`
- [ ] Systemd service files exist:
  - `/home/tensi/tensi-trossen-studio/deployment/tensi-camera.service`
  - `/home/tensi/tensi-trossen-studio/deployment/tensi-backend.service`

## Permissions and Access

- [ ] User `tensi` exists on both PCs
- [ ] User `tensi` has sudo access (for systemd operations)
- [ ] User `tensi` can access USB devices (for cameras/robots)
- [ ] Check USB permissions: `ls -l /dev/bus/usb/*/*`

## Firewall Preparation

### PC2
- [ ] UFW installed: `sudo ufw --version` (or firewalld)
- [ ] Current UFW status: `sudo ufw status`
- [ ] Prepared to allow port 8001 from 192.168.1.0/24

## Post-Deployment Verification Plan

### PC2 Verification
```bash
# Service status
sudo systemctl status tensi-camera

# Health check
curl http://localhost:8001/health

# Camera detection
curl http://localhost:8001/api/cameras/detect

# Camera status
curl http://localhost:8001/api/cameras/status
```

### PC1 Verification
```bash
# Backend status
sudo systemctl status tensi-backend

# Backend health
curl http://localhost:8000/health

# Remote camera service reachable
curl http://192.168.1.5:8001/health

# Frontend running
curl http://localhost:5173
```

### Browser Tests
- [ ] Open web UI: `http://<PC1-IP>:5173`
- [ ] Camera feeds visible
- [ ] Camera feeds show live video (not "Camera unavailable")
- [ ] Configuration page loads
- [ ] Can detect cameras via diagnostic button
- [ ] Teleoperation button is clickable

### Integration Tests
1. **Camera Streaming**
   - [ ] Open web UI
   - [ ] Both cameras show live feeds
   - [ ] No lag or freezing

2. **Teleoperation**
   - [ ] Click "Start Teleoperation"
   - [ ] Camera feeds disappear (cameras released)
   - [ ] Rerun window opens on PC1
   - [ ] Can control follower via leader
   - [ ] Stop teleoperation
   - [ ] Camera feeds resume in web UI

3. **Recording**
   - [ ] Click "Start Recording"
   - [ ] Cameras released
   - [ ] Recording progresses
   - [ ] Stop recording
   - [ ] Camera feeds resume

## Rollback Plan

If deployment fails, be prepared to:

### PC2 Rollback
```bash
# Stop service
sudo systemctl stop tensi-camera

# Disable service
sudo systemctl disable tensi-camera

# Remove service file
sudo rm /etc/systemd/system/tensi-camera.service
sudo systemctl daemon-reload

# Restore previous setup (if any)
```

### PC1 Rollback
```bash
# Stop services
sudo systemctl stop tensi-backend

# Disable services
sudo systemctl disable tensi-backend

# Remove service files
sudo rm /etc/systemd/system/tensi-backend.service
sudo systemctl daemon-reload

# Restore single-PC mode
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Known Issues and Workarounds

### Issue: Cameras show "Device busy"
**Cause**: Previous process didn't release cameras
**Fix**: Restart PC2 or unplug/replug cameras

### Issue: Cannot reach PC2 from PC1
**Cause**: Firewall or network configuration
**Fix**: 
```bash
# On PC2
sudo ufw allow from 192.168.1.0/24 to any port 8001
```

### Issue: Camera feeds are black
**Cause**: Cameras not getting enough power
**Fix**: Use powered USB hub

### Issue: High latency in camera streams
**Cause**: Network bandwidth or USB bandwidth
**Fix**: 
- Reduce camera FPS in config (30 → 15)
- Reduce camera resolution (848x480 → 640x480)
- Check network with `iperf3`

## Emergency Contacts

Before deployment, note:
- [ ] System administrator contact
- [ ] Network administrator contact
- [ ] Hardware vendor support
- [ ] Project lead contact

## Sign-Off

- [ ] Hardware verified
- [ ] Software verified
- [ ] Network verified
- [ ] Configuration verified
- [ ] Backup/rollback plan ready
- [ ] Team notified of deployment schedule

**Verified by**: _______________ **Date**: _______________

**Ready for deployment**: [ ] Yes [ ] No

**Notes**:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________
