from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.events import bus
from app.core.state import state

router = APIRouter(tags=["ws"])


@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = bus.subscribe()
    try:
        await websocket.send_json({"type": "state", "data": state.to_dict()})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        bus.unsubscribe(queue)
