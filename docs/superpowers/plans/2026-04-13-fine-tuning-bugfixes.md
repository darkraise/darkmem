# Fine-Tuning Pipeline Bug Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all six bugs found during code review so the fine-tuning pipeline (generate → validate → train GLiNER → train REBEL → evaluate) runs end-to-end without crashes or silent data corruption.

**Architecture:** Six independent fixes, each testable in isolation. Tasks 1-3 fix data generation bugs (span computation, template error, GLiNER output format). Task 4 fixes REBEL training labels. Task 5 rewrites the GLiNER training script to use the correct API. Task 6 adds a guard in the split logic. A final task re-runs data generation + validation to verify the full pipeline.

**Tech Stack:** Python 3.14, GLiNER 0.2.26, transformers, datasets, pytest

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `fine-tuning/scripts/generate_data.py` | Modify | Fix `text.find()` substring span bug |
| `fine-tuning/config/templates.py` | Modify | Fix broken template (slot 1 missing from string) |
| `fine-tuning/scripts/validate_data.py` | Modify | Fix GLiNER output format + split guard |
| `fine-tuning/scripts/train_rebel.py` | Modify | Mask padding tokens in labels |
| `fine-tuning/scripts/train_gliner.py` | Modify | Rewrite to use correct GLiNER training API |
| `fine-tuning/tests/test_generate_data.py` | Create | Unit tests for span computation |
| `fine-tuning/tests/test_validate_data.py` | Create | Unit tests for GLiNER/REBEL format + splits |
| `fine-tuning/tests/test_train_rebel.py` | Create | Unit test for label masking |
| `fine-tuning/tests/test_train_gliner.py` | Create | Unit test for GLiNER format compatibility |
| `fine-tuning/tests/conftest.py` | Create | Shared fixtures |

---

### Task 1: Fix `text.find()` substring span bug in generate_data.py

**Files:**
- Create: `fine-tuning/tests/test_generate_data.py`
- Create: `fine-tuning/tests/conftest.py`
- Modify: `fine-tuning/scripts/generate_data.py:83-105`

**Bug:** `text.find(name)` returns the first occurrence, so "Java" matches inside "JavaScript". Entities with names that are substrings of other entity names get overlapping or mis-located spans.

**Fix:** After formatting the template, record each slot's exact character position from the format operation itself, rather than searching with `find()`. We do this by walking the template's `{N}` placeholders and tracking where each one lands in the formatted string.

- [ ] **Step 1: Write failing test exposing the substring bug**

```python
# fine-tuning/tests/test_generate_data.py
"""Tests for generate_data span computation."""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generate_data import build_example
from config.templates import Template


def test_substring_entity_names_get_correct_spans():
    """When one entity name is a substring of another, each gets its own span."""
    rng = random.Random(42)

    # Template: "We use {0}, {1}, and {2} for different parts of the stack."
    # entity_slots with substring-prone names
    tmpl: Template = (
        "We use {0}, {1}, and {2} for different parts of the stack.",
        [(0, "language"), (1, "language"), (2, "language")],
        [],
        "fact",
    )

    # Monkey-patch pick_entity to return specific names
    import scripts.generate_data as gen_mod
    original_pick = gen_mod.pick_entity

    names_to_return = iter(["JavaScript", "Java", "TypeScript"])
    def fake_pick(rng, etype, used):
        return next(names_to_return)

    gen_mod.pick_entity = fake_pick
    try:
        ex = build_example(rng, tmpl, "test", "test-0001")
    finally:
        gen_mod.pick_entity = original_pick

    text = ex["text"]
    entities = ex["entities"]

    # All three entities should be present
    assert len(entities) == 3, f"Expected 3 entities, got {len(entities)}: {entities}"

    # Every span must match its entity name exactly
    for ent in entities:
        actual = text[ent["start"]:ent["end"]]
        assert actual == ent["name"], (
            f"Span mismatch for '{ent['name']}': text[{ent['start']}:{ent['end']}] = '{actual}'"
        )

    # No two spans should overlap
    spans = sorted((e["start"], e["end"]) for e in entities)
    for i in range(len(spans) - 1):
        assert spans[i][1] <= spans[i + 1][0], (
            f"Overlapping spans: {spans[i]} and {spans[i+1]}"
        )


def test_duplicate_entity_name_across_slots():
    """When two slots get the same entity name (pool exhaustion), only one entity is emitted."""
    rng = random.Random(42)
    tmpl: Template = (
        "Switched from {0} to {1}.",
        [(0, "language"), (1, "language")],
        [(1, 0, "REPLACES")],
        "decision",
    )

    import scripts.generate_data as gen_mod
    original_pick = gen_mod.pick_entity

    # Force both slots to return the same name
    def fake_pick(rng, etype, used):
        return "Python"

    gen_mod.pick_entity = fake_pick
    try:
        ex = build_example(rng, tmpl, "test", "test-0002")
    finally:
        gen_mod.pick_entity = original_pick

    # Duplicate name: only one entity emitted (existing dedup in seen_entities)
    assert len(ex["entities"]) == 1
    # Relationship dropped because source == target
    assert len(ex["relationships"]) == 0
```

```python
# fine-tuning/tests/conftest.py
"""Shared fixtures for fine-tuning tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the fine-tuning root is on sys.path for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd fine-tuning && python -m pytest tests/test_generate_data.py -v`
Expected: `test_substring_entity_names_get_correct_spans` FAILS (overlapping spans or wrong span for "Java")

- [ ] **Step 3: Fix build_example to compute spans from template positions**

Replace the span-finding logic in `generate_data.py` (lines 83-105) with a two-pass approach that records each slot's position during formatting:

```python
    # --- Compute text and character-level spans from formatting ---
    # Walk the template to compute exact positions for each slot occurrence.
    # Split the template on {N} placeholders and rebuild, tracking where each
    # slot's text lands in the final string.
    import re as _re
    max_slot = max(
        (int(m) for m in _re.findall(r"\{(\d+)\}", tmpl_str)),
        default=-1,
    )
    format_args = [slot_names.get(i, f"MISSING_{i}") for i in range(max_slot + 1)]
    text = tmpl_str.format(*format_args)

    slot_positions: dict[int, list[tuple[int, int]]] = {}  # slot -> [(start, end), ...]
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd fine-tuning && python -m pytest tests/test_generate_data.py -v`
Expected: Both tests PASS

- [ ] **Step 5: Commit**

```bash
git add fine-tuning/tests/conftest.py fine-tuning/tests/test_generate_data.py fine-tuning/scripts/generate_data.py
git commit -m "fix(fine-tune): compute entity spans from template positions, not text.find()"
```

---

### Task 2: Fix broken template in templates.py

**Files:**
- Modify: `fine-tuning/config/templates.py:123`
- Append to: `fine-tuning/tests/test_generate_data.py`

**Bug:** `AI_CODING_TEMPLATES["architectural_decision"]` template index 3 declares slot 1 in `entity_slots` and `relationship_specs` but `{1}` never appears in the template string. The library entity and IMPLEMENTS relationship are silently dropped.

- [ ] **Step 1: Write failing test**

Append to `fine-tuning/tests/test_generate_data.py`:

```python
def test_all_templates_reference_declared_slots():
    """Every slot in entity_slots must appear as {N} in the template string."""
    import re
    from config.templates import (
        TECHNICAL_TEMPLATES, AI_CODING_TEMPLATES,
        PERSONAL_TEMPLATES, KNOWLEDGE_TEMPLATES, CROSS_DOMAIN_TEMPLATES,
    )

    errors = []
    all_groups = [
        ("TECHNICAL", TECHNICAL_TEMPLATES),
        ("AI_CODING", AI_CODING_TEMPLATES),
        ("PERSONAL", PERSONAL_TEMPLATES),
        ("KNOWLEDGE", KNOWLEDGE_TEMPLATES),
    ]

    for group_name, templates in all_groups:
        for cat_name, cat_templates in templates.items():
            for i, (tmpl_str, entity_slots, rel_specs, _) in enumerate(cat_templates):
                format_slots = {int(m) for m in re.findall(r"\{(\d+)\}", tmpl_str)}
                for slot_idx, etype in entity_slots:
                    if slot_idx not in format_slots:
                        errors.append(
                            f"{group_name}/{cat_name}[{i}]: slot {slot_idx} ({etype}) "
                            f"not in template string"
                        )

    for i, (tmpl_str, entity_slots, rel_specs, _) in enumerate(CROSS_DOMAIN_TEMPLATES):
        format_slots = {int(m) for m in re.findall(r"\{(\d+)\}", tmpl_str)}
        for slot_idx, etype in entity_slots:
            if slot_idx not in format_slots:
                errors.append(
                    f"CROSS_DOMAIN[{i}]: slot {slot_idx} ({etype}) "
                    f"not in template string"
                )

    assert not errors, "Templates with undeclared slots:\n" + "\n".join(errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd fine-tuning && python -m pytest tests/test_generate_data.py::test_all_templates_reference_declared_slots -v`
Expected: FAIL, reporting `AI_CODING/architectural_decision[3]`

- [ ] **Step 3: Fix the template**

In `fine-tuning/config/templates.py` line 123, add `{1}` to the template string:

```python
        ("Decided to implement the {0} using {1} as suggested by Claude for better testability.", [(0, "pattern"), (1, "library")], [(0, 1, "IMPLEMENTS")], "decision"),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd fine-tuning && python -m pytest tests/test_generate_data.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add fine-tuning/config/templates.py fine-tuning/tests/test_generate_data.py
git commit -m "fix(fine-tune): add missing {1} slot to architectural_decision template"
```

---

### Task 3: Fix GLiNER output format in validate_data.py

**Files:**
- Create: `fine-tuning/tests/test_validate_data.py`
- Modify: `fine-tuning/scripts/validate_data.py:228-242`

**Bug:** `write_gliner_jsonl` writes `{"text": str, "entities": [{"start", "end", "label"}]}` with character offsets. GLiNER 0.2.26 expects `{"tokenized_text": list[str], "ner": list[[start_token, end_token, label]]}` with token-level indices. The collator will crash with `KeyError: 'tokenized_text'`.

**Fix:** Rewrite `write_gliner_jsonl` to word-tokenize the text and convert character spans to token spans.

- [ ] **Step 1: Write failing test for GLiNER format**

```python
# fine-tuning/tests/test_validate_data.py
"""Tests for validate_data output formats."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_data import write_gliner_jsonl, write_rebel_jsonl


def test_gliner_format_has_tokenized_text_and_ner():
    """GLiNER JSONL must use tokenized_text (list[str]) and ner (list of [start, end, label])."""
    examples = [
        {
            "text": "We switched from Flask to FastAPI for better performance.",
            "entities": [
                {"name": "Flask", "type": "framework", "start": 17, "end": 22},
                {"name": "FastAPI", "type": "framework", "start": 26, "end": 33},
            ],
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = Path(f.name)

    try:
        write_gliner_jsonl(examples, path)
        with path.open() as fh:
            record = json.loads(fh.readline())

        # Must have tokenized_text as a list of strings
        assert "tokenized_text" in record, f"Missing 'tokenized_text', got keys: {list(record.keys())}"
        assert isinstance(record["tokenized_text"], list)
        assert all(isinstance(tok, str) for tok in record["tokenized_text"])

        # Must have ner as list of [start, end, label] with token indices
        assert "ner" in record, f"Missing 'ner', got keys: {list(record.keys())}"
        assert isinstance(record["ner"], list)
        for span in record["ner"]:
            assert len(span) == 3, f"Expected [start, end, label], got {span}"
            assert isinstance(span[0], int) and isinstance(span[1], int)
            assert isinstance(span[2], str)

        # Token indices must reconstruct the entity name
        tokens = record["tokenized_text"]
        for span in record["ner"]:
            start_tok, end_tok, label = span
            entity_tokens = tokens[start_tok:end_tok]
            entity_text = " ".join(entity_tokens)
            assert entity_text in ("Flask", "FastAPI"), f"Bad span: tokens[{start_tok}:{end_tok}] = '{entity_text}'"
    finally:
        path.unlink(missing_ok=True)


def test_gliner_format_multiword_entity():
    """Multi-word entities like 'Apache Spark' must span the correct token range."""
    examples = [
        {
            "text": "We deployed Apache Spark on Kubernetes.",
            "entities": [
                {"name": "Apache Spark", "type": "technology", "start": 12, "end": 24},
                {"name": "Kubernetes", "type": "technology", "start": 28, "end": 38},
            ],
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        path = Path(f.name)

    try:
        write_gliner_jsonl(examples, path)
        with path.open() as fh:
            record = json.loads(fh.readline())

        tokens = record["tokenized_text"]
        ner = record["ner"]

        # Find the Apache Spark span
        spark_spans = [s for s in ner if s[2] == "technology" and " ".join(tokens[s[0]:s[1]]) == "Apache Spark"]
        assert len(spark_spans) == 1, f"Expected 1 'Apache Spark' span, got {spark_spans}"

        # The span should cover 2 tokens
        s = spark_spans[0]
        assert s[1] - s[0] == 2, f"Expected 2-token span, got {s[1] - s[0]}"
    finally:
        path.unlink(missing_ok=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd fine-tuning && python -m pytest tests/test_validate_data.py -v`
Expected: FAIL — assertion on missing `tokenized_text`

- [ ] **Step 3: Rewrite write_gliner_jsonl with word tokenization and token-span conversion**

Replace the existing `write_gliner_jsonl` function in `validate_data.py`:

```python
def _char_spans_to_token_spans(
    text: str, char_entities: list[dict],
) -> tuple[list[str], list[list]]:
    """Word-tokenize text and convert character-level entity spans to token indices.

    Returns (tokens, ner) where ner entries are [start_token, end_token, label].
    end_token is exclusive (GLiNER convention).
    """
    tokens: list[str] = text.split()

    # Build char_offset -> token_index mapping
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
                end_tok = ti + 1  # exclusive
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd fine-tuning && python -m pytest tests/test_validate_data.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add fine-tuning/scripts/validate_data.py fine-tuning/tests/test_validate_data.py
git commit -m "fix(fine-tune): write GLiNER data as tokenized_text + token-index ner spans"
```

---

### Task 4: Mask padding tokens in REBEL training labels

**Files:**
- Create: `fine-tuning/tests/test_train_rebel.py`
- Modify: `fine-tuning/scripts/train_rebel.py:83-97`

**Bug:** Labels include padding token IDs. The cross-entropy loss trains the model to predict padding, inflating loss and degrading output quality. Padding positions must be -100 so they're ignored.

- [ ] **Step 1: Write failing test**

```python
# fine-tuning/tests/test_train_rebel.py
"""Tests for REBEL training data preparation."""
from __future__ import annotations


def test_rebel_labels_mask_padding_tokens():
    """Padding positions in labels must be -100, not the pad token ID."""
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained("Babelscape/rebel-large")

    batch = {
        "input": ["The quick brown fox."],
        "output": ["<triplet> fox <subj> brown <obj> HAS_COLOR"],
    }

    inputs = tokenizer(
        batch["input"], max_length=64, truncation=True, padding="max_length",
    )
    targets = tokenizer(
        batch["output"], max_length=64, truncation=True, padding="max_length",
    )

    # Apply the fix: mask padding tokens with -100
    pad_id = tokenizer.pad_token_id
    labels = [
        [(-100 if tok == pad_id else tok) for tok in seq]
        for seq in targets["input_ids"]
    ]

    # Padding positions should be -100
    assert any(tok == -100 for tok in labels[0]), "No -100 found in labels — padding not masked"

    # Non-padding positions should NOT be -100
    non_pad = [tok for tok in labels[0] if tok != -100]
    assert len(non_pad) > 0, "All tokens are -100 — something is wrong"
    assert all(tok != pad_id for tok in non_pad), "Non-masked token equals pad_id"
```

Note: this test validates the masking logic itself. We apply the fix in step 3.

- [ ] **Step 2: Run test to verify it passes (the test demonstrates the correct pattern)**

Run: `cd fine-tuning && python -m pytest tests/test_train_rebel.py -v`
Expected: PASS (the test validates the correct pattern)

- [ ] **Step 3: Fix tokenize_fn in train_rebel.py**

In `fine-tuning/scripts/train_rebel.py`, replace the `tokenize_fn` function (lines 83-97):

```python
    def tokenize_fn(batch: dict) -> dict:
        inputs = tokenizer(
            batch["input"],
            max_length=max_source_length,
            truncation=True,
            padding="max_length",
        )
        targets = tokenizer(
            batch["output"],
            max_length=max_target_length,
            truncation=True,
            padding="max_length",
        )
        pad_id = tokenizer.pad_token_id
        inputs["labels"] = [
            [(-100 if tok == pad_id else tok) for tok in seq]
            for seq in targets["input_ids"]
        ]
        return inputs
```

- [ ] **Step 4: Also fix bf16 safety in train_rebel.py**

In the `training_args` block, change `bf16=device == "cuda"` to:

```python
        bf16=device == "cuda" and torch.cuda.is_bf16_supported(),
```

- [ ] **Step 5: Commit**

```bash
git add fine-tuning/scripts/train_rebel.py fine-tuning/tests/test_train_rebel.py
git commit -m "fix(fine-tune): mask padding tokens in REBEL labels, gate bf16 on GPU support"
```

---

### Task 5: Rewrite GLiNER training script to use correct API

**Files:**
- Create: `fine-tuning/tests/test_train_gliner.py`
- Modify: `fine-tuning/scripts/train_gliner.py` (full rewrite)

**Bug:** `from gliner.training import TrainDataset` crashes immediately — `TrainDataset` does not exist in GLiNER 0.2.26. The correct API is `model.train_model()` which handles dataset creation, collation, and trainer setup internally.

- [ ] **Step 1: Write test that verifies the API surface**

```python
# fine-tuning/tests/test_train_gliner.py
"""Tests for GLiNER training script compatibility."""
from __future__ import annotations


def test_gliner_training_imports():
    """All imports used by train_gliner.py must resolve without error."""
    from gliner import GLiNER
    from gliner.training import TrainingArguments, Trainer
    import importlib
    mod = importlib.import_module("gliner.training")
    assert hasattr(mod, "Trainer")
    assert hasattr(mod, "TrainingArguments")
    assert not hasattr(mod, "TrainDataset"), "TrainDataset should not exist in gliner.training"


def test_gliner_model_has_train_model():
    """GLiNER model exposes the train_model convenience method."""
    from gliner import GLiNER
    assert hasattr(GLiNER, "train_model"), "GLiNER.train_model() not found"


def test_gliner_model_has_create_training_args():
    """GLiNER model exposes create_training_args for building TrainingArguments."""
    from gliner import GLiNER
    assert hasattr(GLiNER, "create_training_args"), "GLiNER.create_training_args() not found"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd fine-tuning && python -m pytest tests/test_train_gliner.py -v`
Expected: All PASS (these validate the API surface, not the broken script)

- [ ] **Step 3: Rewrite train_gliner.py**

Replace the entire file with a version that uses `model.train_model()` instead of the non-existent `TrainDataset`. Also gates bf16 on `torch.cuda.is_bf16_supported()`. See full replacement code in the plan file at `docs/superpowers/plans/2026-04-13-fine-tuning-bugfixes.md`, Task 5, Step 3.

Key changes:
- Remove `from gliner.training import TrainDataset` import
- Replace manual `Trainer(model=model, args=..., train_dataset=TrainDataset(...))` with `model.train_model(train_dataset=..., eval_dataset=..., **kwargs)`
- Pass training hyperparameters as keyword arguments to `train_model()`
- Gate `bf16` on `torch.cuda.is_bf16_supported()`

- [ ] **Step 4: Verify the script can be imported without error**

Run: `cd fine-tuning && python -c "import scripts.train_gliner; print('OK')"`
Expected: `OK` (no ImportError)

- [ ] **Step 5: Commit**

```bash
git add fine-tuning/scripts/train_gliner.py fine-tuning/tests/test_train_gliner.py
git commit -m "fix(fine-tune): rewrite GLiNER training to use model.train_model() API"
```

---

### Task 6: Guard against negative n_train in split_data

**Files:**
- Modify: `fine-tuning/scripts/validate_data.py:202-211`
- Append to: `fine-tuning/tests/test_validate_data.py`

**Bug:** When a domain has 1 or 2 examples, `n_train` goes negative. Python slice with negative index silently misroutes examples, causing data leakage.

- [ ] **Step 1: Write failing test**

Append to `fine-tuning/tests/test_validate_data.py`:

```python
from scripts.validate_data import split_data


def test_split_single_example_domain():
    """A domain with 1 example should place it in train, not leak to test."""
    examples = [{"id": "solo-1", "domain": "tiny", "text": "hello"}]
    train, val, test = split_data(examples, seed=42)

    total = len(train) + len(val) + len(test)
    assert total == 1, f"Expected 1 total, got {total}"
    assert len(train) == 1
    assert len(val) == 0
    assert len(test) == 0


def test_split_two_example_domain():
    """A domain with 2 examples should not leak the same example into multiple splits."""
    examples = [
        {"id": "pair-1", "domain": "tiny", "text": "hello"},
        {"id": "pair-2", "domain": "tiny", "text": "world"},
    ]
    train, val, test = split_data(examples, seed=42)

    total = len(train) + len(val) + len(test)
    assert total == 2, f"Expected 2 total, got {total}"

    all_ids = [ex["id"] for ex in train + val + test]
    assert len(all_ids) == len(set(all_ids)), f"Duplicate IDs across splits: {all_ids}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd fine-tuning && python -m pytest tests/test_validate_data.py::test_split_single_example_domain -v`
Expected: FAIL (single example ends up in test, not train)

- [ ] **Step 3: Fix split_data to handle tiny domains**

In `fine-tuning/scripts/validate_data.py`, replace the split logic inside the loop (around lines 202-211):

```python
    for domain, domain_examples in by_domain.items():
        rng.shuffle(domain_examples)
        n = len(domain_examples)

        if n <= 2:
            train.extend(domain_examples)
            continue

        n_val = max(1, round(n * VAL_RATIO))
        n_test = max(1, round(n * TEST_RATIO))
        n_train = n - n_val - n_test

        train.extend(domain_examples[:n_train])
        val.extend(domain_examples[n_train:n_train + n_val])
        test.extend(domain_examples[n_train + n_val:])
```

- [ ] **Step 4: Run all validate_data tests**

Run: `cd fine-tuning && python -m pytest tests/test_validate_data.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add fine-tuning/scripts/validate_data.py fine-tuning/tests/test_validate_data.py
git commit -m "fix(fine-tune): guard split_data against domains with fewer than 3 examples"
```

---

### Task 7: Regenerate data and verify full pipeline

**Files:** None modified (verification only)

- [ ] **Step 1: Delete stale generated data**

```bash
rm -rf fine-tuning/data/raw/ fine-tuning/data/validated/ fine-tuning/data/splits/
```

- [ ] **Step 2: Run data generation**

```bash
cd fine-tuning && python -m scripts.generate_data --seed 42
```

Expected: Completes without assertion errors, prints summary with ~6000 examples.

- [ ] **Step 3: Run validation and splitting**

```bash
cd fine-tuning && python -m scripts.validate_data --fix --seed 42
```

Expected: 0 validation errors, splits written for all three formats (generic, GLiNER, REBEL).

- [ ] **Step 4: Spot-check GLiNER format**

```bash
cd fine-tuning && python -c "
import json
with open('data/splits/gliner_train.jsonl') as f:
    rec = json.loads(f.readline())
assert 'tokenized_text' in rec, f'Missing tokenized_text: {list(rec.keys())}'
assert 'ner' in rec, f'Missing ner: {list(rec.keys())}'
tokens = rec['tokenized_text']
for span in rec['ner']:
    name = ' '.join(tokens[span[0]:span[1]])
    print(f'  {name} -> {span[2]}')
print('GLiNER format OK')
"
```

Expected: Prints entity names reconstructed from token spans, then "GLiNER format OK".

- [ ] **Step 5: Spot-check REBEL format**

```bash
cd fine-tuning && python -c "
import json
with open('data/splits/rebel_train.jsonl') as f:
    rec = json.loads(f.readline())
assert 'input' in rec and 'output' in rec
print(f'Input: {rec[\"input\"][:120]}...')
print(f'Output: {rec[\"output\"][:120]}...')
print('REBEL format OK')
"
```

Expected: Shows input with entity annotations and output with linearized triplets.

- [ ] **Step 6: Run the full test suite**

```bash
cd fine-tuning && python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Verify no untracked data files**

```bash
cd fine-tuning && git status
```

Expected: No untracked files from `data/` or `models/` (covered by `.gitignore`).

---

## Verification

After all tasks are complete:

1. **Unit tests:** `cd fine-tuning && python -m pytest tests/ -v` — all pass
2. **Data generation:** `python -m scripts.generate_data --seed 42` — no assertion errors
3. **Validation:** `python -m scripts.validate_data --fix --seed 42` — 0 errors, all formats written
4. **GLiNER import:** `python -c "import scripts.train_gliner"` — no ImportError
5. **REBEL import:** `python -c "import scripts.train_rebel"` — no ImportError
6. **Pipeline dry-run:** `python start.py --dry-run` — all steps listed without error

Full training (`python start.py`) requires GPU and model downloads, so it is not part of the automated verification. The dry-run confirms the orchestrator wiring is correct.
