"""Plant watering service: one zone, five sensors, gravity tank + valve."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.config import Settings
from app.core.db import Database
from app.core.events import EventBus
from app.core.serial_manager import SerialManager
from app.core.state import state

log = logging.getLogger("homerun.plants")

ZONE = 1
ZONE_NAME = "Plants"


class PlantsService:
    def __init__(self, settings: Settings, serial: SerialManager,
                 db: Database, bus: EventBus) -> None:
        self.settings = settings
        self.serial = serial
        self.db = db
        self.bus = bus
        self._task: asyncio.Task | None = None

    # --- queries -----------------------------------------------------------
    def zone_state(self) -> dict[str, Any]:
        avg = round(sum(state.soil) / len(state.soil)) if state.soil else 0
        schedule = self.db.get_schedule(ZONE) or {
            "enabled": 1,
            "every_hours": 24,
            "duration_s": 20,
            "min_soil": self.settings.soil_threshold,
        }
        return {
            "zone": ZONE,
            "name": ZONE_NAME,
            "plants": len(state.soil) or 5,
            "soil": state.soil,
            "soil_avg": avg,
            "tank": state.tank,
            "flow_lpm": state.flow_lpm,
            "flow_total_l": state.flow_total_l,
            "valve_open": state.valve_open,
            "valve_remaining_ms": state.valve_remaining_ms,
            "last_watered_ts": state.last_watered_ts,
            "threshold": self.settings.soil_threshold,
            "target": self.settings.soil_target,
            "schedule": schedule,
        }

    # --- commands ----------------------------------------------------------
    async def water(self, seconds: int, trigger: str = "manual") -> dict[str, Any]:
        seconds = max(1, min(int(seconds), self.settings.water_max_s))
        # Only trust the tank level once telemetry has arrived; the firmware
        # enforces the same limit independently.
        if state.last_seen is not None and state.tank < 10:
            raise ValueError("tank level too low")
        response = await self.serial.send("water.run", {"duration_ms": seconds * 1000})
        if response.get("type") == "error":
            raise ValueError(response.get("message", "device error"))
        state.last_watered_ts = time.time()
        self.db.add_watering_event(ZONE, seconds, trigger,
                                   liters=round(state.flow_lpm * seconds / 60, 3))
        await self.bus.publish({"type": "watering", "zone": ZONE,
                                "seconds": seconds, "trigger": trigger})
        return {"ok": True, "zone": ZONE, "seconds": seconds}

    async def stop(self) -> dict[str, Any]:
        await self.serial.send("water.stop", {})
        await self.bus.publish({"type": "watering_stopped", "zone": ZONE})
        return {"ok": True}

    def set_schedule(self, enabled: bool, every_hours: float, duration_s: int,
                     min_soil: int) -> dict[str, Any]:
        self.db.upsert_schedule(ZONE, enabled, every_hours, duration_s, min_soil)
        return self.db.get_schedule(ZONE) or {}

    # --- automation --------------------------------------------------------
    async def start_automation(self) -> None:
        self._task = asyncio.create_task(self._auto_loop())

    async def stop_automation(self) -> None:
        if self._task:
            self._task.cancel()

    async def _auto_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                await self._auto_check()
            except Exception as exc:  # noqa: BLE001
                log.warning("auto watering check failed: %s", exc)

    async def _auto_check(self) -> None:
        schedule = self.db.get_schedule(ZONE)
        if not schedule or not schedule["enabled"]:
            return
        if not state.soil:
            return
        avg = sum(state.soil) / len(state.soil)
        if avg >= schedule["min_soil"]:
            return
        if state.tank < 10:
            return
        if not state.connected:
            return
        last = state.last_watered_ts or 0
        if time.time() - last < self.settings.water_min_interval_s:
            return
        await self.water(int(schedule["duration_s"]), trigger="auto")
