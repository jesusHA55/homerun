from fastapi import APIRouter, Depends, Request

from app.core.security import require_auth
from app.core.state import state

router = APIRouter(prefix="/api", tags=["system"],
                   dependencies=[Depends(require_auth)])


@router.get("/system")
async def system(request: Request) -> dict:
    services = request.app.state.services
    return {
        "device_connected": services.serial.connected,
        "state": state.to_dict(),
        "camera": services.camera.status(),
        "ollama": {
            "enabled": services.settings.ollama_enabled,
            "model": services.settings.ollama_model,
        },
    }


@router.get("/events")
async def events(request: Request, limit: int = 20) -> dict:
    db = request.app.state.services.db
    return {
        "motion": db.recent("motion_events", limit),
        "watering": db.recent("watering_events", limit),
        "climate": db.recent("climate_events", limit),
    }
