"""LLM relation extraction via Ollama, for apples-to-apples comparison against
fine-tuned rebel heads.

For each gold row supply the text plus the gold entity list to the LLM, ask
for relations using only the 10-type taxonomy, parse JSON, write in the same
pred format as scripts/_infer_relation.py so rebel_pair_rescore.py can score.

Usage:
    python -m scripts.infer_relation_llm \
        --model qwen3.5:4b \
        --gold data/splits/rebel_coding10_test_gold.jsonl \
        --pred runs/relation-llm-qwen4b/pred.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests


ALLOWED_REL_TYPES = {
    "USES", "DEPENDS_ON", "REPLACES", "IS_A", "HAS_PART",
    "DEPLOYED_ON", "CAUSES", "AUTHORED_BY", "HAPPENED_ON", "RELATED_TO",
}


SYSTEM_PROMPT_DEFAULT = (
    "You extract relations between entities in a text. "
    "Use ONLY these 10 relation types:\n"
    "- USES: source uses target (tool, dependency, api call)\n"
    "- DEPENDS_ON: source hard-requires target (version pin, prerequisite)\n"
    "- REPLACES: source is the successor of target (migration away from target)\n"
    "- IS_A: source is a kind of target (taxonomic membership)\n"
    "- HAS_PART: source has target as a component or subsystem\n"
    "- DEPLOYED_ON: source runs on target (host, cluster, IP, device)\n"
    "- CAUSES: source causes/produces/fixes target (effect, output, resolution)\n"
    "- AUTHORED_BY: source was created by target (person, org, team)\n"
    "- HAPPENED_ON: source event/person on target (date, place)\n"
    "- RELATED_TO: catch-all (preferences, plans, contradictions, supports)\n"
    "\n"
    "Rules:\n"
    "- Output strict JSON: {\"relationships\": [{\"source\": \"name\", \"target\": \"name\", \"type\": \"TYPE\"}]}\n"
    "- `source` and `target` must be EXACT strings from the given Entities list.\n"
    "- Only emit relations that are directly supported by the text.\n"
    "- No self-loops. No explanation. No prose."
)

SYSTEM_PROMPT_OPTIMIZED = (
    "You extract relations between named entities in a coding/engineering memory. "
    "Output strict JSON only: {\"relationships\": [{\"source\": \"name\", \"target\": \"name\", \"type\": \"TYPE\"}]}.\n"
    "\n"
    "TYPE must be exactly one of these 10 (no others):\n"
    "- USES: source invokes/calls/integrates target at runtime (soft dependency).\n"
    "  Example: \"FastAPI uses Pydantic for validation\" -> FastAPI USES Pydantic.\n"
    "- DEPENDS_ON: source HARD-requires target. Fails without it. Version pins, must-have plugins.\n"
    "  Example: \"pg_repack requires a primary key\" -> pg_repack DEPENDS_ON primary key.\n"
    "- REPLACES: source is the newer/successor thing; target is the old thing being replaced.\n"
    "  Direction rule: NEW REPLACES OLD. Example: \"switched from Jenkins to GitHub Actions\" -> GitHub Actions REPLACES Jenkins.\n"
    "- IS_A: source is a kind or implementation of target (true taxonomy, not loose similarity).\n"
    "  Example: \"Ruff is a Python linter\" -> Ruff IS_A linter.\n"
    "- HAS_PART: source is a whole that contains target as a built-in component/subsystem.\n"
    "  Example: \"Postgres ships autovacuum\" -> Postgres HAS_PART autovacuum.\n"
    "- DEPLOYED_ON: source runs/is hosted on target (host, IP, cluster, GPU, device). Target = location.\n"
    "  Example: \"Redis runs on 192.168.0.10\" -> Redis DEPLOYED_ON 192.168.0.10.\n"
    "- CAUSES: source triggers/produces/fixes target (effect, output, resolution).\n"
    "  Example: \"schema drift broke the fraud model\" -> schema drift CAUSES fraud model.\n"
    "- AUTHORED_BY: source was created by target (person, org, team).\n"
    "  Example: \"Kubernetes by Google\" -> Kubernetes AUTHORED_BY Google.\n"
    "- HAPPENED_ON: source (event/person) on target (date/place).\n"
    "  Example: \"DR drill on 2026-03-05\" -> DR drill HAPPENED_ON 2026-03-05.\n"
    "- RELATED_TO: use ONLY for preferences/plans/contradictions/supports that do not fit the other 9.\n"
    "  Example: \"prefer CDK over CloudFormation\" -> CDK RELATED_TO CloudFormation.\n"
    "\n"
    "RULES:\n"
    "1. source and target MUST be exact strings from the Entities list (case-sensitive, character-exact).\n"
    "2. Only emit relations DIRECTLY supported by the text. Do not infer beyond the sentence.\n"
    "3. Prefer fewer, high-confidence relations over many speculative ones. If unsure, omit.\n"
    "4. No self-loops (source != target).\n"
    "5. Disambiguation shortcuts:\n"
    "   - USES vs DEPENDS_ON: pick USES unless text uses words like 'requires', 'needs', 'must', 'prerequisite'.\n"
    "   - CAUSES vs USES: pick CAUSES only for problem/outcome/fix language; USES for routine calls.\n"
    "   - DEPLOYED_ON vs USES: target is a host/IP/cluster for DEPLOYED_ON; a tool/API for USES.\n"
    "   - RELATED_TO is a last resort; try the other 9 first.\n"
    "6. Do NOT emit a relation just because two entities appear together. Text must state the link.\n"
    "7. No prose, no explanation, no markdown. JSON only."
)


SYSTEM_PROMPTS = {
    "default": SYSTEM_PROMPT_DEFAULT,
    "optimized": SYSTEM_PROMPT_OPTIMIZED,
}
SYSTEM_PROMPT = SYSTEM_PROMPT_DEFAULT  # backward-compat


def build_prompt(text: str, entities: list[dict]) -> str:
    ent_str = "\n".join(f"- {e['name']} ({e.get('type', 'entity')})" for e in entities)
    return (
        f"Text: {text}\n\n"
        f"Entities:\n{ent_str}\n\n"
        f"Extract all supported relations between these entities. Output JSON only."
    )


def call_ollama(endpoint: str, model: str, system: str, prompt: str,
                timeout: int = 120, num_ctx: int = 2048, think: bool = False) -> str:
    r = requests.post(
        f"{endpoint}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "think": think,
            "options": {"temperature": 0.0, "num_ctx": num_ctx},
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def parse_triples(raw: str, allowed_names: set[str]) -> list[dict]:
    stripped = raw.strip()
    if stripped.startswith("```"):
        first = stripped.find("\n")
        last = stripped.rfind("```")
        if first != -1 and last > first:
            stripped = stripped[first + 1:last].strip()
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    if isinstance(obj, list):
        rels = obj
    elif isinstance(obj, dict):
        rels = obj.get("relationships") or obj.get("triples") or obj.get("relations") or []
    else:
        return []
    if not isinstance(rels, list):
        return []
    out: list[dict] = []
    for r in rels:
        if not isinstance(r, dict):
            continue
        src = r.get("source") or r.get("subject") or r.get("head")
        tgt = r.get("target") or r.get("object") or r.get("tail")
        rtype = r.get("type") or r.get("relation") or r.get("predicate")
        if not (src and tgt and rtype):
            continue
        if src not in allowed_names or tgt not in allowed_names:
            continue
        if src == tgt:
            continue
        rtype_upper = str(rtype).upper()
        if rtype_upper not in ALLOWED_REL_TYPES:
            continue
        out.append({"source": src, "target": tgt, "type": rtype_upper})
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--gold", required=True, type=Path)
    p.add_argument("--pred", required=True, type=Path)
    p.add_argument("--endpoint", default="http://localhost:11434")
    p.add_argument("--limit", type=int, default=0, help="Process only first N rows (debug)")
    p.add_argument("--num-ctx", type=int, default=2048)
    p.add_argument("--prompt-variant", choices=list(SYSTEM_PROMPTS.keys()), default="default")
    args = p.parse_args()
    system_prompt = SYSTEM_PROMPTS[args.prompt_variant]

    rows = [json.loads(line) for line in args.gold.open("r", encoding="utf-8") if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    print(f"Scoring {len(rows)} rows with {args.model} at {args.endpoint}", flush=True)

    args.pred.parent.mkdir(parents=True, exist_ok=True)
    latencies: list[float] = []
    n_ok = 0
    n_bad = 0
    with args.pred.open("w", encoding="utf-8") as fout:
        for i, row in enumerate(rows):
            text = row["text"]
            entities = row.get("entities") or []
            names = {e["name"] for e in entities}
            prompt = build_prompt(text, entities)
            t0 = time.time()
            try:
                raw = call_ollama(args.endpoint, args.model, system_prompt, prompt, num_ctx=args.num_ctx)
                triples = parse_triples(raw, names)
                n_ok += 1
            except Exception as e:
                print(f"  row {i} error: {e}", flush=True)
                triples = []
                n_bad += 1
            latencies.append((time.time() - t0) * 1000)
            fout.write(json.dumps({"id": row["id"], "relationships": triples}) + "\n")
            fout.flush()
            if (i + 1) % 25 == 0 or i + 1 == len(rows):
                mean = sum(latencies) / len(latencies)
                print(f"  [{i+1}/{len(rows)}] ok={n_ok} bad={n_bad} mean {mean:.0f} ms", flush=True)

    latencies.sort()
    mean = sum(latencies) / len(latencies) if latencies else 0.0
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    side = {
        "model": args.model,
        "endpoint": args.endpoint,
        "rows": len(rows),
        "n_ok": n_ok,
        "n_bad": n_bad,
        "latency_ms_per_row_mean": mean,
        "latency_ms_per_row_p50": p50,
        "latency_ms_per_row_p95": p95,
    }
    side_path = args.pred.parent / "pred.runtime.json"
    side_path.write_text(json.dumps(side, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} preds to {args.pred}")
    print(f"  mean {mean:.1f} ms, p50 {p50:.1f}, p95 {p95:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
