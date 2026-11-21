"""Grok Bot client shell (T5/T6).

Outbound: dispatch AgentEvents to GROKBOT_WEBHOOK_URL.
Inbound:  parse payloads arriving at POST /api/webhooks/grokbot.
"""
from typing import Any

import httpx

from ..config import settings
from ..schemas import AgentEvent


async def dispatch_event(event: AgentEvent) -> bool:
    """POST an AgentEvent to the Grok Bot webhook. Returns False (no-op)
    when GROKBOT_WEBHOOK_URL is unset or the dispatch fails — never raises."""
    if not settings.grokbot_enabled:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                settings.grokbot_webhook_url,
                json=event.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {settings.grokbot_api_key}"},
            )
            return resp.is_success
    except httpx.HTTPError:
        return False


def dispatch_event_sync(event: AgentEvent) -> bool:
    """Sync variant for the pipeline's worker thread — fire-and-forget."""
    if not settings.grokbot_enabled:
        return False
    try:
        resp = httpx.post(
            settings.grokbot_webhook_url,
            json=event.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {settings.grokbot_api_key}"},
            timeout=3.0,
        )
        return resp.is_success
    except httpx.HTTPError:
        return False


def parse_inbound(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize an inbound Grok Bot webhook payload.

    TODO(T6): map known event types (sleeper_trigger, outreach_result,
    routine_heartbeat) onto internal actions; pass through unknown types.
    """
    return {
        "type": payload.get("type", "unknown"),
        "scan_id": payload.get("scan_id"),
        "payload": payload,
    }
