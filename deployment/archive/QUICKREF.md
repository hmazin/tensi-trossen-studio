# Distributed Setup Quick Reference

## PC2 (Follower Side)

### Deploy
```bash
sudo deployment/deploy-pc2.sh
```

### Service Management
```bash
sudo systemctl status tensi-camera
sudo systemctl restart tensi-camera
sudo journalctl -u tensi-camera -f
```

### Test
```bash
curl http://localhost:8001/health
curl http://localhost:8001/api/cameras/detect
```

### Config (`~/.tensi_trossen_studio/config.json`)
```json
{
  "robot": {
    "enable_local_cameras": true
  }
}
```

---

## PC1 (Leader Side)

### Deploy
```bash
sudo deployment/deploy-pc1.sh
# Enter PC2 IP when prompted (e.g., 192.168.1.5)
```

### Service Management
```bash
sudo systemctl status tensi-backend
sudo systemctl restart tensi-backend
sudo journalctl -u tensi-backend -f
tail -f /tmp/tensi-frontend.log
```

### Test
```bash
curl http://localhost:8000/health
curl http://192.168.1.5:8001/health
```

### Config (`~/.tensi_trossen_studio/config.json`)
```json
{
  "robot": {
    "leader_ip": "192.168.1.2",
    "follower_ip": "192.168.1.5",
    "camera_service_url": "http://192.168.1.5:8001",
    "enable_local_cameras": false
  }
}
```

### Environment (in systemd service or shell)
```bash
export CAMERA_SERVICE_URL=http://192.168.1.5:8001
```

---

## Verification Checklist

- [ ] PC2 camera service running: `systemctl status tensi-camera`
- [ ] PC2 cameras detected: `curl http://192.168.1.5:8001/api/cameras/detect`
- [ ] PC1 can reach PC2: `curl http://192.168.1.5:8001/health`
- [ ] PC1 backend running: `systemctl status tensi-backend`
- [ ] Web UI accessible: `http://<PC1-IP>:5173`
- [ ] Camera feeds visible in web UI
- [ ] Teleoperation starts without camera conflicts
- [ ] Cameras resume streaming after teleoperation stops

---

## Common Commands

### Update frontend camera API URL
```bash
# frontend/.env.production
VITE_CAMERA_API_BASE=http://192.168.1.5:8001/api
```

### Rebuild frontend
```bash
cd frontend
VITE_CAMERA_API_BASE=http://192.168.1.5:8001/api npm run build
```

### Restart all services
```bash
# PC2
sudo systemctl restart tensi-camera

# PC1
sudo systemctl restart tensi-backend
```

### View all logs
```bash
# PC2
sudo journalctl -u tensi-camera -f

# PC1
sudo journalctl -u tensi-backend -f
tail -f /tmp/tensi-frontend.log
```

---

## Network Ports

| Port | Service | Location |
|------|---------|----------|
| 5173 | Frontend (Web UI) | PC1 |
| 8000 | Backend API | PC1 |
| 8001 | Camera Service | PC2 |
| 9876 | Rerun.io (teleoperation GUI) | PC1 |

---

## Troubleshooting

### Cameras not showing
1. Check PC2 service: `sudo systemctl status tensi-camera`
2. Check network: `ping 192.168.1.5`
3. Check firewall: `sudo ufw status`
4. Check frontend env: Browser console → `import.meta.env`

### Teleoperation camera conflict
1. Check PC1 shuts down remote cameras: `journalctl -u tensi-backend -f`
2. Check PC2 receives shutdown: `journalctl -u tensi-camera -f`
3. Verify `CAMERA_SERVICE_URL` is set in PC1 backend service

### Network unreachable
```bash
# Test connectivity
ping 192.168.1.5
nc -zv 192.168.1.5 8001

# Check firewall on PC2
sudo ufw allow from 192.168.1.0/24 to any port 8001
```
