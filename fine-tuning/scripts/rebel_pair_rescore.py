"""Rescore rebel-large predictions on the same pair-wise metric the
relclass classifiers use, so F1 is apples-to-apples across seq2seq and
classifier heads.

Enumerates every directional entity pair per row from the gold file. For each
pair, the gold label is the schema-mapped relation type (or NONE); the
prediction label is the schema-mapped type if rebel emitted a triple with
matching source/target, else NONE.

The `--schema` flag selects the relation-map + label set:

    --schema 10type   REL_MAP  (30 -> 10)   default, backward compatible
    --schema 5type    REL_MAP_5 (30/10 -> 5), the new coding-native schema

Inputs:
    --pred   rebel pred JSONL (from _infer_relation.py)
    --gold   gold JSONL (rebel_coding10_test_gold.jsonl or rebel_coding5_test_gold.jsonl)

Output: pos micro P/R/F1 and per-class F1, same schema as eval_relclass.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts._build_rebel_coding10_splits import REL_MAP  # noqa: E402
from scripts._build_rebel_coding5_splits import REL_MAP_5  # noqa: E402


LABELS_10 = [
    "NONE",
    "USES", "DEPENDS_ON", "REPLACES", "IS_A", "HAS_PART",
    "DEPLOYED_ON", "CAUSES", "AUTHORED_BY", "HAPPENED_ON", "RELATED_TO",
]
LABELS_5 = ["NONE", "USES", "REPLACES", "IS_A", "DEPLOYED_ON", "CAUSES"]

SCHEMAS = {
    "10type": (REL_MAP, LABELS_10),
    "5type": (REL_MAP_5, LABELS_5),
}


def load_rows(path: Path):
    return [json.loads(line) for line in path.open("r", encoding="utf-8") if line.strip()]


def make_pair_label(rel_map: dict, label2id: dict[str, int]):
    def pair_label(rels, src, tgt):
        for r in rels or []:
            if r.get("source") == src and r.get("target") == tgt:
                rt = r.get("type")
                mapped = rel_map.get(rt, rt)
                if mapped in label2id:
                    return mapped
        return "NONE"
    return pair_label


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pred", required=True, type=Path)
    p.add_argument("--gold", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument(
        "--schema",
        choices=sorted(SCHEMAS),
        default="10type",
        help="Relation map + label set to score under. Default 10type (backward compatible).",
    )
    args = p.parse_args()

    rel_map, LABELS = SCHEMAS[args.schema]
    LABEL2ID = {l: i for i, l in enumerate(LABELS)}
    pair_label = make_pair_label(rel_map, LABEL2ID)

    gold_rows = {r["id"]: r for r in load_rows(args.gold)}
    pred_rows = {r["id"]: r for r in load_rows(args.pred)}

    y_true = []
    y_pred = []
    for row_id, g in gold_rows.items():
        entities = g.get("entities") or []
        pred_rels = pred_rows.get(row_id, {}).get("relationships") or []
        gold_rels = g.get("relationships") or []
        for i, e1 in enumerate(entities):
            for j, e2 in enumerate(entities):
                if i == j:
                    continue
                y_true.append(pair_label(gold_rels, e1["name"], e2["name"]))
                y_pred.append(pair_label(pred_rels, e1["name"], e2["name"]))

    none_id = LABEL2ID["NONE"]
    total = len(y_true)
    gold_pos = sum(1 for t in y_true if t != "NONE")
    pred_pos = sum(1 for t in y_pred if t != "NONE")
    correct_pos = sum(1 for t, p_ in zip(y_true, y_pred) if t == p_ and t != "NONE")
    correct_all = sum(1 for t, p_ in zip(y_true, y_pred) if t == p_)

    pos_precision = correct_pos / pred_pos if pred_pos else 0.0
    pos_recall = correct_pos / gold_pos if gold_pos else 0.0
    pos_f1 = (2 * pos_precision * pos_recall) / (pos_precision + pos_recall) if (pos_precision + pos_recall) else 0.0
    accuracy = correct_all / total if total else 0.0

    per_class = {}
    for label in LABELS:
        gold = sum(1 for t in y_true if t == label)
        pred = sum(1 for t in y_pred if t == label)
        tp = sum(1 for t, p_ in zip(y_true, y_pred) if t == p_ == label)
        pp = tp / pred if pred else 0.0
        rr = tp / gold if gold else 0.0
        f1 = (2 * pp * rr) / (pp + rr) if (pp + rr) else 0.0
        per_class[label] = {"precision": pp, "recall": rr, "f1": f1, "support": gold, "n_pred": pred}

    result = {
        "schema": args.schema,
        "pos_micro_precision": pos_precision,
        "pos_micro_recall": pos_recall,
        "pos_micro_f1": pos_f1,
        "accuracy": accuracy,
        "n_rows": total,
        "n_gold_pos": gold_pos,
        "n_pred_pos": pred_pos,
        "per_class": per_class,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    summary = {k: v for k, v in result.items() if k != "per_class"}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
