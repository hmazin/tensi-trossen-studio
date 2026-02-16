# PC2 Setup Guide - Network-Aware Deployment

## Network Configuration

**PC1:**
- WiFi: 192.168.2.140 (PC-to-PC communication)
- Ethernet: 192.168.1.100 (Leader robot connection)
- Leader Robot: 192.168.1.2

**PC2:**
- WiFi: 192.168.2.138 (PC-to-PC communication) ← Camera service accessible here
- Ethernet: Connects to Follower Robot at 192.168.1.5

**Important:** Camera service on PC2 will be accessible at `http://192.168.2.138:8001`

---

## Step-by-Step Deployment via SSH

### Step 1: SSH to PC2
```bash
# From PC1
ssh tensi@192.168.2.138
```

### Step 2: Clone Repository
```bash
cd /home/tensi
git clone <repo-url> tensi-trossen-studio
cd tensi-trossen-studio
```

**Alternative: Copy from PC1 via rsync**
```bash
# Run from PC1 (not in SSH session)
rsync -avz --exclude 'node_modules' --exclude '.venv' --exclude 'backend/.venv' \
  /home/tensi/tensi-trossen-studio/ \
  tensi@192.168.2.138:/home/tensi/tensi-trossen-studio/
```

### Step 3: Verify Camera Hardware
```bash
# Check cameras are detected
rs-enumerate-devices
# Should show: 218622275782 and 218622278263
```

### Step 4: Install Backend Dependencies
```bash
cd /home/tensi/tensi-trossen-studio/backend
uv sync
```

### Step 5: Create Configuration File
```bash
mkdir -p ~/.tensi_trossen_studio
cat > ~/.tensi_trossen_studio/config.json << 'EOF'
{
  "robot": {
    "leader_ip": "192.168.1.2",
    "follower_ip": "192.168.1.5",
    "enable_local_cameras": true,
    "cameras": {
      "wrist": {
        "type": "intelrealsense",
        "serial_number_or_name": "218622275782",
        "width": 848,
        "height": 480,
        "fps": 30
      },
      "top": {
        "type": "intelrealsense",
        "serial_number_or_name": "218622278263",
        "width": 848,
        "height": 480,
        "fps": 30
      }
    }
  },
  "lerobot_trossen_path": "/home/tensi/lerobot_trossen"
}
EOF
```

### Step 6: Test Camera Service Manually
```bash
cd /home/tensi/tensi-trossen-studio/backend
uv run uvicorn camera_service:app --host 0.0.0.0 --port 8001
```

**In a new terminal on PC1**, test via WiFi:
```bash
curl http://192.168.2.138:8001/health
curl http://192.168.2.138:8001/api/cameras/detect
curl http://192.168.2.138:8001/api/cameras/status
```

**Press Ctrl+C** in SSH session to stop test server.

### Step 7: Run Deployment Script
```bash
cd /home/tensi/tensi-trossen-studio
sudo ./deployment/deploy-pc2.sh
```

### Step 8: Verify Systemd Service
```bash
# Check service status
sudo systemctl status tensi-camera

# View live logs
sudo journalctl -u tensi-camera -f
# Press Ctrl+C to exit
```

### Step 9: Test from PC1
```bash
# From PC1 (exit SSH session first)
curl http://192.168.2.138:8001/health
curl http://192.168.2.138:8001/api/cameras/detect

# Test camera stream in browser
# Open: http://192.168.2.138:8001/api/cameras/stream/wrist
```

---

## PC2 Configuration Summary

**Camera Service URL for PC1:**
```
http://192.168.2.138:8001
```

**Key Settings:**
- Service binds to: `0.0.0.0:8001` (all interfaces)
- Accessible on WiFi: `192.168.2.138:8001`
- Cameras connected via USB to PC2
- Follower robot accessible via Ethernet at `192.168.1.5`

---

## Next Steps

Once PC2 is deployed and verified:

1. Note these values for PC1 setup:
   - `CAMERA_SERVICE_URL=http://192.168.2.138:8001`
   - Camera service is accessible at WiFi IP

2. PC1 will need environment variable:
   ```bash
   export CAMERA_SERVICE_URL=http://192.168.2.138:8001
   ```

3. Frontend `.env.production` on PC1:
   ```
   VITE_CAMERA_API_BASE=http://192.168.2.138:8001/api
   ```

---

## Troubleshooting

### Cannot reach camera service from PC1
```bash
# On PC2, check service is running
sudo systemctl status tensi-camera

# On PC2, test locally
curl http://localhost:8001/health

# On PC2, check WiFi IP
ip addr show | grep "192.168.2"

# On PC1, test connectivity
ping 192.168.2.138
curl http://192.168.2.138:8001/health

# On PC2, check firewall
sudo ufw status
# Should show rule for port 8001
```

### Firewall blocking access
```bash
# On PC2
sudo ufw allow from 192.168.2.0/24 to any port 8001 comment "TENSI Camera from WiFi"
sudo ufw reload
sudo ufw status numbered
```

### Cameras not detected
```bash
# Check USB
rs-enumerate-devices

# Check logs
sudo journalctl -u tensi-camera -f
```

---

## Quick Command Reference

```bash
# Service management (on PC2)
sudo systemctl status tensi-camera
sudo systemctl restart tensi-camera
sudo journalctl -u tensi-camera -f

# Testing from PC1
curl http://192.168.2.138:8001/health
curl http://192.168.2.138:8001/api/cameras/detect

# Network verification
ping 192.168.2.138  # PC1 to PC2 WiFi
ssh tensi@192.168.2.138  # SSH to PC2
```
