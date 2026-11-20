"""Zero-LLM deterministic regulator replay (T5).

Re-verifies a scan purely from stored artifacts: no network, no probe, no LLM.
`llm_calls` must remain 0 forever — that invariant is the product.
"""
from pathlib import Path

from ..schemas import ReplayVerification


def replay(scan_id: str, artifacts_dir: Path) -> ReplayVerification:
    """Re-verify scan artifacts deterministically.

    TODO(T5):
      * load artifacts_dir/{scan_id}/ (HTML, PNGs, manifests)
      * recompute SHA-256 of every artifact -> compare to stored hashes
        => hash_integrity EXACT_MATCH | MISMATCH
      * re-derive the verdict from stored diff/injection outputs
      * checks[] entries: artifact presence, hash integrity, verdict
        consistency, heatmap dimensions, injection-count stability
      * elapsed_ms = real perf_counter() (hash set should be <5ms; report
        actual), llm_calls = 0 always
    """
    raise NotImplementedError("T5 — implement per docs/TASKS.md")
