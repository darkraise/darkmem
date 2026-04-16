"""Comprehensive corpus review: distribution, duplicates, length, and boundary issues."""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "data" / "classification" / "train.jsonl"
TEST_PATH = ROOT.parent / "docs" / "e2e" / "scripts" / "classification_eval" / "corpus" / "gold.jsonl"


def load(path: Path) -> list[dict]:
    data = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def distribution_report(data: list[dict], name: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"DISTRIBUTION: {name}")
    print(f"{'=' * 70}")
    c = Counter(d["label"] if "label" in d else d["type"] for d in data)
    total = sum(c.values())
    for k in sorted(c):
        bar = "#" * int(50 * c[k] / max(c.values()))
        print(f"  {k:<14} {c[k]:>4} ({c[k]/total:>5.1%}) {bar}")
    print(f"  TOTAL: {total}")


def length_analysis(data: list[dict], name: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"TEXT LENGTH BY CLASS: {name}")
    print(f"{'=' * 70}")
    print(f"{'Class':<14} {'Mean':>6} {'Med':>6} {'Min':>5} {'Max':>5} {'StdDev':>7}")
    by_class: dict[str, list[int]] = defaultdict(list)
    for d in data:
        label = d.get("label", d.get("type"))
        by_class[label].append(len(d["text"]))
    for label in sorted(by_class):
        lens = by_class[label]
        print(f"  {label:<12} {statistics.mean(lens):>6.0f} {statistics.median(lens):>6.0f} "
              f"{min(lens):>5} {max(lens):>5} {statistics.stdev(lens):>7.1f}")


def find_near_duplicates(data: list[dict], name: str, threshold: float = 0.85) -> None:
    print(f"\n{'=' * 70}")
    print(f"NEAR-DUPLICATES (cosine >= {threshold}): {name}")
    print(f"{'=' * 70}")
    texts = [d["text"] for d in data]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2).fit_transform(texts)
    # Compute upper-triangle similarities in chunks to save memory
    n = len(texts)
    pairs = []
    chunk = 500
    for i in range(0, n, chunk):
        sims = cosine_similarity(vec[i:i+chunk], vec)
        for local_i, row in enumerate(sims):
            global_i = i + local_i
            for j, s in enumerate(row):
                if j > global_i and s >= threshold:
                    pairs.append((global_i, j, float(s)))
    pairs.sort(key=lambda x: -x[2])
    print(f"Found {len(pairs)} near-duplicate pairs")
    for i, j, s in pairs[:20]:
        li = data[i].get("label", data[i].get("type"))
        lj = data[j].get("label", data[j].get("type"))
        marker = " !!" if li != lj else ""
        print(f"  [{s:.2f}]{marker} {li}|{lj}")
        print(f"    a: {data[i]['text'][:90]}")
        print(f"    b: {data[j]['text'][:90]}")


def cross_class_similarity(data: list[dict], name: str) -> None:
    """For each test-set error boundary, find the most similar training examples from the confused class."""
    print(f"\n{'=' * 70}")
    print(f"CROSS-CLASS HIGH-SIMILARITY PAIRS (potential mislabels): {name}")
    print(f"{'=' * 70}")
    texts = [d["text"] for d in data]
    labels = [d.get("label", d.get("type")) for d in data]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2).fit_transform(texts)
    n = len(texts)
    # For each example, find its nearest neighbor and check if labels differ
    suspicious = []
    chunk = 500
    for i in range(0, n, chunk):
        sims = cosine_similarity(vec[i:i+chunk], vec)
        for local_i, row in enumerate(sims):
            global_i = i + local_i
            row[global_i] = -1  # exclude self
            nearest = int(np.argmax(row))
            if labels[nearest] != labels[global_i] and row[nearest] > 0.5:
                suspicious.append((global_i, nearest, float(row[nearest])))
    suspicious.sort(key=lambda x: -x[2])
    print(f"Found {len(suspicious)} examples whose nearest neighbor has a different label (similarity > 0.5)")
    # Group by (source_label, target_label)
    boundary_counts = Counter(
        (labels[i], labels[j]) for i, j, _ in suspicious
    )
    print("\nTop confused-label boundaries in training data (source_label -> nearest_neighbor_label):")
    for (src, tgt), count in boundary_counts.most_common(15):
        print(f"  {src:<14} -> {tgt:<14} {count} pairs")
    print("\nTop-20 highest-similarity cross-label pairs:")
    for i, j, s in suspicious[:20]:
        print(f"  [{s:.2f}] {labels[i]} vs {labels[j]}")
        print(f"    a: {data[i]['text'][:100]}")
        print(f"    b: {data[j]['text'][:100]}")


def starter_word_analysis(data: list[dict], name: str) -> None:
    """Some classes may be identifiable from just the first word — a shortcut the model could exploit."""
    print(f"\n{'=' * 70}")
    print(f"STARTER-WORD SHORTCUTS: {name}")
    print(f"{'=' * 70}")
    by_class: dict[str, Counter] = defaultdict(Counter)
    for d in data:
        label = d.get("label", d.get("type"))
        first_word = d["text"].split()[0].lower().rstrip(":,.;")
        by_class[label][first_word] += 1
    for label in sorted(by_class):
        total = sum(by_class[label].values())
        top = by_class[label].most_common(5)
        dominant = top[0]
        pct = dominant[1] / total
        flag = " !!SHORTCUT!!" if pct > 0.25 else ""
        top_str = ", ".join(f"{w}({c})" for w, c in top)
        print(f"  {label:<14} top: {top_str}{flag}")


def question_mark_check(data: list[dict], name: str) -> None:
    """Check if question class is identifiable purely by presence of '?'."""
    print(f"\n{'=' * 70}")
    print(f"QUESTION MARK SHORTCUT CHECK: {name}")
    print(f"{'=' * 70}")
    by_class_qmark: dict[str, int] = defaultdict(int)
    by_class_total: dict[str, int] = defaultdict(int)
    for d in data:
        label = d.get("label", d.get("type"))
        by_class_total[label] += 1
        if "?" in d["text"]:
            by_class_qmark[label] += 1
    for label in sorted(by_class_total):
        pct = by_class_qmark[label] / by_class_total[label]
        flag = " !!SHORTCUT!!" if label == "question" and pct > 0.9 else (" (expected)" if label == "question" else "")
        print(f"  {label:<14} {by_class_qmark[label]:>4}/{by_class_total[label]:<4} ({pct:>5.1%}){flag}")


def main() -> int:
    train = load(TRAIN_PATH)
    test = load(TEST_PATH)

    distribution_report(train, "TRAIN")
    distribution_report(test, "TEST")
    length_analysis(train, "TRAIN")
    starter_word_analysis(train, "TRAIN")
    question_mark_check(train, "TRAIN")
    question_mark_check(test, "TEST")
    find_near_duplicates(train, "TRAIN", threshold=0.80)
    cross_class_similarity(train, "TRAIN")
    return 0


if __name__ == "__main__":
    main()
