"""Climate (IR A/C) service."""

from __future__ import annotations

from typing import Any

from app.core.db import Database
from app.core.events import EventBus
from app.core.serial_manager import SerialManager
from app.core.state import state

VALID_MODES = {"auto", "cool", "heat", "dry", "fan"}
VALID_FANS = {"auto", "1", "2", "3"}


class ClimateService:
    def __init__(self, serial: SerialManager, db: Database, bus: EventBus) -> None:
        self.serial = serial
        self.db = db
        self.bus = bus

    def get_state(self) -> dict[str, Any]:
        return dict(state.climate)

    async def set_state(self, power: str, mode: str, temp: int, fan: str,
                        source: str = "api") -> dict[str, Any]:
        if mode not in VALID_MODES:
            raise ValueError(f"invalid mode: {mode}")
        if fan not in VALID_FANS:
            raise ValueError(f"invalid fan: {fan}")
        if not 17 <= int(temp) <= 30:
            raise ValueError("temp out of range (17-30)")

        response = await self.serial.send(
            "climate.set",
            {"power": power, "mode": mode, "temp": int(temp), "fan": fan},
        )
        if response.get("type") == "error":
            raise ValueError(response.get("message", "device error"))

        state.climate = {
            "power": power,
            "mode": mode,
            "temp": int(temp),
            "fan": fan,
        }
        self.db.add_climate_event(state.climate, source)
        await self.bus.publish({"type": "climate", "source": source, **state.climate})
        return dict(state.climate)

    def record_remote_change(self, climate: dict[str, Any]) -> None:
        state.climate = dict(climate)
        self.db.add_climate_event(state.climate, "remote")
