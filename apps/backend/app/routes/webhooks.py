"""Inbound webhooks — /api/webhooks.

Grok Bot posts events here (sleeper triggers, covert outreach results).
When GROKBOT_API_KEY is configured, Bearer auth is enforced; when blank
(offline mode) the route accepts everything. Parsed events with a scan_id
are injected into that scan's AgentEvent stream so they surface in the
Mission Control feed.
"""
from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..integrations import grokbot_client
from .scans import _all_events, _event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/grokbot")
async def grokbot_webhook(request: Request) -> dict:
    """Receive Grok Bot events and surface them in the scan's mission feed."""
    if settings.grokbot_api_key:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {settings.grokbot_api_key}":
            raise HTTPException(status_code=401, detail="bad webhook key")

    payload = await request.json()
    parsed = grokbot_client.parse_inbound(payload)

    scan_id = parsed.get("scan_id")
    injected = False
    if scan_id and _all_events(scan_id):
        _event(
            scan_id,
            f"grokbot.{parsed['type']}",
            "alert",
            f"Grok Bot: {parsed['type']} — "
            f"{str(payload.get('detail') or payload.get('message') or 'received')[:120]}",
            agent="grok-bot",
        )
        injected = True

    return {"received": True, "event_type": parsed["type"], "injected": injected}
