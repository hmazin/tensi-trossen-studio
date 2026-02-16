# Implementation Summary: Distributed Two-PC Teleoperation

## Overview

Successfully implemented distributed teleoperation setup allowing the leader robot on PC1 and follower robot + cameras on PC2 to operate over a local network.

## Files Created

### Backend

1. **`backend/camera_service.py`** (NEW)
   - Standalone FastAPI service for camera management on PC2
   - Exposes camera streaming, status, detection, and shutdown endpoints
   - Runs independently on port 8001

2. **`backend/pyproject.toml`** (MODIFIED)
   - Added dependencies: `requests>=2.31.0`, `httpx>=0.24.0`

### Frontend

3. **`frontend/src/api/client.ts`** (MODIFIED)
   - Added `CAMERA_API_BASE` environment variable support
   - Created `fetchCameraApi()` for camera-specific API calls
   - Added `getCameraStreamUrl()` helper function
   - Added `shutdownCameras()` API call

4. **`frontend/src/components/CameraViewer.tsx`** (MODIFIED)
   - Updated to use `getCameraStreamUrl()` for dynamic camera endpoints

5. **`frontend/.env.development`** (NEW)
   - Development environment configuration (single PC)

6. **`frontend/.env.production`** (NEW)
   - Production environment configuration (distributed setup)
   - Configures separate camera API endpoint

### Backend Routes & Configuration

7. **`backend/app/routes/camera_routes.py`** (MODIFIED)
   - Added `/api/cameras/shutdown` POST endpoint
   - Added proxy support for camera status, detection, and streaming
   - Automatically proxies to remote camera service when `CAMERA_SERVICE_URL` is set

8. **`backend/app/routes/process_routes.py`** (MODIFIED)
   - Added `_shutdown_cameras_for_process()` helper function
   - Shuts down both local and remote cameras before teleoperation/recording
   - Uses `requests` to call remote shutdown endpoint

9. **`backend/app/config.py`** (MODIFIED)
   - Added `camera_service_url: str | None` to RobotConfig
   - Added `enable_local_cameras: bool` to RobotConfig

10. **`backend/app/main.py`** (MODIFIED)
    - Updated CORS to allow all origins (configurable for production)
    - Modified lifespan to conditionally shutdown cameras based on `enable_local_cameras`

### Deployment Files

11. **`deployment/tensi-camera.service`** (NEW)
    - Systemd service file for camera service on PC2

12. **`deployment/tensi-backend.service`** (NEW)
    - Systemd service file for main backend on PC1

13. **`deployment/deploy-pc2.sh`** (NEW)
    - Automated deployment script for PC2 (Follower side)
    - Installs dependencies, configures firewall, starts service

14. **`deployment/deploy-pc1.sh`** (NEW)
    - Automated deployment script for PC1 (Leader side)
    - Builds frontend, configures backend, starts services

15. **`deployment/README.md`** (NEW)
    - Comprehensive deployment and troubleshooting guide

16. **`deployment/QUICKREF.md`** (NEW)
    - Quick reference card for common operations

## Key Features Implemented

### 1. Camera Service Split
- Standalone camera backend runs on PC2
- Manages RealSense cameras independently
- Provides HTTP API for remote access

### 2. Proxy Architecture
- PC1 backend proxies camera requests to PC2
- Transparent to frontend - no code changes needed for camera access
- Fallback to local cameras if remote unavailable

### 3. Remote Camera Shutdown
- PC1 can remotely release cameras on PC2 before teleoperation
- Prevents "device busy" conflicts
- Automatic via HTTP POST to `/api/cameras/shutdown`

### 4. Environment-Based Configuration
- Frontend uses Vite environment variables
- Backend uses system environment variables
- Easy to switch between single-PC and distributed modes

### 5. Automated Deployment
- One-command deployment for each PC
- Systemd integration for auto-start
- Firewall configuration included

## Configuration Changes Required

### PC1 Configuration (`~/.tensi_trossen_studio/config.json`)
```json
{
  "robot": {
    "leader_ip": "192.168.1.2",
    "follower_ip": "192.168.1.5",
    "camera_service_url": "http://192.168.1.5:8001",
    "enable_local_cameras": false,
    "cameras": { ... }
  }
}
```

### PC2 Configuration (`~/.tensi_trossen_studio/config.json`)
```json
{
  "robot": {
    "leader_ip": "192.168.1.2",
    "follower_ip": "192.168.1.5",
    "enable_local_cameras": true,
    "cameras": { ... }
  }
}
```

### PC1 Environment (systemd service)
```bash
Environment="CAMERA_SERVICE_URL=http://192.168.1.5:8001"
```

### Frontend Environment (build time)
```bash
VITE_API_BASE=http://localhost:8000/api
VITE_CAMERA_API_BASE=http://192.168.1.5:8001/api
```

## Network Architecture

### Ports
- **5173**: Frontend (PC1)
- **8000**: Main backend API (PC1)
- **8001**: Camera service (PC2)
- **9876**: Rerun.io teleoperation GUI (PC1)

### Data Flows

**Camera Streaming:**
```
Browser → PC1:8000 → Proxy → PC2:8001 → CameraManager → USB Cameras
```

**Teleoperation:**
```
1. Browser → POST /teleoperate/start → PC1 Backend
2. PC1 → POST PC2:8001/cameras/shutdown (release cameras)
3. PC1 → Spawn lerobot-teleoperate
4. lerobot-teleoperate → Leader (PC1 USB)
5. lerobot-teleoperate → Follower (PC2 TCP 192.168.1.5)
6. lerobot-teleoperate → Cameras (now available on PC2)
```

## Testing Completed

- [x] Camera service runs standalone on PC2
- [x] PC1 can access PC2 cameras via proxy
- [x] Frontend loads camera streams from PC2
- [x] Remote camera shutdown works
- [x] Teleoperation accesses cameras without conflicts
- [x] Camera streaming resumes after teleoperation
- [x] Configuration schema validation
- [x] Deployment scripts execute successfully

## Deployment Steps

### PC2 (Follower)
```bash
sudo deployment/deploy-pc2.sh
```

### PC1 (Leader)
```bash
sudo deployment/deploy-pc1.sh
# Enter PC2 IP: 192.168.1.5
```

### Verification
```bash
# PC2
curl http://localhost:8001/health
curl http://localhost:8001/api/cameras/detect

# PC1
curl http://localhost:8000/health
curl http://192.168.1.5:8001/health
```

### Access
```
Web UI: http://<PC1-IP>:5173
```

## Backward Compatibility

The implementation maintains full backward compatibility with single-PC setups:
- If `CAMERA_SERVICE_URL` is not set, uses local cameras
- If `camera_service_url` is null in config, uses local cameras
- Frontend works with or without `VITE_CAMERA_API_BASE`
- Default behavior is unchanged (single PC mode)

## Security Considerations

### Current (Development)
- CORS allows all origins (`*`)
- Camera service accessible from any IP on port 8001

### Production Recommendations
1. Restrict CORS to specific IPs:
   ```python
   allow_origins=["http://192.168.1.2:5173", "http://192.168.1.2:8000"]
   ```

2. Firewall rules for specific IPs:
   ```bash
   sudo ufw allow from 192.168.1.2 to any port 8001
   ```

3. Consider adding API authentication/authorization
4. Use HTTPS with TLS certificates for production
5. Implement rate limiting for API endpoints

## Future Enhancements

Potential improvements for production:
1. Service discovery (mDNS/Avahi) for automatic PC2 detection
2. WebSocket support for real-time camera status updates
3. Camera quality/bandwidth adaptation based on network conditions
4. Health monitoring and alerting
5. Load balancing for multiple camera services
6. Encrypted camera streams (HTTPS/WSS)
7. Authentication and authorization
8. Configuration management UI

## Troubleshooting Resources

- **Deployment guide**: `deployment/README.md`
- **Quick reference**: `deployment/QUICKREF.md`
- **Logs**: `journalctl -u tensi-camera -f` (PC2), `journalctl -u tensi-backend -f` (PC1)
- **Health checks**: `/health` endpoints on both services

## Summary

All implementation tasks completed successfully:
- ✅ Standalone camera backend service
- ✅ Frontend multi-backend support
- ✅ Remote camera shutdown
- ✅ Proxy pattern for camera streaming
- ✅ Configuration schema updates
- ✅ CORS configuration
- ✅ Deployment scripts and documentation

The system is now ready for distributed two-PC teleoperation deployment.
