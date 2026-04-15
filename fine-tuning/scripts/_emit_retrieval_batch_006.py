"""One-off emitter for retrieval top-up batch-006 — acronym query kind.

Reads shared rows at line offsets SHARED_OFFSET..SHARED_OFFSET+99 from
data/v2/shared/shared.jsonl and writes 100 retrieval rows to
data/v2/retrieval/batch_006.tmp.jsonl. Each row's query rewrites a concept
from the source text using an acronym or abbreviated form so retrieval has
to bridge the short form to the full term.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
OUT = ROOT / "data" / "v2" / "retrieval" / "batch_006.tmp.jsonl"

ID_OFFSET = 500
SHARED_OFFSET = 500
QUERY_KIND = "acronym"

# One acronym-style query per source row, in the same order as the 100 lines
# starting at SHARED_OFFSET. Each query is 3-15 words and uses an acronym,
# initialism, or abbreviation that maps onto a concept in the source memory.
QUERIES: list[str] = [
    # shared-00501 — Flink RocksDB, GC pauses
    "which SB for Flink avoids GC pauses on JM",
    # shared-00502 — Prometheus remote_write, Mimir, multi-tenant
    "PromQL LTS via Mimir MT ingest fleet",
    # shared-00503 — Thanos rejected for Mimir hash-ring
    "Mimir HR ingest vs Thanos sidecar TSDB upload",
    # shared-00504 — Ceph RGW, NVMe OSD, EC
    "Ceph RGW hot NVMe OSD vs EC cold pool",
    # shared-00505 — MinIO S3 multipart abort
    "MinIO vs S3 MPU abort API drift",
    # shared-00506 — Vault dynamic Postgres secrets
    "Vault dyn PG role STS per app instance",
    # shared-00507 — SOPS age vs PGP
    "SOPS age key replaces PGP for VCS secrets",
    # shared-00508 — MySQL 8 vs MariaDB replication
    "MySQL 8 vs MariaDB repl for write-heavy shards",
    # shared-00509 — MongoDB change streams, search indexer
    "Mongo CS drives search IDX resume-token RS failover",
    # shared-00510 — noise
    "IDK give me a sec BRB dashboard",
    # shared-00511 — etcd compaction defrag cron
    "etcd KV compact vs defrag cron drift latency",
    # shared-00512 — Helm vs Kustomize
    "Kustomize vs Helm YAML tmpl env-specific pain",
    # shared-00513 — Crossplane RDS Kubernetes drift
    "Crossplane RDS as K8s CRD drift detect",
    # shared-00514 — Gatekeeper OPA admission
    "OPA GK admission blocks priv hostPath without label",
    # shared-00515 — Falco runtime detection
    "Falco syscall IDS caught miner drop ROI",
    # shared-00516 — Trivy CI SBOM OCI
    "Trivy CI SBOM pushed to OCI artifact repo",
    # shared-00517 — SLSA provenance payments
    "SLSA L3 attained for payments svc hardened runners",
    # shared-00518 — Bazel to Nix
    "Nix over Bazel for hermetic BLD toolchain",
    # shared-00519 — Tilt replaces Makefiles Go
    "Tilt vs Makefile inner-loop LU for Go binaries",
    # shared-00520 — Skaffold over Tilt CI previews
    "Skaffold over Tilt for CI preview env pipeline",
    # shared-00521 — Traefik v3 Docker provider
    "Traefik v3 Docker provider silent 404 fix",
    # shared-00522 — Caddy autocert DNS-01 Cloudflare
    "Caddy DNS-01 CF skips port 80 for RP TLS",
    # shared-00523 — HAProxy resolver DNS Consul
    "HAProxy dyn resolver TTL vs Consul flap DNS",
    # shared-00524 — io_uring log shipper ARM64
    "io_uring on ARM64 halves syscall ovhd log ship",
    # shared-00525 — Pixie eBPF profiler
    "Pixie eBPF prof finds noisy HC loop",
    # shared-00526 — OpenTelemetry Collector tail sampling PII
    "OTel Collector proc tail sample PII redact vendor export",
    # shared-00527 — Zig cross-compile Linux libc
    "Zig xcompile Linux libc matrix fast BLD",
    # shared-00528 — C++20 modules replace PCH
    "C++20 mods over PCH in render core IB",
    # shared-00529 — LLVM ThinLTO vs full LTO
    "LLVM ThinLTO vs full LTO release BLD size cut",
    # shared-00530 — Swift actors concurrency
    "Swift actor concurrency ends DB mutable-state races",
    # shared-00531 — Kotlin coroutines vs Project Reactor Android
    "KT coroutines over PR on AND client",
    # shared-00532 — Lua OpenResty edge rate limit
    "Lua OR edge RL coroutine footprint stable",
    # shared-00533 — Cilium vs kube-proxy eBPF
    "Cilium eBPF DP replaces KP cuts P99",
    # shared-00534 — noise
    "TTY tailing the logs AFK",
    # shared-00535 — Linkerd mTLS cert rotation
    "Linkerd wl cert rotation 24h TA",
    # shared-00536 — Sidekiq Ruby Redis
    "Sidekiq swaps Resque on RB jobs Redis-backed",
    # shared-00537 — BullMQ Node.js queue
    "BullMQ on NodeJS delay priority queue Redis",
    # shared-00538 — Pub/Sub vs SQS global fan-out
    "GCP PS over SQS for global fan-out ALO",
    # shared-00539 — SNS SQS fan-out billing
    "SNS to SQS fan-out billing retry ARC analytics",
    # shared-00540 — AWS IAM Identity Center SSO
    "AWS IdC SSO consolidation for eng consoles date",
    # shared-00541 — GitHub Advanced Security SQLi
    "GHAS CodeQL caught SQLi in admin via MQ",
    # shared-00542 — Renovate vs Dependabot
    "Renovate over Dependabot weekday-only PR schedule",
    # shared-00543 — sigstore cosign admission webhook
    "cosign sigstore verify AC webhook blocks unsigned",
    # shared-00544 — Tekton PipelineRun Argo Events
    "Tekton PR triggered via Argo Events on VCS tag",
    # shared-00545 — FluxCD Argo CD GitOps
    "Flux vs Argo CD split for plat vs app GitOps",
    # shared-00546 — Karpenter vs Cluster Autoscaler EC2
    "Karpenter vs CA cuts EC2 spend bin-pack",
    # shared-00547 — Descheduler Karpenter topology
    "Descheduler TSC evict with Karpenter for hygiene",
    # shared-00548 — Node problem detector Alertmanager NVMe
    "NPD DS events to AM catch NVMe wear",
    # shared-00549 — Velero DR RTO
    "Velero BR drill hits 4h RTO target",
    # shared-00550 — Citus TimescaleDB online rebalance
    "Citus shard online rebal while TSDB HT ingest",
    # shared-00551 — VS Code remote container node_modules volume
    "VSC RC dev loop NM named vol fix",
    # shared-00552 — Copilot vs Claude refactor
    "GH Copilot vs Claude RFC boundary adherence",
    # shared-00553 — pair programming AI refactor
    "PP with AI during RFC keeps ratchet",
    # shared-00554 — LSP memory cap monorepo
    "LSP mem cap 2GB to 4GB fixes MR freeze",
    # shared-00555 — IntelliJ Ruff Java
    "IntelliJ IDE vs Ruff bug coverage on JV",
    # shared-00556 — static analysis noise budget
    "SAST noise budget 50 open findings per repo",
    # shared-00557 — TypeScript project references
    "TS PR incremental BLD 90s to 22s win",
    # shared-00558 — Turborepo S3 remote cache
    "Turborepo RC on S3 SU gateway cost zero",
    # shared-00559 — esbuild vs swc
    "esbuild over swc for LIB plugin DX",
    # shared-00560 — noise
    "BRB grabbing another cup ASAP",
    # shared-00561 — Vitest browser mode Chromium
    "Vitest BM real Chromium for UI snap parity",
    # shared-00562 — Playwright component JSDOM
    "PW CT over JSDOM harness a11y asserts",
    # shared-00563 — Jest to Vitest ESM
    "Jest to Vitest swap reveals ESM boundary issues",
    # shared-00564 — PyCharm conditional breakpoints
    "PyCharm cond BP for noisy loop pauses",
    # shared-00565 — rr record-replay C++ segfault
    "rr R&R chases nondet SEGV in C++ SC",
    # shared-00566 — Valgrind DHAT jemalloc
    "VG DHAT finds retained alloc jemalloc hides",
    # shared-00567 — ASAN TSAN nightly
    "ASAN and TSAN nightly CI catch TOCTOU race",
    # shared-00568 — libFuzzer protocol parser
    "libFuzzer on proto parser crashes vs UT",
    # shared-00569 — Hypothesis property-based pagination
    "Hypothesis PBT finds OBO in pagination",
    # shared-00570 — mutmut mutation testing
    "mutmut MT score exposes dead UT files",
    # shared-00571 — Golden-file testing
    "GFT snapshot compare rot on FMT tweaks",
    # shared-00572 — Pydantic v2 TypeAdapter BaseModel
    "Pydantic v2 TA validates DC without BM",
    # shared-00573 — structural pattern matching webhook
    "SPM in webhook dispatcher match on event shape",
    # shared-00574 — poetry PDM Hatch
    "Poetry over PDM or Hatch for new LIB CI",
    # shared-00575 — Rye pyenv
    "Rye replaces pyenv for PY interp mgmt",
    # shared-00576 — tox-uv speedup
    "tox-uv cuts PY test matrix WCT 60 pct",
    # shared-00577 — nox task runner
    "nox over make task runner PY DSL sessions",
    # shared-00578 — just vs make
    "just over make greenfield repos CLI recipes",
    # shared-00579 — terraform fmt pre-commit
    "TF fmt diff churn fix via pre-commit hook",
    # shared-00580 — Spin Kubernetes WASM
    "Spin K8s WASM RT cold start 800 to 40 ms",
    # shared-00581 — Deno npm postinstall
    "Deno npm compat PI script gap workaround",
    # shared-00582 — Bun Yarn lockfile
    "Bun LF unparsable by Yarn blocks swap",
    # shared-00583 — Yarn PnP rollback
    "Yarn PnP IDE resolve without NM rollback date",
    # shared-00584 — Corepack package manager pin
    "Corepack pins PM choice per repo ends drift",
    # shared-00585 — npm workspaces pnpm patch
    "npm WS lacks patch cmd pnpm workaround upstream",
    # shared-00586 — Renovate shared preset auto-merge
    "Renovate shared preset new repo AM on day 1",
    # shared-00587 — lefthook parallel timeout
    "lefthook par group slow step TO serialised fix",
    # shared-00588 — Prettier eslint-plugin-import
    "Prettier imp sort over ESLint plugin import rules",
    # shared-00589 — BiomeJS oxc TypeScript
    "BiomeJS FMT LNT over oxc for new TS repos",
    # shared-00590 — Rolldown Oxc Vite 5
    "Rolldown on Oxc cuts Vite 5 cold BT 40 pct",
    # shared-00591 — esbuild plugin babel env
    "esbuild plugin env strip replaces babel xform-define",
    # shared-00592 — Docker buildx layer cache
    "Docker bx LC split lock vs src copy 4x BT",
    # shared-00593 — devcontainer.json onboarding
    "devcontainer.json shared cuts BE svc OB time",
    # shared-00594 — nix-shell Python uv
    "nix-shell over uv alone for repro PY layer hash",
    # shared-00595 — direnv uv-python
    "direnv plus uv-python auto CWD PY activation",
    # shared-00596 — asdf to mise Rust
    "mise replaces asdf RS core polyglot VM",
    # shared-00597 — ARM Macs Linux CI clang Rust
    "AS cross-BLD from Linux CI clang triple RS",
    # shared-00598 — Go 1.22 gorilla-mux
    "Go 1.22 stdlib mux replaces gorilla-mux in API",
    # shared-00599 — WASI component model CLI
    "WASI CM for CLI DBG tool maturity Q3 park",
    # shared-00600 — Obsidian to Logseq
    "Logseq over Obsidian KB BL graph queries date",
]

assert len(QUERIES) == 100, f"expected 100 queries, got {len(QUERIES)}"


def main() -> None:
    with SHARED_PATH.open("r", encoding="utf-8") as f:
        all_lines = f.readlines()

    window = all_lines[SHARED_OFFSET:SHARED_OFFSET + 100]
    assert len(window) == 100, f"expected 100 source rows, got {len(window)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as out:
        for i, (raw, query) in enumerate(zip(window, QUERIES)):
            source = json.loads(raw)
            rid = f"ret-{ID_OFFSET + i + 1:05d}"
            words = len(query.split())
            assert 3 <= words <= 15, f"{rid} query has {words} words: {query!r}"
            row = {
                "id": rid,
                "source_id": source["id"],
                "query": query,
                "positive": source["text"],
                "query_kind": QUERY_KIND,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote {len(QUERIES)} rows to {OUT}")


if __name__ == "__main__":
    main()
