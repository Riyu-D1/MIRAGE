"""MIRAGE demo target merchant — port 8001.

Self-hosted storefront used by every demo/probe. Routes are bootable stubs;
full cloaked storefronts + 6-channel injections are T1 (docs/TASKS.md).

Run:  uvicorn main:app --port 8001   (from apps/target-merchant/)
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="MIRAGE Target Merchant", version="0.1.0")

MOBILE_UA_HINTS = ("iphone", "android", "mobile")
SOCIAL_REFERER_HINTS = ("tiktok.com", "instagram.com", "t.co", "facebook.com")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "mirage-target-merchant"}


def is_buyer_persona(request: Request) -> bool:
    """True when the request looks like a social-referred mobile buyer.

    TODO(T1): tighten heuristics (UA parse + referer allowlist) as storefronts
    are built out.
    """
    ua = request.headers.get("user-agent", "").lower()
    referer = request.headers.get("referer", "").lower()
    return any(h in ua for h in MOBILE_UA_HINTS) and any(
        h in referer for h in SOCIAL_REFERER_HINTS
    )


@app.get("/", response_class=HTMLResponse)
def storefront(request: Request) -> HTMLResponse:
    """Persona-aware storefront.

    TODO(T1): serve TWO different pages:
      * Persona A (direct desktop, is_buyer_persona False): cloaked "clean"
        storefront — benign catalog, checkout -> /mock-gateway/declared,
        descriptor MERCHANT*SHOP — PLUS all 6 hidden prompt-injection
        channels embedded (meta tag, HTML comment, display:none, invisible
        CSS text, malicious aria-label, hidden input) as DETERMINISTIC
        constants (identical bytes every request).
      * Persona B (mobile UA + social referer): the REAL storefront —
        true catalog, checkout -> /mock-gateway/hidden,
        descriptor SHADOWPAY*LTD, no injections.
    """
    buyer = is_buyer_persona(request)
    persona = "buyer" if buyer else "compliance"
    return HTMLResponse(
        f"""<!doctype html>
<html><head><title>MIRAGE Demo Merchant</title></head>
<body>
  <h1>MIRAGE Demo Merchant — stub storefront</h1>
  <p>persona detected: {persona} (T1 will serve distinct cloaked/real pages)</p>
</body></html>"""
    )


@app.get("/control", response_class=HTMLResponse)
def control() -> HTMLResponse:
    """Fully clean control storefront — used for the 0-false-positive check.

    TODO(T1): honest catalog + honest /mock-gateway/declared checkout, no
    injections of any kind.
    """
    return HTMLResponse(
        """<!doctype html>
<html><head><title>Control Store</title></head>
<body><h1>Control Store — clean stub (T1)</h1></body></html>"""
    )


@app.get("/sleeper", response_class=HTMLResponse)
def sleeper(day: int = 1) -> HTMLResponse:
    """Day-N storefront for Sleeper Watch.

    TODO(T1): day=1 serves the approved clean page; day=30 swaps the checkout
    gateway; day=60 swaps catalog + gateway + descriptor (bait-and-switch).
    Hashes across days must differ deterministically.
    """
    return HTMLResponse(
        f"""<!doctype html>
<html><head><title>Sleeper Merchant — day {day}</title></head>
<body><h1>Sleeper stub — day {day} (T1)</h1></body></html>"""
    )


@app.get("/mock-gateway/declared")
def mock_gateway_declared() -> dict:
    """The gateway the merchant SHOWS the compliance reviewer."""
    # TODO(T1): return the full mock checkout page/payload convention agreed
    # with playwright_probe (T2) for checkout_endpoint + billing_descriptor.
    return {"gateway": "declared", "descriptor": "MERCHANT*SHOP"}


@app.get("/mock-gateway/hidden")
def mock_gateway_hidden() -> dict:
    """The gateway real buyers actually hit — the laundering tell."""
    # TODO(T1): see mock_gateway_declared.
    return {"gateway": "hidden", "descriptor": "SHADOWPAY*LTD"}
