"""Evaluate small text classifier models on the gold test corpus with VRAM tracking."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import joblib
import torch

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT.parent / "docs" / "e2e" / "scripts" / "classification_eval" / "corpus" / "gold.jsonl"


def load_corpus():
    examples = []
    with CORPUS_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def eval_hf_classifier(name: str, path: str):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    base = torch.cuda.memory_allocated()

    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path).to("cuda")
    getattr(model, "eval")()

    params = sum(p.numel() for p in model.parameters())
    model_vram = (torch.cuda.memory_allocated() - base) / (1024 * 1024)

    id2label = model.config.id2label

    corpus = load_corpus()
    correct = 0
    errors = []
    latencies = []

    for ex in corpus:
        t0 = time.perf_counter()
        with torch.no_grad():
            inp = tokenizer(ex["text"], truncation=True, max_length=256, return_tensors="pt").to("cuda")
            pred_id = int(torch.argmax(model(**inp).logits[0]).item())
            pred = id2label[pred_id] if pred_id in id2label else id2label[str(pred_id)]
        latencies.append((time.perf_counter() - t0) * 1000)
        if pred == ex["type"]:
            correct += 1
        else:
            errors.append((ex["id"], ex["type"], pred, ex["difficulty"]))

    peak_vram = (torch.cuda.max_memory_allocated() - base) / (1024 * 1024)

    # Disk size
    disk_bytes = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            disk_bytes += os.path.getsize(os.path.join(root, f))

    return {
        "name": name,
        "params_m": params / 1e6,
        "disk_mb": disk_bytes / (1024 * 1024),
        "model_vram_mb": model_vram,
        "peak_vram_mb": peak_vram,
        "accuracy": correct / len(corpus),
        "avg_latency_ms": sum(latencies) / len(latencies),
        "errors": errors,
    }


def eval_setfit(name: str, path: str):
    from sentence_transformers import SentenceTransformer

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    base = torch.cuda.memory_allocated()

    encoder_path = os.path.join(path, "encoder")
    classifier_path = os.path.join(path, "classifier.joblib")

    encoder = SentenceTransformer(encoder_path, device="cuda")
    bundle = joblib.load(classifier_path)
    clf = bundle["clf"]
    labels = bundle["labels"]

    params = sum(p.numel() for p in encoder.parameters())
    model_vram = (torch.cuda.memory_allocated() - base) / (1024 * 1024)

    corpus = load_corpus()
    correct = 0
    errors = []
    latencies = []

    for ex in corpus:
        t0 = time.perf_counter()
        emb = encoder.encode([ex["text"]], convert_to_numpy=True, show_progress_bar=False)
        pred_id = int(clf.predict(emb)[0])
        pred = labels[pred_id]
        latencies.append((time.perf_counter() - t0) * 1000)
        if pred == ex["type"]:
            correct += 1
        else:
            errors.append((ex["id"], ex["type"], pred, ex["difficulty"]))

    peak_vram = (torch.cuda.max_memory_allocated() - base) / (1024 * 1024)

    disk_bytes = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            disk_bytes += os.path.getsize(os.path.join(root, f))

    return {
        "name": name,
        "params_m": params / 1e6,
        "disk_mb": disk_bytes / (1024 * 1024),
        "model_vram_mb": model_vram,
        "peak_vram_mb": peak_vram,
        "accuracy": correct / len(corpus),
        "avg_latency_ms": sum(latencies) / len(latencies),
        "errors": errors,
    }


if __name__ == "__main__":
    results = []
    results.append(eval_hf_classifier("ELECTRA-small", str(ROOT / "models" / "classifier-electra-small" / "best")))
    results.append(eval_hf_classifier("bge-small-en-v1.5", str(ROOT / "models" / "classifier-bge-small" / "best")))
    results.append(eval_setfit("SetFit (MiniLM-L6)", str(ROOT / "models" / "classifier-setfit-manual" / "best")))

    print()
    print("=" * 90)
    print(f"{'Model':<22} {'Params':>8} {'Disk':>8} {'VRAM':>8} {'Acc':>7} {'Latency':>9}")
    print("=" * 90)
    for r in results:
        print(f"{r['name']:<22} {r['params_m']:>7.1f}M {r['disk_mb']:>6.0f}MB {r['model_vram_mb']:>6.0f}MB {r['accuracy']:>6.1%} {r['avg_latency_ms']:>7.1f}ms")
    print("=" * 90)

    print("\nErrors per model:")
    for r in results:
        print(f"\n{r['name']} ({len(r['errors'])} errors):")
        for e in r['errors']:
            print(f"  {e[0]:<20} {e[1]} -> {e[2]} ({e[3]})")
