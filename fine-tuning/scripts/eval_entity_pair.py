"""Entity-pair F1 scorer — the primary metric for agentic memory quality.

A match requires BOTH the normalized name AND the entity type to be equal.
Span offsets are ignored (they normalize away when entities become KG nodes).
Case-insensitive name match with acronym/trailing-suffix tolerance via the
extraction_eval normalizer when available, simple lowercase fallback otherwise.

Schema (gold and pred, per-row):
  {"id": "...", "entities": [{"name": str, "type": str, ...}, ...]}

Output (JSON):
  {
    "micro_precision": ..., "micro_recall": ..., "micro_f1": ...,
    "per_type": {"<type>": {"precision": ..., "recall": ..., "f1": ..., "support": int}},
    "components": {"name_recall": ..., "type_accuracy_given_name": ...},
    "n_rows": int, "n_gold_entities": int, "n_pred_entities": int
  }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_WHITESPACE = re.compile(r"\s+")
_TRAILING = re.compile(r"(?i)\b(inc|llc|corp|ltd|gmbh|ag|sa|co)\.?$")


def _lazy_lenient_matcher():
    """If the extraction_eval normalizer is reachable, use it. Otherwise fall
    back to a simple lowercase + whitespace-collapse + trailing-suffix strip."""
    try:
        repo = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo / "docs" / "e2e" / "scripts"))
        sys.path.insert(0, str(repo / "backend"))
        from extraction_eval.metrics import normalize_name, names_match  # type: ignore
        return normalize_name, names_match
    except Exception:
        def normalize_name(n: str) -> str:
            if not n:
                return ""
            n = n.strip().lower()
            n = _TRAILING.sub("", n).strip()
            n = _WHITESPACE.sub(" ", n)
            return n

        def names_match(a: str, b: str) -> bool:
            if not a or not b:
                return False
            na = normalize_name(a)
            nb = normalize_name(b)
            if na == nb:
                return True
            if len(na) >= 3 and len(nb) >= 3:
                if na in nb or nb in na:
                    shorter, longer = (na, nb) if len(na) < len(nb) else (nb, na)
                    if longer.startswith(shorter + " ") or longer.endswith(" " + shorter):
                        return True
            return False

        return normalize_name, names_match


NORMALIZE_NAME, NAMES_MATCH = _lazy_lenient_matcher()


def _load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _pair_set(entities: list[dict]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for e in entities or []:
        name = (e.get("name") or "").strip()
        etype = (e.get("type") or e.get("label") or "").strip()
        if not name or not etype:
            continue
        pairs.append((NORMALIZE_NAME(name), etype))
    return pairs


def score(gold_rows: list[dict], pred_index: dict[str, dict]) -> dict:
    tp_by_type: dict[str, int] = defaultdict(int)
    fp_by_type: dict[str, int] = defaultdict(int)
    fn_by_type: dict[str, int] = defaultdict(int)
    total_gold = 0
    total_pred = 0
    # Diagnostics: what share of gold entities are name-matched at all, and
    # among name-matched, what share have the correct type.
    name_matched = 0
    name_matched_type_right = 0

    for g in gold_rows:
        pred = pred_index.get(g["id"], {})
        gold_pairs = _pair_set(g.get("entities", []))
        pred_pairs = _pair_set(pred.get("entities", []))

        total_gold += len(gold_pairs)
        total_pred += len(pred_pairs)

        # Exact (normalized_name, type) match
        gold_multiset = defaultdict(int)
        for p in gold_pairs:
            gold_multiset[p] += 1
        pred_multiset = defaultdict(int)
        for p in pred_pairs:
            pred_multiset[p] += 1

        all_keys = set(gold_multiset) | set(pred_multiset)
        for key in all_keys:
            g_n, p_n = gold_multiset[key], pred_multiset[key]
            matched = min(g_n, p_n)
            tp_by_type[key[1]] += matched
            fp_by_type[key[1]] += max(0, p_n - matched)
            fn_by_type[key[1]] += max(0, g_n - matched)

        # Diagnostics via name-match bridge
        pred_name_counts = defaultdict(int)
        for (pn, pt) in pred_pairs:
            pred_name_counts[pn] += 1
        for (gn, gt) in gold_pairs:
            if pred_name_counts.get(gn, 0) > 0:
                name_matched += 1
                for (pn, pt) in pred_pairs:
                    if pn == gn and pt == gt:
                        name_matched_type_right += 1
                        break
            else:
                for (pn, pt) in pred_pairs:
                    if NAMES_MATCH(gn, pn):
                        name_matched += 1
                        if pt == gt:
                            name_matched_type_right += 1
                        break

    per_type: dict[str, dict] = {}
    for t in set(tp_by_type) | set(fp_by_type) | set(fn_by_type):
        tp, fp, fn = tp_by_type[t], fp_by_type[t], fn_by_type[t]
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_type[t] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}

    tp = sum(tp_by_type.values())
    fp = sum(fp_by_type.values())
    fn = sum(fn_by_type.values())
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    return {
        "micro_precision": prec,
        "micro_recall": rec,
        "micro_f1": f1,
        "components": {
            "name_recall": name_matched / total_gold if total_gold else 0.0,
            "type_accuracy_given_name": (
                name_matched_type_right / name_matched if name_matched else 0.0
            ),
        },
        "per_type": per_type,
        "n_rows": len(gold_rows),
        "n_gold_entities": total_gold,
        "n_pred_entities": total_pred,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Entity-pair F1: strict (normalized_name, type) match, ignores offsets.",
    )
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--pred", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()

    gold = _load_rows(a.gold)
    pred = {r["id"]: r for r in _load_rows(a.pred)}
    metrics = score(gold, pred)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    summary = {k: v for k, v in metrics.items() if k != "per_type"}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
