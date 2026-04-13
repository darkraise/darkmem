"""Validate generated training data and split into train/val/test.

Checks:
  1. Every entity span matches text[start:end] == name
  2. Every relationship endpoint exists in the entity list
  3. Entity types are from the allowed set
  4. Relationship types are from the allowed set
  5. No duplicate IDs
  6. text is non-empty

Usage:
    python -m scripts.validate_data                    # validate + split
    python -m scripts.validate_data --check-only       # validate without splitting
    python -m scripts.validate_data --fix              # auto-fix span offsets where possible
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.domains import ALL_ENTITY_TYPES, ALL_RELATIONSHIP_TYPES, ALL_MEMORY_TYPES

RAW_DIR = ROOT / "data" / "raw"
VALIDATED_DIR = ROOT / "data" / "validated"
SPLITS_DIR = ROOT / "data" / "splits"

TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10


def load_raw_examples() -> list[dict]:
    """Load all JSONL files from raw/ into a flat list."""
    examples: list[dict] = []
    if not RAW_DIR.exists():
        print(f"ERROR: {RAW_DIR} does not exist", file=sys.stderr)
        return examples
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    ex = json.loads(line)
                    ex["_source_file"] = path.name
                    ex["_source_line"] = line_no
                    examples.append(ex)
                except json.JSONDecodeError as exc:
                    print(f"  WARN: {path.name}:{line_no} — invalid JSON: {exc}")
    return examples


def try_fix_spans(example: dict) -> int:
    """Try to auto-fix entity spans by searching for the name in text. Returns fix count."""
    text = example.get("text", "")
    fixes = 0
    for ent in example.get("entities", []):
        name = ent.get("name", "")
        start = ent.get("start")
        end = ent.get("end")
        if not name or start is None or end is None:
            continue
        if text[start:end] == name:
            continue
        idx = text.find(name)
        if idx >= 0:
            ent["start"] = idx
            ent["end"] = idx + len(name)
            fixes += 1
    return fixes


def validate_example(
    example: dict,
    entity_type_set: set[str],
    rel_type_set: set[str],
    memory_type_set: set[str],
) -> list[str]:
    """Return list of error strings. Empty means valid."""
    errors: list[str] = []
    eid = example.get("id", "???")
    text = example.get("text", "")

    if not text.strip():
        errors.append(f"{eid}: empty text")
        return errors

    entity_names: set[str] = set()
    for i, ent in enumerate(example.get("entities", [])):
        name = ent.get("name", "")
        etype = ent.get("type", "")
        start = ent.get("start")
        end = ent.get("end")

        if not name:
            errors.append(f"{eid}: entity[{i}] has empty name")
            continue

        entity_names.add(name)

        if start is None or end is None:
            errors.append(f"{eid}: entity '{name}' missing start/end offsets")
            continue

        if not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"{eid}: entity '{name}' start/end must be integers")
            continue

        if start < 0 or end > len(text) or start >= end:
            errors.append(f"{eid}: entity '{name}' has invalid span [{start}:{end}] for text length {len(text)}")
            continue

        actual = text[start:end]
        if actual != name:
            errors.append(
                f"{eid}: entity '{name}' span mismatch: text[{start}:{end}] = '{actual}'"
            )

        if etype and etype not in entity_type_set:
            errors.append(f"{eid}: entity '{name}' has unknown type '{etype}'")

    for i, rel in enumerate(example.get("relationships", [])):
        src = rel.get("source", "")
        tgt = rel.get("target", "")
        rtype = rel.get("type", "")

        if src not in entity_names:
            errors.append(f"{eid}: rel[{i}] source '{src}' not in entities")
        if tgt not in entity_names:
            errors.append(f"{eid}: rel[{i}] target '{tgt}' not in entities")
        if rtype and rtype not in rel_type_set:
            errors.append(f"{eid}: rel[{i}] unknown type '{rtype}'")

    mt = example.get("memory_type", "")
    if mt and mt not in memory_type_set:
        errors.append(f"{eid}: unknown memory_type '{mt}'")

    return errors


def validate_all(
    examples: list[dict],
    auto_fix: bool = False,
) -> tuple[list[dict], list[str]]:
    """Validate all examples. Returns (valid_examples, all_errors)."""
    entity_type_set = set(ALL_ENTITY_TYPES)
    rel_type_set = set(ALL_RELATIONSHIP_TYPES)
    memory_type_set = set(ALL_MEMORY_TYPES)

    all_errors: list[str] = []
    valid: list[dict] = []
    ids_seen: set[str] = set()
    fix_count = 0

    for ex in examples:
        eid = ex.get("id", "")
        if eid in ids_seen:
            all_errors.append(f"{eid}: duplicate ID")
            continue
        if eid:
            ids_seen.add(eid)

        if auto_fix:
            fix_count += try_fix_spans(ex)

        errors = validate_example(ex, entity_type_set, rel_type_set, memory_type_set)
        if errors:
            all_errors.extend(errors)
        else:
            valid.append(ex)

    if auto_fix and fix_count:
        print(f"  Auto-fixed {fix_count} span offsets", flush=True)

    return valid, all_errors


def split_data(
    examples: list[dict],
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Stratified split by domain into train/val/test."""
    rng = random.Random(seed)

    by_domain: dict[str, list[dict]] = {}
    for ex in examples:
        domain = ex.get("domain", "unknown")
        by_domain.setdefault(domain, []).append(ex)

    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []

    for domain, domain_examples in by_domain.items():
        rng.shuffle(domain_examples)
        n = len(domain_examples)
        n_val = max(1, round(n * VAL_RATIO))
        n_test = max(1, round(n * TEST_RATIO))
        n_train = n - n_val - n_test

        train.extend(domain_examples[:n_train])
        val.extend(domain_examples[n_train:n_train + n_val])
        test.extend(domain_examples[n_train + n_val:])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    return train, val, test


def write_jsonl(examples: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            cleaned = {k: v for k, v in ex.items() if not k.startswith("_")}
            fh.write(json.dumps(cleaned, ensure_ascii=False) + "\n")


def _char_spans_to_token_spans(
    text: str, char_entities: list[dict],
) -> tuple[list[str], list[list]]:
    """Word-tokenize text and convert character-level entity spans to token indices.

    Returns (tokens, ner) where ner entries are [start_token, end_token, label].
    end_token is exclusive (GLiNER convention).
    """
    tokens: list[str] = text.split()

    token_char_starts: list[int] = []
    pos = 0
    for tok in tokens:
        idx = text.index(tok, pos)
        token_char_starts.append(idx)
        pos = idx + len(tok)

    ner: list[list] = []
    for ent in char_entities:
        char_start = ent["start"]
        char_end = ent["end"]
        label = ent["label"] if "label" in ent else ent.get("type", "")

        start_tok = None
        end_tok = None
        for ti, tcs in enumerate(token_char_starts):
            tok_end = tcs + len(tokens[ti])
            if start_tok is None and tcs <= char_start < tok_end:
                start_tok = ti
            if start_tok is not None and char_end <= tok_end:
                end_tok = ti + 1
                break

        if start_tok is not None and end_tok is not None:
            ner.append([start_tok, end_tok, label])

    return tokens, ner


def write_gliner_jsonl(examples: list[dict], path: Path) -> None:
    """Write in GLiNER fine-tuning format: {tokenized_text, ner: [[start, end, label]]}."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            char_entities = []
            for ent in ex.get("entities", []):
                if "start" in ent and "end" in ent:
                    char_entities.append({
                        "start": ent["start"],
                        "end": ent["end"],
                        "label": ent["type"],
                    })

            tokens, ner = _char_spans_to_token_spans(ex["text"], char_entities)
            record = {"tokenized_text": tokens, "ner": ner}
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_rebel_jsonl(examples: list[dict], path: Path) -> None:
    """Write in REBEL training format: {input, output} with linearized triplets."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            entities = ex.get("entities", [])
            rels = ex.get("relationships", [])
            if not entities:
                continue

            ent_str = ", ".join(f"{e['name']} ({e['type']})" for e in entities)
            input_text = f"{ex['text']} | Entities: {ent_str}"

            triplets = []
            for r in rels:
                triplets.append(
                    f"<triplet> {r['source']} <subj> {r['target']} <obj> {r['type']}"
                )
            output_text = " ".join(triplets) if triplets else "<triplet> NONE"

            record = {"input": input_text, "output": output_text}
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and split training data")
    parser.add_argument("--check-only", action="store_true", help="Validate without splitting")
    parser.add_argument("--fix", action="store_true", help="Auto-fix span offsets where possible")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    args = parser.parse_args()

    print("Loading raw examples...", flush=True)
    examples = load_raw_examples()
    if not examples:
        print("No examples found. Run generate_data.py first.", file=sys.stderr)
        return 1
    print(f"  Loaded {len(examples)} raw examples", flush=True)

    domain_counts = Counter(ex.get("domain", "unknown") for ex in examples)
    for domain, count in sorted(domain_counts.items()):
        print(f"    {domain}: {count}", flush=True)

    print("\nValidating...", flush=True)
    valid, errors = validate_all(examples, auto_fix=args.fix)
    print(f"  Valid: {len(valid)}, Errors: {len(errors)}", flush=True)

    if errors:
        print(f"\nFirst 20 errors:", flush=True)
        for err in errors[:20]:
            print(f"  {err}", flush=True)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more", flush=True)

        VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
        errors_path = VALIDATED_DIR / "validation_errors.txt"
        errors_path.write_text("\n".join(errors), encoding="utf-8")
        print(f"\nFull error log: {errors_path}", flush=True)

    if args.check_only:
        return 0 if not errors else 1

    if not valid:
        print("No valid examples to split.", file=sys.stderr)
        return 1

    print(f"\nWriting validated examples...", flush=True)
    VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(valid, VALIDATED_DIR / "all.jsonl")
    print(f"  {VALIDATED_DIR / 'all.jsonl'}: {len(valid)} examples", flush=True)

    print("\nSplitting (train/val/test)...", flush=True)
    train, val, test = split_data(valid, seed=args.seed)
    print(f"  Train: {len(train)}, Val: {len(val)}, Test: {len(test)}", flush=True)

    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(train, SPLITS_DIR / "train.jsonl")
    write_jsonl(val, SPLITS_DIR / "val.jsonl")
    write_jsonl(test, SPLITS_DIR / "test.jsonl")

    print("\nWriting GLiNER format...", flush=True)
    write_gliner_jsonl(train, SPLITS_DIR / "gliner_train.jsonl")
    write_gliner_jsonl(val, SPLITS_DIR / "gliner_val.jsonl")
    write_gliner_jsonl(test, SPLITS_DIR / "gliner_test.jsonl")

    print("Writing REBEL format...", flush=True)
    write_rebel_jsonl(train, SPLITS_DIR / "rebel_train.jsonl")
    write_rebel_jsonl(val, SPLITS_DIR / "rebel_val.jsonl")
    write_rebel_jsonl(test, SPLITS_DIR / "rebel_test.jsonl")

    print("\nSplit statistics:", flush=True)
    for name, split in [("train", train), ("val", val), ("test", test)]:
        domain_counts = Counter(ex.get("domain", "?") for ex in split)
        print(f"  {name}: {dict(sorted(domain_counts.items()))}", flush=True)

    print("\nDone.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
