"""Authoritative in-memory device state, refreshed from telemetry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


def _default_climate() -> dict[str, Any]:
    return {"power": "off", "mode": "cool", "temp": 24, "fan": "auto"}


@dataclass
class DeviceState:
    connected: bool = False
    last_seen: Optional[float] = None
    soil: list[int] = field(default_factory=list)
    tank: int = 0
    flow_lpm: float = 0.0
    flow_total_l: float = 0.0
    valve_open: bool = False
    valve_remaining_ms: int = 0
    climate: dict[str, Any] = field(default_factory=_default_climate)
    last_watered_ts: Optional[float] = None

    def apply_telemetry(self, msg: dict[str, Any]) -> None:
        self.connected = True
        self.last_seen = time.time()
        self.soil = list(msg.get("soil", []))
        self.tank = int(msg.get("tank_level", 0))
        self.flow_lpm = float(msg.get("flow_lpm", 0.0))
        self.flow_total_l = float(msg.get("flow_total_l", 0.0))
        self.valve_open = bool(msg.get("valve", 0))
        self.valve_remaining_ms = int(msg.get("valve_remaining_ms", 0))
        if isinstance(msg.get("climate"), dict):
            self.climate = dict(msg["climate"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "last_seen": self.last_seen,
            "soil": self.soil,
            "tank": self.tank,
            "flow_lpm": self.flow_lpm,
            "flow_total_l": self.flow_total_l,
            "valve_open": self.valve_open,
            "valve_remaining_ms": self.valve_remaining_ms,
            "climate": self.climate,
            "last_watered_ts": self.last_watered_ts,
        }


state = DeviceState()
