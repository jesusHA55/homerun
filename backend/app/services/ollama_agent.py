"""Ollama tool-calling agent."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import Settings
from app.tools.registry import TOOL_SCHEMAS, ToolRegistry

log = logging.getLogger("homerun.agent")

SYSTEM_PROMPT = (
    "You are Homerun, the assistant for a small smart home. You control an "
    "air conditioner (climate), a plant watering valve, and a camera. "
    "Use the provided tools when the user asks you to change or check "
    "something. Keep replies short and friendly. Temperatures are in Celsius "
    "between 17 and 30. Never water for more than 60 seconds. If a tool "
    "returns an error, explain it plainly."
)


class OllamaAgent:
    def __init__(self, settings: Settings, registry: ToolRegistry) -> None:
        self.settings = settings
        self.registry = registry

    async def chat(self, message: str, history: list[dict[str, Any]]) -> tuple[str, list]:
        if not self.settings.ollama_enabled:
            raise RuntimeError("Ollama is disabled")

        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in history[-20:]:
            messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": message})

        actions: list[dict[str, Any]] = []
        url = self.settings.ollama_url.rstrip("/") + "/api/chat"

        async with httpx.AsyncClient(timeout=120) as client:
            for _ in range(6):
                resp = await client.post(
                    url,
                    json={
                        "model": self.settings.ollama_model,
                        "messages": messages,
                        "tools": TOOL_SCHEMAS,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                msg = data.get("message", {})
                messages.append(msg)

                calls = msg.get("tool_calls") or []
                if not calls:
                    return msg.get("content", "").strip(), actions

                for call in calls:
                    fn = call.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    result = await self.registry.execute(name, args)
                    actions.append({"tool": name, "args": args, "result": result})
                    messages.append(
                        {"role": "tool", "content": json.dumps(result)}
                    )

        return "I stopped after several tool calls without a final answer.", actions
