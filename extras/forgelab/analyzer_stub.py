"""ForgeLab — PDF 4-layer forensics stub (backup audible).

Same determinism contract as apps/backend/app/core/: SHA-256 evidence,
perf_counter() latencies, NO LLM calls. Wire as a backend route only if the
track pivots to document verification (see extras/forgelab/README.md).
"""
import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass
class LayerFinding:
    layer: int
    name: str
    passed: bool
    detail: str
    elapsed_ms: float


@dataclass
class PdfForensicsReport:
    path: str
    sha256: str
    verdict: str  # "AUTHENTIC" | "SUSPICIOUS" | "FORGED"
    layers: list[LayerFinding] = field(default_factory=list)


def check_metadata(pdf_path: Path) -> LayerFinding:
    """Layer 1 — metadata forensics.

    TODO(pivot): parse PDF trailer/XMP for producer, creation/mod timestamps,
    and tool-inconsistency flags (e.g. producer claims Acrobat but object
    structure says reportlab; mod_date precedes creation_date).
    """
    raise NotImplementedError("forge-lab pivot — implement per README")


def check_running_balance(
    opening: Decimal, transactions: list[Decimal], stated_closing: Decimal
) -> LayerFinding:
    """Layer 4 — running-balance re-derivation for bank statements.

    TODO(pivot): replay credits/debits from `opening`, compare computed
    closing to `stated_closing`; flag arithmetic discontinuities that indicate
    spliced/edited transaction rows. Keep Decimal precision — no floats.
    """
    raise NotImplementedError("forge-lab pivot — implement per README")


def analyze(pdf_path: Path) -> PdfForensicsReport:
    """Run all implemented layers and aggregate a verdict.

    TODO(pivot): orchestrate layers 1-4, hash the file, emit per-layer
    elapsed_ms via perf_counter(), verdict = worst failing layer.
    """
    sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    return PdfForensicsReport(
        path=str(pdf_path), sha256=sha, verdict="SUSPICIOUS", layers=[]
    )
