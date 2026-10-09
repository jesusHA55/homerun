from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal

from app.core.security import require_auth

router = APIRouter(prefix="/api/camera", tags=["camera"],
                   dependencies=[Depends(require_auth)])


class ModeBody(BaseModel):
    mode: Literal["manual", "motion"]


@router.get("/status")
async def status(request: Request) -> dict:
    return request.app.state.services.camera.status()


@router.post("/mode")
async def set_mode(body: ModeBody, request: Request) -> dict:
    try:
        return request.app.state.services.camera.set_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    camera = request.app.state.services.camera
    return StreamingResponse(
        camera.mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/snapshot")
async def snapshot(request: Request, save: bool = False) -> Response:
    camera = request.app.state.services.camera
    if save:
        camera.save_snapshot("manual")
    jpeg = camera.snapshot_jpeg()
    if jpeg is None:
        raise HTTPException(status_code=503, detail="no frame available")
    return Response(content=jpeg, media_type="image/jpeg")


@router.get("/events")
async def events(request: Request, limit: int = 20) -> list:
    return request.app.state.services.db.recent("motion_events", limit)
