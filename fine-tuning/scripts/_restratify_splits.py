"""Re-stratify the 14k v2 shared corpus into GLiNER and REBEL splits.

Replaces the legacy train/val/test produced when shared.jsonl was 7k.

GLiNER: every row in shared.jsonl is eligible (noise rows with empty entity
lists are kept as negative signal). Stratified by memory_type; target sizes
10000 / 2000 / 2000.

REBEL: only rows with non-empty relationships. With the darkmem-only 14k
corpus we have 10,065 such rows, so the split is 80/10/10 of that subset
(approx 8052 / 1007 / 1006). Stratified by memory_type. Train hits the plan's
>=8000 floor; val/test sit at ~1000 each, which is below the plan's 1800
aspiration but is forced by the data budget once Phase 1.1 was skipped.

Output schema matches scripts.convert_to_gliner and scripts.convert_to_rebel
verbatim so the existing trainers work unchanged.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "data" / "v2" / "shared" / "shared.jsonl"
SPLITS_DIR = ROOT / "data" / "splits"

GLINER_TRAIN_N = 10_000
GLINER_VAL_N = 2_000
GLINER_TEST_N = 2_000

REBEL_TRAIN_FRAC = 0.80
REBEL_VAL_FRAC = 0.10
REBEL_TEST_FRAC = 0.10

SEED = 42


def load_rows() -> list[dict]:
    rows: list[dict] = []
    with SHARED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def stratified_split_counts(
    group_counts: dict[str, int], targets: tuple[int, int, int]
) -> dict[str, tuple[int, int, int]]:
    """Distribute targets across groups so per-group sums == group size and
    per-axis sums == targets.

    Step 1: per-group largest-remainder — sum(tr, va, te) = n_g exactly.
    Step 2: if per-axis totals drift from targets, shift single rows between
    axes within large groups until drift = 0.
    """
    train_t, val_t, test_t = targets
    total = sum(group_counts.values())
    assert train_t + val_t + test_t == total, (
        f"targets {targets} must sum to total rows {total}"
    )
    alloc: dict[str, list[int]] = {}
    for k, n in group_counts.items():
        raw = (n * train_t / total, n * val_t / total, n * test_t / total)
        floors = [int(x) for x in raw]
        deficit = n - sum(floors)
        rem = sorted(
            ((raw[a] - floors[a], a) for a in range(3)), reverse=True
        )
        for i in range(deficit):
            floors[rem[i][1]] += 1
        alloc[k] = floors

    axis_sums = [sum(alloc[k][a] for k in alloc) for a in range(3)]
    for _ in range(1000):
        diffs = [axis_sums[a] - targets[a] for a in range(3)]
        if all(d == 0 for d in diffs):
            break
        over = max(range(3), key=lambda a: diffs[a])
        under = min(range(3), key=lambda a: diffs[a])
        if diffs[over] <= 0 or diffs[under] >= 0:
            break
        moved = False
        for k in sorted(alloc.keys(), key=lambda k: group_counts[k], reverse=True):
            if alloc[k][over] > 0:
                alloc[k][over] -= 1
                alloc[k][under] += 1
                axis_sums[over] -= 1
                axis_sums[under] += 1
                moved = True
                break
        if not moved:
            break
    return {k: tuple(v) for k, v in alloc.items()}


def split_group(
    rows: list[dict], counts: tuple[int, int, int], rng: random.Random
) -> tuple[list[dict], list[dict], list[dict]]:
    train_n, val_n, test_n = counts
    shuffled = rows[:]
    rng.shuffle(shuffled)
    total = train_n + val_n + test_n
    if total > len(shuffled):
        # clamp counts to available rows (shouldn't happen with our budgets)
        train_n = min(train_n, len(shuffled))
        rem = len(shuffled) - train_n
        val_n = min(val_n, rem)
        test_n = max(0, rem - val_n)
    train = shuffled[:train_n]
    val = shuffled[train_n : train_n + val_n]
    test = shuffled[train_n + val_n : train_n + val_n + test_n]
    return train, val, test


def to_gliner(row: dict) -> dict:
    text = row["text"]
    entities = []
    for ent in row.get("entities", []) or []:
        start, end = ent["start"], ent["end"]
        if start < 0 or end > len(text) or end <= start:
            continue
        entities.append({"start": start, "end": end, "label": ent["type"]})
    return {"text": text, "entities": entities}


def to_rebel(row: dict) -> dict:
    text = row["text"]
    entities = row.get("entities", []) or []
    ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
    inp = f"{text} | Entities: {ent_str}"
    rels = row.get("relationships", []) or []
    parts = [f"<triplet> {r['source']} <subj> {r['target']} <obj> {r['type']}" for r in rels]
    out = " ".join(parts) if parts else "<triplet> NONE"
    return {"input": inp, "output": out}


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def stratified_partition(
    rows: list[dict], targets: tuple[int, int, int], seed: int
) -> tuple[list[dict], list[dict], list[dict]]:
    rng = random.Random(seed)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row.get("memory_type", "fact")].append(row)
    group_counts = {k: len(v) for k, v in grouped.items()}
    plan = stratified_split_counts(group_counts, targets)
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for mt in sorted(grouped.keys()):
        tr, va, te = split_group(grouped[mt], plan[mt], rng)
        train += tr
        val += va
        test += te
    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def summarize(tag: str, rows: list[dict]) -> None:
    from collections import Counter
    c = Counter(r.get("memory_type", "?") for r in rows)
    parts = ", ".join(f"{k}={v}" for k, v in sorted(c.items()))
    print(f"  {tag}: {len(rows)} [{parts}]")


def main() -> int:
    rows = load_rows()
    print(f"loaded {len(rows)} rows from shared.jsonl")

    # GLiNER: all rows
    print("\nGLiNER stratification (all rows):")
    g_train, g_val, g_test = stratified_partition(
        rows, (GLINER_TRAIN_N, GLINER_VAL_N, GLINER_TEST_N), SEED
    )
    summarize("train", g_train)
    summarize("val", g_val)
    summarize("test", g_test)
    write_jsonl(SPLITS_DIR / "gliner_train.jsonl", [to_gliner(r) for r in g_train])
    write_jsonl(SPLITS_DIR / "gliner_val.jsonl", [to_gliner(r) for r in g_val])
    write_jsonl(SPLITS_DIR / "gliner_test.jsonl", [to_gliner(r) for r in g_test])

    # REBEL: filter to rows with non-empty relationships
    rel_rows = [r for r in rows if r.get("relationships")]
    print(f"\nREBEL-eligible rows (non-empty relationships): {len(rel_rows)}")
    n = len(rel_rows)
    r_train_n = int(n * REBEL_TRAIN_FRAC)
    r_val_n = int(n * REBEL_VAL_FRAC)
    r_test_n = n - r_train_n - r_val_n
    print(f"REBEL split targets: {r_train_n} / {r_val_n} / {r_test_n}")
    r_train, r_val, r_test = stratified_partition(
        rel_rows, (r_train_n, r_val_n, r_test_n), SEED
    )
    summarize("train", r_train)
    summarize("val", r_val)
    summarize("test", r_test)
    write_jsonl(SPLITS_DIR / "rebel_train.jsonl", [to_rebel(r) for r in r_train])
    write_jsonl(SPLITS_DIR / "rebel_val.jsonl", [to_rebel(r) for r in r_val])
    write_jsonl(SPLITS_DIR / "rebel_test.jsonl", [to_rebel(r) for r in r_test])

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
