# fine-tuning/scripts/eval_baseline_qwen.py
"""qwen3.5:4b prompted baseline runner for all three tasks."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
import requests

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_PATH = ROOT / "config" / "prompts_v2.yaml"
TAXONOMY_PATH = ROOT / "config" / "taxonomy_v2.yaml"


def load_prompts() -> dict:
    with PROMPTS_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_taxonomy() -> dict:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_entity_list(entities: list[dict]) -> str:
    return "\n".join(f"- {e['name']} ({e['type']})" for e in entities)


def call_ollama(system: str, user: str, model: str, options: dict, format: str = "json") -> str:
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": options,
            "format": format,
            "stream": False,
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def run_entity(text: str, prompts: dict, entity_types: list[str], model: str = "qwen3.5:4b", options: dict | None = None) -> list[dict]:
    options = options or {"temperature": 0.0, "seed": 42}
    system = prompts["system"].replace("{ENTITY_TYPES}", ", ".join(entity_types))
    user = prompts["user_template"].format(text=text)
    raw = call_ollama(system, user, model=model, options=options)
    try:
        data = json.loads(raw)
        return data.get("entities", [])
    except json.JSONDecodeError:
        return []


def run_relation(text: str, entities: list[dict], prompts: dict, relation_types: list[str], model: str = "qwen3.5:4b", options: dict | None = None) -> list[dict]:
    options = options or {"temperature": 0.0, "seed": 42}
    system = prompts["system"].replace("{RELATION_TYPES}", ", ".join(relation_types))
    user = prompts["user_template"].format(text=text, entity_list=format_entity_list(entities))
    raw = call_ollama(system, user, model=model, options=options)
    try:
        data = json.loads(raw)
        return data.get("relationships", [])
    except json.JSONDecodeError:
        return []


def run_classification(text: str, prompts: dict, model: str = "qwen3.5:4b", options: dict | None = None) -> str:
    options = options or {"temperature": 0.0, "seed": 42}
    user = prompts["user_template"].format(text=text)
    raw = call_ollama(prompts["system"], user, model=model, options=options)
    try:
        data = json.loads(raw)
        return data.get("memory_type", "")
    except json.JSONDecodeError:
        return ""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True, choices=["entity", "relation", "classification"])
    p.add_argument("--input", type=Path, required=True, help="test split JSONL")
    p.add_argument("--output", type=Path, required=True, help="predictions JSONL")
    args = p.parse_args()

    prompts_all = load_prompts()
    taxonomy = load_taxonomy()
    model = prompts_all["ollama"]["model"]
    options = prompts_all["ollama"]["options"]
    entity_types = [t for group in taxonomy["entity_types"].values() for t in group]
    relation_types = taxonomy["relation_types"]["core"] + taxonomy["relation_types"]["extended"]
    task_prompts = prompts_all[args.task if args.task != "classification" else "classification"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.input.open("r", encoding="utf-8") as fi, args.output.open("w", encoding="utf-8") as fo:
        for line in fi:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if args.task == "entity":
                pred = run_entity(row["text"], task_prompts, entity_types, model=model, options=options)
                fo.write(json.dumps({"id": row["id"], "entities": pred}) + "\n")
            elif args.task == "relation":
                pred = run_relation(row["text"], row.get("entities", []), task_prompts, relation_types, model=model, options=options)
                fo.write(json.dumps({"id": row["id"], "relationships": pred}) + "\n")
            else:
                pred = run_classification(row["text"], task_prompts, model=model, options=options)
                fo.write(json.dumps({"id": row["id"], "memory_type": pred}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
