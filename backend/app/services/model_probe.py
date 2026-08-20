"""Parse a vendor's model-list response.

Shared by the wizard's probe and the authenticated provider probes. The two
wire shapes are OpenAI-compat (`{"data": [{"id": ...}]}`) and Ollama native
(`{"models": [{"name": ...}]}`); a vendor serving neither yields an empty
list rather than an error, because "no models listed" is a real answer.
"""
from __future__ import annotations


def parse_model_list(data: object) -> list[str]:
    models: list[str] = []
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            for entry in data["data"]:
                mid = entry.get("id") if isinstance(entry, dict) else None
                if isinstance(mid, str):
                    models.append(mid)
        elif isinstance(data.get("models"), list):
            for entry in data["models"]:
                mid = entry.get("name") if isinstance(entry, dict) else None
                if isinstance(mid, str):
                    models.append(mid)
    return sorted(set(models))
