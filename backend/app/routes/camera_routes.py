"""Camera streaming API routes."""

import logging
import os
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import load_config
from app.services.camera_manager import CameraManager
from app.services.camera_streamer import CameraStreamer

router = APIRouter(prefix="/api/cameras", tags=["cameras"])
logger = logging.getLogger(__name__)


@router.get("/status")
def camera_status() -> dict:
    """Return status of all cameras including any hardware errors."""
    config = load_config()
    cameras = config.robot.cameras or {}
    
    # Check if we should proxy to remote camera service
    camera_service_url = os.getenv("CAMERA_SERVICE_URL")
    if camera_service_url:
        try:
            import requests
            response = requests.get(f"{camera_service_url}/api/cameras/status", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get status from remote camera service: {e}")
            # Fall back to local cameras
    
    # Local camera status (teleop cameras + operator if configured)
    manager = CameraManager.get_instance()
    status = {}
    for key in cameras:
        status[key] = manager.get_camera_status(key)
    if config.robot.operator_camera:
        status["operator"] = manager.get_camera_status("operator")
    return {"cameras": status}


@router.get("/usb-devices")
def list_usb_video_devices() -> dict:
    """List USB video devices (e.g. for operator view camera). Returns index, path, and name."""
    devices = []
    try:
        import glob
        # Linux: /dev/video0, /dev/video1, ...
        video_glob = "/dev/video*"
        paths = sorted(glob.glob(video_glob), key=lambda p: (len(p), p))
        for path in paths:
            try:
                base = os.path.basename(path)
                if not base.startswith("video"):
                    continue
                idx_str = base.replace("video", "")
                if not idx_str.isdigit():
                    continue
                index = int(idx_str)
                name = ""
                sys_name = f"/sys/class/video4linux/{base}/name"
                if os.path.exists(sys_name):
                    try:
                        name = open(sys_name).read().strip()
                    except Exception:
                        pass
                devices.append({"index": index, "path": path, "name": name or path})
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Failed to list USB video devices: {e}")
        return {"devices": [], "error": str(e)}
    return {"devices": devices}


@router.get("/detect")
def detect_cameras() -> dict:
    """List detected RealSense cameras. Use to verify serial numbers in config."""
    # Check if we should proxy to remote camera service
    camera_service_url = os.getenv("CAMERA_SERVICE_URL")
    if camera_service_url:
        try:
            import requests
            response = requests.get(f"{camera_service_url}/api/cameras/detect", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to detect cameras from remote service: {e}")
            # Fall back to local detection
    
    # Local camera detection
    try:
        import pyrealsense2 as rs
    except ImportError:
        return {"detected": [], "message": "pyrealsense2 not installed"}
    devices = []
    try:
        ctx = rs.context()
        for d in ctx.query_devices():
            serial = d.get_info(rs.camera_info.serial_number)
            name = d.get_info(rs.camera_info.name)
            devices.append({"serial": serial, "name": name})
    except Exception as e:
        return {"detected": [], "error": str(e)}
    config = load_config()
    configured = {
        k: c.get("serial_number_or_name", "?")
        for k, c in (config.robot.cameras or {}).items()
    }
    return {"detected": devices, "configured": configured}


@router.post("/shutdown")
def shutdown_cameras() -> dict:
    """Shutdown only teleop cameras (robot.cameras); operator camera stays on."""
    config = load_config()
    teleop_keys = set(config.robot.cameras or {})
    manager = CameraManager.get_instance()
    with manager.manager_lock:
        to_release = [k for k in manager.cameras if k in teleop_keys]
    manager.shutdown_cameras_for_teleop(teleop_keys)
    return {"status": "shutdown", "cameras_released": to_release}


@router.get("/stream/{camera_key}")
async def stream_camera(camera_key: str) -> StreamingResponse:
    """Stream MJPEG feed for the specified camera (wrist, top, operator, etc.)."""
    config = load_config()
    cameras = config.robot.cameras or {}
    operator_camera = config.robot.operator_camera

    # Operator stream: allowed when operator_camera is set
    if camera_key == "operator":
        if not operator_camera:
            raise HTTPException(status_code=404, detail="Operator camera not configured")
        camera_config = operator_camera
    elif camera_key in cameras:
        camera_config = cameras[camera_key]
    else:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_key}' not in config")

    # Check if we should proxy to remote camera service (only for teleop cameras, not operator)
    camera_service_url = os.getenv("CAMERA_SERVICE_URL")
    if camera_service_url and camera_key != "operator":
        try:
            import httpx

            async def proxy_stream():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    url = f"{camera_service_url}/api/cameras/stream/{camera_key}"
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes():
                            yield chunk

            return StreamingResponse(
                proxy_stream(),
                media_type="multipart/x-mixed-replace; boundary=frame",
            )
        except Exception as e:
            logger.error(f"Failed to proxy camera stream from remote service: {e}")

    # Local camera streaming
    manager = CameraManager.get_instance()

    # Lazy init camera if not already started
    if camera_key not in manager.cameras or not manager.cameras[camera_key].is_running:
        if camera_key == "operator":
            device_index = int(camera_config.get("device_index", 0))
            width = int(camera_config.get("width", 640))
            height = int(camera_config.get("height", 480))
            fps = int(camera_config.get("fps", 30))
            manager.initialize_usb_camera(camera_key, device_index, width, height, fps)
        else:
            serial = str(camera_config.get("serial_number_or_name", ""))
            width = int(camera_config.get("width", 640))
            height = int(camera_config.get("height", 480))
            fps = int(camera_config.get("fps", 30))
            manager.initialize_camera(camera_key, serial, width, height, fps)

    fps_val = int(camera_config.get("fps", 30))
    frame_delay = 1.0 / fps_val

    def generate():
        while True:
            frame = manager.get_latest_frame(camera_key)
            if frame:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            else:
                placeholder = CameraStreamer._placeholder_frame()
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
            time.sleep(frame_delay)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
