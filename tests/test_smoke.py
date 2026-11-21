"""MIRAGE smoke suite — proves the starter repo boots and contracts hold.

Run from repo root:   pytest tests/
Requires (for HTTP tests): scripts/dev.sh / dev.ps1 running, or manually
started backend (:8000) and target-merchant (:8001). Service tests SKIP
cleanly when services are unreachable; schema + Playwright tests always run.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))

import httpx  # noqa: E402

from app import schemas  # noqa: E402
from app.config import settings  # noqa: E402

BACKEND = "http://localhost:8000"
TARGET = "http://localhost:8001"


def _up(url: str) -> bool:
    try:
        return httpx.get(url, timeout=1.5).status_code < 500
    except httpx.HTTPError:
        return False


requires_backend = pytest.mark.skipif(not _up(f"{BACKEND}/api/health"), reason="backend not running")
requires_target = pytest.mark.skipif(not _up(f"{TARGET}/health"), reason="target-merchant not running")


# ── 1. Contract integrity: every locked schema serializes/validates cleanly ──
def test_schemas_roundtrip():
    box = schemas.BoundingBox(x=1, y=2, width=3, height=4, viewport_width=1280, viewport_height=800)
    finding = schemas.InjectionFinding(
        id="abc123",
        channel=schemas.InjectionChannel.META_TAG,
        severity="CRITICAL",
        raw_payload="ignore previous instructions",
        matched_triggers=["ignore previous"],
        dom_selector="meta[name='x']",
        bbox=box,
    )
    capture = schemas.PersonaCapture(
        persona="compliance_desktop",
        url="http://localhost:8001/",
        screenshot_url="/artifacts/x/persona_a.png",
        html_sha256="a" * 64,
        screenshot_sha256="b" * 64,
        checkout_endpoint="/mock-gateway/declared",
        billing_descriptor="MERCHANT*SHOP",
        detected_items=["mug"],
        network_hosts=["localhost"],
    )
    divergence = schemas.DivergenceReport(
        checkout_swapped=True,
        descriptor_swapped=True,
        claimed_gateway="declared",
        buyer_gateway="hidden",
        claimed_descriptor="MERCHANT*SHOP",
        buyer_descriptor="SHADOWPAY*LTD",
        text_jaccard_distance=0.8,
        pixel_divergence_pct=42.0,
        heatmap_url="/artifacts/x/heatmap.png",
        compliance_only_items=["mug"],
        buyer_only_items=["vape"],
        compute_ms=1.5,
    )
    osint = schemas.OsintSummary(
        source_mode="cached_fallback",
        company_name="Acme Ltd",
        company_number="12345678",
        address_shell_density=0.5,
        adverse_media_hits=[{"title": "t", "url": "u", "snippet": "s"}],
        covert_outreach_log={"sender": "agent@mail.grokbot.com", "status": "sent", "transcript": "hi"},
    )
    scan = schemas.ScanResult(
        scan_id="s1",
        target_url="http://localhost:8001/",
        created_at="2026-01-01T00:00:00Z",
        verdict=schemas.Verdict.CLOAKED_CRITICAL,
        reality_gap_score=88,
        evidence_merkle_hash="c" * 64,
        persona_a=capture,
        persona_b=None,
        divergence=divergence,
        injections=[finding],
        osint=osint,
    )
    event = schemas.AgentEvent(
        id="e1", scan_id="s1", timestamp="t", step="probe", agent="mirage",
        status="done", detail="ok", latency_ms=3.2,
    )
    replay = schemas.ReplayVerification(
        scan_id="s1", verified=True, llm_calls=0, elapsed_ms=1.0,
        hash_integrity="EXACT_MATCH",
        checks=[{"name": "hashes", "passed": True, "detail": "exact"}],
    )
    sleeper = schemas.SleeperCheckResult(
        target_url="u", day=60, intact=False, baseline_hash="a" * 64,
        current_hash="b" * 64, baseline_gateway="declared",
        current_gateway="hidden", alert_triggered=True, screenshot_url=None,
    )
    for model in (finding, capture, divergence, osint, scan, event, replay, sleeper):
        dumped = model.model_dump(mode="json")
        type(model).model_validate(dumped)  # round-trips cleanly

    assert set(v.value for v in schemas.Verdict) == {
        "CLOAKED_CRITICAL", "INJECTION_DETECTED", "DRIFT_DETECTED", "VERIFIED_CLEAN", "PENDING"
    }
    assert set(c.value for c in schemas.InjectionChannel) == {
        "meta_tag", "html_comment", "css_display_none",
        "css_invisible_text", "aria_label_attr", "hidden_input",
    }


# ── 2. Playwright Chromium launches and closes cleanly (headless) ─────────────
def test_playwright_chromium_headless():
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser.close()


# ── 3. Settings load with integration flags present ──────────────────────────
def test_settings_flags():
    for flag in ("supabase_enabled", "grokbot_enabled", "tavily_enabled", "companies_house_enabled"):
        assert isinstance(getattr(settings, flag), bool)


# ── 4. Health endpoints ───────────────────────────────────────────────────────
@requires_backend
def test_backend_health():
    r = httpx.get(f"{BACKEND}/api/health", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    for flag in ("supabase", "grokbot", "tavily", "companies_house"):
        assert flag in body["integrations"]


@requires_target
def test_target_health():
    assert httpx.get(f"{TARGET}/health", timeout=5).status_code == 200


@requires_target
def test_target_stub_routes():
    assert httpx.get(f"{TARGET}/", timeout=5).status_code == 200
    assert httpx.get(f"{TARGET}/control", timeout=5).status_code == 200
    assert httpx.get(f"{TARGET}/sleeper?day=60", timeout=5).status_code == 200
    assert httpx.get(f"{TARGET}/mock-gateway/declared", timeout=5).status_code == 200


# ── 5. Stub API routes return valid typed responses (no 500s) ────────────────
@requires_backend
def test_scan_lifecycle_stub():
    created = httpx.post(f"{BACKEND}/api/scans", json={"url": "http://localhost:8001/"}, timeout=45)
    assert created.status_code == 200
    scan = schemas.ScanResult.model_validate(created.json())
    # T4 acceptance: the cloaked target yields exactly 6 injection findings
    # covering all 6 channels (verdict hardens to CLOAKED_CRITICAL in T6).
    assert scan.verdict in (schemas.Verdict.INJECTION_DETECTED, schemas.Verdict.CLOAKED_CRITICAL)
    channels = {f.channel for f in scan.injections}
    assert channels == set(schemas.InjectionChannel)

    got = httpx.get(f"{BACKEND}/api/scans/{scan.scan_id}", timeout=5)
    assert got.status_code == 200
    assert got.json()["scan_id"] == scan.scan_id

    replay = httpx.post(f"{BACKEND}/api/scans/{scan.scan_id}/replay", timeout=5)
    assert replay.status_code == 200
    rv = schemas.ReplayVerification.model_validate(replay.json())
    assert rv.llm_calls == 0

    dossier = httpx.get(f"{BACKEND}/api/scans/{scan.scan_id}/dossier", timeout=5)
    assert dossier.status_code == 200

    stream = httpx.get(f"{BACKEND}/api/scans/{scan.scan_id}/stream", timeout=5)
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers["content-type"]

    missing = httpx.get(f"{BACKEND}/api/scans/does-not-exist", timeout=5)
    assert missing.status_code == 404


@requires_backend
def test_sleeper_and_webhook_stubs():
    reg = httpx.post(f"{BACKEND}/api/sleeper/register", json={"target_url": "http://localhost:8001/"}, timeout=5)
    assert reg.status_code == 200

    sim = httpx.post(
        f"{BACKEND}/api/sleeper/simulate",
        json={"target_url": "http://localhost:8001/", "day": 60},
        timeout=5,
    )
    assert sim.status_code == 200
    schemas.SleeperCheckResult.model_validate(sim.json())

    hook = httpx.post(f"{BACKEND}/api/webhooks/grokbot", json={"type": "ping"}, timeout=5)
    assert hook.status_code == 200
    assert hook.json()["received"] is True
