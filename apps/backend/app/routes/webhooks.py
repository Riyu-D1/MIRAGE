"""Inbound webhooks — /api/webhooks.

Stub implementation. # TODO(T5/T6): authenticate with GROKBOT_API_KEY and
route parsed events via integrations/grokbot_client.parse_inbound.
"""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/grokbot")
async def grokbot_webhook(request: Request) -> dict:
    """Receive Grok Bot events (sleeper triggers, covert outreach results).

    TODO(T6): verify Authorization: Bearer {GROKBOT_API_KEY} when configured,
    then dispatch on integrations.grokbot_client.parse_inbound(payload).
    """
    payload = await request.json()
    return {
        "received": True,
        "event_type": payload.get("type", "unknown"),
        "note": "stub — inbound event handling implemented in T6",
    }
