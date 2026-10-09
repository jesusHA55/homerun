"""Token-based auth. Disabled while the token is the default placeholder."""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import get_settings


async def require_auth(
    authorization: str | None = Header(default=None),
    x_auth_token: str | None = Header(default=None),
) -> bool:
    token = get_settings().auth_token
    if token in ("", "change-me"):
        return True  # open on the LAN until the user sets a token

    provided = x_auth_token
    if not provided and authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:]
    if provided != token:
        raise HTTPException(status_code=401, detail="unauthorized")
    return True
