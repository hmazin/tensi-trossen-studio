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
    
    # Local camera status
    manager = CameraManager.get_instance()
    status = {}
    for key in cameras:
        status[key] = manager.get_camera_status(key)
    
    return {"cameras": status}


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
    """Shutdown all cameras to release resources for teleoperation/recording."""
    manager = CameraManager.get_instance()
    cameras_released = list(manager.cameras.keys())
    manager.shutdown_all()
    return {"status": "shutdown", "cameras_released": cameras_released}


@router.get("/stream/{camera_key}")
async def stream_camera(camera_key: str) -> StreamingResponse:
    """Stream MJPEG feed for the specified camera (wrist, top, etc.)."""
    config = load_config()
    cameras = config.robot.cameras
    if camera_key not in cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_key}' not in config")
    
    # Check if we should proxy to remote camera service
    camera_service_url = os.getenv("CAMERA_SERVICE_URL")
    if camera_service_url:
        try:
            import httpx
            
            async def proxy_stream():
                """Proxy the camera stream from remote service."""
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
            # Fall through to local camera or placeholder
    
    # Local camera streaming
    camera_config = cameras[camera_key]
    manager = CameraManager.get_instance()
    
    # Lazy init camera if not already started
    if camera_key not in manager.cameras or not manager.cameras[camera_key].is_running:
        serial = str(camera_config.get("serial_number_or_name", ""))
        width = int(camera_config.get("width", 640))
        height = int(camera_config.get("height", 480))
        fps = int(camera_config.get("fps", 30))
        
        manager.initialize_camera(camera_key, serial, width, height, fps)
    
    def generate():
        fps = int(camera_config.get("fps", 30))
        frame_delay = 1.0 / fps
        
        while True:
            frame = manager.get_latest_frame(camera_key)
            if frame:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            else:
                # Placeholder frame if camera not ready
                placeholder = CameraStreamer._placeholder_frame()
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
            
            time.sleep(frame_delay)
    
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
