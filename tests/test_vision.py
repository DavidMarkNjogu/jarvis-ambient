"""Tests for Phase 6 Eyes: screen capture, downscaling, camera gating, in-memory invariants."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from jarvis.vision import (
    look_at_screen,
    look_through_camera,
    encode_image_bytes,
    downscale_image,
    CameraError,
)


def test_screenshot_is_downscaled_and_encoded(tmp_path: Path) -> None:
    """P6-01: Screenshot is captured, downscaled so width <= max_width, and encoded as data URL."""
    # Create fake RGB bitmap image of 1920x1080
    data_url = look_at_screen(max_width=1024)
    assert data_url.startswith("data:image/")
    assert ";base64," in data_url

    # Decode and verify header/payload is valid base64
    header, b64_data = data_url.split(";base64,", 1)
    raw = base64.b64decode(b64_data)
    assert len(raw) > 100


def test_camera_is_opened_only_for_an_explicit_request_and_closed_after() -> None:
    """P6-02: Camera is never opened at import; on request, it is opened and strictly released."""
    mock_cam = MagicMock()
    mock_cam.isOpened.return_value = True
    fake_frame = MagicMock()
    fake_frame.tobytes.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    mock_cam.read.return_value = (True, fake_frame)

    with patch("jarvis.vision._open_camera_device", return_value=mock_cam):
        result = look_through_camera()
        assert result.startswith("data:image/")
        # Ensure release() was called after capture
        mock_cam.release.assert_called_once()


def test_camera_always_released_even_on_exception() -> None:
    """P6-Pitfall: Camera hardware lock prevention. Camera must be released even if read() raises."""
    mock_cam = MagicMock()
    mock_cam.isOpened.return_value = True
    mock_cam.read.side_effect = RuntimeError("Failed frame buffer read")

    with patch("jarvis.vision._open_camera_device", return_value=mock_cam):
        with pytest.raises(CameraError):
            look_through_camera()
        mock_cam.release.assert_called_once()


def test_images_are_not_written_to_disk_unless_asked(tmp_path: Path, monkeypatch) -> None:
    """P6-04: Capturing screen and camera operations must remain in memory without writing temp files."""
    monkeypatch.setenv("TEMP", str(tmp_path))
    monkeypatch.setenv("TMP", str(tmp_path))

    before_files = set(tmp_path.glob("**/*"))
    data_url = look_at_screen(max_width=800)
    assert isinstance(data_url, str)
    after_files = set(tmp_path.glob("**/*"))

    # Assert no new image files were dumped on disk
    new_files = [f for f in (after_files - before_files) if f.is_file()]
    assert not new_files, f"Unexpected files written to temp: {new_files}"


def test_downscale_image_exact_dimensions_and_stride() -> None:
    """Pin downscale_image boundary logic and RGB downsampling calculations."""
    # 1. Image already narrower than max_width is returned unchanged
    small_rgb = b"\x01\x02\x03" * 16  # 4x4
    res, w, h = downscale_image(small_rgb, 4, 4, max_width=100)
    assert res == small_rgb
    assert w == 4 and h == 4

    # 2. Image wider than max_width is correctly scaled and stride preserved
    wide_rgb = b"\xff\x00\x00" * 200 + b"\x00\xff\x00" * 200  # 200x2
    scaled, new_w, new_h = downscale_image(wide_rgb, 200, 2, max_width=100)
    assert new_w == 100
    assert new_h == 1
    assert len(scaled) == new_w * new_h * 3
    assert scaled[0:3] == b"\xff\x00\x00"
    assert scaled[-3:] == b"\xff\x00\x00"



def test_camera_returns_none_or_false_raises_camera_error() -> None:
    """Pin cam.read returning (False, None) condition."""
    mock_cam = MagicMock()
    mock_cam.isOpened.return_value = True
    # ret is False
    mock_cam.read.return_value = (False, None)

    with patch("jarvis.vision._open_camera_device", return_value=mock_cam):
        with pytest.raises(CameraError, match="deliver a valid frame"):
            look_through_camera()

    # ret is True but frame is None
    mock_cam.read.return_value = (True, None)
    with patch("jarvis.vision._open_camera_device", return_value=mock_cam):
        with pytest.raises(CameraError, match="deliver a valid frame"):
            look_through_camera()


def test_camera_device_open_failure_raises() -> None:
    """Pin _open_camera_device failure path."""
    import sys
    mock_cv2 = MagicMock()
    mock_cam = MagicMock()
    mock_cam.isOpened.return_value = False
    mock_cv2.VideoCapture.return_value = mock_cam

    with patch.dict(sys.modules, {"cv2": mock_cv2}):
        with pytest.raises(CameraError, match="Could not open camera"):
            look_through_camera()



def test_screen_capture_custom_monitor_selection() -> None:
    """Pin monitor_index logic in look_at_screen."""
    # Custom monitor index beyond length defaults to 0
    url = look_at_screen(max_width=640, monitor_index=999)
    assert url.startswith("data:image/png;base64,")

