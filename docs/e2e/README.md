# darkmem End-to-End Test Plan

**`scripts/` is superseded by `backend/scripts/e2e/` for automated runs (T1.64).** That
suite has one documented entry point (`python scripts/e2e/run_e2e.py`), boots its own
disposable database and server, and is what `scripts/gate.sh --full` invokes. This
directory's `scripts/` are retained only as a manual pre-cutover QA reference — their own
stated precondition ("Fresh darkmem deployment — server running, no admin password set,
empty database") describes a one-shot runbook against a real, about-to-launch deployment,
not a repeatable per-merge harness, and `env.sh`'s hardcoded
`DARKMEM_BACKEND_DIR=/workspace/darkmem/backend` is stale on this machine. Retired, not
deleted: they are a readable checklist of what a "fresh deployment" smoke pass once
covered. `test-plan.md` and `ui-test-plan.md` are untouched by this note — they describe a
broader manual QA superset this disposition does not cover.

This directory contains the comprehensive E2E test plan and reusable scripts for verifying a fresh darkmem deployment. Run against a clean instance to validate all flows, features, APIs, UI pages, components, and catch design/UX/performance issues.

## Structure

```
docs/e2e/
├── README.md                        this file
├── test-plan.md                     master API+UI runbook (Phase 0-16)
├── ui-test-plan.md                  deep UI-only runbook (Phase U1-U24) — every route, every component, every violation class
├── checklist.md                     short runbook checklist for manual QA
├── fixtures/                        seed data used by scripts
│   └── sample_memories.json         ~30 diverse memories for ingest
└── scripts/                         reusable Python/HTTP scripts
    ├── env.sh                       shared env vars for bash scripts
    ├── 00_health_check.py           server + service liveness
    ├── 01_auth_flow.py              setup → login → me → refresh → change → logout
    ├── 02_config_flow.py            LLM config, feature flags, enrichment, classification areas
    ├── 03_memories_crud.py          single memory CRUD + search + batch + merge + duplicates
    ├── 04_memories_batch_mcp.py     MCP batch add via /mcp JSON-RPC
    ├── 05_reason_chat.py            RAG reason + chat completions + conversations
    ├── 06_graph_entities.py         entities/relations/neighbors/memory-context
    ├── 07_code_repos.py             repo add/list/reindex/search/symbols/graph/wiki
    ├── 08_analytics_reprocess.py    overview/stats/pipeline-logs/reprocess-all
    ├── 09_pipeline_failures.py      failure tracking + retry flow
    ├── 10_reembed_flow.py           obsolete counts + re-embed by category + prune cache
    ├── 11_websocket_listener.py     live WebSocket event dump
    ├── 12_perf_baseline.py          latency + throughput measurements
    ├── 13_db_audit.py               DB-level assertions (fingerprints, orphans, counts)
    ├── run_all.py                   orchestrates 00–13 in order
    └── lib/
        ├── client.py                shared HTTP client with cookie auth
        └── assertions.py            reusable assertion helpers
```

## Prerequisites

- **Fresh darkmem deployment** — server running, no admin password set, empty database
- **Backend** reachable at `http://localhost:8000`
- **Frontend** reachable at `http://host.docker.internal:3636` (or `http://localhost:3636`)
- **Ollama** reachable at `http://localhost:11434` with at least one embedding model and one chat model
- **Python 3.12+** with `httpx` installed (already a backend dependency)

## Quick Start

```bash
cd docs/e2e/scripts

# 1. Set up the admin password (one time)
python 01_auth_flow.py --setup --password "e2e-admin-pw"

# 2. Run the full E2E suite
python run_all.py --password "e2e-admin-pw"

# 3. Or run individual phases
python 00_health_check.py
python 03_memories_crud.py --password "e2e-admin-pw"
python 12_perf_baseline.py --password "e2e-admin-pw"
```

All scripts accept `--base-url` (default `http://localhost:8000`) and `--password` for auth. See `test-plan.md` for the full phase-by-phase breakdown.

## Conventions

- **Exit code 0** means all assertions passed; non-zero means at least one failed. `run_all.py` aggregates.
- Scripts are **idempotent** where possible — running twice against the same DB should not cause duplicate data issues.
- Scripts do **not** wipe the database. To re-run from scratch, truncate tables or use a fresh PostgreSQL instance.
- Performance baselines are **soft** — a script may warn rather than fail if latency exceeds a threshold.

## What the suite does not cover

- Multi-user scenarios (darkmem is single-admin)
- Cross-browser UI testing beyond what a headless Playwright run provides
- Chaos / fault injection (network partition, LLM outage mid-flight)
- Load testing beyond the baseline ~100 operations

See `test-plan.md` section "Out of scope" for details.
