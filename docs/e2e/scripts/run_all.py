"""Orchestrates all E2E phases in order.

Runs each phase script as a subprocess, collects results, prints a
summary, and exits non-zero if any phase failed.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PHASES = [
    ("00", "Health check", "00_health_check.py"),
    ("01", "Auth flow", "01_auth_flow.py"),
    ("02", "Config flow", "02_config_flow.py"),
    ("03", "Memory CRUD", "03_memories_crud.py"),
    ("04", "MCP batch add", "04_memories_batch_mcp.py"),
    ("05", "Reason and chat", "05_reason_chat.py"),
    ("06", "Graph endpoints", "06_graph_entities.py"),
    ("07", "Code repos", "07_code_repos.py"),
    ("08", "Analytics", "08_analytics_reprocess.py"),
    ("09", "Pipeline failures", "09_pipeline_failures.py"),
    ("10", "Re-embed flow", "10_reembed_flow.py"),
    ("11", "Perf baseline", "12_perf_baseline.py"),
    ("12", "DB audit", "13_db_audit.py"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all E2E phases")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--password", default="e2e-admin-pw")
    parser.add_argument("--skip", default="", help="Comma-separated phase IDs to skip (e.g. 06,12)")
    args = parser.parse_args()

    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    scripts_dir = Path(__file__).parent

    results: list[tuple[str, str, int]] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(scripts_dir) + os.pathsep + env.get("PYTHONPATH", "")

    for phase_id, label, script in PHASES:
        if phase_id in skip:
            print(f"\n[SKIP] Phase {phase_id}: {label}")
            results.append((phase_id, label, -1))
            continue

        print(f"\n{'=' * 60}")
        print(f"Phase {phase_id}: {label}")
        print("=" * 60)

        cmd = [sys.executable, str(scripts_dir / script),
               "--base-url", args.base_url,
               "--password", args.password]
        try:
            r = subprocess.run(cmd, env=env)
            results.append((phase_id, label, r.returncode))
        except Exception as e:
            print(f"Phase {phase_id} failed to execute: {e}")
            results.append((phase_id, label, 2))

    print()
    print("=" * 60)
    print("E2E SUMMARY")
    print("=" * 60)
    failed = 0
    for phase_id, label, rc in results:
        if rc == -1:
            status = "SKIP"
        elif rc == 0:
            status = "PASS"
        else:
            status = "FAIL"
            failed += 1
        print(f"  [{status}] Phase {phase_id}: {label}")

    print()
    if failed:
        print(f"{failed} phase(s) failed")
        return 1
    print("All phases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
