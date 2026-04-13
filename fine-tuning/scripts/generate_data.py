"""Generate fine-tuning training data from templates and entity pools.

Produces diverse examples by combining sentence templates with randomized
entity names from curated pools.  Character-level spans are computed
programmatically, guaranteeing text[start:end] == entity_name for every entity.

Usage:
    python -m scripts.generate_data                     # full 6,000
    python -m scripts.generate_data --domain technical   # one domain
    python -m scripts.generate_data --dry-run            # show plan only
    python -m scripts.generate_data --seed 123           # reproducible
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.domains import (
    ALL_DOMAINS,
    CROSS_DOMAIN_COUNT,
    NOISE_COUNT,
    DomainConfig,
)
from config.entity_pools import ENTITY_POOLS
from config.templates import (
    TECHNICAL_TEMPLATES,
    AI_CODING_TEMPLATES,
    PERSONAL_TEMPLATES,
    KNOWLEDGE_TEMPLATES,
    NOISE_TEMPLATES,
    CROSS_DOMAIN_TEMPLATES,
    Template,
)

RAW_DIR = ROOT / "data" / "raw"

DOMAIN_TEMPLATES: dict[str, dict[str, list[Template]]] = {
    "technical": TECHNICAL_TEMPLATES,
    "ai_coding": AI_CODING_TEMPLATES,
    "personal": PERSONAL_TEMPLATES,
    "knowledge": KNOWLEDGE_TEMPLATES,
}


def pick_entity(rng: random.Random, etype: str, used: set[str]) -> str:
    """Pick a random entity name of the given type, avoiding repeats within one example."""
    pool = ENTITY_POOLS.get(etype, [])
    if not pool:
        return etype.title()
    candidates = [n for n in pool if n not in used]
    if not candidates:
        candidates = pool
    name = rng.choice(candidates)
    used.add(name)
    return name


def build_example(
    rng: random.Random,
    template: Template,
    domain: str,
    example_id: str,
) -> dict:
    """Build one training example from a template. Returns a dict with computed spans."""
    tmpl_str, entity_slots, rel_specs, memory_type = template

    used_names: set[str] = set()
    slot_names: dict[int, str] = {}
    slot_types: dict[int, str] = {}

    for slot_idx, etype in entity_slots:
        name = pick_entity(rng, etype, used_names)
        slot_names[slot_idx] = name
        slot_types[slot_idx] = etype

    import re as _re
    max_slot = max(
        (int(m) for m in _re.findall(r"\{(\d+)\}", tmpl_str)),
        default=-1,
    )
    format_args = [slot_names.get(i, f"MISSING_{i}") for i in range(max_slot + 1)]
    text = tmpl_str.format(*format_args)

    slot_positions: dict[int, list[tuple[int, int]]] = {}
    pattern = _re.compile(r"\{(\d+)\}")
    result_cursor = 0
    last_end = 0

    for m in pattern.finditer(tmpl_str):
        literal = tmpl_str[last_end:m.start()]
        result_cursor += len(literal)

        slot_idx = int(m.group(1))
        name = format_args[slot_idx]
        start = result_cursor
        end = result_cursor + len(name)
        slot_positions.setdefault(slot_idx, []).append((start, end))
        result_cursor = end
        last_end = m.end()

    entities = []
    seen_entities: set[str] = set()
    for slot_idx, etype in entity_slots:
        name = slot_names[slot_idx]
        if name in seen_entities:
            continue
        positions = slot_positions.get(slot_idx, [])
        if not positions:
            continue
        start, end = positions[0]
        seen_entities.add(name)
        entities.append({
            "name": name,
            "type": etype,
            "start": start,
            "end": end,
        })

    for e in entities:
        assert text[e["start"]:e["end"]] == e["name"], (
            f"Span mismatch: text[{e['start']}:{e['end']}] = "
            f"'{text[e['start']:e['end']]}' != '{e['name']}'"
        )

    entity_name_set = {e["name"] for e in entities}
    relationships = []
    for src_slot, tgt_slot, rtype in rel_specs:
        src = slot_names.get(src_slot, "")
        tgt = slot_names.get(tgt_slot, "")
        if src in entity_name_set and tgt in entity_name_set and src != tgt:
            relationships.append({
                "source": src,
                "target": tgt,
                "type": rtype,
            })

    return {
        "id": example_id,
        "domain": domain,
        "text": text,
        "entities": entities,
        "relationships": relationships,
        "memory_type": memory_type,
    }


def generate_domain(
    rng: random.Random,
    domain: DomainConfig,
    templates: dict[str, list[Template]],
) -> list[dict]:
    """Generate all examples for one domain."""
    examples: list[dict] = []

    for cat in domain.categories:
        cat_templates = templates.get(cat.name, [])
        if not cat_templates:
            print(f"  WARN: no templates for {domain.name}/{cat.name}, skipping", flush=True)
            continue

        for i in range(cat.count):
            tmpl = rng.choice(cat_templates)
            eid = f"{domain.name[:4]}-{cat.name[:8]}-{i+1:04d}"
            ex = build_example(rng, tmpl, domain.name, eid)
            examples.append(ex)

    return examples


def generate_noise(rng: random.Random, count: int) -> list[dict]:
    """Generate noise examples with zero entities."""
    examples = []
    for i in range(count):
        text = rng.choice(NOISE_TEMPLATES)
        examples.append({
            "id": f"noise-{i+1:04d}",
            "domain": "noise",
            "text": text,
            "entities": [],
            "relationships": [],
            "memory_type": "fact",
        })
    return examples


def generate_cross_domain(rng: random.Random, count: int) -> list[dict]:
    """Generate cross-domain examples mixing entity types."""
    examples = []
    for i in range(count):
        tmpl = rng.choice(CROSS_DOMAIN_TEMPLATES)
        eid = f"cross-{i+1:04d}"
        ex = build_example(rng, tmpl, "cross_domain", eid)
        examples.append(ex)
    return examples


def write_jsonl(examples: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(json.dumps(ex, ensure_ascii=False) + "\n")


def run(
    domain_filter: str | None,
    dry_run: bool,
    seed: int,
) -> int:
    rng = random.Random(seed)

    plan: list[tuple[str, int]] = []
    if domain_filter:
        domain_map = {d.name: d for d in ALL_DOMAINS}
        if domain_filter not in domain_map:
            print(f"ERROR: unknown domain '{domain_filter}'", file=sys.stderr)
            return 1
        d = domain_map[domain_filter]
        plan.append((d.name, d.total))
    else:
        for d in ALL_DOMAINS:
            plan.append((d.name, d.total))
        plan.append(("cross_domain", CROSS_DOMAIN_COUNT))
        plan.append(("noise", NOISE_COUNT))

    total = sum(c for _, c in plan)
    print(f"Plan: {total} examples", flush=True)
    for name, count in plan:
        print(f"  {name}: {count}", flush=True)

    if dry_run:
        print("\n--dry-run: stopping here.", flush=True)
        return 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_examples: list[dict] = []
    t0 = time.perf_counter()

    domain_map = {d.name: d for d in ALL_DOMAINS}
    for name, _ in plan:
        if name == "noise":
            examples = generate_noise(rng, NOISE_COUNT)
        elif name == "cross_domain":
            examples = generate_cross_domain(rng, CROSS_DOMAIN_COUNT)
        else:
            domain = domain_map[name]
            templates = DOMAIN_TEMPLATES.get(name, {})
            examples = generate_domain(rng, domain, templates)

        write_jsonl(examples, RAW_DIR / f"{name}.jsonl")
        all_examples.extend(examples)
        print(f"  {name}: {len(examples)} examples written", flush=True)

    elapsed = time.perf_counter() - t0
    print(f"\nDone in {elapsed:.1f}s. Total: {len(all_examples)} examples", flush=True)

    with_entities = sum(1 for ex in all_examples if ex["entities"])
    with_rels = sum(1 for ex in all_examples if ex["relationships"])
    print(f"  With entities: {with_entities} ({100*with_entities/len(all_examples):.1f}%)", flush=True)
    print(f"  With relationships: {with_rels} ({100*with_rels/len(all_examples):.1f}%)", flush=True)

    ent_count = sum(len(ex["entities"]) for ex in all_examples)
    rel_count = sum(len(ex["relationships"]) for ex in all_examples)
    print(f"  Total entities: {ent_count} (avg {ent_count/len(all_examples):.1f}/example)", flush=True)
    print(f"  Total relationships: {rel_count} (avg {rel_count/len(all_examples):.1f}/example)", flush=True)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate fine-tuning training data")
    parser.add_argument(
        "--domain", choices=["technical", "ai_coding", "personal", "knowledge"],
        help="Generate for one domain only",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show plan without generating")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    return run(args.domain, args.dry_run, args.seed)


if __name__ == "__main__":
    sys.exit(main())
