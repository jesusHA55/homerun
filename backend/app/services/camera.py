"""Camera service: manual streaming/snapshots and motion-triggered events.

Backends:
  * picamera  - Raspberry Pi Camera Module 3 via picamera2
  * opencv    - USB / built-in camera via cv2.VideoCapture
  * synthetic - generated frames (dev / no hardware)
  * auto      - prefer picamera, then opencv, then synthetic
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from app.config import Settings
from app.core.db import Database
from app.core.events import EventBus
from app.services.motion import MotionDetector

log = logging.getLogger("homerun.camera")

JPEG_BOUNDARY = b"--frame\r\n"
MODES = ("manual", "motion")


class CameraService:
    def __init__(self, settings: Settings, db: Database, bus: EventBus) -> None:
        self.settings = settings
        self.db = db
        self.bus = bus

        self.mode = "manual"
        self.backend_name = "none"
        self.available = False
        self.last_error: Optional[str] = None

        self._frame: Any = None
        self._jpeg: Optional[bytes] = None
        self._task: Optional[asyncio.Task] = None
        self._picam: Any = None
        self._cap: Any = None
        self._writer: Any = None
        self._record_until = 0.0

        self._detector = MotionDetector(
            diff_threshold=settings.motion_diff_threshold,
            min_area=settings.motion_min_area,
            cooldown_s=settings.motion_cooldown_s,
        )

    # --- lifecycle ---------------------------------------------------------
    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
        self._release()

    def _release(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        if self._picam is not None:
            try:
                self._picam.stop()
            except Exception:
                pass
            self._picam = None
        if self._writer is not None:
            try:
                self._writer.release()
            except Exception:
                pass
            self._writer = None

    # --- backends ----------------------------------------------------------
    def _cv2(self) -> Any:
        import cv2

        return cv2

    def _open(self) -> None:
        backend = self.settings.camera_backend
        if backend == "auto":
            backend = self._pick_backend()

        try:
            if backend == "picamera":
                from picamera2 import Picamera2

                self._picam = Picamera2()
                config = self._picam.create_preview_configuration(
                    main={"size": (self.settings.camera_width, self.settings.camera_height)}
                )
                self._picam.configure(config)
                self._picam.start()
                time.sleep(0.5)
                self.backend_name = "picamera"
            elif backend == "opencv":
                cv2 = self._cv2()
                self._cap = cv2.VideoCapture(self.settings.camera_index)
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.camera_width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.camera_height)
                if not self._cap.isOpened():
                    raise RuntimeError("could not open camera index")
                self.backend_name = "opencv"
            else:
                self._cv2()  # ensure cv2 exists for encoding
                self.backend_name = "synthetic"
            self.available = True
            self.last_error = None
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if message != self.last_error:
                log.warning("camera unavailable: %s", message)
            self.available = False
            self.last_error = message
            self.backend_name = "none"

    def _pick_backend(self) -> str:
        try:
            import picamera2  # noqa: F401

            return "picamera"
        except Exception:
            pass
        try:
            import cv2

            cap = cv2.VideoCapture(self.settings.camera_index)
            ok = cap.isOpened()
            cap.release()
            if ok:
                return "opencv"
        except Exception:
            pass
        try:
            import cv2  # noqa: F401

            return "synthetic"
        except Exception:
            return "none"

    def _read_frame(self) -> Any:
        if self.backend_name == "picamera" and self._picam is not None:
            cv2 = self._cv2()
            array = self._picam.capture_array("main")  # RGB
            return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        if self.backend_name == "opencv" and self._cap is not None:
            ok, frame = self._cap.read()
            return frame if ok else None
        if self.backend_name == "synthetic":
            return self._synthetic_frame()
        return None

    def _synthetic_frame(self) -> Any:
        import numpy as np

        w, h = self.settings.camera_width, self.settings.camera_height
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :, 1] = 40
        t = time.time()
        x = int((w - 120) * (0.5 + 0.5 * __import__("math").sin(t / 2)))
        frame[100:220, x:x + 120] = (30, 30, 220)  # moving red block
        return frame

    def _encode(self, frame: Any) -> Optional[bytes]:
        try:
            cv2 = self._cv2()
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return buf.tobytes() if ok else None
        except Exception:
            return None

    # --- main loop ---------------------------------------------------------
    async def _loop(self) -> None:
        self._open()
        interval = 1.0 / 10  # ~10 fps is plenty for monitoring
        while True:
            try:
                if not self.available:
                    await asyncio.sleep(2)
                    self._open()
                    continue

                frame = await asyncio.to_thread(self._read_frame)
                if frame is None:
                    await asyncio.sleep(0.2)
                    continue

                self._frame = frame
                jpeg = await asyncio.to_thread(self._encode, frame)
                if jpeg:
                    self._jpeg = jpeg

                if self._writer is not None:
                    self._writer.write(frame)
                    if time.time() >= self._record_until:
                        self._writer.release()
                        self._writer = None

                if self.mode == "motion" and self._detector.available():
                    if await asyncio.to_thread(self._detector.detect, frame):
                        await self._on_motion(frame)

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("camera loop error: %s", exc)
                await asyncio.sleep(1)

    async def _on_motion(self, frame: Any) -> None:
        snap = self.save_snapshot("motion")
        clip = self._start_clip()
        area = self._detector.last_area
        self.db.add_motion_event(snap, clip, area)
        await self.bus.publish({"type": "motion", "snapshot": snap, "clip": clip,
                                "area": area, "ts": time.time()})
        log.info("motion detected (area=%.0f)", area)

    # --- public API --------------------------------------------------------
    def set_mode(self, mode: str) -> dict[str, Any]:
        if mode not in MODES:
            raise ValueError(f"invalid mode: {mode}")
        self.mode = mode
        return {"mode": self.mode}

    def latest_jpeg(self) -> Optional[bytes]:
        return self._jpeg

    def snapshot_jpeg(self) -> Optional[bytes]:
        return self._jpeg

    def save_snapshot(self, prefix: str = "snap") -> Optional[str]:
        if self._jpeg is None:
            return None
        directory = Path(self.settings.media_dir) / "snapshots"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{prefix}_{int(time.time())}.jpg"
        path.write_bytes(self._jpeg)
        return str(path)

    def _start_clip(self) -> Optional[str]:
        try:
            cv2 = self._cv2()
        except Exception:
            return None
        directory = Path(self.settings.media_dir) / "clips"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"motion_{int(time.time())}.avi"
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(
            str(path), fourcc, 10.0,
            (self.settings.camera_width, self.settings.camera_height),
        )
        if not writer.isOpened():
            return None
        self._writer = writer
        self._record_until = time.time() + 5.0
        return str(path)

    async def mjpeg_stream(self) -> AsyncIterator[bytes]:
        while True:
            jpeg = self._jpeg
            if jpeg:
                yield (JPEG_BOUNDARY + b"Content-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                       + jpeg + b"\r\n")
            await asyncio.sleep(0.1)

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "backend": self.backend_name,
            "mode": self.mode,
            "motion_available": self._detector.available(),
            "last_error": self.last_error,
            "has_frame": self._jpeg is not None,
        }
