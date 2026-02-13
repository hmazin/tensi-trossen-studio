"""Camera streaming utilities."""

import cv2
import numpy as np


class CameraStreamer:
    """Utility class for camera streaming helpers."""

    @staticmethod
    def _placeholder_frame() -> bytes:
        """Return a simple gray placeholder JPEG."""
        img = np.full((480, 640, 3), 80, dtype=np.uint8)
        cv2.putText(
            img,
            "Camera unavailable",
            (120, 250),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        _, jpeg = cv2.imencode(".jpg", img)
        return jpeg.tobytes()

