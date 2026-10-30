"""Phase 6: Eyes (Screen and Camera).

Provides screen and camera capture functions with in-memory encoding,
strict resource management, and desktop-switching resilience.
"""

from __future__ import annotations

import base64
import contextlib
import ctypes
import io
import sys
from typing import Any, Iterator


class CameraError(Exception):
    """Raised when camera initialization or frame reading fails."""
    pass


class VisionError(Exception):
    """Raised when screen or image capture fails."""
    pass


def _ensure_active_desktop() -> None:
    """Ensure current thread is attached to the interactive input desktop on Windows."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        pass


def downscale_image(raw_rgb: bytes, width: int, height: int, max_width: int = 1024) -> tuple[bytes, int, int]:
    """Downscale an RGB byte array if width exceeds max_width using nearest-neighbor/subsampling."""
    if width <= max_width:
        return raw_rgb, width, height

    scale = max_width / width
    new_w = int(width * scale)
    new_h = int(height * scale)

    # Fast row-stride downsampling
    out = bytearray(new_w * new_h * 3)
    out_idx = 0
    for y in range(new_h):
        orig_y = int(y / scale)
        row_offset = orig_y * width * 3
        for x in range(new_w):
            orig_x = int(x / scale)
            src_idx = row_offset + orig_x * 3
            out[out_idx : out_idx + 3] = raw_rgb[src_idx : src_idx + 3]
            out_idx += 3

    return bytes(out), new_w, new_h


def encode_image_bytes(png_bytes: bytes) -> str:
    """Encode raw PNG/JPEG bytes into an OpenAI/Gemini compatible base64 data URL."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _open_camera_device(index: int = 0) -> Any:
    """Isolate camera opening for dependency injection and mocking."""
    cv2_module = sys.modules.get("cv2")
    if cv2_module is None:
        try:
            cv2_module = __import__("cv2")
        except ImportError:
            raise CameraError("OpenCV is not installed. Camera requires opencv-python.")

    cam = cv2_module.VideoCapture(index)
    if not cam.isOpened():
        raise CameraError(f"Could not open camera at index {index}")
    return cam


def _capture_screen_raw(monitor_index: int = 1) -> tuple[bytes, int, int]:
    """Capture screen inside a clean worker thread to avoid Win32 SetThreadDesktop error 170 if COM initialized."""
    import concurrent.futures

    def _worker():
        _ensure_active_desktop()
        import mss
        with mss.MSS() as sct:
            monitors = sct.monitors
            idx = monitor_index if monitor_index < len(monitors) else 0
            img = sct.grab(monitors[idx])
            return bytes(img.rgb), img.width, img.height

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_worker).result()


def look_at_screen(max_width: int = 1024, monitor_index: int = 1) -> str:
    """Capture the primary desktop screen, downscale if wider than max_width, and return as base64 data URL.
    
    Zero files are written to disk. All operations are kept strictly in-memory.
    """
    import mss.tools

    try:
        raw_rgb, width, height = _capture_screen_raw(monitor_index=monitor_index)
        rgb, w, h = downscale_image(raw_rgb, width, height, max_width=max_width)
        png_bytes = mss.tools.to_png(rgb, (w, h))
        return encode_image_bytes(png_bytes)
    except Exception as err:
        raise VisionError(f"Screen capture failed: {err}") from err



def look_through_camera(index: int = 0) -> str:
    """Capture a single frame from the camera, strictly releasing hardware handles in all cases."""
    cam = _open_camera_device(index)
    try:
        ret, frame = cam.read()
        if not ret or frame is None:
            raise CameraError("Camera failed to deliver a valid frame.")

        # Encode frame to memory
        if hasattr(frame, "tobytes"):
            raw_bytes = frame.tobytes()
        elif isinstance(frame, bytes):
            raw_bytes = frame
        else:
            raw_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

        return encode_image_bytes(raw_bytes)
    except CameraError:
        raise
    except Exception as err:
        raise CameraError(f"Camera capture error: {err}") from err
    finally:
        with contextlib.suppress(Exception):
            cam.release()
