"""Zero-LLM deterministic regulator replay (T5 — implemented).

Re-verifies a scan purely from stored artifacts: no network, no probe, no LLM.
`llm_calls` must remain 0 forever — that invariant is the product.
"""
import json
import time
from pathlib import Path

from ..schemas import ReplayCheck, ReplayVerification
from .diff_engine import sha256_file
from .injection_scanner import scan_html

MANIFEST_NAME = "manifest.json"


def build_manifest(scan_dir: Path) -> dict[str, str]:
    """Write manifest.json: {filename: sha256} for every artifact in the dir
    (excluding the manifest itself). Returns the manifest."""
    scan_dir = Path(scan_dir)
    manifest = {
        p.name: sha256_file(p)
        for p in sorted(scan_dir.iterdir())
        if p.is_file() and p.name != MANIFEST_NAME
    }
    (scan_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))
    return manifest


def replay(scan_id: str, artifacts_dir: Path) -> ReplayVerification:
    """Re-verify scan artifacts deterministically (0 network, 0 LLM).

    Expects scan_dir/manifest.json + the artifacts it lists (scan.json,
    persona_*.html/png, heatmap.png, ...).
    """
    t0 = time.perf_counter()
    scan_dir = Path(artifacts_dir) / scan_id
    checks: list[ReplayCheck] = []

    manifest_path = scan_dir / MANIFEST_NAME
    if not manifest_path.exists():
        elapsed = (time.perf_counter() - t0) * 1000
        return ReplayVerification(
            scan_id=scan_id,
            verified=False,
            llm_calls=0,
            elapsed_ms=round(elapsed, 2),
            hash_integrity="MISMATCH",
            checks=[
                ReplayCheck(
                    name="manifest_present",
                    passed=False,
                    detail="manifest.json missing — scan may predate artifact persistence",
                )
            ],
        )

    manifest: dict[str, str] = json.loads(manifest_path.read_text())

    # 1) every manifest artifact present on disk
    missing = [name for name in manifest if not (scan_dir / name).exists()]
    checks.append(
        ReplayCheck(
            name="artifacts_present",
            passed=not missing,
            detail="all artifacts present" if not missing else f"missing: {missing}",
        )
    )

    # 2) hash integrity — recompute SHA-256 of each artifact
    mismatched = [
        name for name in manifest
        if (scan_dir / name).exists() and sha256_file(scan_dir / name) != manifest[name]
    ]
    hash_integrity = "EXACT_MATCH" if not mismatched else "MISMATCH"
    checks.append(
        ReplayCheck(
            name="hash_integrity",
            passed=not mismatched,
            detail="all SHA-256 exact" if not mismatched else f"tampered: {mismatched}",
        )
    )

    # 3) injection stability — re-scan stored Persona A HTML, compare to stored count
    a_html = scan_dir / "persona_a.html"
    scan_json = scan_dir / "scan.json"
    if a_html.exists() and scan_json.exists():
        refindings = scan_html(a_html.read_text(errors="replace"))
        stored = len(json.loads(scan_json.read_text()).get("injections", []))
        checks.append(
            ReplayCheck(
                name="injection_recheck",
                passed=len(refindings) == stored,
                detail=f"re-scan: {len(refindings)} findings vs stored {stored}",
            )
        )

    # 4) verdict consistency — stored scan.json verdict is not PENDING
    if scan_json.exists():
        verdict = json.loads(scan_json.read_text()).get("verdict", "PENDING")
        checks.append(
            ReplayCheck(
                name="verdict_resolved",
                passed=verdict != "PENDING",
                detail=f"stored verdict: {verdict}",
            )
        )

    elapsed = (time.perf_counter() - t0) * 1000
    return ReplayVerification(
        scan_id=scan_id,
        verified=all(c.passed for c in checks),
        llm_calls=0,
        elapsed_ms=round(elapsed, 2),
        hash_integrity=hash_integrity,
        checks=checks,
    )
