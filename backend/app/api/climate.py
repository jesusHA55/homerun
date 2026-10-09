from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Literal

from app.core.security import require_auth

router = APIRouter(prefix="/api/climate", tags=["climate"],
                   dependencies=[Depends(require_auth)])


class ClimateBody(BaseModel):
    power: Literal["on", "off"] = "on"
    mode: Literal["auto", "cool", "heat", "dry", "fan"] = "cool"
    temp: int = 24
    fan: Literal["auto", "1", "2", "3"] = "auto"


@router.get("")
async def get_climate(request: Request) -> dict:
    return request.app.state.services.climate.get_state()


@router.post("")
async def set_climate(body: ClimateBody, request: Request) -> dict:
    try:
        return await request.app.state.services.climate.set_state(
            body.power, body.mode, body.temp, body.fan, source="api"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
