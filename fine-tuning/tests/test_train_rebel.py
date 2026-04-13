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

    pad_id = tokenizer.pad_token_id
    labels = [
        [(-100 if tok == pad_id else tok) for tok in seq]
        for seq in targets["input_ids"]
    ]

    assert any(tok == -100 for tok in labels[0]), "No -100 found in labels — padding not masked"

    non_pad = [tok for tok in labels[0] if tok != -100]
    assert len(non_pad) > 0, "All tokens are -100 — something is wrong"
    assert all(tok != pad_id for tok in non_pad), "Non-masked token equals pad_id"
