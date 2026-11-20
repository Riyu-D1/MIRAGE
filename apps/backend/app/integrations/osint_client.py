"""OSINT client shell (T6) — UK Companies House + Tavily adverse media.

Live when the matching API key is set; otherwise serve cached fixtures from
this directory so OsintSummary.source_mode="cached_fallback" stays honest.
"""
import json
from pathlib import Path

from ..config import settings
from ..schemas import OsintSummary

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a canned OSINT response (company_lookup.json, adverse_media.json).

    TODO(T6): commit the fixture files this reads.
    """
    path = FIXTURES_DIR / name
    return json.loads(path.read_text()) if path.exists() else {}


def lookup_company(company_name: str) -> OsintSummary:
    """Companies House profile -> partial OsintSummary.

    TODO(T6): when settings.companies_house_enabled, call
    https://api.company-information.service.gov.uk (basic auth = key + '');
    else load_fixture("company_lookup.json") with source_mode="cached_fallback".
    Fill company_name, company_number, address_shell_density.
    """
    raise NotImplementedError("T6 — implement per docs/TASKS.md")


def adverse_media(merchant_name: str) -> OsintSummary:
    """Tavily adverse-media search -> adverse_media_hits.

    TODO(T6): when settings.tavily_enabled, POST https://api.tavily.com/search;
    else load_fixture("adverse_media.json"). Attach covert_outreach_log when a
    Grok Bot outreach event has arrived via /api/webhooks/grokbot.
    """
    raise NotImplementedError("T6 — implement per docs/TASKS.md")
