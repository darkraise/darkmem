"""One-off emitter for classification top-up batch-011 — short_ambiguous mode, technical slice.

Writes 100 rows to data/v2/classification/batch_011.tmp.jsonl with ids class-01001..01100.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_011.tmp.jsonl"
ID_OFFSET = 1000

# (text, domain, memory_type) — no pair_id
ROWS: list[tuple[str, str, str]] = [
    # --- fact (~14) ---
    ("Redis listens on port 6379 by default.", "technical", "fact"),
    ("Postgres 16 ships with logical replication built in.", "technical", "fact"),
    ("GPT-4 context window is 128k tokens.", "ai_coding", "fact"),
    ("Docker images are immutable once built.", "technical", "fact"),
    ("Kubernetes pods share a network namespace.", "technical", "fact"),
    ("Node 20 is the current LTS release.", "technical", "fact"),
    ("Python 3.12 removed distutils from the stdlib.", "technical", "fact"),
    ("Claude 3.5 Sonnet scores 92% on HumanEval.", "ai_coding", "fact"),
    ("gRPC uses HTTP/2 for transport.", "technical", "fact"),
    ("TLS 1.3 dropped support for RSA key exchange.", "technical", "fact"),
    ("SQLite supports WAL mode since version 3.7.", "technical", "fact"),
    ("Nginx workers default to one per CPU core.", "technical", "fact"),
    ("Embeddings from text-embedding-3-small are 1536 dims.", "ai_coding", "fact"),
    ("Rust edition 2024 stabilized async closures.", "technical", "fact"),

    # --- decision (~14) ---
    ("We'll standardize on pnpm for all repos.", "technical", "decision"),
    ("Going with Postgres over MongoDB for the new service.", "technical", "decision"),
    ("Switching from Jest to Vitest next sprint.", "technical", "decision"),
    ("Team picked Tailwind over styled-components.", "technical", "decision"),
    ("Adopting Claude Code as the default assistant.", "ai_coding", "decision"),
    ("We're dropping IE11 support in v3.", "technical", "decision"),
    ("Chose Traefik instead of Nginx for ingress.", "technical", "decision"),
    ("Moving CI from CircleCI to GitHub Actions.", "technical", "decision"),
    ("We'll use pgvector instead of a separate vector DB.", "ai_coding", "decision"),
    ("Settling on Zod for all runtime validation.", "technical", "decision"),
    ("Going monorepo with Turborepo this quarter.", "technical", "decision"),
    ("We'll prompt-cache on every Claude call.", "ai_coding", "decision"),
    ("Replacing Redux with Zustand in the web app.", "technical", "decision"),
    ("Adopting conventional commits across all repos.", "technical", "decision"),

    # --- preference (~14) ---
    ("I prefer ripgrep over grep.", "technical", "preference"),
    ("I like tabs over spaces.", "technical", "preference"),
    ("Prefer vim bindings in every editor.", "technical", "preference"),
    ("I'd rather use fish than bash.", "technical", "preference"),
    ("I like small, atomic commits.", "technical", "preference"),
    ("I prefer typed Python via pyright strict.", "technical", "preference"),
    ("Favor prose answers over bullet points.", "ai_coding", "preference"),
    ("I like Claude Opus for planning tasks.", "ai_coding", "preference"),
    ("Prefer pnpm workspaces over Lerna.", "technical", "preference"),
    ("I like dark mode everywhere.", "technical", "preference"),
    ("Prefer TDD for anything non-trivial.", "technical", "preference"),
    ("I like Rust for systems code.", "technical", "preference"),
    ("Prefer explicit imports to wildcards.", "technical", "preference"),
    ("I like zed over VS Code lately.", "technical", "preference"),

    # --- problem (~14) ---
    ("Container OOMs under moderate load.", "technical", "problem"),
    ("Build fails intermittently on CI.", "technical", "problem"),
    ("Hot reload breaks after every dep upgrade.", "technical", "problem"),
    ("Claude responses truncate mid-tool-call.", "ai_coding", "problem"),
    ("Postgres connection pool exhausts at peak.", "technical", "problem"),
    ("Dockerfile layer cache invalidates too often.", "technical", "problem"),
    ("Tests flake on Windows runners.", "technical", "problem"),
    ("Memory leak in the websocket handler.", "technical", "problem"),
    ("Login returns 500 after session refresh.", "technical", "problem"),
    ("Embeddings drift after reindex.", "ai_coding", "problem"),
    ("Nginx returns 502 during rolling deploys.", "technical", "problem"),
    ("Kafka consumer lags behind on Mondays.", "technical", "problem"),
    ("GPU runs out of VRAM at batch size 8.", "ai_coding", "problem"),
    ("Migration stalls on large tenant tables.", "technical", "problem"),

    # --- reference (~14) ---
    ("See RFC 9110 for HTTP semantics.", "technical", "reference"),
    ("Docs live at docs.example.com/api.", "technical", "reference"),
    ("Runbook is in the ops wiki under 'incidents'.", "technical", "reference"),
    ("Refer to CLAUDE.md at the repo root.", "ai_coding", "reference"),
    ("See PEP 695 for the new type syntax.", "technical", "reference"),
    ("Spec is tracked in JIRA ticket PLAT-421.", "technical", "reference"),
    ("Grafana dashboard id is 17856.", "technical", "reference"),
    ("See the Anthropic tool-use guide online.", "ai_coding", "reference"),
    ("ADR-0042 covers the auth redesign.", "technical", "reference"),
    ("API contract in openapi.yaml on main.", "technical", "reference"),
    ("Check the SRE on-call handbook.", "technical", "reference"),
    ("See Postgres docs on vacuum tuning.", "technical", "reference"),
    ("Notebook lives in research/embeddings.ipynb.", "ai_coding", "reference"),
    ("Schema diagram is in docs/architecture.png.", "technical", "reference"),

    # --- architecture (~14) ---
    ("Auth service sits behind the API gateway.", "technical", "architecture"),
    ("Writes fan out to three read replicas.", "technical", "architecture"),
    ("Frontend talks to BFF, not services directly.", "technical", "architecture"),
    ("Events flow through Kafka then into ClickHouse.", "technical", "architecture"),
    ("RAG pipeline retrieves before calling the model.", "ai_coding", "architecture"),
    ("Workers pull jobs from a Redis queue.", "technical", "architecture"),
    ("Each tenant gets its own Postgres schema.", "technical", "architecture"),
    ("Sidecar proxies handle mTLS between pods.", "technical", "architecture"),
    ("Edge caches sit in front of the origin.", "technical", "architecture"),
    ("Agent loop calls tools then summarizes.", "ai_coding", "architecture"),
    ("Search uses a hybrid BM25 plus vectors layer.", "ai_coding", "architecture"),
    ("Control plane is separate from the data plane.", "technical", "architecture"),
    ("All services emit traces to a central collector.", "technical", "architecture"),
    ("Front-end is a TanStack Router SPA.", "technical", "architecture"),

    # --- milestone (~16 to reach 100) ---
    ("v1.0.0 shipped to production.", "technical", "milestone"),
    ("Hit 10k monthly active users last week.", "technical", "milestone"),
    ("Cutover to Postgres 16 is complete.", "technical", "milestone"),
    ("Finished migrating the auth service to Go.", "technical", "milestone"),
    ("Fine-tuning corpus crossed 5000 rows today.", "ai_coding", "milestone"),
    ("GA launch landed yesterday.", "technical", "milestone"),
    ("All repos now run on Node 20.", "technical", "milestone"),
    ("Achieved sub-100ms p99 on the search path.", "technical", "milestone"),
    ("Hit 95% test coverage on the core package.", "technical", "milestone"),
    ("Shipped the first agent-powered feature.", "ai_coding", "milestone"),
    ("Decommissioned the legacy monolith.", "technical", "milestone"),
    ("Zero-downtime deploys now green for 30 days.", "technical", "milestone"),
    ("Finished the security audit remediation.", "technical", "milestone"),
    ("Cut build time in half this quarter.", "technical", "milestone"),
    ("First 1000 paying customers onboarded.", "technical", "milestone"),
    ("Closed out the Q1 reliability roadmap.", "technical", "milestone"),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, domain, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            f.write(
                json.dumps(
                    {"id": row_id, "domain": domain, "text": text, "memory_type": mt},
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
