"""Prompt × model sweep for LLM entity extraction against the 2k v2 test set.

Primary metric: entity-pair F1 (normalized_name + type must match; offsets ignored).

Caches per-row predictions at runs/2026-04-17-push-to-95/sweep_cache/<model_safe>/<variant>/<id>.json
so a single (model, variant, row) run never repeats — re-running picks up where it left off.

Usage:
    python -m scripts._prompt_sweep --n 100 --seed 42 \
        --models sorc/qwen3.5-claude-4.6-opus-q4:4b qwen3.5:4b \
        --variants A B C D E
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "docs" / "e2e" / "scripts"))

from scripts.eval_entity_pair import score as pair_score

TEST_PATH = ROOT / "data" / "splits" / "test.jsonl"
OUT_DIR = ROOT / "runs" / "2026-04-17-push-to-95"
CACHE_DIR = OUT_DIR / "sweep_cache"
OLLAMA_URL = "http://localhost:11434"

ENTITY_TYPES = [
    "technology", "service", "library", "database", "framework", "protocol",
    "algorithm", "project", "language", "platform", "infrastructure",
    "file", "command", "error", "config", "pattern", "api",
    "person", "place", "organization", "event", "date", "food",
    "activity", "goal", "emotion", "hobby",
    "concept", "theory", "publication", "method", "finding", "claim", "field", "tool",
]

# ── Prompt variants ───────────────────────────────────────────────────────

PROMPT_HEADER = """You read text and emit STRICT JSON with this exact shape:

{
  "entities": [{"name": "<surface in text>", "type": "<one allowed type>"}],
  "relationships": [{"source": "<entity name>", "target": "<entity name>", "type": "<one allowed type>"}],
  "memory_type": "<one of: fact, decision, preference, problem, reference, architecture, milestone>"
}

ENTITY TYPES (pick exactly one per entity, from this list):
technology, service, library, database, framework, protocol, algorithm, project, language, platform, infrastructure, file, command, error, config, pattern, api, person, place, organization, event, date, food, activity, goal, emotion, hobby, concept, theory, publication, method, finding, claim, field, tool

RELATION TYPES:
USES, DEPENDS_ON, REPLACES, IMPROVES_ON, IS_A, HAS_PART, COMMUNICATES_WITH, KNOWS, LOCATED_IN, HAPPENED_ON, CAUSES, RELATED_TO, DEPLOYED_ON, PRODUCES, IMPLEMENTS, FIXES, CONFIGURES, EXTENDS, LIVES_IN, WORKS_AT, VISITED, FEELS_ABOUT, PLANS_TO, PREFERS, SUPPORTS, CONTRADICTS, BUILDS_ON, AUTHORED_BY, PUBLISHED_IN, APPLIES_TO
"""


# Variant A — original champion style: strong negative rules + compact positives
PROMPT_A = PROMPT_HEADER + """
RULES — check NEGATIVE rules first, then POSITIVE:

NEGATIVE (when in doubt, omit):
1. Do NOT extract generic nouns (database, function, parameter, format, value, system, service, user, client, server, endpoint, error, result, config, setting, tool, platform, component, module, version).
2. Do NOT extract enumeration items from lists: 'name patterns (main, run, start)' — do not extract main/run/start.
3. Do NOT extract article phrases: 'a database', 'the system', 'this feature'.
4. Do NOT extract status words (DEBUG, INFO, WARNING, ERROR), HTTP methods (GET, POST), or Python builtins (list, dict, str, int).
5. Do NOT extract file extensions or generic filenames.

POSITIVE:
1. Extract SPECIFIC named things: pgvector, Redis, Leiden, JWT, Ollama, darkmem, Einstein, London, Python.
2. Deduplicate abbreviations: 'Reciprocal Rank Fusion (RRF)' → extract RRF only if used standalone; if both appear extract the full form only.
3. Every relationship source and target MUST appear in entities.

Return ONLY the JSON object. No prose, no markdown fences.

Text:
"""


# Variant D — prior winner, B+C combined (examples + 10-type decision tree)
PROMPT_D = PROMPT_HEADER + """
TYPE DECISION TREE (pick the FIRST rule that matches):
- Stored data system (Postgres, Redis, MongoDB, Qdrant, etcd) → database
- Running deployed system reached over a network (Grafana, Nginx, Jenkins, Vault, Ollama) → service
- Hosted cloud environment or VM (EC2, Kubernetes, Docker, AWS) → platform or infrastructure
- Code framework you build inside (Django, FastAPI, Rails, React, Hugo) → framework
- Installable package you import (NetworkX, httpx, pgvector, Tree-sitter) → library
- Programming language (Python, Go, Rust, TypeScript) → language
- Network or data format protocol (HTTP, JWT, SSE, gRPC) → protocol
- Named algorithm (BFS, Leiden, RRF, HS256) → algorithm
- Repository or product name ('darkmem', 'gitnexus') → project
- Otherwise → concept

Rules:
1. Extract SPECIFIC named things; skip generic nouns and enumeration items.
2. Deduplicate abbreviations.
3. Every relationship source and target MUST appear in entities.

Example — 'We switched from Jenkins to GitHub Actions.'
{"entities":[{"name":"Jenkins","type":"service"},{"name":"GitHub Actions","type":"service"}],"relationships":[{"source":"GitHub Actions","target":"Jenkins","type":"REPLACES"}],"memory_type":"decision"}

Example — 'darkmem uses Tree-sitter for parsing.'
{"entities":[{"name":"darkmem","type":"project"},{"name":"Tree-sitter","type":"library"}],"relationships":[{"source":"darkmem","target":"Tree-sitter","type":"USES"}],"memory_type":"fact"}

Example — 'I had coffee this morning.'
{"entities":[],"relationships":[],"memory_type":"fact"}

Return ONLY the JSON object. No prose, no markdown fences.

Text:
"""


# Variant E — full 35-type decision tree tailored to our taxonomy
PROMPT_E = PROMPT_HEADER + """
TYPE DECISION TREE (pick the FIRST rule that matches the entity):
- Stored data system: Postgres, Redis, MongoDB, Qdrant, etcd, ClickHouse, Elasticsearch, Valkey → database
- Running deployed system over a network: Grafana, Nginx, Jenkins, Vault, Ollama, Kafka, RabbitMQ, GitHub Actions → service
- Cloud environment or VM: EC2, Kubernetes, Docker, AWS, GCP, Azure → platform (cloud brand) or infrastructure (generic runtime)
- Code framework you build inside: Django, FastAPI, Rails, React, Hugo, Flask, Spring, Celery → framework
- Installable package imported in code: NetworkX, httpx, pgvector, Tree-sitter, PyJWT, Argon2, FAISS, requests → library
- Programming language: Python, Go, Rust, TypeScript, JavaScript, Java, C++ → language
- Network/data/auth protocol: HTTP, HTTPS, JWT, SSE, gRPC, mTLS, OAuth2, WebSocket, JSON-RPC → protocol
- Named algorithm: BFS, Leiden, RRF, HS256, PageRank, HNSW, PKCE → algorithm
- Codebase or product name used as owner/project: darkmem, gitnexus, mempalace, specific repo names → project
- A specific API endpoint, SDK, or service surface: 'Stripe API', '/api/v1/search' → api
- A file path or filename: 'auth.py', 'config.yaml', 'postgresql.conf' → file
- A CLI command: 'ls -la', 'git reset --hard', 'kubectl apply' → command
- An error code or exception class: '500 errors', 'ConnectionTimeout', 'OOMKilled' → error
- A configuration key/value/setting: 'max_connections=200', 'num_gpu=999', 'TTL=60' → config
- A software pattern/paradigm: 'strategy pattern', 'ports and adapters', 'CQRS' → pattern
- A named technology category (when it isn't a specific product): 'vector search', 'zero-knowledge proofs' → technology
- A person by name: Alice, Einstein → person
- A place (city, country, region): London, SF, Europe → place
- An organization/company: OpenAI, MIT, Anthropic → organization
- An event: DEFCON, Oscars, a specific birthday party → event
- A date or relative time: '2026-01-01', 'last Tuesday', 'Q1 2026' → date
- A food item: coffee, pasta, biryani → food
- An activity (the DOING of it): running, meal prep, sparring → activity
- A stated goal: 'lose 10 pounds', 'ship v2' → goal
- An emotion: happy, frustrated, anxious → emotion
- A hobby (named repeating interest): photography, woodworking → hobby
- A scientific theory: 'general relativity', 'plate tectonics' → theory
- A publication (book, paper, article): 'Attention Is All You Need' → publication
- A named method/procedure in science or practice: 'ablation study', 'gradient descent' → method
- A specific research finding: 'the transformer scales with data' → finding
- A claim or assertion: 'LLMs plateau at 10T tokens' → claim
- A field/discipline: 'machine learning', 'topology' → field
- A general tool (screwdriver, whisk, Git): → tool
- Otherwise, last resort → concept

Rules:
1. Extract SPECIFIC named things; skip generic nouns, enumeration items, article phrases.
2. Deduplicate abbreviations — prefer the full form when both appear.
3. Every relationship source and target MUST appear in entities.
4. memory_type choice: decision (explicit choice made), preference (stated liking), problem (bug/issue), architecture (structural description), milestone (dated accomplishment), reference (citation to external), else fact.

Example — 'We switched from Jenkins to GitHub Actions for CI.'
{"entities":[{"name":"Jenkins","type":"service"},{"name":"GitHub Actions","type":"service"}],"relationships":[{"source":"GitHub Actions","target":"Jenkins","type":"REPLACES"}],"memory_type":"decision"}

Example — 'darkmem uses Tree-sitter for parsing and NetworkX for graphs.'
{"entities":[{"name":"darkmem","type":"project"},{"name":"Tree-sitter","type":"library"},{"name":"NetworkX","type":"library"}],"relationships":[{"source":"darkmem","target":"Tree-sitter","type":"USES"},{"source":"darkmem","target":"NetworkX","type":"USES"}],"memory_type":"fact"}

Example — 'Laura works at Netlify as a principal engineer.'
{"entities":[{"name":"Laura","type":"person"},{"name":"Netlify","type":"organization"}],"relationships":[{"source":"Laura","target":"Netlify","type":"WORKS_AT"}],"memory_type":"fact"}

Example — 'I had coffee this morning.'
{"entities":[{"name":"coffee","type":"food"}],"relationships":[],"memory_type":"fact"}

Return ONLY the JSON object. No prose, no markdown fences.

Text:
"""


# Variant F — E + chain-of-thought reasoning (ask the model to plan before emitting)
PROMPT_F = PROMPT_E.replace(
    "Return ONLY the JSON object. No prose, no markdown fences.",
    "First, internally decide which spans are specific named things (ignore generic nouns) and which type "
    "each one maps to by walking the decision tree. Then emit ONLY the JSON object as your response."
)


PROMPTS = {
    "A": PROMPT_A,
    "D": PROMPT_D,
    "E": PROMPT_E,
    "F": PROMPT_F,
}


# ── Runner ────────────────────────────────────────────────────────────────

def safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


def stratified_sample(n: int, seed: int) -> list[dict]:
    rows = [json.loads(l) for l in TEST_PATH.open("r", encoding="utf-8") if l.strip()]
    by = defaultdict(list)
    for r in rows:
        by[r.get("memory_type", "?")].append(r)
    rng = random.Random(seed)
    for k in by:
        rng.shuffle(by[k])
    total = len(rows)
    out = []
    for mt, bucket in by.items():
        share = int(round(len(bucket) / total * n))
        out.extend(bucket[:share])
    rng.shuffle(out)
    return out[:n]


def call_ollama(model: str, prompt: str, text: str, timeout: float = 120.0) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt + text}],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0, "num_gpu": 999, "num_ctx": 4096},
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{OLLAMA_URL}/api/chat", json=body)
        r.raise_for_status()
        content = r.json().get("message", {}).get("content", "") or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        fixed = content.strip()
        for fence in ("```json", "```"):
            fixed = fixed.removeprefix(fence).removesuffix(fence).strip()
        try:
            return json.loads(fixed)
        except Exception:
            return {"_error": "json_parse_failed", "entities": [], "relationships": [], "memory_type": "fact"}


def run_cell(model: str, variant: str, rows: list[dict]) -> list[dict]:
    cache = CACHE_DIR / safe_name(model) / variant
    cache.mkdir(parents=True, exist_ok=True)
    prompt = PROMPTS[variant]
    preds: list[dict] = []
    latencies: list[float] = []
    for i, row in enumerate(rows):
        cache_file = cache / f"{row['id']}.json"
        if cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            preds.append({"id": row["id"], **cached["pred"]})
            latencies.append(cached.get("latency_ms", 0.0))
            continue
        t0 = time.perf_counter()
        pred = call_ollama(model, prompt, row["text"])
        dt = (time.perf_counter() - t0) * 1000
        cache_file.write_text(json.dumps({"pred": pred, "latency_ms": dt}), encoding="utf-8")
        preds.append({"id": row["id"], **pred})
        latencies.append(dt)
        if (i + 1) % 10 == 0:
            print(f"    [{model} / {variant}] {i+1}/{len(rows)} rows", flush=True)
    return preds, latencies


def score_cell(gold_rows: list[dict], preds: list[dict]) -> dict:
    pred_index = {p["id"]: p for p in preds}
    return pair_score(gold_rows, pred_index)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--models", nargs="+", required=True)
    p.add_argument("--variants", nargs="+", default=["A", "D", "E", "F"])
    p.add_argument("--out", type=Path, default=OUT_DIR / "prompt_sweep.json")
    args = p.parse_args()

    sample = stratified_sample(args.n, args.seed)
    print(f"Sampled {len(sample)} rows (seed={args.seed}, stratified by memory_type)", flush=True)

    leaderboard: list[dict] = []
    for model in args.models:
        for variant in args.variants:
            print(f"\n=== model={model} / variant={variant} ===", flush=True)
            t0 = time.perf_counter()
            preds, latencies = run_cell(model, variant, sample)
            elapsed = time.perf_counter() - t0
            metrics = score_cell(sample, preds)
            row = {
                "model": model,
                "variant": variant,
                "n": len(sample),
                "entity_pair_f1": metrics["micro_f1"],
                "entity_pair_precision": metrics["micro_precision"],
                "entity_pair_recall": metrics["micro_recall"],
                "name_recall": metrics["components"]["name_recall"],
                "type_accuracy_given_name": metrics["components"]["type_accuracy_given_name"],
                "n_pred_entities": metrics["n_pred_entities"],
                "n_gold_entities": metrics["n_gold_entities"],
                "ms_per_row_mean": statistics.mean(latencies) if latencies else 0.0,
                "elapsed_s": elapsed,
            }
            leaderboard.append(row)
            print(
                f"  -> pair F1 {row['entity_pair_f1']:.3f} "
                f"(P {row['entity_pair_precision']:.3f}, R {row['entity_pair_recall']:.3f}) "
                f"name-recall {row['name_recall']:.3f} "
                f"type-acc {row['type_accuracy_given_name']:.3f} "
                f"mean {row['ms_per_row_mean']:.0f} ms", flush=True,
            )

    leaderboard.sort(key=lambda r: -r["entity_pair_f1"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"sample_n": args.n, "seed": args.seed, "leaderboard": leaderboard}, indent=2), encoding="utf-8")
    print(f"\nWrote {args.out}", flush=True)
    print("\nLeaderboard (entity-pair F1, best first):")
    print(f"  {'model':<50} {'variant':<8} {'F1':>6} {'P':>6} {'R':>6} {'name-R':>7} {'type-A':>7} {'ms/row':>8}")
    for r in leaderboard:
        print(
            f"  {r['model']:<50} {r['variant']:<8} "
            f"{r['entity_pair_f1']:.3f}  {r['entity_pair_precision']:.3f}  {r['entity_pair_recall']:.3f}  "
            f"{r['name_recall']:.3f}   {r['type_accuracy_given_name']:.3f}  "
            f"{int(r['ms_per_row_mean']):>7}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
