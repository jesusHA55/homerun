from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.security import require_auth
from app.core.state import state

router = APIRouter(prefix="/api/chat", tags=["chat"],
                   dependencies=[Depends(require_auth)])


class ChatBody(BaseModel):
    message: str


@router.post("")
async def chat(body: ChatBody, request: Request) -> dict:
    services = request.app.state.services
    db = services.db
    db.add_chat_message("user", body.message)

    history = list(reversed(db.recent("chat_messages", 20)))
    history = [{"role": m["role"], "content": m["content"]}
               for m in history if m["content"] != body.message]

    try:
        reply, actions = await services.agent.chat(body.message, history)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"agent unavailable: {exc}") from exc

    db.add_chat_message("assistant", reply, actions)
    return {"reply": reply, "actions": actions}


@router.get("/history")
async def history(request: Request, limit: int = 50) -> list:
    return list(reversed(request.app.state.services.db.recent("chat_messages", limit)))
