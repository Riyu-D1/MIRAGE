"""MIRAGE deterministic forensics core.

NO LLM CALLS in this package — every module is deterministic and must emit
SHA-256 artifact hashes + real perf_counter() latencies. See AGENTS.md §1.
"""
