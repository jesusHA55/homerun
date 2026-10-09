from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.security import require_auth

router = APIRouter(prefix="/api/plants", tags=["plants"],
                   dependencies=[Depends(require_auth)])


class WaterBody(BaseModel):
    seconds: int = 20


class ScheduleBody(BaseModel):
    enabled: bool = True
    every_hours: float = 24
    duration_s: int = 20
    min_soil: int = 35


@router.get("")
async def get_plants(request: Request) -> dict:
    return request.app.state.services.plants.zone_state()


@router.post("/water")
async def water(body: WaterBody, request: Request) -> dict:
    try:
        return await request.app.state.services.plants.water(body.seconds, "manual")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/stop")
async def stop(request: Request) -> dict:
    return await request.app.state.services.plants.stop()


@router.get("/schedule")
async def get_schedule(request: Request) -> dict:
    return request.app.state.services.plants.zone_state()["schedule"]


@router.post("/schedule")
async def set_schedule(body: ScheduleBody, request: Request) -> dict:
    return request.app.state.services.plants.set_schedule(
        body.enabled, body.every_hours, body.duration_s, body.min_soil
    )
