"""Canonical entity/relationship type definitions and tool schemas for extraction.

Single source of truth — imported by extraction.py (JSON validation),
prompt.py (prompt generation), and tool call schemas. Types are re-exported
from ``app.taxonomy`` so the LLM and ML extraction heads stay in lock-step.
"""

from app.taxonomy import (
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    normalize_entity_type,
    normalize_relation_type,
)


__all__ = [
    "ENTITY_TYPES",
    "RELATIONSHIP_TYPES",
    "normalize_entity_type",
    "normalize_relation_type",
    "build_extraction_schema",
    "FLAT_ENTITY_TOOL",
    "FLAT_RELATIONSHIP_TOOL",
    "NESTED_EXTRACT_TOOL",
    "tools_for_mode",
]


def build_extraction_schema() -> str:
    entity_types = "|".join(ENTITY_TYPES)
    rel_types = "|".join(RELATIONSHIP_TYPES)
    return (
        "{\n"
        f'  "entities": [{{"name": "string", "type": "{entity_types}", "properties": {{}}}}],\n'
        f'  "relationships": [{{"source": "entity_name", "target": "entity_name", "type": "{rel_types}", "properties": {{}}, "weight": 0.8}}],\n'
        '  "memory_type": "fact|decision|preference|problem|reference|architecture|milestone",\n'
        '  "importance": 0.7\n'
        "}"
    )


# ── Flat tool schemas (for small models like Qwen2.5:3b) ────────────

FLAT_ENTITY_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "add_entity",
        "description": "Add a single entity found in the text.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Entity name (specific named thing, not generic nouns)"},
                "type": {"type": "string", "enum": ENTITY_TYPES, "description": "Entity type"},
            },
            "required": ["name", "type"],
            "additionalProperties": False,
        },
    },
}

FLAT_RELATIONSHIP_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "add_relationship",
        "description": "Add a relationship between two entities.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source entity name"},
                "target": {"type": "string", "description": "Target entity name"},
                "type": {"type": "string", "enum": RELATIONSHIP_TYPES, "description": "Relationship type"},
                "confidence": {"type": "number", "description": "Confidence score 0.0-1.0"},
            },
            "required": ["source", "target", "type"],
            "additionalProperties": False,
        },
    },
}


# ── Nested tool schema (for larger models) ──────────────────────────

NESTED_EXTRACT_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "extract",
        "description": "Extract all entities and relationships from the text.",
        "parameters": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string", "enum": ENTITY_TYPES},
                        },
                        "required": ["name", "type"],
                        "additionalProperties": False,
                    },
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "type": {"type": "string", "enum": RELATIONSHIP_TYPES},
                            "confidence": {"type": "number"},
                        },
                        "required": ["source", "target", "type"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["entities", "relationships"],
            "additionalProperties": False,
        },
    },
}


def tools_for_mode(mode: str, step: str = "all") -> list[dict]:
    if mode == "flat":
        if step == "entities":
            return [FLAT_ENTITY_TOOL]
        elif step == "relationships":
            return [FLAT_RELATIONSHIP_TOOL]
        return [FLAT_ENTITY_TOOL, FLAT_RELATIONSHIP_TOOL]
    elif mode == "nested":
        return [NESTED_EXTRACT_TOOL]
    return []
