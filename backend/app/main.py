from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import camera as camera_api
from app.api import chat, climate, plants, system, ws
from app.config import get_settings
from app.core.db import Database
from app.core.events import bus
from app.core.serial_manager import SerialManager
from app.core.state import state
from app.services.camera import CameraService
from app.services.climate import ClimateService
from app.services.ollama_agent import OllamaAgent
from app.services.plants import PlantsService
from app.tools.registry import ToolRegistry

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("homerun")


class Services:
    settings: object
    db: Database
    serial: SerialManager
    climate: ClimateService
    plants: PlantsService
    camera: CameraService
    agent: OllamaAgent


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = Database(settings.db_path)
    db.init_schema()

    async def on_message(msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type == "telemetry":
            state.apply_telemetry(msg)
            db.add_telemetry(state.soil, state.tank, state.flow_lpm,
                             state.valve_open, state.climate)
            await bus.publish({"type": "telemetry", "data": state.to_dict()})
        elif msg_type == "climate_remote":
            climate_svc.record_remote_change(msg.get("params", {}))
            await bus.publish({"type": "climate", "source": "remote",
                               **state.climate})

    serial = SerialManager(settings, on_message)
    climate_svc = ClimateService(serial, db, bus)
    plants_svc = PlantsService(settings, serial, db, bus)
    camera_svc = CameraService(settings, db, bus)
    registry = ToolRegistry(climate_svc, plants_svc, camera_svc)
    agent = OllamaAgent(settings, registry)

    services = Services()
    services.settings = settings
    services.db = db
    services.serial = serial
    services.climate = climate_svc
    services.plants = plants_svc
    services.camera = camera_svc
    services.agent = agent
    app.state.services = services

    await serial.start()
    await plants_svc.start_automation()
    await camera_svc.start()
    log.info("Homerun backend ready (serial=%s, camera=%s)",
             settings.serial_enabled, settings.camera_backend)

    try:
        yield
    finally:
        await camera_svc.stop()
        await plants_svc.stop_automation()
        await serial.stop()


app = FastAPI(title="Homerun", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (system, climate, plants, camera_api, chat, ws):
    app.include_router(module.router)


# Serve the built React app if it exists (production), with SPA fallback.
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    _assets = _dist / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
