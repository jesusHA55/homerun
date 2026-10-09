"""Tool registry exposed to the Ollama agent."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.core.state import state
from app.services.camera import CameraService
from app.services.climate import ClimateService
from app.services.plants import PlantsService

log = logging.getLogger("homerun.tools")

# OpenAI-compatible tool schemas (Ollama understands this shape).
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get the overall house status: climate, plants, tank and camera.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_climate",
            "description": "Get the current air-conditioner state.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_climate",
            "description": "Set the air conditioner. Mode is auto/cool/heat/dry/fan, "
                           "temperature 17-30 C, fan auto/1/2/3.",
            "parameters": {
                "type": "object",
                "properties": {
                    "power": {"type": "string", "enum": ["on", "off"]},
                    "mode": {"type": "string", "enum": ["auto", "cool", "heat", "dry", "fan"]},
                    "temp": {"type": "integer", "minimum": 17, "maximum": 30},
                    "fan": {"type": "string", "enum": ["auto", "1", "2", "3"]},
                },
                "required": ["power"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_plants",
            "description": "Get soil moisture for the plants and tank level.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "water_zone",
            "description": "Open the watering valve for a number of seconds.",
            "parameters": {
                "type": "object",
                "properties": {"seconds": {"type": "integer", "minimum": 1, "maximum": 60}},
                "required": ["seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_camera_status",
            "description": "Get camera availability and current mode.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_camera_mode",
            "description": "Switch the camera between manual and motion modes.",
            "parameters": {
                "type": "object",
                "properties": {"mode": {"type": "string", "enum": ["manual", "motion"]}},
                "required": ["mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_snapshot",
            "description": "Capture a still image from the camera now.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_events",
            "description": "List the most recent motion and watering events.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50}},
            },
        },
    },
]


class ToolRegistry:
    def __init__(self, climate: ClimateService, plants: PlantsService,
                 camera: CameraService) -> None:
        self.climate = climate
        self.plants = plants
        self.camera = camera
        self._tools: dict[str, Callable[[dict], Awaitable[Any]]] = {
            "get_status": self._get_status,
            "get_climate": self._get_climate,
            "set_climate": self._set_climate,
            "get_plants": self._get_plants,
            "water_zone": self._water_zone,
            "get_camera_status": self._get_camera_status,
            "set_camera_mode": self._set_camera_mode,
            "capture_snapshot": self._capture_snapshot,
            "get_recent_events": self._get_recent_events,
        }

    async def execute(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"unknown tool: {name}"}
        try:
            result = await tool(args or {})
            return {"ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            log.warning("tool %s failed: %s", name, exc)
            return {"ok": False, "error": str(exc)}

    async def _get_status(self, _: dict) -> Any:
        return {
            "climate": self.climate.get_state(),
            "plants": self.plants.zone_state(),
            "camera": self.camera.status(),
            "device_connected": state.connected,
        }

    async def _get_climate(self, _: dict) -> Any:
        return self.climate.get_state()

    async def _set_climate(self, args: dict) -> Any:
        current = self.climate.get_state()
        return await self.climate.set_state(
            power=args.get("power", current["power"]),
            mode=args.get("mode", current["mode"]),
            temp=int(args.get("temp", current["temp"])),
            fan=args.get("fan", current["fan"]),
            source="ollama",
        )

    async def _get_plants(self, _: dict) -> Any:
        return self.plants.zone_state()

    async def _water_zone(self, args: dict) -> Any:
        return await self.plants.water(int(args.get("seconds", 20)), trigger="ollama")

    async def _get_camera_status(self, _: dict) -> Any:
        return self.camera.status()

    async def _set_camera_mode(self, args: dict) -> Any:
        return self.camera.set_mode(args["mode"])

    async def _capture_snapshot(self, _: dict) -> Any:
        path = self.camera.save_snapshot("agent")
        return {"snapshot": path}

    async def _get_recent_events(self, args: dict) -> Any:
        limit = int(args.get("limit", 10))
        return {
            "motion": self.camera.db.recent("motion_events", limit),
            "watering": self.camera.db.recent("watering_events", limit),
        }
