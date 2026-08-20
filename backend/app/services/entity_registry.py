"""
entity_registry.py — Persistent personal entity registry.

Ported from MemPalace's entity_registry.py. Pure logic module — no darkmem
imports, no async, no database access.

Source priority (highest → lowest):
  onboarding — explicitly told by user
  learned    — inferred from session history with high confidence
  wiki       — confirmed via Wikipedia research

Storage: JSON file at registry_path (default: ~/.darkmem/entity_registry.json).
Schema maps entity names to 3-letter AAAK codes.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional


# =============================================================================
# AMBIGUOUS WORDS
# =============================================================================

COMMON_ENGLISH_WORDS: set[str] = {
    "ever", "grace", "will", "bill", "mark", "april", "may", "june",
    "joy", "hope", "faith", "chance", "chase", "hunter", "dash", "flash",
    "star", "sky", "river", "brook", "lane", "art", "clay", "gil", "nat",
    "max", "rex", "ray", "jay", "rose", "violet", "lily", "ivy", "ash",
    "reed", "sage",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "january", "february", "march", "april", "june", "july",
    "august", "september", "october", "november", "december",
}

# Context patterns that indicate the word is used as a PERSON name
_PERSON_CONTEXT_PATTERNS: list[str] = [
    r"\b{name}\s+said\b",
    r"\b{name}\s+told\b",
    r"\b{name}\s+asked\b",
    r"\b{name}\s+laughed\b",
    r"\b{name}\s+smiled\b",
    r"\b{name}\s+was\b",
    r"\b{name}\s+is\b",
    r"\b{name}\s+called\b",
    r"\b{name}\s+texted\b",
    r"\bwith\s+{name}\b",
    r"\bsaw\s+{name}\b",
    r"\bcalled\s+{name}\b",
    r"\btook\s+{name}\b",
    r"\bpicked\s+up\s+{name}\b",
    r"\bdrop(?:ped)?\s+(?:off\s+)?{name}\b",
    r"\b{name}(?:'s|s')\b",
    r"\bhey\s+{name}\b",
    r"\bthanks?\s+{name}\b",
    r"^{name}[:\s]",
    r"\bmy\s+(?:son|daughter|kid|child|brother|sister|friend|partner|colleague|coworker)\s+{name}\b",
]

# Context patterns that indicate the word is NOT used as a name
_CONCEPT_CONTEXT_PATTERNS: list[str] = [
    r"\bhave\s+you\s+{name}\b",
    r"\bif\s+you\s+{name}\b",
    r"\b{name}\s+since\b",
    r"\b{name}\s+again\b",
    r"\bnot\s+{name}\b",
    r"\b{name}\s+more\b",
    r"\bwould\s+{name}\b",
    r"\bcould\s+{name}\b",
    r"\bwill\s+{name}\b",
    r"(?:the\s+)?{name}\s+(?:of|in|at|for|to)\b",
]


def _context_disambiguate(
    name: str, context: str, person_info: dict
) -> Optional[dict]:
    """Check surrounding sentence to determine if an ambiguous word is a name.

    Args:
        name: Word to disambiguate.
        context: Surrounding sentence text.
        person_info: Registry entry for this name.

    Returns:
        Classification dict if determinable, or None if genuinely ambiguous.
    """
    name_lower = name.lower()
    ctx_lower = context.lower()

    person_score = sum(
        1
        for pat in _PERSON_CONTEXT_PATTERNS
        if re.search(pat.format(name=re.escape(name_lower)), ctx_lower)
    )
    concept_score = sum(
        1
        for pat in _CONCEPT_CONTEXT_PATTERNS
        if re.search(pat.format(name=re.escape(name_lower)), ctx_lower)
    )

    if person_score > concept_score:
        return {
            "type": "person",
            "confidence": min(0.95, 0.7 + person_score * 0.1),
            "source": person_info["source"],
            "name": name,
            "needs_disambiguation": False,
            "disambiguated_by": "context_patterns",
        }
    if concept_score > person_score:
        return {
            "type": "concept",
            "confidence": min(0.90, 0.7 + concept_score * 0.1),
            "source": "context_disambiguated",
            "name": name,
            "needs_disambiguation": False,
            "disambiguated_by": "context_patterns",
        }
    return None


# =============================================================================
# ENTITY REGISTRY
# =============================================================================

_PRIORITY: dict[str, int] = {"onboarding": 3, "learned": 2, "wiki": 1}


def _code_for(name: str) -> str:
    """Generate a 3-letter uppercase AAAK code from a name."""
    return name[:3].upper()


class EntityRegistry:
    """Persistent entity registry mapping names to 3-letter AAAK codes.

    Storage schema (JSON):
    {
      "version": 1,
      "people": {
        "Alice": {
          "code": "ALC",
          "source": "onboarding",
          "confidence": 1.0,
          "relationship": "colleague",
          "aliases": ["Ali"]
        }
      },
      "projects": {
        "DarkMem": {"code": "DAR", "source": "onboarding"}
      },
      "ambiguous_flags": ["may", "joy"],
    }
    """

    DEFAULT_PATH: Path = Path.home() / ".darkmem" / "entity_registry.json"

    def __init__(self, data: dict, path: Path) -> None:
        self._data = data
        self._path = path

    # ── Load / Save ──────────────────────────────────────────────────────────

    @classmethod
    def load(cls, registry_path: Optional[Path] = None) -> "EntityRegistry":
        """Load the registry from disk, or create an empty one.

        Args:
            registry_path: Path to the JSON file. Defaults to
                           ~/.darkmem/entity_registry.json.

        Returns:
            Loaded or freshly initialised EntityRegistry.
        """
        path = Path(registry_path) if registry_path else cls.DEFAULT_PATH
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return cls(data, path)
            except (json.JSONDecodeError, OSError):
                pass
        return cls(cls._empty(), path)

    def save(self) -> None:
        """Persist the registry to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, self._path)

    @staticmethod
    def _empty() -> dict:
        return {
            "version": 1,
            "people": {},
            "projects": {},
            "ambiguous_flags": [],
        }

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def people(self) -> dict:
        return self._data.get("people", {})

    @property
    def projects(self) -> dict:
        return self._data.get("projects", {})

    @property
    def ambiguous_flags(self) -> list[str]:
        return self._data.get("ambiguous_flags", [])

    # ── Code lookup ──────────────────────────────────────────────────────────

    def get_code(self, name: str) -> Optional[str]:
        """Return the AAAK code for a known entity, or None.

        Args:
            name: Entity name (case-insensitive lookup).

        Returns:
            3-letter uppercase code string, or None if not registered.
        """
        for canonical, info in self.people.items():
            all_names = [canonical] + info.get("aliases", [])
            if any(n.lower() == name.lower() for n in all_names):
                return info.get("code", _code_for(canonical))

        for proj_name, info in self.projects.items():
            if proj_name.lower() == name.lower():
                return info.get("code", _code_for(proj_name))

        return None

    # ── Lookup (full classification) ─────────────────────────────────────────

    def lookup(self, word: str, context: str = "") -> dict:
        """Classify a word against the registry.

        Priority: onboarding > learned > wiki cache. Ambiguous words are
        context-disambiguated when a surrounding sentence is provided.

        Args:
            word: Word to classify.
            context: Surrounding sentence for disambiguation of ambiguous words.

        Returns:
            Dict with type, confidence, source, name, needs_disambiguation.
        """
        for canonical, info in self.people.items():
            all_names = [canonical] + info.get("aliases", [])
            if any(n.lower() == word.lower() for n in all_names):
                if word.lower() in self.ambiguous_flags and context:
                    resolved = _context_disambiguate(word, context, info)
                    if resolved is not None:
                        return resolved
                return {
                    "type": "person",
                    "confidence": info.get("confidence", 1.0),
                    "source": info.get("source", "onboarding"),
                    "name": canonical,
                    "code": info.get("code", _code_for(canonical)),
                    "needs_disambiguation": False,
                }

        for proj_name, info in self.projects.items():
            if proj_name.lower() == word.lower():
                return {
                    "type": "project",
                    "confidence": 1.0,
                    "source": info.get("source", "onboarding"),
                    "name": proj_name,
                    "code": info.get("code", _code_for(proj_name)),
                    "needs_disambiguation": False,
                }

        return {
            "type": "unknown",
            "confidence": 0.0,
            "source": "none",
            "name": word,
            "needs_disambiguation": False,
        }

    # ── Register entities ─────────────────────────────────────────────────────

    def register_person(
        self,
        name: str,
        *,
        source: str = "onboarding",
        relationship: str = "",
        aliases: Optional[list[str]] = None,
        confidence: float = 1.0,
        code: Optional[str] = None,
    ) -> None:
        """Register a person in the registry.

        Existing entries are updated only if the new source has higher priority
        (onboarding > learned > wiki).

        Args:
            name: Canonical name.
            source: Data source — "onboarding", "learned", or "wiki".
            relationship: Optional relationship label (e.g. "colleague").
            aliases: Alternative names that map to this canonical entry.
            confidence: Float 0.0–1.0.
            code: Explicit AAAK code. Auto-generated from name[:3] if omitted.
        """
        existing = self._data["people"].get(name)
        existing_priority = _PRIORITY.get(
            existing.get("source", "") if existing else "", 0
        )
        new_priority = _PRIORITY.get(source, 0)

        if existing and existing_priority > new_priority:
            return

        self._data["people"][name] = {
            "code": code or _code_for(name),
            "source": source,
            "confidence": confidence,
            "relationship": relationship,
            "aliases": aliases or [],
        }

        if name.lower() in COMMON_ENGLISH_WORDS:
            flags = self._data.setdefault("ambiguous_flags", [])
            if name.lower() not in flags:
                flags.append(name.lower())

    def register_project(
        self,
        name: str,
        *,
        source: str = "onboarding",
        code: Optional[str] = None,
    ) -> None:
        """Register a project in the registry.

        Args:
            name: Project name.
            source: Data source.
            code: Explicit AAAK code. Auto-generated if omitted.
        """
        self._data["projects"][name] = {
            "code": code or _code_for(name),
            "source": source,
        }

    # ── Learn from text ───────────────────────────────────────────────────────

    def learn_from_text(
        self, text: str, min_confidence: float = 0.75
    ) -> list[dict]:
        """Scan text for new entity candidates and add high-confidence ones.

        Uses entity_detector to score candidates. Only persons with confidence
        >= min_confidence are added with source "learned".

        Args:
            text: Source text to mine.
            min_confidence: Confidence threshold for auto-registration.

        Returns:
            List of newly discovered entity dicts.
        """
        from .entity_detector import (
            extract_candidates,
            score_entity,
            classify_entity,
        )

        candidates = extract_candidates(text)
        new_entities: list[dict] = []

        word_counts: dict[str, int] = {}
        for name in candidates:
            count = len(re.findall(rf"\b{re.escape(name)}\b", text))
            word_counts[name] = max(count, 3)

        for name in candidates:
            if name in self.people or name in self.projects:
                continue

            frequency = word_counts.get(name, 3)
            scores = score_entity(name, text)
            entity = classify_entity(name, frequency, scores)

            if entity["type"] == "person" and entity["confidence"] >= min_confidence:
                self.register_person(
                    name,
                    source="learned",
                    confidence=entity["confidence"],
                )
                new_entities.append(entity)

        if new_entities:
            self.save()

        return new_entities

    # ── Bulk seed from onboarding ─────────────────────────────────────────────

    def seed(
        self,
        people: list[dict],
        projects: list[str],
        aliases: Optional[dict[str, str]] = None,
    ) -> None:
        """Seed the registry from onboarding data and persist.

        Args:
            people: List of dicts {"name": str, "relationship": str}.
            projects: List of project name strings.
            aliases: Mapping of nickname → canonical name,
                     e.g. {"Ali": "Alice"}.
        """
        aliases = aliases or {}
        reverse_aliases: dict[str, list[str]] = {}
        for nickname, canonical in aliases.items():
            reverse_aliases.setdefault(canonical, []).append(nickname)

        for entry in people:
            name = entry.get("name", "").strip()
            if not name:
                continue
            self.register_person(
                name,
                source="onboarding",
                relationship=entry.get("relationship", ""),
                aliases=reverse_aliases.get(name, []),
                confidence=1.0,
            )

        for proj in projects:
            self.register_project(proj, source="onboarding")

        self.save()

    # ── Summary ──────────────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a human-readable summary of registry contents."""
        people_names = list(self.people.keys())
        project_names = list(self.projects.keys())
        lines = [
            f"People ({len(people_names)}): "
            + (", ".join(people_names[:8]) + ("..." if len(people_names) > 8 else "")),
            f"Projects ({len(project_names)}): "
            + (", ".join(project_names) or "(none)"),
            "Ambiguous flags: "
            + (", ".join(self.ambiguous_flags) or "(none)"),
        ]
        return "\n".join(lines)

    # ── Build entity_codes dict for dialect.compress() ───────────────────────

    def to_entity_codes(self) -> dict[str, str]:
        """Return a flat name → code mapping for use with dialect.compress().

        Returns:
            Dict like {"Alice": "ALC", "DarkMem": "DAR"}.
        """
        codes: dict[str, str] = {}
        for name, info in self.people.items():
            codes[name] = info.get("code", _code_for(name))
            for alias in info.get("aliases", []):
                codes[alias] = codes[name]
        for name, info in self.projects.items():
            codes[name] = info.get("code", _code_for(name))
        return codes
