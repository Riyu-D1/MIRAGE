"""OSINT client shell (T6) — UK Companies House + Tavily adverse media.

Fixture fallback path is implemented (source_mode="cached_fallback").
Live API calls are TODO(T6): implement inside the marked branches —
on any failure, fall back to fixtures so the demo never hard-fails.
"""
import json
from pathlib import Path
from typing import Any

from ..config import settings
from ..schemas import AdverseMediaHit, CovertOutreachLog, OsintSummary

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a canned OSINT response (company_lookup.json, adverse_media.json)."""
    path = FIXTURES_DIR / name
    return json.loads(path.read_text()) if path.exists() else {}


def lookup_company(company_name: str) -> OsintSummary:
    """Companies House profile -> OsintSummary (identity half).

    TODO(T6): when settings.companies_house_enabled, GET
    https://api.company-information.service.gov.uk/search/companies?q={name}
    with basic auth (key, ""), take items[0], and set source_mode="live".
    """
    data = load_fixture("company_lookup.json")
    return OsintSummary(
        source_mode="cached_fallback",
        company_name=data.get("company_name", company_name),
        company_number=data.get("company_number"),
        address_shell_density=data.get("address_shell_density"),
    )


def adverse_media(merchant_name: str) -> OsintSummary:
    """Tavily adverse-media search -> OsintSummary (media + outreach half).

    TODO(T6): when settings.tavily_enabled, POST https://api.tavily.com/search
    with {query: f"{merchant_name} fraud laundering descriptor"}; map results
    into adverse_media_hits; set source_mode="live". covert_outreach_log is
    populated when a Grok Bot outreach event arrives via /api/webhooks/grokbot
    — until then the fixture supplies it.
    """
    data = load_fixture("adverse_media.json")
    hits = [AdverseMediaHit(**h) for h in data.get("adverse_media_hits", [])]
    outreach = data.get("covert_outreach_log")
    return OsintSummary(
        source_mode="cached_fallback",
        adverse_media_hits=hits,
        covert_outreach_log=CovertOutreachLog(**outreach) if outreach else None,
    )


def enrich(merchant_name: str) -> OsintSummary:
    """Merged OSINT summary — call sites use this single entry point."""
    company = lookup_company(merchant_name)
    media = adverse_media(merchant_name)
    return OsintSummary(
        source_mode=company.source_mode
        if company.source_mode == media.source_mode
        else "cached_fallback",
        company_name=company.company_name,
        company_number=company.company_number,
        address_shell_density=company.address_shell_density,
        adverse_media_hits=media.adverse_media_hits,
        covert_outreach_log=media.covert_outreach_log,
    )
