import json
import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vector import MemoryFilter
from app.services.embedder_registry import child_table

logger = logging.getLogger(__name__)

# Ceiling on a scoped walk. Every extra hop multiplies the frontier, and the
# read paths that traverse the graph want a neighbourhood, not a component.
MAX_TRAVERSAL_DEPTH = 5


class PostgresGraphRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_similar_entity(
        self, embedding: list[float], fingerprint: str, threshold: float = 0.85,
        entity_type: str | None = None,
    ) -> dict | None:
        table = child_table("entity_embeddings", fingerprint)
        # The ORDER BY ... <=> uses the HNSW index for ranking; the threshold in
        # WHERE is a cheap post-filter on the single nearest row (LIMIT 1). A
        # similarity threshold cannot be pushed into an HNSW index scan, so this
        # recomputed-distance predicate is inherent, not an oversight.
        # Constrain the match to the probe's own type: a name embedding alone
        # can't tell a `tool` named "react" from a `concept` named "react", and
        # canonicalizing one onto the other corrupts the (name, type) binding.
        type_cond = "AND e.entity_type = :etype" if entity_type is not None else ""
        params = {"vec": str(embedding), "threshold": threshold}
        if entity_type is not None:
            params["etype"] = entity_type
        result = await self.session.execute(
            text(f"""
                SELECT e.id, e.name, e.entity_type,
                       1 - (ee.embedding <=> CAST(:vec AS vector)) AS score
                FROM {table} ee
                JOIN entities e ON e.id = ee.entity_id
                WHERE 1 - (ee.embedding <=> CAST(:vec AS vector)) >= :threshold {type_cond}
                ORDER BY ee.embedding <=> CAST(:vec AS vector)
                LIMIT 1
            """),
            params,
        )
        row = result.mappings().first()
        if not row:
            return None
        return {"id": str(row["id"]), "name": row["name"], "entity_type": row["entity_type"], "score": float(row["score"])}

    async def upsert_entity_embedding(
        self, entity_id: str, embedding: list[float], fingerprint: str,
    ):
        table = child_table("entity_embeddings", fingerprint)
        await self.session.execute(
            text(f"""
                INSERT INTO {table} (entity_id, fingerprint, embedding)
                VALUES (CAST(:id AS uuid), :fp, CAST(:vec AS vector))
                ON CONFLICT (entity_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {"id": entity_id, "vec": str(embedding), "fp": fingerprint},
        )

    async def get_cached_entity_embeddings(
        self,
        name_lowers: list[str],
        fingerprint: str,
    ) -> dict[str, list[float]]:
        """Return {name_lower: embedding} for entries matching the fingerprint.

        Names not present in the cache (for this fingerprint) are omitted.
        """
        if not name_lowers:
            return {}
        table = child_table("entity_embedding_cache", fingerprint)
        # The child table may not exist yet for a brand-new fingerprint that
        # hasn't been registered. Defend against that with a to_regclass
        # check; missing partitions simply return zero hits.
        exists = (
            await self.session.execute(
                text("SELECT to_regclass(:t)"),
                {"t": f"public.{table}"},
            )
        ).scalar_one_or_none()
        if exists is None:
            return {}
        result = await self.session.execute(
            text(f"""
                SELECT name_lower, embedding::text AS embedding_text
                FROM {table}
                WHERE name_lower = ANY(:names)
            """),
            {"names": name_lowers},
        )
        out: dict[str, list[float]] = {}
        for row in result.mappings().all():
            text_vec = row["embedding_text"]
            out[row["name_lower"]] = [float(x) for x in text_vec.strip("[]").split(",")]
        return out

    async def upsert_entity_embeddings_cache(
        self,
        name_to_embedding: dict[str, list[float]],
        fingerprint: str,
    ) -> None:
        """Upsert cache entries. ON CONFLICT updates last_used_at and hit_count.

        Single multi-row INSERT via ``unnest``/``jsonb_to_recordset`` so a
        Phase 3 batch with M misses costs one round-trip instead of M.
        """
        if not name_to_embedding:
            return
        table = child_table("entity_embedding_cache", fingerprint)
        names = list(name_to_embedding.keys())
        vecs = [str(name_to_embedding[n]) for n in names]
        await self.session.execute(
            text(f"""
                INSERT INTO {table}
                    (name_lower, fingerprint, embedding, created_at, last_used_at, hit_count)
                SELECT n, :fp, CAST(v AS vector), NOW(), NOW(), 1
                FROM unnest(CAST(:names AS text[]), CAST(:vecs AS text[])) AS t(n, v)
                ON CONFLICT (name_lower, fingerprint) DO UPDATE SET
                    last_used_at = NOW(),
                    hit_count = {table}.hit_count + 1
            """),
            {"fp": fingerprint, "names": names, "vecs": vecs},
        )

    async def create_entity(self, name: str, entity_type: str, properties: dict, memory_id: UUID) -> dict:
        result = await self.session.execute(
            text("""
                INSERT INTO entities (id, name, entity_type, properties, memory_ids)
                VALUES (:id, :name, :entity_type, CAST(:properties AS jsonb), ARRAY[CAST(:memory_id AS uuid)])
                ON CONFLICT (name, entity_type) DO UPDATE SET
                    properties = entities.properties || EXCLUDED.properties,
                    memory_ids = CASE
                        WHEN CAST(:memory_id AS uuid) = ANY(entities.memory_ids) THEN entities.memory_ids
                        ELSE array_append(entities.memory_ids, CAST(:memory_id AS uuid))
                    END
                RETURNING id, name, entity_type, properties, memory_ids
            """),
            {
                "id": str(uuid4()),
                "name": name,
                "entity_type": entity_type,
                "properties": json.dumps(properties),
                "memory_id": str(memory_id),
            },
        )
        row = result.mappings().one()
        return {
            "id": str(row["id"]),
            "name": row["name"],
            "entity_type": row["entity_type"],
            "properties": row["properties"] or {},
            "memory_ids": [str(m) for m in (row["memory_ids"] or [])],
        }

    async def create_relationship(
        self,
        source_name: str,
        target_name: str,
        rel_type: str,
        properties: dict,
        weight: float,
        memory_id: UUID,
        source_type: str | None = None,
        target_type: str | None = None,
    ):
        # Entity uniqueness is (name, entity_type), so resolving endpoints by
        # name alone can bind to the wrong entity when two share a name across
        # types. When the caller knows the endpoint types, scope the lookup;
        # otherwise fall back to name-only resolution for legacy callers.
        source_cond = "s.name = :source_name"
        target_cond = "t.name = :target_name"
        params: dict = {"source_name": source_name, "target_name": target_name}
        if source_type is not None:
            source_cond += " AND s.entity_type = :source_type"
            params["source_type"] = source_type
        if target_type is not None:
            target_cond += " AND t.entity_type = :target_type"
            params["target_type"] = target_type
        pair_result = await self.session.execute(
            text(f"""
                SELECT s.id AS source_id, t.id AS target_id
                FROM entities s, entities t
                WHERE {source_cond} AND {target_cond}
                LIMIT 1
            """),
            params,
        )
        pair = pair_result.mappings().first()
        if not pair:
            logger.debug(
                "create_relationship dropped: endpoint not resolvable (%s -%s-> %s)",
                source_name, rel_type, target_name,
            )
            return

        await self.session.execute(
            text("""
                INSERT INTO entity_relations (id, source_entity_id, target_entity_id, rel_type, properties, weight, memory_ids)
                VALUES (:id, :source_id, :target_id, :rel_type, CAST(:properties AS jsonb), :weight, ARRAY[CAST(:memory_id AS uuid)])
                ON CONFLICT (source_entity_id, target_entity_id, rel_type) DO UPDATE SET
                    weight = GREATEST(entity_relations.weight, EXCLUDED.weight),
                    memory_ids = CASE
                        WHEN CAST(:memory_id AS uuid) = ANY(entity_relations.memory_ids) THEN entity_relations.memory_ids
                        ELSE array_append(entity_relations.memory_ids, CAST(:memory_id AS uuid))
                    END
            """),
            {
                "id": str(uuid4()),
                "source_id": str(pair["source_id"]),
                "target_id": str(pair["target_id"]),
                "rel_type": rel_type,
                "properties": json.dumps(properties),
                "weight": weight,
                "memory_id": str(memory_id),
            },
        )

    async def get_entities(
        self,
        entity_type: str | None = None,
        name_query: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions = []
        params: dict = {"limit": limit}

        if entity_type:
            conditions.append("entity_type = :entity_type")
            params["entity_type"] = entity_type
        if name_query:
            conditions.append("name ILIKE :name_query ESCAPE '\\'")
            escaped = name_query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            params["name_query"] = f"%{escaped}%"

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        result = await self.session.execute(
            text(f"SELECT id, name, entity_type, properties, memory_ids FROM entities {where_clause} LIMIT :limit"),
            params,
        )
        rows = result.mappings().all()
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "entity_type": r["entity_type"],
                "properties": r["properties"] or {},
                "memory_ids": [str(m) for m in (r["memory_ids"] or [])],
            }
            for r in rows
        ]

    def neighbors_query(
        self,
        entity_id,
        max_depth: int = 1,
        scope: MemoryFilter | None = None,
    ) -> tuple[str, dict]:
        """The traversal statement and its bound parameters.

        Exposed so the query plan can be measured against the statement the
        read path actually runs, rather than against a transcription of it.
        """
        depth = max(1, min(int(max_depth), MAX_TRAVERSAL_DEPTH))
        params: dict = {"entity_id": str(entity_id), "max_depth": depth}
        entity_scope = "TRUE"
        relation_scope = "TRUE"
        if scope is not None:
            params.update(scope.params())
            entity_scope = scope.asserted_by_sql("n.memory_ids")
            relation_scope = scope.asserted_by_sql("r.memory_ids")

        # The scope predicates sit inside the recursive term, not on its
        # output: a walk that admits an out-of-scope entity has already
        # crossed the boundary even if that row is dropped afterwards,
        # because the next hop expands from it.
        sql = f"""
                WITH RECURSIVE walk(entity_id, depth) AS (
                    SELECT CAST(:entity_id AS uuid), 0
                    UNION
                    SELECT n.id, w.depth + 1
                    FROM walk w
                    JOIN entity_relations r
                        ON r.source_entity_id = w.entity_id
                        OR r.target_entity_id = w.entity_id
                    JOIN entities n ON n.id = CASE
                        WHEN r.source_entity_id = w.entity_id THEN r.target_entity_id
                        ELSE r.source_entity_id
                    END
                    WHERE w.depth < :max_depth
                      AND {relation_scope}
                      AND {entity_scope}
                ),
                reached AS (
                    SELECT entity_id, MIN(depth) AS depth FROM walk GROUP BY entity_id
                )
                SELECT
                    r.rel_type,
                    r.weight,
                    src.id AS source_id,
                    src.name AS source_name,
                    src.entity_type AS source_type,
                    src.properties AS source_properties,
                    tgt.id AS target_id,
                    tgt.name AS target_name,
                    tgt.entity_type AS target_type,
                    tgt.properties AS target_properties
                FROM entity_relations r
                JOIN reached ra ON ra.entity_id = r.source_entity_id
                JOIN reached rb ON rb.entity_id = r.target_entity_id
                JOIN entities src ON src.id = r.source_entity_id
                JOIN entities tgt ON tgt.id = r.target_entity_id
                WHERE LEAST(ra.depth, rb.depth) < :max_depth
                  AND {relation_scope}
                ORDER BY LEAST(ra.depth, rb.depth), src.name, tgt.name, r.rel_type
        """
        return sql, params

    async def _build_neighbors(
        self,
        entity_row,
        max_depth: int = 1,
        scope: MemoryFilter | None = None,
    ) -> dict:
        if not entity_row:
            return {"entity": None, "neighbors": [], "relations": []}

        entity_id = entity_row["id"]
        entity_dict = {
            "id": str(entity_id),
            "name": entity_row["name"],
            "entity_type": entity_row["entity_type"],
            "properties": entity_row["properties"] or {},
        }

        sql, params = self.neighbors_query(entity_id, max_depth, scope)
        rel_result = await self.session.execute(text(sql), params)
        rel_rows = rel_result.mappings().all()

        seed_id = str(entity_id)
        seen_neighbor_ids: set = set()
        neighbors = []
        relations = []

        for r in rel_rows:
            for side in ("source", "target"):
                nid = str(r[f"{side}_id"])
                if nid == seed_id or nid in seen_neighbor_ids:
                    continue
                seen_neighbor_ids.add(nid)
                neighbors.append({
                    "id": nid,
                    "name": r[f"{side}_name"],
                    "entity_type": r[f"{side}_type"],
                    "properties": r[f"{side}_properties"] or {},
                })
            relations.append({
                "type": r["rel_type"],
                "weight": r["weight"],
                "source": r["source_name"],
                "target": r["target_name"],
            })

        return {"entity": entity_dict, "neighbors": neighbors, "relations": relations}

    async def get_neighbors_by_name(
        self, name: str, max_depth: int = 1, scope: MemoryFilter | None = None,
    ) -> dict:
        # Entity uniqueness is (name, entity_type), so a bare name can match
        # several types. This by-name read path can't disambiguate type, so it
        # picks the most-referenced one deterministically (callers that know the
        # type should use get_neighbors_by_id).
        params: dict = {"name": name}
        seed_scope = ""
        if scope is not None:
            params.update(scope.params())
            seed_scope = f"AND {scope.asserted_by_sql('e.memory_ids')}"
        result = await self.session.execute(
            text(
                "SELECT e.id, e.name, e.entity_type, e.properties, e.memory_ids "
                "FROM entities e "
                f"WHERE e.name = :name {seed_scope} "
                "ORDER BY COALESCE(array_length(e.memory_ids, 1), 0) DESC, e.id LIMIT 1"
            ),
            params,
        )
        return await self._build_neighbors(result.mappings().first(), max_depth, scope)

    async def get_neighbors_by_id(
        self, entity_id: str, max_depth: int = 1, scope: MemoryFilter | None = None,
    ) -> dict:
        params: dict = {"id": entity_id}
        seed_scope = ""
        if scope is not None:
            params.update(scope.params())
            seed_scope = f"AND {scope.asserted_by_sql('e.memory_ids')}"
        result = await self.session.execute(
            text(
                "SELECT e.id, e.name, e.entity_type, e.properties, e.memory_ids "
                f"FROM entities e WHERE e.id = CAST(:id AS uuid) {seed_scope} LIMIT 1"
            ),
            params,
        )
        return await self._build_neighbors(result.mappings().first(), max_depth, scope)

    async def get_full_graph(self, limit: int = 200) -> dict:
        entity_result = await self.session.execute(
            text("SELECT id, name, entity_type, properties, memory_ids FROM entities LIMIT :limit"),
            {"limit": limit},
        )
        entity_rows = entity_result.mappings().all()
        entity_ids = [r["id"] for r in entity_rows]

        entities = [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "entity_type": r["entity_type"],
                "properties": r["properties"] or {},
                "memory_ids": [str(m) for m in (r["memory_ids"] or [])],
            }
            for r in entity_rows
        ]

        if not entity_ids:
            return {"entities": [], "relations": []}

        rel_result = await self.session.execute(
            text("""
                SELECT r.source_entity_id, r.target_entity_id, r.rel_type, r.weight
                FROM entity_relations r
                WHERE r.source_entity_id = ANY(:ids) AND r.target_entity_id = ANY(:ids)
            """),
            {"ids": entity_ids},
        )
        rel_rows = rel_result.mappings().all()
        relations = [
            {
                "source": str(r["source_entity_id"]),
                "target": str(r["target_entity_id"]),
                "type": r["rel_type"],
                "weight": r["weight"],
            }
            for r in rel_rows
        ]

        return {"entities": entities, "relations": relations}

    async def delete_by_memory_id(self, memory_id: UUID):
        mid = str(memory_id)

        # Strip this memory's contribution from both tables, capturing the
        # touched ids. Only rows this memory referenced can become orphaned, so
        # scoping the orphan sweeps to those ids avoids two full-table scans on
        # every memory write (the previous unscoped DELETEs on a non-sargable
        # emptiness predicate were guaranteed sequential scans of both tables).
        ent_ids = [
            str(r) for r in (await self.session.execute(
                text("""
                    UPDATE entities
                    SET memory_ids = array_remove(memory_ids, CAST(:mid AS uuid))
                    WHERE CAST(:mid AS uuid) = ANY(memory_ids)
                    RETURNING id
                """),
                {"mid": mid},
            )).scalars().all()
        ]
        rel_ids = [
            str(r) for r in (await self.session.execute(
                text("""
                    UPDATE entity_relations
                    SET memory_ids = array_remove(memory_ids, CAST(:mid AS uuid))
                    WHERE CAST(:mid AS uuid) = ANY(memory_ids)
                    RETURNING id
                """),
                {"mid": mid},
            )).scalars().all()
        ]

        # Drop relations no LIVE memory asserts any more (scoped to touched
        # rows). Checking "no live memory" rather than "array empty" also
        # self-heals dangling memory_ids — ids left pointing at memories that
        # were deleted without graph cleanup. Do this BEFORE deleting orphaned
        # entities so the entity guard below sees only relations that survive.
        if rel_ids:
            await self.session.execute(
                text("""
                    DELETE FROM entity_relations
                    WHERE id = ANY(CAST(:ids AS uuid[]))
                      AND NOT EXISTS (
                          SELECT 1 FROM memories m
                          WHERE m.id = ANY(entity_relations.memory_ids)
                      )
                      AND NOT EXISTS (
                          SELECT 1 FROM repositories rp
                          WHERE rp.id = ANY(entity_relations.repo_ids)
                      )
                """),
                {"ids": rel_ids},
            )

        # Delete an entity no live memory asserts, but only when no surviving
        # relation still references it. The FK is ON DELETE CASCADE, so deleting
        # an entity a relation still points at would silently destroy a relation
        # that other memories assert — losing another memory's edge on
        # re-extraction. The "no live memory" predicate also drops an entity
        # kept alive only by dangling memory_ids (ghost), which is what the
        # Phase-4 dedup would otherwise collapse fresh entities onto.
        if ent_ids:
            await self.session.execute(
                text("""
                    DELETE FROM entities e
                    WHERE e.id = ANY(CAST(:ids AS uuid[]))
                      AND NOT EXISTS (
                          SELECT 1 FROM memories m WHERE m.id = ANY(e.memory_ids)
                      )
                      AND NOT EXISTS (
                          SELECT 1 FROM repositories rp WHERE rp.id = ANY(e.repo_ids)
                      )
                      AND NOT EXISTS (
                          SELECT 1 FROM entity_relations r
                          WHERE r.source_entity_id = e.id OR r.target_entity_id = e.id
                      )
                """),
                {"ids": ent_ids},
            )

    async def prune_orphan_entities(self) -> dict:
        """Remove entities and relations that no LIVE memory asserts any more.

        Ghosts accumulate when a memory is deleted via a path that skips
        ``delete_by_memory_id`` (e.g. a swallowed cleanup error, a raw DB
        delete) or when a row is kept alive only by ``memory_ids`` that point at
        already-deleted memories. Such ghosts otherwise survive forever and the
        Phase-4 ANN dedup collapses fresh entities onto them (a fresh
        ``february outage`` snapped onto a stale ``march outage``). Unscoped
        full-table sweep — meant for the periodic maintenance job, not the write
        path. Relations are pruned first so the entity guard sees only surviving
        relations; the ``entity_embeddings__*`` FK is ON DELETE CASCADE, so an
        entity's embeddings go with it (which is what stops the dedup match).

        Invariant-8 amendment (T0.13): a row survives while any live memory OR
        any live repo still asserts it. ``repo_ids`` is empty everywhere until
        the code deriver (T2.27) ships, so the added predicate is
        vacuously true and this sweep behaves byte-identically to before."""
        rel_ids = (await self.session.execute(text("""
            DELETE FROM entity_relations r
            WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = ANY(r.memory_ids))
              AND NOT EXISTS (SELECT 1 FROM repositories rp WHERE rp.id = ANY(r.repo_ids))
            RETURNING r.id
        """))).scalars().all()
        ent_ids = (await self.session.execute(text("""
            DELETE FROM entities e
            WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = ANY(e.memory_ids))
              AND NOT EXISTS (SELECT 1 FROM repositories rp WHERE rp.id = ANY(e.repo_ids))
              AND NOT EXISTS (
                  SELECT 1 FROM entity_relations r
                  WHERE r.source_entity_id = e.id OR r.target_entity_id = e.id
              )
            RETURNING e.id
        """))).scalars().all()
        return {"relations_pruned": len(rel_ids), "entities_pruned": len(ent_ids)}

    async def get_entities_by_memory_id(self, memory_id: str) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT id, name, entity_type, properties, memory_ids
                FROM entities
                WHERE CAST(:mid AS uuid) = ANY(memory_ids)
            """),
            {"mid": memory_id},
        )
        rows = result.mappings().all()
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "entity_type": r["entity_type"],
                "properties": r["properties"] or {},
                "memory_ids": [str(m) for m in (r["memory_ids"] or [])],
            }
            for r in rows
        ]

    async def get_relations_between(
        self, entity_names: list[str], scope: MemoryFilter | None = None,
    ) -> list[dict]:
        if not entity_names:
            return []

        params: dict = {"names": entity_names}
        scope_sql = ""
        if scope is not None:
            params.update(scope.params())
            scope_sql = f"AND {scope.asserted_by_sql('r.memory_ids')}"

        result = await self.session.execute(
            text(f"""
                SELECT src.name AS source, tgt.name AS target, r.rel_type AS type, r.weight
                FROM entity_relations r
                JOIN entities src ON src.id = r.source_entity_id
                JOIN entities tgt ON tgt.id = r.target_entity_id
                WHERE src.name = ANY(CAST(:names AS varchar[]))
                  AND tgt.name = ANY(CAST(:names AS varchar[]))
                  {scope_sql}
            """),
            params,
        )
        rows = result.mappings().all()
        return [
            {
                "source": r["source"],
                "target": r["target"],
                "type": r["type"],
                "weight": r["weight"],
            }
            for r in rows
        ]

    async def get_stats(self) -> dict:
        entity_result = await self.session.execute(text("SELECT COUNT(*) AS count FROM entities"))
        entity_count = entity_result.scalar_one()

        rel_result = await self.session.execute(text("SELECT COUNT(*) AS count FROM entity_relations"))
        rel_count = rel_result.scalar_one()

        return {"entity_count": entity_count, "relationship_count": rel_count}

    # ── knowledge_triples / temporal graph ───────────────────────────────

    async def upsert_entity_simple(self, name: str, entity_type: str, properties_json: str) -> dict:
        result = await self.session.execute(
            text("""
                INSERT INTO entities (name, entity_type, properties)
                VALUES (:name, :entity_type, CAST(:properties AS jsonb))
                ON CONFLICT (name, entity_type) DO UPDATE
                    SET properties = entities.properties || CAST(:properties AS jsonb)
                RETURNING id, name, entity_type, properties, created_at
            """),
            {"name": name, "entity_type": entity_type, "properties": properties_json},
        )
        return dict(result.mappings().one())

    async def insert_entity_stub(self, name: str) -> None:
        # Stub entities carry no memory_ids, so the periodic graph_orphan_cleanup
        # sweep will reclaim them unless a memory later asserts them. This is
        # acceptable for the experimental knowledge-triple path that calls this;
        # the main extraction write path always sets memory_ids.
        await self.session.execute(
            text("""
                INSERT INTO entities (name, entity_type)
                VALUES (:name, 'unknown')
                ON CONFLICT (name, entity_type) DO NOTHING
            """),
            {"name": name},
        )

    async def get_active_triple(self, subject: str, predicate: str, obj: str) -> dict | None:
        result = await self.session.execute(
            text("""
                SELECT id, subject, predicate, object, valid_from, valid_to,
                       confidence, source_memory_id, created_at
                FROM knowledge_triples
                WHERE subject = :sub AND predicate = :pred AND object = :obj
                  AND valid_to IS NULL
            """),
            {"sub": subject, "pred": predicate, "obj": obj},
        )
        row = result.mappings().first()
        return dict(row) if row else None

    async def insert_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: str | None,
        source_memory_id: str | None,
    ) -> dict:
        result = await self.session.execute(
            text("""
                INSERT INTO knowledge_triples
                    (subject, predicate, object, valid_from, source_memory_id)
                VALUES
                    (:sub, :pred, :obj, :valid_from, :source_memory_id)
                RETURNING id, subject, predicate, object, valid_from, valid_to,
                          confidence, source_memory_id, created_at
            """),
            {
                "sub": subject,
                "pred": predicate,
                "obj": obj,
                "valid_from": valid_from,
                "source_memory_id": source_memory_id,
            },
        )
        return dict(result.mappings().one())

    async def expire_triple(
        self, subject: str, predicate: str, obj: str, ended: str
    ) -> int:
        result = await self.session.execute(
            text("""
                UPDATE knowledge_triples
                SET valid_to = :ended
                WHERE subject = :sub AND predicate = :pred AND object = :obj
                  AND valid_to IS NULL
            """),
            {"ended": ended, "sub": subject, "pred": predicate, "obj": obj},
        )
        return result.rowcount

    async def get_triples_by_subject(
        self, slug: str, temporal_clause: str, params: dict[str, Any]
    ) -> list[dict]:
        result = await self.session.execute(
            text(f"""
                SELECT t.id, t.subject, t.predicate, t.object,
                       t.valid_from, t.valid_to, t.confidence,
                       t.source_memory_id, t.created_at
                FROM knowledge_triples t
                WHERE t.subject = :slug{temporal_clause}
                ORDER BY t.valid_from ASC NULLS LAST
            """),
            params,
        )
        return [dict(r) for r in result.mappings()]

    async def get_triples_by_object(
        self, slug: str, temporal_clause: str, params: dict[str, Any]
    ) -> list[dict]:
        result = await self.session.execute(
            text(f"""
                SELECT t.id, t.subject, t.predicate, t.object,
                       t.valid_from, t.valid_to, t.confidence,
                       t.source_memory_id, t.created_at
                FROM knowledge_triples t
                WHERE t.object = :slug{temporal_clause}
                ORDER BY t.valid_from ASC NULLS LAST
            """),
            params,
        )
        return [dict(r) for r in result.mappings()]

    async def get_triples_by_predicate(self, predicate: str) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT subject, predicate, object, valid_from, valid_to, confidence
                FROM knowledge_triples
                WHERE predicate = :pred
                ORDER BY valid_from ASC NULLS LAST
            """),
            {"pred": predicate},
        )
        return [dict(r) for r in result.mappings()]

    async def get_triples_for_entity_timeline(self, slug: str) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT subject, predicate, object, valid_from, valid_to, confidence
                FROM knowledge_triples
                WHERE subject = :slug OR object = :slug
                ORDER BY valid_from ASC NULLS LAST
            """),
            {"slug": slug},
        )
        return [dict(r) for r in result.mappings()]

    async def get_recent_triples(self, limit: int = 100) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT subject, predicate, object, valid_from, valid_to, confidence
                FROM knowledge_triples
                ORDER BY valid_from ASC NULLS LAST
                LIMIT :limit
            """),
            {"limit": limit},
        )
        return [dict(r) for r in result.mappings()]

    async def get_triple_stats(self) -> dict:
        row = await self.session.execute(
            text("""
                SELECT
                    (SELECT COUNT(*) FROM entities)                          AS entities,
                    (SELECT COUNT(*) FROM knowledge_triples)                 AS triples,
                    (SELECT COUNT(*) FROM knowledge_triples WHERE valid_to IS NULL) AS current_facts
            """)
        )
        counts = row.mappings().one()

        pred_rows = await self.session.execute(
            text("SELECT DISTINCT predicate FROM knowledge_triples ORDER BY predicate")
        )
        predicates = [r["predicate"] for r in pred_rows.mappings()]

        return {
            "entities": counts["entities"],
            "triples": counts["triples"],
            "current_facts": counts["current_facts"],
            "expired_facts": counts["triples"] - counts["current_facts"],
            "relationship_types": predicates,
        }
