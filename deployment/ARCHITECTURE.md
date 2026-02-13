# Architecture Diagrams

## System Overview

```
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│         PC1 (Leader Side)        │         │        PC2 (Follower Side)       │
│         192.168.1.2              │         │         192.168.1.5              │
├─────────────────────────────────┤         ├─────────────────────────────────┤
│                                 │         │                                 │
│  ┌───────────────────────────┐  │         │  ┌───────────────────────────┐  │
│  │   Web UI (Frontend)       │  │         │  │  Camera Service           │  │
│  │   Port 5173               │  │         │  │  Port 8001                │  │
│  │                           │  │         │  │                           │  │
│  │  - React + Vite           │  │         │  │  - FastAPI                │  │
│  │  - Camera Viewer          │  │         │  │  - CameraManager          │  │
│  │  - Config UI              │  │         │  │  - RealSense Streams      │  │
│  └───────────┬───────────────┘  │         │  └───────────┬───────────────┘  │
│              │ HTTP              │         │              │                  │
│  ┌───────────▼───────────────┐  │         │  ┌───────────▼───────────────┐  │
│  │   Backend API             │  │         │  │  USB Cameras              │  │
│  │   Port 8000               │  │         │  │                           │  │
│  │                           │  │◄────────┤  │  - Wrist (218622275782)   │  │
│  │  - FastAPI                │  │  HTTP   │  │  - Top (218622278263)     │  │
│  │  - ProcessManager         │  │  Proxy  │  │                           │  │
│  │  - Camera Proxy           │  │         │  └───────────────────────────┘  │
│  └───────────┬───────────────┘  │         │                                 │
│              │                   │         │  ┌───────────────────────────┐  │
│  ┌───────────▼───────────────┐  │         │  │  Follower Robot           │  │
│  │  lerobot-teleoperate      │  │◄────────┼──┤  TCP Connection           │  │
│  │                           │  │  TCP    │  │  192.168.1.5              │  │
│  │  - Leader Control         │  │         │  │                           │  │
│  │  - Follower Control       │  │         │  │  - WidowX AI              │  │
│  │  - Camera Access          │  │         │  │  - Joint Control          │  │
│  │  - Rerun GUI (9876)       │  │         │  └───────────────────────────┘  │
│  └───────────┬───────────────┘  │         │                                 │
│              │ USB               │         └─────────────────────────────────┘
│  ┌───────────▼───────────────┐  │
│  │  Leader Robot             │  │
│  │  USB Connection           │  │
│  │                           │  │
│  │  - WidowX AI              │  │
│  │  - Joint Sensing          │  │
│  └───────────────────────────┘  │
│                                 │
└─────────────────────────────────┘

                    Local Network (192.168.1.0/24)
```

## Camera Streaming Flow

```
┌──────────┐     GET /api/cameras/stream/wrist      ┌──────────┐
│          │────────────────────────────────────────►│          │
│ Browser  │                                         │ PC1      │
│ (User)   │◄────────────────────────────────────────│ Backend  │
│          │     MJPEG Stream (Proxied)             │ :8000    │
└──────────┘                                         └────┬─────┘
                                                          │
                                                          │ GET /api/cameras/stream/wrist
                                                          │ (Proxy Request)
                                                          │
                                                     ┌────▼─────┐
                                                     │ PC2      │
                                                     │ Camera   │
                                                     │ Service  │
                                                     │ :8001    │
                                                     └────┬─────┘
                                                          │
                                                          │ Read from buffer
                                                          │
                                                     ┌────▼─────┐
                                                     │ Camera   │
                                                     │ Manager  │
                                                     │ Thread   │
                                                     └────┬─────┘
                                                          │
                                                          │ USB
                                                          │
                                                     ┌────▼─────┐
                                                     │ RealSense│
                                                     │ Camera   │
                                                     │ Hardware │
                                                     └──────────┘
```

## Teleoperation Startup Flow

```
┌──────────┐
│ User     │
│ clicks   │
│ "Start   │
│ Teleop"  │
└────┬─────┘
     │
     │ POST /api/teleoperate/start
     │
┌────▼─────────────────────────────────────────────┐
│ PC1 Backend (process_routes.py)                 │
│                                                  │
│ 1. _shutdown_cameras_for_process()              │
│    ├─ Shutdown local cameras (no-op)            │
│    └─ POST http://192.168.1.5:8001/              │
│       api/cameras/shutdown ──────────────┐       │
│                                          │       │
│ 2. Spawn lerobot-teleoperate            │       │
│    ├─ Connect to Leader (USB)           │       │
│    ├─ Connect to Follower (TCP) ────────┼───┐   │
│    └─ Access Cameras (USB) ─────────────┼───┼─┐ │
│                                          │   │ │ │
└──────────────────────────────────────────┼───┼─┼─┘
                                           │   │ │
                                           │   │ │
                                      ┌────▼───▼─▼────┐
                                      │ PC2            │
                                      │                │
                                      │ 1. Shutdown    │
                                      │    cameras     │
                                      │                │
                                      │ 2. Follower    │
                                      │    accepts TCP │
                                      │                │
                                      │ 3. Cameras     │
                                      │    available   │
                                      │    for teleop  │
                                      └────────────────┘
```

## Configuration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Development Mode                         │
│                     (Single PC)                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Backend: No CAMERA_SERVICE_URL set                          │
│  Frontend: VITE_CAMERA_API_BASE=/api                         │
│  Config: enable_local_cameras=true                           │
│                                                              │
│  Result: All services run locally                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Production Mode                          │
│                     (Distributed - Two PCs)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PC1 Backend:                                                │
│    CAMERA_SERVICE_URL=http://192.168.1.5:8001               │
│    enable_local_cameras=false                                │
│                                                              │
│  PC1 Frontend:                                               │
│    VITE_API_BASE=http://localhost:8000/api                   │
│    VITE_CAMERA_API_BASE=http://192.168.1.5:8001/api        │
│                                                              │
│  PC2 Backend:                                                │
│    No CAMERA_SERVICE_URL                                     │
│    enable_local_cameras=true                                 │
│                                                              │
│  Result: Camera service on PC2, everything else on PC1       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Service Dependencies

```
┌─────────────────┐
│  Network        │  (Required for all)
└────────┬────────┘
         │
    ┌────▼────┐    ┌─────────┐
    │ PC2     │    │ PC1     │
    │ Camera  │    │ Backend │
    │ Service │◄───┤ Service │
    └────┬────┘    └────┬────┘
         │              │
         │         ┌────▼────┐
         │         │ PC1     │
         │         │ Frontend│
         │         └─────────┘
         │
         │         ┌──────────────┐
         └────────►│ lerobot-     │
                   │ teleoperate  │
                   └──────────────┘
```

## Data Flow Sequence

### Normal Operation (Camera Streaming)

```
Time │ PC1 Browser    │ PC1 Backend       │ PC2 Camera Service │ PC2 Cameras
─────┼────────────────┼───────────────────┼────────────────────┼──────────────
  1  │ Request stream │                   │                    │
  2  │───────────────►│                   │                    │
  3  │                │ Proxy to PC2      │                    │
  4  │                │──────────────────►│                    │
  5  │                │                   │ Get latest frame   │
  6  │                │                   │───────────────────►│
  7  │                │                   │◄───────────────────│
  8  │                │◄──────────────────│  JPEG data         │
  9  │◄───────────────│  MJPEG stream     │                    │
 10  │ Display frame  │                   │                    │
 11  │                │                   │  (Repeat 5-10)     │
```

### Teleoperation Start

```
Time │ PC1 Browser    │ PC1 Backend       │ PC2 Camera Service │ lerobot-teleoperate
─────┼────────────────┼───────────────────┼────────────────────┼────────────────────
  1  │ Start teleop   │                   │                    │
  2  │───────────────►│                   │                    │
  3  │                │ Shutdown remote   │                    │
  4  │                │──────────────────►│                    │
  5  │                │                   │ Release cameras    │
  6  │                │◄──────────────────│                    │
  7  │                │ Spawn process     │                    │
  8  │                │──────────────────────────────────────►│
  9  │                │                   │                    │ Connect to Leader
 10  │                │                   │                    │ Connect to Follower
 11  │                │                   │                    │ Open cameras
 12  │                │                   │                    │ Start teleoperation
 13  │◄─ Rerun GUI ───┼───────────────────┼────────────────────┼─────────────────────
```

## Port Mapping

```
┌──────┬─────────────────────┬──────────┬────────────────────┐
│ Port │ Service             │ Location │ Access             │
├──────┼─────────────────────┼──────────┼────────────────────┤
│ 5173 │ Frontend (Vite)     │ PC1      │ Browser            │
│ 8000 │ Backend API         │ PC1      │ Browser, Internal  │
│ 8001 │ Camera Service      │ PC2      │ PC1 Backend        │
│ 9876 │ Rerun GUI (gRPC)    │ PC1      │ Local              │
└──────┴─────────────────────┴──────────┴────────────────────┘
```

## File Structure

```
tensi-trossen-studio/
├── backend/
│   ├── app/
│   │   ├── main.py                    (Modified: CORS, lifespan)
│   │   ├── config.py                  (Modified: distributed config)
│   │   ├── routes/
│   │   │   ├── camera_routes.py       (Modified: proxy, shutdown)
│   │   │   └── process_routes.py      (Modified: remote shutdown)
│   │   └── services/
│   │       ├── camera_manager.py      (Existing)
│   │       └── camera_streamer.py     (Existing)
│   ├── camera_service.py              (NEW: standalone camera service)
│   └── pyproject.toml                 (Modified: added dependencies)
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts              (Modified: multi-backend)
│   │   └── components/
│   │       └── CameraViewer.tsx       (Modified: dynamic URLs)
│   ├── .env.development               (NEW: dev config)
│   └── .env.production                (NEW: production config)
│
└── deployment/
    ├── deploy-pc1.sh                  (NEW: PC1 deployment)
    ├── deploy-pc2.sh                  (NEW: PC2 deployment)
    ├── tensi-backend.service          (NEW: PC1 systemd)
    ├── tensi-camera.service           (NEW: PC2 systemd)
    ├── README.md                      (NEW: full guide)
    ├── QUICKREF.md                    (NEW: quick reference)
    ├── IMPLEMENTATION.md              (NEW: details)
    ├── CHECKLIST.md                   (NEW: pre-deployment)
    ├── SUMMARY.md                     (NEW: overview)
    └── ARCHITECTURE.md                (NEW: this file)
```
