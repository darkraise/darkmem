import json
import re
from datetime import date
from typing import Any

from app.repositories.graph import PostgresGraphRepository


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"['\"]", "", slug)
    slug = re.sub(r"[\s\-]+", "_", slug)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    return slug


def _normalize_predicate(predicate: str) -> str:
    return predicate.lower().replace(" ", "_")


class KnowledgeGraphService:
    def __init__(self, repo: PostgresGraphRepository) -> None:
        self._repo = repo

    # ── Write operations ──────────────────────────────────────────────────

    async def add_entity(
        self,
        name: str,
        entity_type: str = "unknown",
        properties: dict | None = None,
    ) -> dict:
        props = properties or {}
        return await self._repo.upsert_entity_simple(
            name, entity_type, json.dumps(props)
        )

    async def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: str | None = None,
        source_memory_id: str | None = None,
    ) -> dict:
        sub_slug = _slugify(subject)
        obj_slug = _slugify(obj)
        pred = _normalize_predicate(predicate)

        for display_name in (subject, obj):
            await self._repo.insert_entity_stub(display_name)

        existing = await self._repo.get_active_triple(sub_slug, pred, obj_slug)
        if existing:
            return existing

        return await self._repo.insert_triple(
            sub_slug, pred, obj_slug, valid_from, source_memory_id
        )

    async def invalidate(
        self,
        subject: str,
        predicate: str,
        obj: str,
        ended: str | None = None,
    ) -> bool:
        sub_slug = _slugify(subject)
        obj_slug = _slugify(obj)
        pred = _normalize_predicate(predicate)
        ended_date = ended or date.today().isoformat()
        rowcount = await self._repo.expire_triple(sub_slug, pred, obj_slug, ended_date)
        return rowcount > 0

    # ── Query operations ──────────────────────────────────────────────────

    async def query_entity(
        self,
        name: str,
        as_of: str | None = None,
        direction: str = "both",
    ) -> dict:
        slug = _slugify(name)
        temporal_clause = ""
        if as_of:
            temporal_clause = (
                " AND (t.valid_from IS NULL OR t.valid_from <= :as_of)"
                " AND (t.valid_to IS NULL OR t.valid_to > :as_of)"
            )

        params: dict[str, Any] = {"slug": slug}
        if as_of:
            params["as_of"] = as_of

        results: list[dict] = []

        if direction in ("outgoing", "both"):
            for row in await self._repo.get_triples_by_subject(slug, temporal_clause, params):
                results.append({
                    "direction": "outgoing",
                    "subject": name,
                    "predicate": row["predicate"],
                    "object": row["object"],
                    "valid_from": _date_str(row["valid_from"]),
                    "valid_to": _date_str(row["valid_to"]),
                    "confidence": row["confidence"],
                    "source_memory_id": str(row["source_memory_id"]) if row["source_memory_id"] else None,
                    "current": row["valid_to"] is None,
                })

        if direction in ("incoming", "both"):
            for row in await self._repo.get_triples_by_object(slug, temporal_clause, params):
                results.append({
                    "direction": "incoming",
                    "subject": row["subject"],
                    "predicate": row["predicate"],
                    "object": name,
                    "valid_from": _date_str(row["valid_from"]),
                    "valid_to": _date_str(row["valid_to"]),
                    "confidence": row["confidence"],
                    "source_memory_id": str(row["source_memory_id"]) if row["source_memory_id"] else None,
                    "current": row["valid_to"] is None,
                })

        return {"entity": name, "slug": slug, "as_of": as_of, "facts": results}

    async def query_relationship(self, predicate: str) -> list[dict]:
        pred = _normalize_predicate(predicate)
        return [
            {
                "subject": r["subject"],
                "predicate": r["predicate"],
                "object": r["object"],
                "valid_from": _date_str(r["valid_from"]),
                "valid_to": _date_str(r["valid_to"]),
                "confidence": r["confidence"],
                "current": r["valid_to"] is None,
            }
            for r in await self._repo.get_triples_by_predicate(pred)
        ]

    async def timeline(self, name: str | None = None) -> list[dict]:
        if name:
            slug = _slugify(name)
            rows = await self._repo.get_triples_for_entity_timeline(slug)
        else:
            rows = await self._repo.get_recent_triples(limit=100)

        return [
            {
                "subject": r["subject"],
                "predicate": r["predicate"],
                "object": r["object"],
                "valid_from": _date_str(r["valid_from"]),
                "valid_to": _date_str(r["valid_to"]),
                "confidence": r["confidence"],
                "current": r["valid_to"] is None,
            }
            for r in rows
        ]

    async def seed_from_entity_facts(self, entity_data: list[dict]) -> int:
        inserted = 0
        for facts in entity_data:
            name = facts.get("full_name") or facts.get("name", "unknown")
            etype = facts.get("type", "person")
            await self.add_entity(
                name,
                etype,
                {"gender": facts.get("gender", ""), "birthday": facts.get("birthday", "")},
            )

            parent = facts.get("parent")
            if parent:
                await self.add_triple(name, "child_of", parent.capitalize(), valid_from=facts.get("birthday"))
                inserted += 1

            partner = facts.get("partner")
            if partner:
                await self.add_triple(name, "married_to", partner.capitalize())
                inserted += 1

            relationship = facts.get("relationship", "")
            if relationship == "daughter":
                await self.add_triple(name, "is_child_of", (facts.get("parent") or name).capitalize(), valid_from=facts.get("birthday"))
                inserted += 1
            elif relationship == "husband":
                await self.add_triple(name, "is_partner_of", (facts.get("partner") or name).capitalize())
                inserted += 1
            elif relationship == "brother":
                await self.add_triple(name, "is_sibling_of", (facts.get("sibling") or name).capitalize())
                inserted += 1
            elif relationship == "dog":
                await self.add_entity(name, "animal")
                await self.add_triple(name, "is_pet_of", (facts.get("owner") or name).capitalize())
                inserted += 1

            for interest in facts.get("interests", []):
                await self.add_triple(name, "loves", interest.capitalize(), valid_from="2025-01-01")
                inserted += 1

        return inserted

    async def stats(self) -> dict:
        return await self._repo.get_triple_stats()


# ── Helpers ───────────────────────────────────────────────────────────────

def _date_str(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
