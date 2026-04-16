"""Phase 5: load all 4 extraction heads on the GPU and report VRAM cost.

Measures the idle VRAM footprint when the classifier, retriever, a GLiNER
variant (small or large), and REBEL-large are all resident at once, with
qwen3.5:4b also warm-loaded in ollama. Reports per-model torch allocations
and the total nvidia-smi figure (which includes driver/reserved overhead
and the ollama-resident model).

Writes JSON to runs/2026-04-16-training-session/vram_coload.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "2026-04-16-training-session"
MODELS_DIR = ROOT / "models"


def nvidia_smi_used_mb() -> int | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            timeout=10,
        )
        return int(out.strip().splitlines()[0])
    except Exception as exc:
        print(f"nvidia-smi read failed: {exc}", file=sys.stderr)
        return None


def check_ollama() -> dict:
    info: dict = {"docker_ps": None, "tags": None}
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--filter", "name=ollama", "--format", "{{.Names}} {{.Status}}"],
            text=True,
            timeout=10,
        )
        info["docker_ps"] = out.strip() or "(no ollama container running)"
    except Exception as exc:
        info["docker_ps"] = f"error: {exc}"
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
            info["tags"] = json.loads(r.read().decode())
    except Exception as exc:
        info["tags"] = f"error: {exc}"
    return info


def _torch_allocated_mb() -> float:
    import torch
    if not torch.cuda.is_available():
        return 0.0
    return torch.cuda.memory_allocated() / 1e6


def load_classifier(path: Path):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch
    tok = AutoTokenizer.from_pretrained(str(path))
    mdl = AutoModelForSequenceClassification.from_pretrained(str(path))
    if torch.cuda.is_available():
        mdl = mdl.to("cuda")
    mdl.train(False)
    return (tok, mdl)


def load_retriever(path: Path):
    import torch
    from sentence_transformers import SentenceTransformer
    mdl = SentenceTransformer(str(path), device="cuda" if torch.cuda.is_available() else "cpu")
    return mdl


def load_gliner(path: Path):
    import torch
    from gliner import GLiNER
    mdl = GLiNER.from_pretrained(str(path))
    if torch.cuda.is_available():
        mdl = mdl.to("cuda")
    return mdl


def load_rebel(path: Path):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(path))
    mdl = AutoModelForSeq2SeqLM.from_pretrained(str(path))
    if torch.cuda.is_available():
        mdl = mdl.to("cuda")
    mdl.train(False)
    return (tok, mdl)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--classifier", type=Path,
                   default=MODELS_DIR / "classifier-v3aug2-modernbert-base" / "best")
    p.add_argument("--retriever", type=Path,
                   default=MODELS_DIR / "retriever-bge-base-7500clean-hn-ep5-b64")
    p.add_argument("--gliner-small", type=Path,
                   default=MODELS_DIR / "gliner-small-v2corpus" / "best")
    p.add_argument("--gliner-large", type=Path,
                   default=MODELS_DIR / "gliner-large-v2corpus" / "best")
    p.add_argument("--rebel", type=Path,
                   default=MODELS_DIR / "rebel-large-v2corpus" / "best")
    p.add_argument("--out", type=Path, default=RUN_DIR / "vram_coload.json")
    args = p.parse_args()

    import torch

    report: dict = {
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ollama": check_ollama(),
        "variants": {},
    }
    if torch.cuda.is_available():
        report["gpu_name"] = torch.cuda.get_device_name(0)
        report["gpu_total_mb"] = torch.cuda.get_device_properties(0).total_memory / 1e6

    baseline_smi = nvidia_smi_used_mb()
    report["baseline_nvidia_smi_mb"] = baseline_smi

    for label, gliner_path in [("with_gliner_small", args.gliner_small),
                                ("with_gliner_large", args.gliner_large)]:
        print(f"\n=== {label} ===", flush=True)
        if not gliner_path.exists():
            report["variants"][label] = {"error": f"missing {gliner_path}"}
            continue

        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        mdls = {}
        steps = [
            ("classifier", args.classifier, load_classifier),
            ("retriever", args.retriever, load_retriever),
            ("gliner", gliner_path, load_gliner),
            ("rebel", args.rebel, load_rebel),
        ]
        per_step = []
        for name, path, loader in steps:
            if not path.exists():
                per_step.append({"model": name, "path": str(path), "error": "missing"})
                continue
            before = _torch_allocated_mb()
            try:
                mdls[name] = loader(path)
            except Exception as exc:
                per_step.append({"model": name, "path": str(path), "error": f"load failed: {exc}"})
                continue
            after = _torch_allocated_mb()
            smi = nvidia_smi_used_mb()
            per_step.append({
                "model": name,
                "path": str(path),
                "torch_allocated_delta_mb": after - before,
                "torch_allocated_cumulative_mb": after,
                "nvidia_smi_used_mb": smi,
            })
            print(f"  {name}: +{after-before:.0f} MB (torch cumulative {after:.0f}, nvidia-smi {smi})", flush=True)

        report["variants"][label] = {
            "per_step": per_step,
            "torch_total_allocated_mb": _torch_allocated_mb(),
            "nvidia_smi_used_mb_final": nvidia_smi_used_mb(),
        }

        # free before next variant
        mdls.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {args.out}", flush=True)

    # Quick summary
    for label, v in report["variants"].items():
        if "error" in v:
            print(f"{label}: {v['error']}")
            continue
        print(f"{label}: torch {v['torch_total_allocated_mb']:.0f} MB, "
              f"nvidia-smi {v['nvidia_smi_used_mb_final']} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
