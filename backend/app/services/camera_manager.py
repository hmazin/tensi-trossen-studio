"""Camera manager for RealSense cameras with background capture threads."""

import logging
import time
from threading import Event, Lock, Thread
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Optional: pyrealsense2 for Intel RealSense
try:
    import pyrealsense2 as rs
    HAS_REALSENSE = True
except ImportError:
    HAS_REALSENSE = False
    logger.warning("pyrealsense2 not installed - RealSense cameras will not work")


class ManagedCamera:
    """Wrapper for a single RealSense camera with background capture thread."""

    def __init__(
        self,
        key: str,
        serial: str,
        width: int,
        height: int,
        fps: int,
    ):
        """Initialize camera but don't start yet.
        
        Args:
            key: Camera identifier (e.g., "wrist", "top")
            serial: RealSense serial number
            width: Frame width in pixels
            height: Frame height in pixels
            fps: Frames per second
        """
        self.key = key
        self.serial = serial
        self.width = width
        self.height = height
        self.fps = fps

        # Pipeline state
        self.pipeline: rs.pipeline | None = None
        self.profile: rs.pipeline_profile | None = None

        # Thread state
        self.thread: Thread | None = None
        self.stop_event = Event()
        self.frame_lock = Lock()
        self.latest_frame: bytes | None = None

        # Error tracking
        self.error: str | None = None
        self.error_lock = Lock()
        
        # Status
        self.is_running = False

    def start(self) -> None:
        """Start the camera pipeline and background capture thread."""
        if not HAS_REALSENSE:
            with self.error_lock:
                self.error = "pyrealsense2 not installed"
            logger.error(f"Camera {self.key} cannot start: pyrealsense2 not installed")
            return

        if self.is_running:
            logger.warning(f"Camera {self.key} already running")
            return

        try:
            # Initialize pipeline
            self.pipeline = rs.pipeline()
            config = rs.config()
            config.enable_device(self.serial)
            config.enable_stream(
                rs.stream.color,
                self.width,
                self.height,
                rs.format.bgr8,
                self.fps,
            )

            # Start pipeline
            logger.info(f"Starting camera {self.key} (serial: {self.serial})")
            self.profile = self.pipeline.start(config)

            # Warmup
            time.sleep(0.5)
            for _ in range(5):
                try:
                    frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                    if frames.get_color_frame():
                        break
                except Exception:
                    pass
                time.sleep(0.1)

            # Start capture thread
            self.stop_event.clear()
            self.thread = Thread(target=self._capture_loop, daemon=True, name=f"Camera-{self.key}")
            self.thread.start()
            self.is_running = True

            logger.info(f"Camera {self.key} started successfully")

        except Exception as e:
            error_msg = str(e)
            with self.error_lock:
                self.error = error_msg
            logger.error(f"Failed to start camera {self.key}: {error_msg}")
            
            # Cleanup on failure
            if self.pipeline:
                try:
                    self.pipeline.stop()
                except Exception:
                    pass
                self.pipeline = None
                self.profile = None

    def _capture_loop(self) -> None:
        """Background thread that continuously captures frames."""
        logger.info(f"Capture loop started for camera {self.key}")
        
        consecutive_failures = 0
        max_consecutive_failures = 10

        while not self.stop_event.is_set():
            try:
                if self.pipeline is None:
                    logger.error(f"Camera {self.key}: pipeline is None in capture loop")
                    break

                # Wait for frames with timeout
                frames = self.pipeline.wait_for_frames(timeout_ms=2000)
                color_frame = frames.get_color_frame()

                if not color_frame:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        error_msg = f"No color frames after {max_consecutive_failures} attempts"
                        with self.error_lock:
                            self.error = error_msg
                        logger.error(f"Camera {self.key}: {error_msg}")
                        break
                    continue

                # Reset failure counter on success
                consecutive_failures = 0

                # Convert to numpy array and encode as JPEG
                img = np.asanyarray(color_frame.get_data())
                _, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                jpeg_bytes = jpeg.tobytes()

                # Update buffer
                with self.frame_lock:
                    self.latest_frame = jpeg_bytes

                # Clear any previous errors
                with self.error_lock:
                    if self.error:
                        self.error = None
                        logger.info(f"Camera {self.key} recovered from error")

            except Exception as e:
                consecutive_failures += 1
                error_msg = str(e)
                
                if consecutive_failures >= max_consecutive_failures:
                    with self.error_lock:
                        self.error = f"Frame capture failed: {error_msg}"
                    logger.error(f"Camera {self.key} failed after {max_consecutive_failures} attempts: {error_msg}")
                    break
                elif consecutive_failures == 1:
                    # Log first failure but don't break immediately
                    logger.warning(f"Camera {self.key} frame capture error: {error_msg}")

            # Small sleep to prevent tight loop on errors
            if consecutive_failures > 0:
                time.sleep(0.1)

        logger.info(f"Capture loop stopped for camera {self.key}")
        self.is_running = False

    def get_latest_frame(self) -> bytes | None:
        """Get the latest captured frame (non-blocking).
        
        Returns:
            JPEG-encoded frame bytes, or None if no frame available
        """
        with self.frame_lock:
            return self.latest_frame

    def get_error(self) -> str | None:
        """Get the current error state.
        
        Returns:
            Error message if camera has failed, None otherwise
        """
        with self.error_lock:
            return self.error

    def stop(self) -> None:
        """Stop the capture thread and close the pipeline."""
        if not self.is_running:
            return

        logger.info(f"Stopping camera {self.key}")

        # Signal thread to stop
        self.stop_event.set()

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                logger.warning(f"Camera {self.key} thread did not stop gracefully")

        # Stop pipeline
        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception as e:
                logger.warning(f"Error stopping pipeline for camera {self.key}: {e}")
            finally:
                self.pipeline = None
                self.profile = None

        self.is_running = False
        logger.info(f"Camera {self.key} stopped")


class CameraManager:
    """Singleton manager for RealSense cameras with background capture threads."""

    _instance: "CameraManager | None" = None
    _lock = Lock()

    def __init__(self):
        """Initialize the camera manager (use get_instance() instead)."""
        self.cameras: dict[str, ManagedCamera] = {}
        self.manager_lock = Lock()
        logger.info("CameraManager initialized")

    @classmethod
    def get_instance(cls) -> "CameraManager":
        """Get the singleton CameraManager instance (thread-safe).
        
        Returns:
            The singleton CameraManager instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = CameraManager()
        return cls._instance

    def initialize_camera(
        self,
        key: str,
        serial: str,
        width: int,
        height: int,
        fps: int,
    ) -> None:
        """Initialize and start a camera.
        
        Args:
            key: Camera identifier (e.g., "wrist", "top")
            serial: RealSense serial number
            width: Frame width in pixels
            height: Frame height in pixels
            fps: Frames per second
        """
        with self.manager_lock:
            # Stop existing camera if it exists
            if key in self.cameras:
                logger.info(f"Camera {key} already exists, stopping old instance")
                self.cameras[key].stop()
                del self.cameras[key]

            # Create and start new camera
            camera = ManagedCamera(key, serial, width, height, fps)
            self.cameras[key] = camera
            camera.start()

    def get_latest_frame(self, key: str) -> bytes | None:
        """Get the latest frame from a camera (non-blocking).
        
        Args:
            key: Camera identifier
            
        Returns:
            JPEG-encoded frame bytes, or None if camera not found or no frame available
        """
        with self.manager_lock:
            camera = self.cameras.get(key)
            if camera is None:
                return None
            return camera.get_latest_frame()

    def get_camera_status(self, key: str) -> dict[str, Any]:
        """Get status information for a camera.
        
        Args:
            key: Camera identifier
            
        Returns:
            Dictionary with status, error, serial, etc.
        """
        with self.manager_lock:
            camera = self.cameras.get(key)
            if camera is None:
                return {"status": "not_initialized"}

            error = camera.get_error()
            if error:
                return {
                    "status": "error",
                    "error_type": "hardware_timeout",
                    "message": "Camera opened but failed to capture frames. Check USB bandwidth/power.",
                    "details": {
                        "serial": camera.serial,
                        "error": error,
                    },
                }
            elif not camera.is_running:
                return {
                    "status": "stopped",
                    "details": {"serial": camera.serial},
                }
            elif camera.get_latest_frame() is None:
                return {
                    "status": "warming_up",
                    "details": {"serial": camera.serial},
                }
            else:
                return {
                    "status": "running",
                    "details": {"serial": camera.serial},
                }

    def shutdown_camera(self, key: str) -> None:
        """Stop and remove a camera.
        
        Args:
            key: Camera identifier
        """
        with self.manager_lock:
            camera = self.cameras.get(key)
            if camera:
                camera.stop()
                del self.cameras[key]
                logger.info(f"Camera {key} shut down")

    def shutdown_all(self) -> None:
        """Stop and remove all cameras."""
        with self.manager_lock:
            logger.info("Shutting down all cameras")
            for key, camera in list(self.cameras.items()):
                camera.stop()
            self.cameras.clear()
            logger.info("All cameras shut down")
