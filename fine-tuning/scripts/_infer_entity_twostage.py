"""Two-stage entity extraction inference:
  Stage 1: GLiNER span detector (single-label ENTITY) proposes candidate spans.
  Stage 2: ModernBERT 10-class classifier types each span in context.

Produces predictions in the same {id, text, entities:[{name,type,start,end}]}
schema as _infer_entity.py, so the existing eval_entity_pair scorer works
unchanged.

Usage:
    python -m scripts._infer_entity_twostage \
        --span-model models/gliner-medium-span/best \
        --type-model models/typer-modernbert-coding10/best \
        --gold data/splits/coding10clean_test_canon.jsonl \
        --pred runs/twostage-medium-modernbert/pred.jsonl \
        --span-threshold 0.4
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


LABELS_10 = ["tool", "service", "database", "language", "protocol",
             "project", "algorithm", "artifact", "concept", "entity"]


def build_marked_text(text: str, start: int, end: int) -> str:
    return text[:start] + "[ENT]" + text[start:end] + "[/ENT]" + text[end:]


def nms_spans(spans: list[dict], iou_threshold: float = 0.3) -> list[dict]:
    """Non-max suppression on overlapping span candidates.

    Sort by score descending, greedily keep the top span, drop any other
    span whose character-level IoU with a kept span exceeds iou_threshold.
    """
    if not spans:
        return []
    sorted_spans = sorted(spans, key=lambda s: -s.get("score", 0.0))
    kept: list[dict] = []
    for s in sorted_spans:
        s_start, s_end = s["start"], s["end"]
        s_len = max(1, s_end - s_start)
        overlap = False
        for k in kept:
            inter_start = max(s_start, k["start"])
            inter_end = min(s_end, k["end"])
            inter = max(0, inter_end - inter_start)
            union = s_len + (k["end"] - k["start"]) - inter
            if union > 0 and inter / union > iou_threshold:
                overlap = True
                break
        if not overlap:
            kept.append(s)
    return kept


def run(span_model_path: Path, type_model_path: Path,
        gold_path: Path, pred_path: Path,
        span_threshold: float, type_batch: int,
        nms_iou: float = 0.3,
        abstain_margin: float = 0.0) -> dict:
    import torch
    from gliner import GLiNER
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}", flush=True)

    # Stage 1 — span detector
    print(f"Stage 1 model: {span_model_path}", flush=True)
    span_model = GLiNER.from_pretrained(str(span_model_path))
    if device == "cuda":
        span_model = span_model.to("cuda")

    # Stage 2 — type classifier
    print(f"Stage 2 model: {type_model_path}", flush=True)
    tok = AutoTokenizer.from_pretrained(str(type_model_path), trust_remote_code=True)
    type_model = AutoModelForSequenceClassification.from_pretrained(
        str(type_model_path), trust_remote_code=True,
    )
    if device == "cuda":
        type_model = type_model.to("cuda")
    type_model.train(False)

    id2label = {int(k): v for k, v in getattr(type_model.config, "id2label", {}).items()}
    if not id2label or set(id2label.values()) != set(LABELS_10):
        id2label = {i: l for i, l in enumerate(LABELS_10)}

    # Load gold
    gold_rows = [json.loads(l) for l in gold_path.open("r", encoding="utf-8") if l.strip()]
    print(f"Gold: {len(gold_rows)} rows", flush=True)

    pred_path.parent.mkdir(parents=True, exist_ok=True)

    stage1_times: list[float] = []
    stage2_times: list[float] = []

    with pred_path.open("w", encoding="utf-8") as out_f:
        for i, row in enumerate(gold_rows):
            text = row["text"]

            # Stage 1 — span detection (single-label ENTITY)
            t0 = time.perf_counter()
            raw_spans = span_model.predict_entities(
                text, ["entity"], threshold=span_threshold,
            )
            # NMS: drop overlapping spans; keep the highest-score candidate
            raw_spans = nms_spans(raw_spans, iou_threshold=nms_iou)
            stage1_times.append((time.perf_counter() - t0) * 1000)

            if not raw_spans:
                out_f.write(json.dumps({"id": row["id"], "text": text,
                                         "entities": []}) + "\n")
                continue

            # Stage 2 — type classification (batched per row)
            marked_texts = [build_marked_text(text, e["start"], e["end"])
                            for e in raw_spans]

            t0 = time.perf_counter()
            # Process in sub-batches if a row has many spans
            import torch.nn.functional as F
            all_preds: list[int] = []
            all_margins: list[float] = []
            for j in range(0, len(marked_texts), type_batch):
                chunk = marked_texts[j:j + type_batch]
                enc = tok(chunk, return_tensors="pt", truncation=True,
                          max_length=256, padding=True)
                if device == "cuda":
                    enc = {k: v.to("cuda") for k, v in enc.items()}
                with torch.no_grad():
                    logits = type_model(**enc).logits
                probs = F.softmax(logits, dim=-1)
                top2 = probs.topk(2, dim=-1)
                preds = top2.indices[:, 0].tolist()
                margins = (top2.values[:, 0] - top2.values[:, 1]).tolist()
                all_preds.extend(preds)
                all_margins.extend(margins)
            stage2_times.append((time.perf_counter() - t0) * 1000)

            entities = []
            for span_info, pred_id, margin in zip(raw_spans, all_preds, all_margins):
                # Confidence abstention: drop predictions where the top-2
                # probability gap is smaller than abstain_margin.
                if margin < abstain_margin:
                    continue
                entities.append({
                    "name": text[span_info["start"]:span_info["end"]],
                    "type": id2label[pred_id],
                    "start": span_info["start"],
                    "end": span_info["end"],
                })

            out_f.write(json.dumps({"id": row["id"], "text": text,
                                     "entities": entities}, ensure_ascii=False) + "\n")

            if (i + 1) % 200 == 0:
                print(f"  [{i+1}/{len(gold_rows)}]", flush=True)

    s1_mean = sum(stage1_times) / max(1, len(stage1_times))
    s2_mean = sum(stage2_times) / max(1, len(stage2_times))
    total_mean = s1_mean + s2_mean

    side = {
        "span_model": str(span_model_path),
        "type_model": str(type_model_path),
        "rows": len(gold_rows),
        "stage1_ms_mean": s1_mean,
        "stage2_ms_mean": s2_mean,
        "total_ms_mean": total_mean,
        "span_threshold": span_threshold,
    }
    pred_path.with_suffix(".runtime.json").write_text(json.dumps(side, indent=2), encoding="utf-8")
    print(f"\nWrote {pred_path}", flush=True)
    print(f"  stage1: {s1_mean:.1f} ms/row   stage2: {s2_mean:.1f} ms/row   total: {total_mean:.1f} ms/row",
          flush=True)
    return side


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--span-model", type=Path, required=True)
    p.add_argument("--type-model", type=Path, required=True)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--pred", type=Path, required=True)
    p.add_argument("--span-threshold", type=float, default=0.4)
    p.add_argument("--type-batch", type=int, default=16)
    p.add_argument("--nms-iou", type=float, default=0.3,
                   help="NMS IoU threshold for overlapping span suppression")
    p.add_argument("--abstain-margin", type=float, default=0.0,
                   help="Drop typer predictions where top1-top2 prob gap is below this")
    a = p.parse_args()
    run(a.span_model, a.type_model, a.gold, a.pred, a.span_threshold, a.type_batch,
        nms_iou=a.nms_iou, abstain_margin=a.abstain_margin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
