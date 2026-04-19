"""Run the historical LLM champion (sorc/qwen3.5-claude-4.6-opus-q4:4b,
json/A prompt) against a stratified sample of the 2k v2 test split.

Scores with extraction_eval.metrics (the lenient scorer the historical 0.913
was measured under) so the number is directly comparable.

Output: runs/2026-04-17-push-to-95/llm_champion_on_v2_<N>.json with mean
entity/rel P/R/F1 and per-row metrics.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "docs" / "e2e" / "scripts"))

from extraction_eval.metrics import AggregatedMetrics, score_example


TEST_PATH = ROOT / "data" / "splits" / "test.jsonl"
OUT_DIR = ROOT / "runs" / "2026-04-17-push-to-95"
OLLAMA_URL = "http://localhost:11434"


PROMPT_A = """You are an entity and relationship extraction engine. Read the text and emit STRICT JSON with this exact shape:

{
  "entities": [{"name": "<surface>", "type": "<one of the allowed types>"}],
  "relationships": [{"source": "<entity name>", "target": "<entity name>", "type": "<one of the allowed relation types>"}],
  "memory_type": "<one of: fact, decision, preference, problem, reference, architecture, milestone>"
}

ENTITY TYPES (pick one):
technology, service, library, database, framework, protocol, algorithm, project, language, platform, infrastructure, file, command, error, config, pattern, api, person, place, organization, event, date, food, activity, goal, emotion, hobby, concept, theory, publication, method, finding, claim, field, tool

RELATION TYPES (pick one):
USES, DEPENDS_ON, REPLACES, IMPROVES_ON, IS_A, HAS_PART, COMMUNICATES_WITH, KNOWS, LOCATED_IN, HAPPENED_ON, CAUSES, RELATED_TO, DEPLOYED_ON, PRODUCES, IMPLEMENTS, FIXES, CONFIGURES, EXTENDS, LIVES_IN, WORKS_AT, VISITED, FEELS_ABOUT, PLANS_TO, PREFERS, SUPPORTS, CONTRADICTS, BUILDS_ON, AUTHORED_BY, PUBLISHED_IN, APPLIES_TO

Rules:
1. Extract SPECIFIC named things (tools, algorithms, services, people, projects). Do NOT extract generic nouns.
2. Deduplicate abbreviations (use the full form if both appear).
3. Every relationship's source and target MUST appear in the entities array.
4. Return ONLY the JSON object, no prose, no markdown fences.

Text to extract from:
"""


def load_and_sample(n: int, seed: int) -> list[dict]:
    rows: list[dict] = []
    with TEST_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    by_mt: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_mt[r.get("memory_type", "?")].append(r)
    rng = random.Random(seed)
    for k in by_mt:
        rng.shuffle(by_mt[k])
    total = len(rows)
    sampled: list[dict] = []
    for mt, bucket in by_mt.items():
        share = int(round(len(bucket) / total * n))
        sampled.extend(bucket[:share])
    rng.shuffle(sampled)
    return sampled[:n]


def call_ollama(model: str, text: str, timeout: float = 60.0) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT_A + text}],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0, "num_gpu": 999, "num_ctx": 4096},
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{OLLAMA_URL}/api/chat", json=body)
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        content_fix = content.strip().strip("```json").strip("```").strip()
        try:
            parsed = json.loads(content_fix)
        except Exception:
            parsed = {"_error": f"json_parse_failed: {content[:200]}",
                      "entities": [], "relationships": [], "memory_type": "fact"}
    return parsed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="sorc/qwen3.5-claude-4.6-opus-q4:4b")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    sample = load_and_sample(args.n, args.seed)
    print(f"Loaded {len(sample)} rows from 2k v2 test split (stratified by memory_type, seed={args.seed})", flush=True)
    print(f"Running model: {args.model}", flush=True)

    agg = AggregatedMetrics()
    per_row: list[dict] = []
    t0 = time.perf_counter()
    shape_fail = 0
    for i, row in enumerate(sample):
        predicted = call_ollama(args.model, row["text"])
        if "_error" in predicted:
            shape_fail += 1
        gold_ents = [{"name": e["name"], "type": e["type"]} for e in row.get("entities") or []]
        gold_rels = [{"source": r["source"], "target": r["target"], "type": r["type"]} for r in row.get("relationships") or []]
        m = score_example(
            example_id=row["id"], tier=row.get("domain", ""), topic=row.get("domain", ""),
            gold_entities=gold_ents, gold_relationships=gold_rels,
            gold_memory_type=row.get("memory_type", "fact"),
            predicted=predicted,
        )
        agg.add(m)
        per_row.append({
            "id": row["id"],
            "entity_p": m.entity_pr.precision, "entity_r": m.entity_pr.recall,
            "rel_p": m.rel_pr.precision, "rel_r": m.rel_pr.recall,
            "type_acc": m.type_accuracy,
        })
        if (i + 1) % 25 == 0:
            ent_f1 = agg.entity_f1()
            rel_f1 = agg.rel_f1()
            print(f"  [{i+1}/{len(sample)}] running ent F1={ent_f1:.3f} rel F1={rel_f1:.3f}", flush=True)
    elapsed = time.perf_counter() - t0

    summary = {
        "model": args.model,
        "n": len(sample),
        "seed": args.seed,
        "elapsed_s": elapsed,
        "ms_per_row_mean": elapsed / max(1, len(sample)) * 1000,
        "shape_failures": shape_fail,
        "entity_f1": agg.entity_f1(),
        "entity_precision_mean": statistics.mean(agg.entity_precision) if agg.entity_precision else 0.0,
        "entity_recall_mean": statistics.mean(agg.entity_recall) if agg.entity_recall else 0.0,
        "rel_f1": agg.rel_f1(),
        "rel_precision_mean": statistics.mean(agg.rel_precision) if agg.rel_precision else 0.0,
        "rel_recall_mean": statistics.mean(agg.rel_recall) if agg.rel_recall else 0.0,
        "type_accuracy_mean": statistics.mean(agg.type_accuracy) if agg.type_accuracy else 0.0,
        "direction_rate_mean": statistics.mean(agg.direction_rate) if agg.direction_rate else 0.0,
        "memtype_accuracy_mean": statistics.mean(agg.memtype_accuracy) if agg.memtype_accuracy else 0.0,
    }

    out_path = args.out or (OUT_DIR / f"llm_champion_on_v2_n{args.n}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"summary": summary, "per_row": per_row}, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)
    for k, v in summary.items():
        print(f"  {k}: {v}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
