"""Deterministic 3-channel divergence + pixel-diff heatmap (T3)."""
import hashlib
from pathlib import Path

from ..schemas import DivergenceReport, PersonaCapture


def sha256_file(path: Path) -> str:
    """SHA-256 hex digest of a file — the standard MIRAGE evidence hash."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compute_divergence(
    persona_a: PersonaCapture,
    persona_b: PersonaCapture,
    scan_id: str,
    artifacts_dir: Path,
) -> DivergenceReport:
    """Diff the two persona captures into a DivergenceReport.

    TODO(T3):
      * checkout_swapped / descriptor_swapped (endpoint + descriptor mismatch)
      * claimed_* (persona A) vs buyer_* (persona B) gateway/descriptor
      * text_jaccard_distance over detected_items token sets
      * pixel_divergence_pct: Pillow+NumPy per-pixel diff of the two 1280x800
        PNGs; render neon 'heatmap.png' into artifacts_dir; heatmap_url =
        "/artifacts/{scan_id}/heatmap.png"
      * compliance_only_items / buyer_only_items set differences
      * compute_ms = real perf_counter() wall time of this function
    """
    raise NotImplementedError("T3 — implement per docs/TASKS.md")


def reality_gap_score(d: DivergenceReport) -> int:
    """Weighted 0-100 score: checkout swap 40, descriptor swap 25,
    pixel divergence up to 20, jaccard distance up to 15.

    TODO(T3): implement and clamp to [0, 100].
    """
    raise NotImplementedError("T3 — implement per docs/TASKS.md")
