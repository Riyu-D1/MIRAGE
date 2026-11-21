"""Deterministic 3-channel divergence + pixel-diff heatmap (T3 — implemented)."""
import hashlib
import time
from pathlib import Path

import numpy as np
from PIL import Image

from ..schemas import DivergenceReport, PersonaCapture

# Per-pixel channel diff above this counts as a divergent pixel.
PIXEL_THRESHOLD = 25


def sha256_file(path: Path) -> str:
    """SHA-256 hex digest of a file — the standard MIRAGE evidence hash."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def merkle_hash(hashes: list[str]) -> str:
    """Deterministic evidence bundle hash: sha256 over sorted digests."""
    return hashlib.sha256("".join(sorted(hashes)).encode()).hexdigest()


def jaccard_distance(a: set[str], b: set[str]) -> float:
    """1 - |A∩B|/|A∪B|; both empty -> 0.0 (identical)."""
    if not a and not b:
        return 0.0
    union = a | b
    return 1.0 - len(a & b) / len(union)


def _pixel_diff(a_png: Path, b_png: Path, out_png: Path) -> float:
    """Diff two same-sized PNGs; render neon heatmap; return % divergent."""
    ia = np.asarray(Image.open(a_png).convert("RGB"), dtype=np.int16)
    ib = np.asarray(Image.open(b_png).convert("RGB"), dtype=np.int16)
    diff = np.abs(ia - ib).sum(axis=2)  # 0..765
    divergent = diff > PIXEL_THRESHOLD
    pct = float(divergent.mean() * 100.0)

    # Neon heatmap: hot orange-red intensity over black (DESIGN_SYSTEM heat glow)
    intensity = np.clip(diff * 1.5, 0, 255).astype(np.uint8)
    heat = np.zeros((*intensity.shape, 3), dtype=np.uint8)
    heat[..., 0] = intensity                                    # R
    heat[..., 1] = (intensity * 0.40).astype(np.uint8)          # G
    heat[..., 2] = (intensity * 0.15).astype(np.uint8)          # B
    Image.fromarray(heat).save(out_png)
    return round(pct, 2)


def compute_divergence(
    persona_a: PersonaCapture,
    persona_b: PersonaCapture,
    scan_id: str,
    artifacts_dir: Path,
) -> DivergenceReport:
    """Diff the two persona captures into a DivergenceReport.

    ``artifacts_dir`` is the scan's artifact dir containing persona_a.png,
    persona_b.png; heatmap.png is written alongside them.
    """
    t0 = time.perf_counter()
    artifacts_dir = Path(artifacts_dir)

    items_a = set(persona_a.detected_items)
    items_b = set(persona_b.detected_items)
    jaccard = jaccard_distance(items_a, items_b)

    heatmap_url = None
    pixel_pct = 0.0
    a_png = artifacts_dir / "persona_a.png"
    b_png = artifacts_dir / "persona_b.png"
    if a_png.exists() and b_png.exists():
        pixel_pct = _pixel_diff(a_png, b_png, artifacts_dir / "heatmap.png")
        heatmap_url = f"/artifacts/{scan_id}/heatmap.png"

    compute_ms = (time.perf_counter() - t0) * 1000
    return DivergenceReport(
        checkout_swapped=persona_a.checkout_endpoint != persona_b.checkout_endpoint,
        descriptor_swapped=persona_a.billing_descriptor != persona_b.billing_descriptor,
        claimed_gateway=persona_a.checkout_endpoint,
        buyer_gateway=persona_b.checkout_endpoint,
        claimed_descriptor=persona_a.billing_descriptor,
        buyer_descriptor=persona_b.billing_descriptor,
        text_jaccard_distance=round(jaccard, 4),
        pixel_divergence_pct=pixel_pct,
        heatmap_url=heatmap_url,
        compliance_only_items=sorted(items_a - items_b),
        buyer_only_items=sorted(items_b - items_a),
        compute_ms=round(compute_ms, 2),
    )


def reality_gap_score(d: DivergenceReport) -> int:
    """Weighted 0-100: checkout swap 40, descriptor swap 25,
    pixel divergence up to 20, jaccard distance up to 15."""
    score = 0.0
    if d.checkout_swapped:
        score += 40
    if d.descriptor_swapped:
        score += 25
    score += min(20.0, d.pixel_divergence_pct / 5.0)
    score += min(15.0, d.text_jaccard_distance * 15.0)
    return int(round(min(100.0, score)))
