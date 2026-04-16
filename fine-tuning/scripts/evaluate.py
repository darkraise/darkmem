"""Evaluate fine-tuned GLiNER + REBEL pipeline against the gold corpus.

Runs the two-model extraction pipeline (fine-tuned GLiNER for entities,
fine-tuned REBEL for relationships) and scores against the existing
90-example gold corpus using the extraction_eval metrics.

Usage:
    python -m scripts.evaluate
    python -m scripts.evaluate --gliner-model ./models/gliner-darkmem/best
    python -m scripts.evaluate --rebel-model ./models/rebel-darkmem/best
    python -m scripts.evaluate --cpu
    python -m scripts.evaluate --test-split  # evaluate on fine-tuning test split instead
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "docs" / "e2e" / "scripts"))

from config.domains import ALL_ENTITY_TYPES
from extraction_eval.corpus import GoldExample, load_corpus
from extraction_eval.metrics import score_example, PrecisionRecall

MODELS_DIR = ROOT / "models"
SPLITS_DIR = ROOT / "data" / "splits"
OUTPUT_DIR = ROOT / "eval_results"

DEFAULT_GLINER = str(MODELS_DIR / "gliner-darkmem" / "best")
DEFAULT_REBEL = str(MODELS_DIR / "rebel-darkmem" / "best")

GLINER_THRESHOLD = 0.5


@dataclass
class EvalResult:
    entity_f1: float = 0.0
    entity_precision: float = 0.0
    entity_recall: float = 0.0
    type_accuracy: float = 0.0
    rel_f1: float = 0.0
    rel_precision: float = 0.0
    rel_recall: float = 0.0
    direction_rate: float = 0.0
    gliner_ms: float = 0.0
    rebel_ms: float = 0.0
    total_ms: float = 0.0
    n_examples: int = 0


class FineTunedPipeline:
    """Two-model extraction: GLiNER (entities) + REBEL (relationships)."""

    def __init__(self, gliner_path: str, rebel_path: str, device: str = "cuda"):
        import torch
        from gliner import GLiNER
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.device = device
        print(f"Loading GLiNER from {gliner_path}...", flush=True)
        self.gliner = GLiNER.from_pretrained(gliner_path)
        if device == "cuda" and torch.cuda.is_available():
            self.gliner = self.gliner.to("cuda")

        print(f"Loading REBEL from {rebel_path}...", flush=True)
        self.rebel_tokenizer = AutoTokenizer.from_pretrained(rebel_path)
        self.rebel_model = AutoModelForSeq2SeqLM.from_pretrained(rebel_path)
        if device == "cuda" and torch.cuda.is_available():
            self.rebel_model = self.rebel_model.to("cuda")

        print("Pipeline ready.", flush=True)

    def extract_entities(self, text: str, entity_types: list[str]) -> list[dict]:
        raw = self.gliner.predict_entities(text, entity_types, threshold=GLINER_THRESHOLD)
        entities = []
        seen: set[tuple[str, str]] = set()
        for e in raw:
            key = (e["text"], e["label"])
            if key not in seen:
                seen.add(key)
                entities.append({"name": e["text"], "type": e["label"], "properties": {}})
        return entities

    def extract_relationships(self, text: str, entities: list[dict]) -> list[dict]:
        import torch

        if not entities:
            return []

        ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
        input_text = f"{text} | Entities: {ent_str}"

        inputs = self.rebel_tokenizer(
            input_text, return_tensors="pt", max_length=512, truncation=True,
        )
        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.rebel_model.generate(**inputs, max_length=128, num_beams=5)

        decoded = self.rebel_tokenizer.decode(outputs[0], skip_special_tokens=False)
        return self._parse_triplets(decoded, {e["name"] for e in entities})

    def _parse_triplets(self, text: str, entity_names: set[str]) -> list[dict]:
        relationships = []
        for triplet in text.split("<triplet>"):
            triplet = triplet.strip()
            if not triplet or triplet == "NONE":
                continue
            parts = triplet.split("<subj>")
            if len(parts) != 2:
                continue
            source = parts[0].strip()
            rest = parts[1].split("<obj>")
            if len(rest) != 2:
                continue
            target = rest[0].strip()
            rel_type = rest[1].strip()
            rel_type = rel_type.split("<")[0].strip()
            if source and target and rel_type:
                relationships.append({
                    "source": source, "target": target,
                    "type": rel_type, "properties": {}, "weight": 0.8,
                })
        return relationships

    def extract(self, text: str, entity_types: list[str]) -> dict:
        entities = self.extract_entities(text, entity_types)
        relationships = self.extract_relationships(text, entities)
        return {"entities": entities, "relationships": relationships, "memory_type": "fact"}


def evaluate_gold_corpus(pipeline: FineTunedPipeline) -> EvalResult:
    """Run pipeline against the 90-example gold corpus."""
    corpus = load_corpus()
    print(f"Gold corpus: {len(corpus)} examples", flush=True)
    return _evaluate(pipeline, corpus)


def evaluate_test_split(pipeline: FineTunedPipeline) -> EvalResult:
    """Run pipeline against the fine-tuning test split."""
    test_path = SPLITS_DIR / "test.jsonl"
    if not test_path.exists():
        print(f"ERROR: {test_path} not found.", file=sys.stderr)
        sys.exit(1)

    examples = []
    with test_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            examples.append(GoldExample(
                id=raw["id"],
                tier=raw.get("domain", "test"),
                topic=raw.get("domain", "test"),
                text=raw["text"],
                expected_entities=[
                    type("GoldEntity", (), {"name": e["name"], "type": e["type"]})()
                    for e in raw.get("entities", [])
                ],
                expected_relationships=[
                    type("GoldRelationship", (), {"source": r["source"], "target": r["target"], "type": r["type"]})()
                    for r in raw.get("relationships", [])
                ],
                expected_memory_type=raw.get("memory_type", "fact"),
            ))

    print(f"Test split: {len(examples)} examples", flush=True)
    return _evaluate(pipeline, examples)


def _evaluate(pipeline: FineTunedPipeline, corpus: list) -> EvalResult:
    tp = fp = fn = 0
    tc = tt = 0
    rtp = rfp = rfn = 0
    dc = dt = 0
    gliner_ms_list: list[float] = []
    rebel_ms_list: list[float] = []

    entity_types = ALL_ENTITY_TYPES

    for i, ex in enumerate(corpus):
        t0 = time.perf_counter()
        entities = pipeline.extract_entities(ex.text, entity_types)
        t1 = time.perf_counter()
        relationships = pipeline.extract_relationships(ex.text, entities)
        t2 = time.perf_counter()

        gliner_ms_list.append((t1 - t0) * 1000)
        rebel_ms_list.append((t2 - t1) * 1000)

        predicted = {
            "entities": entities,
            "relationships": relationships,
            "memory_type": "fact",
        }

        m = score_example(
            example_id=ex.id, tier=ex.tier, topic=ex.topic,
            gold_entities=[asdict(e) if hasattr(e, '__dataclass_fields__') else {"name": e.name, "type": e.type} for e in ex.expected_entities],
            gold_relationships=[asdict(r) if hasattr(r, '__dataclass_fields__') else {"source": r.source, "target": r.target, "type": r.type} for r in ex.expected_relationships],
            gold_memory_type=ex.expected_memory_type,
            predicted=predicted,
        )

        tp += m.entity_pr.tp; fp += m.entity_pr.fp; fn += m.entity_pr.fn
        tc += m.type_correct; tt += m.type_total
        rtp += m.rel_pr.tp; rfp += m.rel_pr.fp; rfn += m.rel_pr.fn
        dc += m.direction_correct; dt += m.direction_total

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(corpus)}] processed", flush=True)

    ep = tp / (tp + fp) if (tp + fp) else (1.0 if fn == 0 else 0.0)
    er = tp / (tp + fn) if (tp + fn) else 1.0
    ef1 = 2 * ep * er / (ep + er) if (ep + er) else 0.0
    ta = tc / tt if tt else 0.0
    rp = rtp / (rtp + rfp) if (rtp + rfp) else (1.0 if rfn == 0 else 0.0)
    rr = rtp / (rtp + rfn) if (rtp + rfn) else 1.0
    rf1 = 2 * rp * rr / (rp + rr) if (rp + rr) else 0.0
    dr = dc / dt if dt else 0.0

    import statistics
    g_ms = statistics.mean(gliner_ms_list) if gliner_ms_list else 0
    r_ms = statistics.mean(rebel_ms_list) if rebel_ms_list else 0

    return EvalResult(
        entity_f1=ef1, entity_precision=ep, entity_recall=er,
        type_accuracy=ta, rel_f1=rf1, rel_precision=rp, rel_recall=rr,
        direction_rate=dr,
        gliner_ms=g_ms, rebel_ms=r_ms, total_ms=g_ms + r_ms,
        n_examples=len(corpus),
    )


def write_report(result: EvalResult, label: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUTPUT_DIR / "results.json").write_text(
        json.dumps(asdict(result), indent=2), encoding="utf-8"
    )

    lines = [
        "# Fine-tuned Pipeline Evaluation",
        f"\nDate: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Corpus: {label} ({result.n_examples} examples)",
        f"Pipeline: fine-tuned GLiNER (entities) + fine-tuned REBEL (relationships)",
        "",
        "## Results",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Entity F1 | **{result.entity_f1:.3f}** |",
        f"| Entity Precision | {result.entity_precision:.3f} |",
        f"| Entity Recall | {result.entity_recall:.3f} |",
        f"| Type Accuracy | {result.type_accuracy:.3f} |",
        f"| **Relationship F1** | **{result.rel_f1:.3f}** |",
        f"| Relationship Precision | {result.rel_precision:.3f} |",
        f"| Relationship Recall | {result.rel_recall:.3f} |",
        f"| Direction Rate | {result.direction_rate:.3f} |",
        f"| GLiNER latency | {result.gliner_ms:.0f} ms |",
        f"| REBEL latency | {result.rebel_ms:.0f} ms |",
        f"| Total latency | {result.total_ms:.0f} ms |",
        "",
        "## Comparison vs zero-shot best",
        "",
        f"| Metric | Zero-shot best | Fine-tuned | Delta |",
        f"|---|---|---|---|",
        f"| Entity F1 | 0.904 | {result.entity_f1:.3f} | {result.entity_f1 - 0.904:+.3f} |",
        f"| Type Accuracy | 0.901 | {result.type_accuracy:.3f} | {result.type_accuracy - 0.901:+.3f} |",
        f"| Rel F1 | 0.654 | {result.rel_f1:.3f} | {result.rel_f1 - 0.654:+.3f} |",
        f"| Latency | 1800 ms | {result.total_ms:.0f} ms | {result.total_ms - 1800:+.0f} ms |",
        "",
    ]

    report_path = OUTPUT_DIR / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {report_path}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned extraction pipeline")
    parser.add_argument("--gliner-model", default=DEFAULT_GLINER, help="Path to fine-tuned GLiNER")
    parser.add_argument("--rebel-model", default=DEFAULT_REBEL, help="Path to fine-tuned REBEL")
    parser.add_argument("--cpu", action="store_true", help="Force CPU inference")
    parser.add_argument("--test-split", action="store_true", help="Evaluate on fine-tuning test split instead of gold corpus")
    args = parser.parse_args()

    device = "cpu" if args.cpu else "cuda"

    pipeline = FineTunedPipeline(args.gliner_model, args.rebel_model, device=device)

    if args.test_split:
        result = evaluate_test_split(pipeline)
        label = "fine-tuning test split"
    else:
        result = evaluate_gold_corpus(pipeline)
        label = "90-example gold corpus"

    print(f"\n{'='*60}", flush=True)
    print(f"Entity F1:    {result.entity_f1:.3f}  (P={result.entity_precision:.3f} R={result.entity_recall:.3f})", flush=True)
    print(f"Type Acc:     {result.type_accuracy:.3f}", flush=True)
    print(f"Rel F1:       {result.rel_f1:.3f}  (P={result.rel_precision:.3f} R={result.rel_recall:.3f})", flush=True)
    print(f"Direction:    {result.direction_rate:.3f}", flush=True)
    print(f"Latency:      {result.total_ms:.0f} ms (GLiNER {result.gliner_ms:.0f} + REBEL {result.rebel_ms:.0f})", flush=True)
    print(f"{'='*60}", flush=True)

    write_report(result, label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
