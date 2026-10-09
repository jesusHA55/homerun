"""Async USB-serial transport to the Arduino Mega.

Protocol: newline-delimited JSON. Commands carry an ``id``; the device replies
with ``{"type":"ack"|"error","id":...}``. Telemetry and remote-IR events are
pushed to an ``on_message`` callback. A heartbeat keeps the firmware's dead-man
switch happy.

When ``serial_enabled`` is false the manager runs a small simulated device so
the backend can be developed and tested without hardware.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Awaitable, Callable, Optional

from app.config import Settings

log = logging.getLogger("homerun.serial")

OnMessage = Callable[[dict[str, Any]], Awaitable[None]]

try:  # pyserial-asyncio is optional at import time (simulation mode)
    import serial_asyncio  # type: ignore
except Exception:  # pragma: no cover
    serial_asyncio = None


class _SimulatedDevice:
    """Fake Mega used when HOMERUN_SERIAL_ENABLED=false."""

    def __init__(self) -> None:
        self.soil = [random.randint(30, 70) for _ in range(5)]
        self.tank = 80
        self.valve = False
        self.climate = {"power": "off", "mode": "cool", "temp": 24, "fan": "auto"}
        self.flow_total = 0.0
        self._valve_stop: Optional[float] = None

    async def handle(self, cmd: str, params: dict) -> dict:
        if cmd == "climate.set":
            self.climate = {
                "power": params.get("power", "on"),
                "mode": params.get("mode", "cool"),
                "temp": int(params.get("temp", 24)),
                "fan": params.get("fan", "auto"),
            }
            return {"type": "ack", "id": 0}
        if cmd in ("ping", "sensor.read", "valve.set", "water.run", "water.stop"):
            if cmd == "water.run":
                self.valve = True
            if cmd in ("water.stop",):
                self.valve = False
            return {"type": "ack", "id": 0}
        return {"type": "error", "id": 0, "message": "unknown command"}

    def telemetry(self) -> dict[str, Any]:
        # gently wander the soil readings
        self.soil = [max(0, min(100, v + random.randint(-2, 2))) for v in self.soil]
        return {
            "type": "telemetry",
            "soil": self.soil,
            "tank_level": self.tank,
            "flow_lpm": 0.4 if self.valve else 0.0,
            "flow_total_l": round(self.flow_total, 2),
            "valve": 1 if self.valve else 0,
            "valve_remaining_ms": 0,
            "climate": self.climate,
        }


class SerialManager:
    def __init__(self, settings: Settings, on_message: OnMessage) -> None:
        self.settings = settings
        self.on_message = on_message

        self._reader = None
        self._writer = None
        self._connected = False
        self._pending: dict[int, asyncio.Future] = {}
        self._next_id = 1

        self._tasks: list[asyncio.Task] = []
        self._sim: Optional[_SimulatedDevice] = None

    @property
    def connected(self) -> bool:
        return self._connected

    async def start(self) -> None:
        if not self.settings.serial_enabled:
            log.warning("serial disabled; running simulated device")
            self._sim = _SimulatedDevice()
            self._connected = True
            self._tasks.append(asyncio.create_task(self._simulate()))
        else:
            self._tasks.append(asyncio.create_task(self._connect_loop()))
        self._tasks.append(asyncio.create_task(self._heartbeat()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._writer is not None:
            try:
                self._writer.close()
            except Exception:
                pass

    async def send(self, cmd: str, params: dict | None = None,
                   timeout: float = 3.0) -> dict[str, Any]:
        if self._sim is not None:
            return await self._sim.handle(cmd, params or {})
        if not self._connected or self._writer is None:
            raise RuntimeError("device not connected")

        msg_id = self._next_id
        self._next_id += 1
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = future
        line = json.dumps({"id": msg_id, "cmd": cmd, "params": params or {}}) + "\n"
        self._writer.write(line.encode())
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise RuntimeError(f"timeout waiting for ack: {cmd}") from None

    # --- internals ---------------------------------------------------------
    async def _connect_loop(self) -> None:
        assert serial_asyncio is not None
        while True:
            try:
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=self.settings.serial_port, baudrate=self.settings.baud
                )
                self._reader, self._writer = reader, writer
                self._connected = True
                log.info("serial connected on %s", self.settings.serial_port)
                await self._read_loop(reader)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self._connected = False
                log.warning("serial unavailable (%s); retrying", exc)
                await asyncio.sleep(3)

    async def _read_loop(self, reader) -> None:
        while True:
            raw = await reader.readline()
            if not raw:
                break
            try:
                msg = json.loads(raw.decode(errors="ignore").strip())
            except Exception:
                continue
            msg_type = msg.get("type")
            if msg_type in ("ack", "error"):
                future = self._pending.pop(msg.get("id"), None)
                if future and not future.done():
                    future.set_result(msg)
                continue
            await self.on_message(msg)
        self._connected = False

    async def _heartbeat(self) -> None:
        while True:
            await asyncio.sleep(self.settings.heartbeat_s)
            if self._sim is not None:
                continue
            if not self._connected:
                continue
            try:
                await self.send("ping", {}, timeout=2.0)
            except Exception:  # noqa: BLE001
                pass

    async def _simulate(self) -> None:
        assert self._sim is not None
        # Emit one reading immediately so consumers have a baseline.
        await self.on_message(self._sim.telemetry())
        while True:
            await asyncio.sleep(2.0)
            self._sim.flow_total += 0.01
            await self.on_message(self._sim.telemetry())
