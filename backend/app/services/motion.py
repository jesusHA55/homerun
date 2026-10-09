"""OpenCV-backed motion detection (MOG2 background subtraction)."""

from __future__ import annotations

import time
from typing import Any


class MotionDetector:
    def __init__(self, diff_threshold: int = 25, min_area: int = 1500,
                 cooldown_s: int = 20) -> None:
        self.diff_threshold = diff_threshold
        self.min_area = min_area
        self.cooldown_s = cooldown_s
        self._bg: Any = None
        self._last_trigger = 0.0
        self.last_area = 0.0

    @staticmethod
    def available() -> bool:
        try:
            import cv2  # noqa: F401
            return True
        except Exception:
            return False

    def detect(self, frame: Any) -> bool:
        """Return True when motion above threshold is detected (rate-limited)."""
        import cv2

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._bg is None:
            self._bg = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=self.diff_threshold, detectShadows=False
            )

        fg = self._bg.apply(gray)
        _, fg = cv2.threshold(fg, self.diff_threshold, 255, cv2.THRESH_BINARY)
        fg = cv2.dilate(fg, None, iterations=2)
        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area = max((cv2.contourArea(c) for c in contours), default=0.0)
        self.last_area = area

        now = time.time()
        if area >= self.min_area and (now - self._last_trigger) >= self.cooldown_s:
            self._last_trigger = now
            return True
        return False
