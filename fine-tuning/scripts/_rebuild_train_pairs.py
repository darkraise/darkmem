"""Rebuild the clean 7k training set.

Fixes mispair issues in topup.jsonl (inherited from batches 3, 8, 9, 13 being
off-by-one relative to their QUERY lists) by re-binding each query to the
best-matching shared row via content-word overlap. Then concatenates:

  clean_topup (2500 positives, rebound where needed) +
  extras (3000 positives from batches 31-45) +
  aug (2000 positives from the 2026-04-16 augmentation)

Output: runs/retrieval-contrastive/train_pairs_7k_clean.jsonl
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
TOPUP_PATH = ROOT / "data" / "v2" / "retrieval" / "topup.jsonl"
EXTRAS_GLOB = str(ROOT / "data" / "v2" / "retrieval" / "extra_*.tmp.jsonl")
AUG_GLOB = str(ROOT / "data" / "v2" / "retrieval" / "aug_*.tmp.jsonl")
OUT_PATH = ROOT / "runs" / "retrieval-contrastive" / "train_pairs_7k_clean.jsonl"
LOG_PATH = ROOT / "runs" / "retrieval-contrastive" / "train_pairs_7k_clean.rebind_log.jsonl"

STOPWORDS = set(
    "the a an of to for in on at with by from is are was were be been being "
    "has have had do does did that this these those it its and or not but if "
    "as which what who where when why how into onto over via per all each any "
    "some no yes we our you your they their he she his her my i me us can "
    "could would should will".split()
)


def tokens(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z]+", s) if w.lower() not in STOPWORDS and len(w) >= 4}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> int:
    shared = [json.loads(l) for l in SHARED_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    sid_to_idx = {r["id"]: i for i, r in enumerate(shared)}

    topup = [json.loads(l) for l in TOPUP_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    topup_positives = [r for r in topup if "positive" in r]

    extras: list[dict] = []
    for f in sorted(glob.glob(EXTRAS_GLOB)):
        extras += [json.loads(l) for l in Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]

    aug: list[dict] = []
    for f in sorted(glob.glob(AUG_GLOB)):
        aug += [json.loads(l) for l in Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"loaded shared={len(shared)} topup_pos={len(topup_positives)} extras={len(extras)} aug={len(aug)}")

    # Rebind each topup_positive to the best-matching shared row within a +/- 5 window
    rebound_log: list[dict] = []
    clean_rows: list[dict] = []
    kept_bad = 0
    rebound = 0
    for r in topup_positives:
        q_tokens = tokens(r["query"])
        src_idx = sid_to_idx.get(r["source_id"])
        if src_idx is None:
            clean_rows.append(r)
            continue
        cur_text = shared[src_idx]["text"]
        cur_score = jaccard(q_tokens, tokens(cur_text))

        # If current alignment already has any overlap, accept it (robust to paraphrase/code-switch/acronym)
        if cur_score > 0.0:
            clean_rows.append({
                "source_id": r["source_id"],
                "query": r["query"],
                "positive": cur_text,
                "query_kind": r.get("query_kind"),
            })
            continue

        # Zero overlap — search a +/- 5 window for any row with nonzero overlap, pick highest.
        best_idx = src_idx
        best_score = 0.0
        lo, hi = max(0, src_idx - 5), min(len(shared), src_idx + 6)
        for j in range(lo, hi):
            if j == src_idx:
                continue
            s = jaccard(q_tokens, tokens(shared[j]["text"]))
            if s > best_score:
                best_score = s
                best_idx = j

        if best_score > 0.0:
            new_src = shared[best_idx]
            clean_rows.append({
                "source_id": new_src["id"],
                "query": r["query"],
                "positive": new_src["text"],
                "query_kind": r.get("query_kind"),
            })
            rebound += 1
            rebound_log.append({
                "ret_id": r.get("id"),
                "old_source_id": r["source_id"],
                "new_source_id": new_src["id"],
                "old_idx_shift": best_idx - src_idx,
                "score": round(best_score, 3),
                "query_kind": r.get("query_kind"),
            })
        else:
            # Nothing matched in window — keep original (paraphrase-heavy kinds can legitimately have 0 overlap).
            clean_rows.append({
                "source_id": r["source_id"],
                "query": r["query"],
                "positive": cur_text,
                "query_kind": r.get("query_kind"),
            })
            kept_bad += 1

    print(f"rebound {rebound} rows, kept {kept_bad} unmatched rows, total {len(clean_rows)}")

    # Append extras + aug (already clean)
    for r in extras:
        clean_rows.append({
            "source_id": r.get("source_id"),
            "query": r.get("query"),
            "positive": r.get("positive"),
            "query_kind": r.get("query_kind"),
        })
    for r in aug:
        clean_rows.append({
            "source_id": r.get("source_id"),
            "query": r.get("query"),
            "positive": r.get("positive"),
            "query_kind": r.get("query_kind"),
        })

    # Drop exact duplicates keyed by (source_id, query_kind, query[:60])
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for r in clean_rows:
        key = (r["source_id"], r["query_kind"], (r["query"] or "")[:60])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    print(f"final: {len(deduped)} rows after dedup")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in deduped) + "\n", encoding="utf-8")
    LOG_PATH.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in rebound_log) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    print(f"wrote {LOG_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
