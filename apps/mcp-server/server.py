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


@mcp.tool()
async def mirage_scan(url: str) -> dict:
    """Run a MIRAGE dual-persona scan of a merchant URL -> ScanResult.

    TODO(T7): validate the response into the ScanResult contract before
    returning; surface verdict, reality_gap_score, and injection count.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        created = (await client.post(f"{BACKEND_URL}/api/scans", json={"url": url})).json()
        result = await client.get(f"{BACKEND_URL}/api/scans/{created['scan_id']}")
        result.raise_for_status()
        return result.json()


@mcp.tool()
async def mirage_replay(scan_id: str) -> dict:
    """Zero-LLM deterministic re-verification of a scan -> ReplayVerification."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{BACKEND_URL}/api/scans/{scan_id}/replay")
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def mirage_sleeper_check(url: str, day: int = 60) -> dict:
    """Check a merchant for Day-N sleeper drift -> SleeperCheckResult."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/sleeper/simulate",
            json={"target_url": url, "day": day},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def mirage_dossier(scan_id: str) -> dict:
    """Fetch the printable evidence dossier for a scan."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{BACKEND_URL}/api/scans/{scan_id}/dossier")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run(transport="sse")
