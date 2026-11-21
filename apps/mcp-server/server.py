"""MIRAGE FastMCP server — port 8002.

Exposes MIRAGE's deterministic tools to Grok Bot over MCP (SSE transport).
Each tool is a thin, validated wrapper over the backend API on :8000.

Run:  python server.py   (from apps/mcp-server/)
"""
import os

import httpx
from mcp.server.fastmcp import FastMCP

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

mcp = FastMCP("mirage", host="0.0.0.0", port=8002)


def _require(data: dict, *keys: str) -> dict:
    """Light contract check — fail loudly if the backend response drifted."""
    missing = [k for k in keys if k not in data]
    if missing:
        raise ValueError(f"backend response missing fields: {missing}")
    return data


@mcp.tool()
async def mirage_scan(url: str) -> dict:
    """Run a MIRAGE dual-persona scan of a merchant URL -> ScanResult.

    POST returns PENDING immediately (pipeline runs in a background thread);
    polls GET until the verdict hardens or ~55s elapses.
    """
    import asyncio

    async with httpx.AsyncClient(timeout=15.0) as client:
        created = (await client.post(f"{BACKEND_URL}/api/scans", json={"url": url})).json()
        scan = {}
        for _ in range(55):
            result = await client.get(f"{BACKEND_URL}/api/scans/{created['scan_id']}")
            result.raise_for_status()
            scan = result.json()
            if scan.get("verdict") != "PENDING":
                break
            await asyncio.sleep(1.0)
        scan = _require(
            scan,
            "scan_id", "verdict", "reality_gap_score", "injections",
            "persona_a", "persona_b", "divergence",
        )
        return {
            "scan_id": scan["scan_id"],
            "verdict": scan["verdict"],
            "reality_gap_score": scan["reality_gap_score"],
            "injection_count": len(scan["injections"]),
            "checkout_swapped": (scan.get("divergence") or {}).get("checkout_swapped"),
            "descriptor_swapped": (scan.get("divergence") or {}).get("descriptor_swapped"),
            "evidence_merkle_hash": scan.get("evidence_merkle_hash"),
            "full_result": scan,
        }


@mcp.tool()
async def mirage_replay(scan_id: str) -> dict:
    """Zero-LLM deterministic re-verification of a scan -> ReplayVerification."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{BACKEND_URL}/api/scans/{scan_id}/replay")
        resp.raise_for_status()
        return _require(resp.json(), "scan_id", "verified", "llm_calls", "hash_integrity")


@mcp.tool()
async def mirage_sleeper_check(url: str, day: int = 60) -> dict:
    """Check a merchant for Day-N sleeper drift -> SleeperCheckResult."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/sleeper/simulate",
            json={"target_url": url, "day": day},
        )
        resp.raise_for_status()
        return _require(
            resp.json(), "target_url", "day", "intact",
            "alert_triggered", "current_gateway",
        )


@mcp.tool()
async def mirage_dossier(scan_id: str) -> dict:
    """Fetch the printable evidence dossier for a scan."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BACKEND_URL}/api/scans/{scan_id}/dossier")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run(transport="sse")
