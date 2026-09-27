"""baseline

Revision ID: 0001
Revises:
Create Date: 2026-07-27

The single greenfield baseline. Doc 19 §2: the schema ships as ONE revision,
regenerated freely (paired with drop/recreate) until the first deploy whose
data must survive — the homelab cutover — at which event it is tagged ``0001``
and frozen, and every change after is a new linear revision forever. Until
then a schema change means editing THIS file and recreating the database, never
appending ``0002``; a CI assertion holds ``alembic history`` at exactly one
revision until the freeze tag exists.

**Freeze date: not yet frozen.** T0.15 owns the regeneration protocol and the
cutover task fills the real date.

Authored as plain SQL rather than ``op.create_table``. Doc 19 §2 binds every
table, constraint, index and trigger to stay expressible as plain SQL so the
deferred .NET port replays this file through DbUp as a mechanical transcription
rather than a re-derivation from ORM metadata. Expressing the DDL as SQLAlchemy
schema objects would defeat that, so the statements below are the SQL itself.

The object inventory this file implements — every table, index, constraint and
column traced to its owning design-doc section, with its disposition — is
``docs/planning/baseline-schema-inventory.md``. Read it before changing
anything here; a divergence between the two is a defect in one of them.

Per-fingerprint embedding child tables (``memory_embeddings__<slug>`` and its
seven siblings) are deliberately ABSENT. Their DDL is parameterised by
fingerprint, which no static migration can express, so they are registry
entries created by the boot-time reconciliation in ``embedder_registry``
(doc 19 §2, inventory §6). Nothing about them belongs in this file.

Built up by T0.12a (this pass), T0.12b and T0.12c. This pass lands the core
memory rows, the knowledge graph, the tag pair, ``config`` and the embedder
registry.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Extensions and types
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # The contradiction scan's second candidate arm (doc 08 §5.3) is a trigram
    # shortlist over knowledge_triples.fact. It is deliberately NOT an
    # embedding channel: triple_embeddings stays template-only until a measured
    # undercount of this generator justifies its writer (doc 04 §5.3).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # The ONE native enum in the schema (doc 04 §2, §11). Every other state
    # column is CHECK-constrained text and every "type" column is varchar
    # normalised in application code against a closed set; promoting any of
    # them to an enum would be a behaviour change, not a tidy-up.
    op.execute(
        "CREATE TYPE memory_status AS ENUM ('active', 'deprecated', 'superseded')"
    )

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE FUNCTION memories_fts_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END $$ LANGUAGE plpgsql
        """
    )

    # The updated_at auto-bump lives in SQL, not in SQLAlchemy's client-side
    # ``onupdate`` (inventory F-20, adjudicated 2026-07-27). onupdate fires only
    # for statements SQLAlchemy constructs: measured on a live database, a Core
    # update() bumps the column while a raw text() UPDATE does not, so the two
    # demote-before-delete paths silently left it stale on a status change.
    op.execute(
        """
        CREATE FUNCTION touch_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END $$ LANGUAGE plpgsql
        """
    )

    # ------------------------------------------------------------------
    # config — feature flags, job:<key> state, admin_password_hash
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE config (
            key   VARCHAR(255) PRIMARY KEY,
            value JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )

    # ------------------------------------------------------------------
    # embedders — the fingerprint registry (doc 04 §5.1)
    # ------------------------------------------------------------------
    # It owns the DDL for each fingerprint's child tables and is the
    # register-before-insert authority and the sole namer. The source CHECK was
    # narrowed to the single value 'llm' when the ML/regex embedder arms were
    # scrubbed; the target does not widen it.
    op.execute(
        """
        CREATE TABLE embedders (
            fingerprint   TEXT PRIMARY KEY,
            model_id      TEXT NOT NULL,
            dims          INTEGER NOT NULL,
            source        TEXT NOT NULL,
            registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            retired_at    TIMESTAMPTZ,
            CONSTRAINT embedders_dims_check   CHECK (dims > 0),
            CONSTRAINT embedders_source_check CHECK (source = 'llm')
        )
        """
    )

    # ------------------------------------------------------------------
    # memories — the central rows and the status lifecycle (doc 04 §3.1)
    # ------------------------------------------------------------------
    # id is application-generated UUIDv7 (doc 04 §2) — time-ordered so B-tree
    # inserts stay local — hence no server default here. source keeps its
    # ORM-only 'api' default, which doc 04 §3.1 records deliberately.
    op.execute(
        """
        CREATE TABLE memories (
            id              UUID NOT NULL,
            content         TEXT NOT NULL,
            source          VARCHAR(100) NOT NULL,
            source_agent    VARCHAR(255),
            origin_key      TEXT,
            memory_type     VARCHAR(50),
            importance      DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at      TIMESTAMPTZ,
            is_archived     BOOLEAN NOT NULL DEFAULT false,
            classified_type VARCHAR(50),
            summary         TEXT,
            emotions        JSONB,
            flags           JSONB,
            project         TEXT NOT NULL DEFAULT 'default',
            status          memory_status NOT NULL DEFAULT 'active',
            superseded_by   UUID,
            technologies    TEXT[] NOT NULL DEFAULT '{}'::text[],
            confidence      REAL NOT NULL DEFAULT 0.75,
            search_vector   TSVECTOR,
            CONSTRAINT memories_pkey PRIMARY KEY (id),
            CONSTRAINT chk_superseded_has_pointer
                CHECK (status != 'superseded' OR superseded_by IS NOT NULL),
            CONSTRAINT fk_memories_superseded_by
                FOREIGN KEY (superseded_by) REFERENCES memories(id) ON DELETE SET NULL
        )
        """
    )

    # Trivially satisfiable (id is already the PK) and it exists solely so
    # memory_relations' endpoint FKs can be declared as composite
    # (memory_id, project) references, which makes a cross-project edge
    # unrepresentable rather than merely forbidden (doc 04 §8.2, §10).
    # Without it memory_relations is undeclarable.
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT memories_id_project_key UNIQUE (id, project)"
    )

    op.execute("CREATE INDEX ix_memories_created_at ON memories (created_at)")
    op.execute(
        "CREATE INDEX ix_memories_is_archived ON memories (is_archived) "
        "WHERE is_archived = false"
    )
    op.execute("CREATE INDEX ix_memories_project ON memories (project)")
    op.execute("CREATE INDEX ix_memories_status ON memories (status)")
    # The reverse lineage query (`get_predecessors`) filters on this column;
    # the forward direction is a plain column read on the row already in
    # hand and needs no index of its own (T1.66).
    op.execute("CREATE INDEX ix_memories_superseded_by ON memories (superseded_by)")
    op.execute("CREATE INDEX ix_memories_technologies ON memories USING gin (technologies)")
    op.execute("CREATE INDEX ix_memories_fts ON memories USING gin (search_vector)")

    # The one index change the SQL filter-pushdown strictly requires
    # (doc 04 §10). Partial rather than a full composite: the pushed-down
    # predicate's common shape is "live rows in this project", and this is the
    # smallest of the three forms doc 04 offers. The semantic channel cannot
    # use it — an HNSW scan applies the predicate post-scan — so it serves the
    # keyword and direct-scan sides.
    op.execute(
        "CREATE INDEX ix_memories_project_live ON memories (project) "
        "WHERE status = 'active' AND is_archived = false"
    )

    op.execute(
        "CREATE TRIGGER memories_fts_update BEFORE INSERT OR UPDATE OF content "
        "ON memories FOR EACH ROW EXECUTE FUNCTION memories_fts_trigger()"
    )
    op.execute(
        "CREATE TRIGGER memories_touch_updated_at BEFORE UPDATE "
        "ON memories FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    # ------------------------------------------------------------------
    # tags, memory_tags (doc 04 §3.2)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE tags (
            id       SERIAL PRIMARY KEY,
            name     VARCHAR(255) NOT NULL UNIQUE,
            category VARCHAR(50)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE memory_tags (
            memory_id UUID    NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            tag_id    INTEGER NOT NULL REFERENCES tags(id)     ON DELETE CASCADE,
            CONSTRAINT memory_tags_pkey PRIMARY KEY (memory_id, tag_id)
        )
        """
    )

    # ------------------------------------------------------------------
    # entities, entity_relations — the knowledge graph (doc 04 §4)
    # ------------------------------------------------------------------
    # Non-memory-scoped: each row carries the memory_ids of every memory that
    # asserts it, so creating a duplicate appends rather than inserting.
    # These two keep server-side gen_random_uuid() (v4) rather than UUIDv7 —
    # they are ANN-probed and sweep-churned, not range-scanned, so insert
    # locality buys nothing (doc 04 §2). Names live lowercase on disk with the
    # original casing in properties.display_name.
    op.execute(
        """
        CREATE TABLE entities (
            id          UUID NOT NULL DEFAULT gen_random_uuid(),
            name        VARCHAR(500) NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            properties  JSONB  DEFAULT '{}'::jsonb,
            memory_ids  UUID[] DEFAULT '{}'::uuid[],
            -- target-new, INERT: the code-assertion analog of memory_ids, by
            -- which a repo asserts a graph row without a memory (invariant 8
            -- amendment, doc 04 §4.1/§4.2). Lands with empty arrays, so the
            -- sweeps' NOT EXISTS (live repo) clauses are vacuously true and
            -- behaviour is byte-identical. First writer: T2.27.
            repo_ids    UUID[] DEFAULT '{}'::uuid[],
            created_at  TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT entities_pkey PRIMARY KEY (id),
            CONSTRAINT entities_name_entity_type_key UNIQUE (name, entity_type)
        )
        """
    )
    op.execute("CREATE INDEX ix_entities_memory_ids ON entities USING gin (memory_ids)")
    op.execute("CREATE INDEX ix_entities_repo_ids ON entities USING gin (repo_ids)")

    op.execute(
        """
        CREATE TABLE entity_relations (
            id               UUID NOT NULL DEFAULT gen_random_uuid(),
            source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            rel_type         VARCHAR(100) NOT NULL,
            properties       JSONB  DEFAULT '{}'::jsonb,
            weight           DOUBLE PRECISION DEFAULT 0.5,
            memory_ids       UUID[] DEFAULT '{}'::uuid[],
            -- target-new, INERT — as on entities above. First writer: T2.27.
            repo_ids         UUID[] DEFAULT '{}'::uuid[],
            created_at       TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT entity_relations_pkey PRIMARY KEY (id),
            CONSTRAINT entity_relations_source_entity_id_target_entity_id_rel_type_key
                UNIQUE (source_entity_id, target_entity_id, rel_type)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_entity_relations_memory_ids ON entity_relations USING gin (memory_ids)"
    )
    op.execute(
        "CREATE INDEX ix_entity_relations_repo_ids ON entity_relations USING gin (repo_ids)"
    )
    # Reverse-lookup, neighbour and orphan-guard queries filter on the target,
    # which the UNIQUE's source-prefix cannot serve.
    op.execute(
        "CREATE INDEX ix_entity_relations_target ON entity_relations (target_entity_id)"
    )

    _pass_two()


def _pass_two() -> None:
    """T0.12b — knowledge vault, memory satellites, code graph, ops, events."""

    # ------------------------------------------------------------------
    # projects — the minimal namespace registry (doc 04 §7)
    # ------------------------------------------------------------------
    # Lazy auto-registration (INSERT … ON CONFLICT DO NOTHING on capture) and
    # NO FK enforcement yet — every scoped table keeps its bare project text
    # column. It lands now because knowledge_triples.triple_key embeds project
    # in FACT IDENTITY, so a typo'd project silently splits corroboration
    # across two identities.
    op.execute(
        """
        CREATE TABLE projects (
            name         TEXT PRIMARY KEY,
            display_name TEXT,
            kind         TEXT NOT NULL DEFAULT 'project'
                         CHECK (kind IN ('project', 'personal')),
            properties   JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # Exactly one personal space, enforced rather than conventional: this is
    # the whole reason `kind` is a column and not a `properties` label.
    op.execute(
        "CREATE UNIQUE INDEX ux_projects_one_personal ON projects (kind) "
        "WHERE kind = 'personal'"
    )

    # ------------------------------------------------------------------
    # Memory satellites (doc 04 §3.3, §8.2, §8.4, §9)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE memory_crossrefs (
            memory_id         UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            related_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
            score             DOUBLE PRECISION NOT NULL,
            CONSTRAINT memory_crossrefs_pkey PRIMARY KEY (memory_id, related_memory_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_memory_crossrefs_related ON memory_crossrefs (related_memory_id)"
    )

    # 1:1 ranking priors live here rather than on memories: memories is the
    # widest hot row in the system, so a per-read bump would rewrite that whole
    # tuple version — MVCC bloat on the most-read table — and would fire the
    # updated_at bump, corrupting its "content changed" meaning (doc 04 §9).
    op.execute(
        """
        CREATE TABLE memory_access_stats (
            memory_id     UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
            access_count  INTEGER NOT NULL DEFAULT 0,
            last_accessed TIMESTAMPTZ
        )
        """
    )

    # Typed, directed memory-to-memory edges. Stores exactly the FIVE
    # associative types — SUPERSEDES is a read-time projection over
    # memories.superseded_by and is never stored, so the pointer stays the
    # single source of truth (doc 04 §8.2). The endpoint FKs are COMPOSITE on
    # (memory_id, project), which is what makes a cross-project edge
    # unrepresentable rather than merely forbidden; they need the
    # memories UNIQUE (id, project) support landed in pass one.
    op.execute(
        """
        CREATE TABLE memory_relations (
            id               UUID NOT NULL,
            source_memory_id UUID NOT NULL,
            target_memory_id UUID NOT NULL,
            rel_type         TEXT NOT NULL,
            project          TEXT NOT NULL,
            properties       JSONB,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT memory_relations_pkey PRIMARY KEY (id),
            CONSTRAINT memory_relations_source_target_type_key
                UNIQUE (source_memory_id, target_memory_id, rel_type),
            CONSTRAINT fk_memory_relations_source
                FOREIGN KEY (source_memory_id, project)
                REFERENCES memories(id, project) ON DELETE CASCADE,
            CONSTRAINT fk_memory_relations_target
                FOREIGN KEY (target_memory_id, project)
                REFERENCES memories(id, project) ON DELETE CASCADE
        )
        """
    )
    # "What points at this memory" filters on the target, which the UNIQUE's
    # source prefix cannot serve — entity_relations' migration-0002 lesson,
    # applied here from day one.
    op.execute(
        "CREATE INDEX ix_memory_relations_target ON memory_relations (target_memory_id)"
    )

    # Topics are Leiden communities over a project-scoped projection, never
    # entities: an entities row would fall through the closed ENTITY_TYPES
    # fallback to 'concept' and collide with UNIQUE(name, entity_type).
    # Re-derivation is delete-and-rewrite per project, so community ids CHURN
    # on every run — nothing durable may FK one (doc 04 §8.4).
    #
    # UNIQUE (id, project) is trivially satisfiable (id is already the PK) and
    # exists for the same reason memories_id_project_key does: it is what lets
    # the members table declare a COMPOSITE endpoint FK.
    op.execute(
        """
        CREATE TABLE memory_communities (
            id            UUID NOT NULL,
            project       TEXT NOT NULL,
            label         TEXT,
            report_string TEXT,
            properties    JSONB,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT memory_communities_pkey PRIMARY KEY (id),
            CONSTRAINT memory_communities_id_project_key UNIQUE (id, project)
        )
        """
    )
    # BOTH endpoint FKs are composite on `project`, and one is not enough.
    # With only the memory-side key, a member row naming a project-A community,
    # a project-B memory and project B satisfies every constraint and is still
    # cross-project. With both, `project` must equal the memory's project AND
    # the community's project, so those two are equal by transitivity — which
    # makes a cross-project membership unrepresentable rather than merely
    # forbidden. All three columns are NOT NULL, so MATCH SIMPLE offers no null
    # escape. There is deliberately no ON UPDATE action: a memory changing
    # project must clear its memberships first (app/services/memory.py), the
    # same shape as the demote-before-delete rule.
    op.execute(
        """
        CREATE TABLE memory_community_members (
            community_id UUID NOT NULL,
            memory_id    UUID NOT NULL,
            project      TEXT NOT NULL,
            CONSTRAINT memory_community_members_pkey PRIMARY KEY (community_id, memory_id),
            CONSTRAINT fk_memory_community_members_community
                FOREIGN KEY (community_id, project)
                REFERENCES memory_communities(id, project) ON DELETE CASCADE,
            CONSTRAINT fk_memory_community_members_memory
                FOREIGN KEY (memory_id, project)
                REFERENCES memories(id, project) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_memory_community_members_memory "
        "ON memory_community_members (memory_id)"
    )

    # ------------------------------------------------------------------
    # memory_buffer — the durable Tier-B ingest buffer (doc 04 §8.6)
    # ------------------------------------------------------------------
    # Claimed via SELECT … FOR UPDATE SKIP LOCKED, so fast capture-ack is
    # decoupled from the five-phase pipeline with a durability an in-process
    # queue cannot give — and no external broker (invariant 1).
    op.execute(
        """
        CREATE TABLE memory_buffer (
            id         UUID NOT NULL,
            project    TEXT NOT NULL,
            source     TEXT,
            content    TEXT NOT NULL,
            token_size INTEGER,
            status     TEXT NOT NULL DEFAULT 'pending',
            attempts   INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            metadata   JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            claimed_at TIMESTAMPTZ,
            claimed_by TEXT,
            CONSTRAINT memory_buffer_pkey PRIMARY KEY (id),
            CONSTRAINT memory_buffer_status_check
                CHECK (status IN ('pending', 'claimed', 'done', 'error'))
        )
        """
    )
    # The claim scan only ever reads pending rows, so the hot index stays small.
    op.execute(
        "CREATE INDEX ix_memory_buffer_pending ON memory_buffer (created_at) "
        "WHERE status = 'pending'"
    )

    # ------------------------------------------------------------------
    # knowledge_triples — the Layer-2 verified-fact store (doc 04 §8.3)
    # ------------------------------------------------------------------
    # A REBUILD that keeps a name, NOT an activation of the dormant demo
    # scaffolding: every column and semantic is new. The endpoints carry NO
    # hard FK — the graph side deletes entities aggressively while this
    # table's contract is invalidate-not-delete, so expired triples must
    # survive their endpoints. The denormalised lowercase names carry the
    # durable identity instead.
    #
    # demotion_pending_since / demotion_pending_cycles are doc 08 §4.3's
    # demotion hysteresis, and they are NOT a fifth rung: the CHECK below
    # still admits exactly four verification_status values, and an
    # under-sourced fact is a still-`corroborated` row wearing an overlay
    # (doc 13 §5.3, doc 14). `demotion_pending_since IS NOT NULL` is
    # simultaneously the label a consumer renders and the review-queue
    # predicate `verification_ladder.derive_review_state` registers, which is
    # why the marker is nullable rather than defaulted. The companion counter
    # is what makes the grace measurable at all: doc 08 §4.3 fixes the window
    # in *consecutive recompute cycles*, and a timestamp cannot count cycles.
    op.execute(
        """
        CREATE TABLE knowledge_triples (
            id                  UUID NOT NULL,
            subject_id          UUID,
            object_id           UUID,
            subject_name        TEXT NOT NULL,
            object_name         TEXT NOT NULL,
            rel_type            TEXT NOT NULL,
            valid_at            TIMESTAMPTZ,
            invalid_at          TIMESTAMPTZ,
            expired_at          TIMESTAMPTZ,
            reference_time      TIMESTAMPTZ NOT NULL,
            fact                TEXT NOT NULL,
            project             TEXT NOT NULL DEFAULT 'default',
            triple_key          TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'candidate',
            confidence          REAL,
            applies_when        JSONB,
            learned_in          TEXT[],
            review_state        TEXT,
            source_file         TEXT,
            demotion_pending_since  TIMESTAMPTZ,
            demotion_pending_cycles INTEGER NOT NULL DEFAULT 0,
            -- T2.112 (doc 08 §6, ruled 2026-08-08). Doc 08 §6's third review
            -- opener, shaped after demotion_pending_since above rather than
            -- invented. The ladder re-derives the model scan's finding on
            -- every recompute (guards re-applied against live rows) and
            -- writes the result here in the SAME UPDATE as
            -- verification_status, so this is a cache the authority refreshes
            -- each cycle, not a frozen verdict. It is not a rung: a flagged
            -- fact keeps its status, its badge and its place in retrieval
            -- while a human looks.
            --
            -- No FK on the counterpart, deliberately. Facts are
            -- invalidate-not-delete, so a counterpart outlives its own
            -- retirement; a cascade would blank the evidence for the flag at
            -- exactly the moment a reviewer needed it. Same reasoning as
            -- knowledge_triples.subject_id/object_id carrying no FK.
            contradiction_suspected_at    TIMESTAMPTZ,
            contradiction_counterpart_id  UUID,
            -- T2.85 (doc 08 §3.1/§9, ruled 2026-08-06). The expiry a fact's
            -- own text STATES, recorded at lift time and spent later by the
            -- recompute arm, which writes invalid_at := stated_expiry once
            -- the date passes. It is deliberately NOT invalid_at at write
            -- time: invalid_at is only-ever-past by contract, and a future
            -- one drops the fact out of OPEN_BELIEF_PREDICATE the day it is
            -- written. It is deliberately NOT expired_at either: as_of
            -- ignores expired_at, so a stated expiry recorded there answers
            -- the historical question wrongly for every instant past the
            -- date. Nullable; a fact whose text states no expiry has none.
            stated_expiry       TIMESTAMPTZ,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT knowledge_triples_pkey PRIMARY KEY (id),
            CONSTRAINT knowledge_triples_verification_status_check
                CHECK (verification_status IN
                       ('candidate', 'corroborated', 'disputed', 'confirmed'))
        )
        """
    )
    # Non-unique on purpose: disjoint validity windows legitimately leave
    # SEVERAL live rows on one subject/predicate/object.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_live "
        "ON knowledge_triples (subject_name, rel_type, object_name) "
        "WHERE expired_at IS NULL"
    )
    # T2.98 (doc 08 §5.3, 2026-08-07). The contradiction scan's same-endpoint
    # arm probes `subject_name = X OR object_name = Y`, and a BitmapOr needs
    # BOTH disjuncts indexed or Postgres falls back to scanning the whole of
    # whatever index is narrowest — the subject one above, in this table's
    # case, since it is still cheaper than the heap. That is real work
    # proportional to every live triple, not a lookup, which is what doc
    # 08 §5.3's "cheap SQL" cost argument assumes for both endpoints.
    # Mirrors the subject index's column order rather than staying
    # object-name-only: `GET /api/v1/knowledge/facts` (`facts_read.list_facts`
    # via `get_live`/`list_live`) filters `object_name` together with
    # `rel_type` and no `subject_name`, the exact object-side analogue of the
    # subject probe the leading `(subject_name, rel_type, ...)` order already
    # serves. A narrower object-name-only index would miss that combination's
    # leading column.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_live_object "
        "ON knowledge_triples (object_name, rel_type, subject_name) "
        "WHERE expired_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_triples_window ON knowledge_triples (valid_at, invalid_at)"
    )
    # At most one CURRENTLY-OPEN belief per fact. Window-closed rows
    # (invalid_at set) leave the unique's scope but remain live history, which
    # is exactly what the disjoint-window pass produces.
    op.execute(
        "CREATE UNIQUE INDEX ux_knowledge_triples_open ON knowledge_triples (triple_key) "
        "WHERE expired_at IS NULL AND invalid_at IS NULL"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_triples_review ON knowledge_triples (review_state) "
        "WHERE review_state = 'open'"
    )
    # The recompute arm's sweep: open beliefs carrying a stated expiry, which
    # is a small subset of a small subset. Partial on the same two-NULL
    # predicate the open-belief indexes use, so it stays in step with them.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_stated_expiry "
        "ON knowledge_triples (stated_expiry) "
        "WHERE expired_at IS NULL AND invalid_at IS NULL "
        "AND stated_expiry IS NOT NULL"
    )
    # The three the Layer-2 retrieval channel is born with (doc 07 §2, §7).
    # All three are partial on the CURRENTLY-OPEN-BELIEF window rather than on
    # `expired_at IS NULL`: doc 08 §3.1 reserves "live" for the latter, which
    # still counts window-closed rows as history, and serving those would
    # present a withdrawn belief as current. Partial rather than full is also
    # what pushes the belief scope into the index itself, so a query that
    # widens the predicate stops matching the index instead of quietly
    # returning history.
    #
    # No tsvector column and no trigger: `fact`, `subject_name` and
    # `object_name` are written once at fact-lift time and never updated (the
    # belief and verification axes move the timestamps and the status, never
    # the text), so a stored column would carry maintenance cost for a value
    # that cannot change. The query must spell these expressions verbatim or
    # the planner cannot match them.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_fact_fts ON knowledge_triples "
        "USING gin (to_tsvector('english', fact)) "
        "WHERE expired_at IS NULL AND invalid_at IS NULL"
    )
    # 'simple' rather than 'english' on the endpoints: these are canonicalised
    # lowercase identifiers, not prose, and stemming a product name buys no
    # recall while risking a collision between two distinct names.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_name_fts ON knowledge_triples "
        "USING gin (to_tsvector('simple', subject_name || ' ' || object_name)) "
        "WHERE expired_at IS NULL AND invalid_at IS NULL"
    )
    # The contradiction scan's trigram shortlist (doc 08 §5.3), and the one
    # index here that is partial on LIVE rather than on OPEN BELIEF. The scan
    # adjudicates a candidate pair on whether their validity windows overlap,
    # so a window-closed row is still a legitimate counterpart; narrowing this
    # to the open-belief predicate the FTS indexes use would silently drop
    # exactly the succession-versus-contradiction cases the overlap guard
    # exists to decide. Same liveness predicate the deterministic
    # same-endpoint scan already selects on, so the two arms agree about which
    # rows exist.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_fact_trgm ON knowledge_triples "
        "USING gin (fact gin_trgm_ops) WHERE expired_at IS NULL"
    )
    # The project pushdown's own support, the analogue of
    # ix_memories_project_live: it serves the scope when the query carries no
    # search term, where neither FTS index applies.
    op.execute(
        "CREATE INDEX ix_knowledge_triples_project_open ON knowledge_triples (project) "
        "WHERE expired_at IS NULL AND invalid_at IS NULL"
    )

    # Provenance leaves the fact row entirely: a uuid[] cannot carry per-source
    # metadata, index per-kind reverse lookups, or compute
    # COUNT(DISTINCT origin_key) — which is the corroboration signal, because
    # echo is not evidence (doc 04 §8.3).
    op.execute(
        """
        CREATE TABLE fact_sources (
            id          UUID NOT NULL,
            fact_id     UUID NOT NULL REFERENCES knowledge_triples(id) ON DELETE CASCADE,
            source_kind TEXT,
            source_ref  TEXT,
            origin_key  TEXT,
            detail      JSONB,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fact_sources_pkey PRIMARY KEY (id),
            CONSTRAINT fact_sources_fact_kind_ref_key UNIQUE (fact_id, source_kind, source_ref)
        )
        """
    )
    # The member-source reverse lookup — "which facts does memory X assert" —
    # the role the removed source_memory_ids GIN played.
    op.execute(
        "CREATE INDEX ix_fact_sources_kind_ref ON fact_sources (source_kind, source_ref)"
    )
    op.execute("CREATE INDEX ix_fact_sources_fact ON fact_sources (fact_id)")

    # The fact-keyed analogue of memory_access_stats (doc 08 §6, T2.84,
    # 2026-08-05). T2.65 measured that FactsChannel serves knowledge_triples
    # rows directly and records heat nowhere, so review_ranking's frequency
    # arm degraded toward zero for facts channel traffic; this table is the
    # replacement substrate, fed from that channel's serving path the same
    # way memory_access_stats is fed from the memory hybrid's. 1:1 side table
    # for the identical reason memory_access_stats is one rather than two
    # columns on knowledge_triples: a per-read bump must never rewrite the
    # fact row itself, which knowledge_triples has no updated_at trigger to
    # protect but which fact_lift and the verification ladder both read and
    # write at a much lower rate than facts are served.
    op.execute(
        """
        CREATE TABLE fact_access_stats (
            fact_id       UUID PRIMARY KEY REFERENCES knowledge_triples(id) ON DELETE CASCADE,
            access_count  INTEGER NOT NULL DEFAULT 0,
            last_accessed TIMESTAMPTZ
        )
        """
    )

    # session_checkpoints — operational, NOT vault knowledge (spec
    # §Feature-2, T3.16). Keyed on `origin_key`, the agent-run identity
    # `resolve_origin_key` already stamps on capture (T1.11), so a checkpoint
    # and the memories from the same run share one key without this table
    # referencing `memories` at all — the two are correlated, never joined.
    #
    # **No verification column, and that is the design.** A checkpoint is an
    # agent's note to its successor, not a claim the vault has corroborated;
    # giving it a rung would put an unearned badge on prose no ladder ever
    # judged. It is deliberately outside `knowledge_triples` for the same
    # reason (T3.18 owns the rule).
    #
    # `next_steps` is JSONB rather than prose: the resume path renders it
    # into a token-budgeted block, and a structured list is what lets that
    # budget drop whole steps instead of truncating a sentence mid-word.
    #
    # The two length CHECKs are the "payload size is bounded" done-when, in
    # the database rather than only in the schema layer: this table is written
    # by two doors and an unbounded summary would be an unbounded row on the
    # resume path's hot read.
    op.execute(
        """
        CREATE TABLE session_checkpoints (
            id          UUID NOT NULL,
            origin_key  TEXT NOT NULL,
            project     TEXT NOT NULL DEFAULT 'default',
            summary     TEXT NOT NULL,
            next_steps  JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT session_checkpoints_pkey PRIMARY KEY (id),
            CONSTRAINT chk_session_checkpoints_summary_len
                CHECK (char_length(summary) <= 4000),
            CONSTRAINT chk_session_checkpoints_next_steps_len
                -- Mirrored by `checkpoints.NEXT_STEPS_MAX_BYTES`, which the
                -- schema layer checks the *encoded* size against. Character
                -- bounds alone were not enough: JSONB encoding of non-ASCII
                -- text costs several bytes per character, so a payload well
                -- inside every character limit still violated this CHECK and
                -- surfaced as a 500 on a request validation had passed.
                CHECK (pg_column_size(next_steps) <= 16384)
        )
        """
    )
    # "Latest per origin is ONE indexed query" (T3.16's done-when): DESC on
    # created_at with id as the tie-break makes the newest row per origin the
    # index's first entry for that key, so the read is a one-row index scan
    # rather than a sort. The id tie-break matters because two checkpoints
    # saved in one transaction share `now()`.
    op.execute(
        "CREATE INDEX ix_session_checkpoints_latest "
        "ON session_checkpoints (project, origin_key, created_at DESC, id DESC)"
    )

    # ------------------------------------------------------------------
    # workstreams + worklog_entries — the work-log lane
    # (docs/superpowers/specs/2026-09-23-work-log-lane-design.md §1)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE workstreams (
            id            UUID NOT NULL,
            project       TEXT NOT NULL,
            key           TEXT NOT NULL,
            title         TEXT,
            client        TEXT,
            state         TEXT NOT NULL DEFAULT 'open',
            closed_at     TIMESTAMPTZ,
            retain        BOOLEAN NOT NULL DEFAULT false,
            properties    JSONB NOT NULL DEFAULT '{}'::jsonb,
            last_entry_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT workstreams_pkey PRIMARY KEY (id),
            CONSTRAINT ux_workstreams_project_key UNIQUE (project, key),
            CONSTRAINT chk_workstreams_state CHECK (state IN ('open', 'closed')),
            CONSTRAINT chk_workstreams_closed_at
                CHECK ((state = 'closed') = (closed_at IS NOT NULL)),
            CONSTRAINT chk_workstreams_key_len CHECK (char_length(key) BETWEEN 1 AND 200),
            CONSTRAINT chk_workstreams_title_len CHECK (char_length(title) <= 500),
            CONSTRAINT chk_workstreams_properties_size
                CHECK (pg_column_size(properties) <= 16384)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER workstreams_touch_updated_at BEFORE UPDATE "
        "ON workstreams FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )
    op.execute(
        "CREATE INDEX ix_workstreams_project_created "
        "ON workstreams (project, created_at DESC, id DESC)"
    )
    # `seq`, not created_at, orders entries: every entry of one append shares
    # the transaction's now(), and a ledger's chunks must concatenate back in
    # the order they were written.
    op.execute(
        """
        CREATE TABLE worklog_entries (
            id            UUID NOT NULL,
            seq           BIGINT GENERATED ALWAYS AS IDENTITY,
            workstream_id UUID NOT NULL REFERENCES workstreams(id) ON DELETE CASCADE,
            run_key       TEXT NOT NULL,
            kind          TEXT NOT NULL,
            body          TEXT NOT NULL,
            properties    JSONB NOT NULL DEFAULT '{}'::jsonb,
            search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', body)) STORED,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT worklog_entries_pkey PRIMARY KEY (id),
            CONSTRAINT chk_worklog_entries_kind
                CHECK (kind IN ('checkpoint', 'ledger', 'note')),
            CONSTRAINT chk_worklog_entries_body_len
                CHECK (char_length(body) BETWEEN 1 AND 65536),
            CONSTRAINT chk_worklog_entries_properties_size
                CHECK (pg_column_size(properties) <= 16384)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_worklog_entries_kind_latest "
        "ON worklog_entries (workstream_id, kind, seq DESC)"
    )
    op.execute(
        "CREATE INDEX ix_worklog_entries_order ON worklog_entries (workstream_id, seq)"
    )
    op.execute(
        "CREATE INDEX ix_worklog_entries_fts ON worklog_entries USING gin (search_vector)"
    )

    # ------------------------------------------------------------------
    # knowledge_articles + article_citations — Layer 3 (doc 04 §8.8)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE knowledge_articles (
            id             UUID NOT NULL,
            subject_key    TEXT NOT NULL,
            project        TEXT NOT NULL,
            title          TEXT,
            content        TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'candidate',
            confidence     REAL,
            applies_when   JSONB,
            learned_in     TEXT[],
            synthesized_at TIMESTAMPTZ,
            fact_set_hash  TEXT,
            review_state   TEXT,
            superseded_by  UUID REFERENCES knowledge_articles(id),
            -- The held-re-synthesis marker (doc 09 §4.4 as amended
            -- 2026-08-12). Attention without withholding: a re-synthesis
            -- measured below the coverage bar marks the standing article so a
            -- human sees the subject, and deliberately does NOT touch
            -- `review_state`, which withholds. `_at` is when the hold opened
            -- and does not move while it is continuously held (doc 08 §4.2's
            -- `contradiction_suspected_at` semantics); the coverage and the
            -- hash it was measured against refresh on every held attempt.
            resynthesis_held_at       TIMESTAMPTZ,
            resynthesis_held_coverage REAL,
            resynthesis_held_hash     TEXT,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT knowledge_articles_pkey PRIMARY KEY (id),
            CONSTRAINT knowledge_articles_status_check
                CHECK (status IN ('candidate', 'corroborated', 'disputed',
                                  'confirmed', 'superseded'))
        )
        """
    )
    # Exactly one live article per subject.
    op.execute(
        "CREATE UNIQUE INDEX ux_knowledge_articles_live ON knowledge_articles (project, subject_key) "
        "WHERE status <> 'superseded'"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_articles_review ON knowledge_articles (review_state) "
        "WHERE review_state = 'open'"
    )
    # The held lane's own partial index. Deliberately not folded into the
    # `review_state = 'open'` index above: the queue's two article arms are
    # separate statements with separate predicates, and widening either
    # predicate to cover both loses the partial index for the arm it was built
    # for.
    op.execute(
        "CREATE INDEX ix_knowledge_articles_resynthesis_held ON knowledge_articles "
        "(resynthesis_held_at) WHERE resynthesis_held_at IS NOT NULL"
    )

    # fact_id takes a HARD FK — the deliberate contrast with §8.3's soft
    # endpoint refs. Facts are invalidate-not-delete (rows are never deleted),
    # so the hard FK is safe, and it buys integrity at the one place a dangling
    # citation would be a truth catastrophe: a dead citation under a
    # corroborated badge.
    op.execute(
        """
        CREATE TABLE article_citations (
            id         UUID NOT NULL,
            article_id UUID NOT NULL REFERENCES knowledge_articles(id) ON DELETE CASCADE,
            fact_id    UUID NOT NULL REFERENCES knowledge_triples(id),
            claim_span INT4RANGE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT article_citations_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX ix_article_citations_article ON article_citations (article_id)")

    # ------------------------------------------------------------------
    # Code graph (doc 04 §6)
    # ------------------------------------------------------------------
    # Repo-scoped, owner-qualified, and it never joins the memory-side entity
    # graph. index_debt lands inert — no doc 19 §3 row and no task list names
    # it (inventory F-13), so it lands with the table that owns it.
    # A named forge credential, shared by every repo that selects it, so a
    # token rotation is one edit rather than one per repo. The token is stored
    # in the clear, the posture llm_providers.api_key already takes.
    op.execute(
        """
        CREATE TABLE git_accounts (
            id               UUID NOT NULL,
            label            VARCHAR(100) NOT NULL,
            provider         VARCHAR(50) NOT NULL DEFAULT 'github',
            host             VARCHAR(255) NOT NULL DEFAULT 'github.com',
            username         VARCHAR(255) NOT NULL,
            token            VARCHAR(1024) NOT NULL,
            scopes           VARCHAR(512),
            is_default       BOOLEAN NOT NULL DEFAULT false,
            last_verified_at TIMESTAMPTZ,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT git_accounts_pkey PRIMARY KEY (id)
        )
        """
    )
    # Keyed on the operator's own label rather than the forge username: two
    # tokens for one account (a read-only and a write one, or an overlap
    # during rotation) are legitimate rows, and the label is what distinguishes
    # them in the picker.
    op.execute(
        "CREATE UNIQUE INDEX ux_git_accounts_label "
        "ON git_accounts (provider, host, label)"
    )
    # At most one default per forge. Scoped to (provider, host) so github.com
    # and a GitHub Enterprise install can each carry their own.
    op.execute(
        "CREATE UNIQUE INDEX ux_git_accounts_default "
        "ON git_accounts (provider, host) WHERE is_default"
    )
    op.execute(
        "CREATE TRIGGER git_accounts_touch_updated_at BEFORE UPDATE "
        "ON git_accounts FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE repositories (
            id                  UUID NOT NULL,
            name                VARCHAR(255) NOT NULL,
            url                 VARCHAR(1024),
            local_path          VARCHAR(1024),
            provider            VARCHAR(50) NOT NULL DEFAULT 'local',
            default_branch      VARCHAR(100) NOT NULL DEFAULT 'main',
            auth_token_ref      VARCHAR(255),
            git_account_id      UUID REFERENCES git_accounts(id) ON DELETE SET NULL,
            last_indexed_commit VARCHAR(64),
            last_indexed_at     TIMESTAMPTZ,
            index_debt          JSONB,
            fetch_enabled            BOOLEAN NOT NULL DEFAULT false,
            fetch_interval_seconds   INTEGER NOT NULL DEFAULT 300,
            index_on_commit_enabled  BOOLEAN NOT NULL DEFAULT false,
            commit_poll_seconds      INTEGER NOT NULL DEFAULT 60,
            index_uncommitted        BOOLEAN NOT NULL DEFAULT false,
            status              VARCHAR(20) NOT NULL,
            status_message      VARCHAR(500),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT repositories_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER repositories_touch_updated_at BEFORE UPDATE "
        "ON repositories FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE code_files (
            id              UUID NOT NULL,
            repo_id         UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            file_path       VARCHAR(1024) NOT NULL,
            language        VARCHAR(50),
            last_commit_sha VARCHAR(64),
            content_hash    VARCHAR(64),
            indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT code_files_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX ix_code_files_repo_path ON code_files (repo_id, file_path)")

    op.execute(
        """
        CREATE TABLE code_symbols (
            id                  UUID NOT NULL,
            file_id             UUID NOT NULL REFERENCES code_files(id) ON DELETE CASCADE,
            name                VARCHAR(500) NOT NULL,
            kind                VARCHAR(50) NOT NULL,
            line_start          INTEGER NOT NULL,
            line_end            INTEGER NOT NULL,
            signature           TEXT,
            docstring           TEXT,
            visibility          VARCHAR(20),
            parent_symbol_id    UUID REFERENCES code_symbols(id) ON DELETE SET NULL,
            source_code         TEXT NOT NULL,
            summary             TEXT,
            enrichment_status   VARCHAR(20) NOT NULL DEFAULT 'pending',
            enrichment_priority INTEGER NOT NULL DEFAULT 0,
            enrichment_attempts INTEGER NOT NULL DEFAULT 0,
            CONSTRAINT code_symbols_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute("CREATE INDEX ix_code_symbols_file_id ON code_symbols (file_id)")
    # THE enrichment backlog. There is no queue table — enrichment_queue was
    # dormant scaffolding with zero references and is dropped (inventory §8).
    op.execute(
        "CREATE INDEX ix_code_symbols_enrichment_pending "
        "ON code_symbols (enrichment_attempts, enrichment_priority DESC) "
        "WHERE enrichment_status = 'pending'"
    )

    # kind is polymorphic: communities and processes are node KINDS, not
    # separate tables. Keys are owner-qualified (name::file_path::owner) so
    # method-level nodes resolve without collision.
    op.execute(
        """
        CREATE TABLE code_graph_nodes (
            id         BIGSERIAL,
            repo_id    UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            kind       VARCHAR(20) NOT NULL,
            key        VARCHAR(1024) NOT NULL,
            label      VARCHAR(500),
            properties JSONB DEFAULT '{}'::jsonb,
            CONSTRAINT code_graph_nodes_pkey PRIMARY KEY (id),
            CONSTRAINT code_graph_nodes_repo_id_kind_key_key UNIQUE (repo_id, kind, key)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE code_edges (
            id          BIGSERIAL,
            repo_id     UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            source_kind VARCHAR(20) NOT NULL,
            source_key  VARCHAR(1024) NOT NULL,
            target_kind VARCHAR(20) NOT NULL,
            target_key  VARCHAR(1024) NOT NULL,
            edge_type   VARCHAR(50) NOT NULL,
            properties  JSONB DEFAULT '{}'::jsonb,
            CONSTRAINT code_edges_pkey PRIMARY KEY (id),
            CONSTRAINT code_edges_repo_id_source_kind_source_key_target_kind_targe_key
                UNIQUE (repo_id, source_kind, source_key, target_kind, target_key, edge_type)
        )
        """
    )
    op.execute("CREATE INDEX ix_code_edges_repo_type ON code_edges (repo_id, edge_type)")
    op.execute("CREATE INDEX ix_code_edges_repo_source ON code_edges (repo_id, source_key)")
    op.execute("CREATE INDEX ix_code_edges_repo_target ON code_edges (repo_id, target_key)")
    op.execute(
        "CREATE INDEX ix_code_edges_covering "
        "ON code_edges (repo_id, edge_type, source_key, target_key)"
    )

    # A registry-level association only — two projects referencing the same
    # remote own the SAME repo and its one code graph, not private copies. This
    # bridges the two graphs without merging them (doc 04 §8.7).
    op.execute(
        """
        CREATE TABLE project_repositories (
            project    TEXT NOT NULL,
            repo_id    UUID NOT NULL REFERENCES repositories(id),
            added_from TEXT,
            opt_out    BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT project_repositories_pkey PRIMARY KEY (project, repo_id)
        )
        """
    )

    # ------------------------------------------------------------------
    # Operations, auth, chat, LLM config (doc 04 §7)
    # ------------------------------------------------------------------
    # The polymorphic retry tracker — the substrate under honest partial
    # results. After Phase 5, derive_memory_failed_step records or resolves a
    # row here PER MEMORY, never collapsed to a batch pass/fail.
    op.execute(
        """
        CREATE TABLE pipeline_failures (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type     VARCHAR(50) NOT NULL,
            entity_id       UUID NOT NULL,
            pipeline_name   VARCHAR(50) NOT NULL,
            failed_step     VARCHAR(100) NOT NULL,
            error_message   TEXT,
            attempts        INTEGER NOT NULL DEFAULT 1,
            first_failed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at     TIMESTAMPTZ,
            metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    # One OPEN failure per entity+pipeline.
    op.execute(
        "CREATE UNIQUE INDEX idx_pipeline_failures_unresolved "
        "ON pipeline_failures (entity_type, entity_id, pipeline_name) "
        "WHERE resolved_at IS NULL"
    )
    op.execute(
        "CREATE INDEX idx_pipeline_failures_pipeline_name ON pipeline_failures (pipeline_name) "
        "WHERE resolved_at IS NULL"
    )

    # ── llm_usage ────────────────────────────────────────────────────────
    # Token and cost telemetry: one row per vendor call. Sibling of job_runs,
    # and for the same reason it is not `events` — that substrate is
    # append-only by trigger and permanent by ruling, and doc 17 section 5.1's
    # metrics are SQL over it alone. This is high-volume telemetry that wants
    # pruning, so DELETE is ordinary here and `llm_usage_cleanup` holds it to
    # a configured ceiling.
    #
    # subject_id is TEXT, not UUID: a job run is `{job_key}@{started_at}`
    # because the job_runs row is written only after the runner returns — and
    # a run reporting nothing writes no row at all — while search and chat
    # subjects are request ids.
    #
    # Token columns are nullable so an unmeasured call stores NULL rather than
    # 0; a vendor that stops reporting usage must never render as free.
    # cost_micros is BIGINT micro-USD: money never touches a float.
    op.execute(
        """
        CREATE TABLE llm_usage (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            purpose           VARCHAR(32) NOT NULL,
            model             VARCHAR(128) NOT NULL,
            provider          VARCHAR(128),
            api_kind          VARCHAR(32) NOT NULL,
            subject_type      VARCHAR(16) NOT NULL,
            subject_id        TEXT,
            project           TEXT,
            prompt_tokens     INTEGER,
            cached_tokens     INTEGER,
            completion_tokens INTEGER,
            reasoning_tokens  INTEGER,
            tokens_measured   BOOLEAN NOT NULL DEFAULT false,
            cost_micros       BIGINT,
            rates_used        JSONB NOT NULL DEFAULT '{}'::jsonb,
            usage_raw         JSONB NOT NULL DEFAULT '{}'::jsonb,
            ok                BOOLEAN NOT NULL DEFAULT true,
            error_kind        VARCHAR(64),
            duration_ms       INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # The per-memory and per-job detail views read by subject; the overview and
    # the retention sweep read by time; the by-purpose rollup reads both.
    op.execute(
        "CREATE INDEX ix_llm_usage_subject ON llm_usage (subject_type, subject_id)"
    )
    op.execute("CREATE INDEX ix_llm_usage_occurred ON llm_usage (occurred_at)")
    op.execute(
        "CREATE INDEX ix_llm_usage_purpose_occurred ON llm_usage (purpose, occurred_at)"
    )

    # ── job_runs ─────────────────────────────────────────────────────────
    # Job telemetry lives here rather than in `events`. That table is the
    # audit substrate: append-only by trigger and permanent by ruling, and
    # doc 17 section 5.1's verification metrics are SQL over it alone. A
    # five-second job wrote ~17k rows a day into something nothing can delete
    # from. Here DELETE is ordinary, so `job_run_cleanup` holds the table to
    # a configured ceiling.
    op.execute(
        """
        CREATE TABLE job_runs (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_key          VARCHAR(128) NOT NULL,
            outcome          VARCHAR(16) NOT NULL,
            started_at       TIMESTAMPTZ NOT NULL,
            duration_seconds DOUBLE PRECISION NOT NULL,
            trigger          VARCHAR(16) NOT NULL DEFAULT 'schedule',
            error            TEXT,
            detail           JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    # The history dialog reads one job newest-first; the cleanup job trims
    # oldest-first across every job.
    op.execute(
        "CREATE INDEX ix_job_runs_key_started ON job_runs (job_key, started_at DESC)"
    )
    op.execute("CREATE INDEX ix_job_runs_started ON job_runs (started_at)")
    op.execute(
        "CREATE INDEX idx_pipeline_failures_resolved_at ON pipeline_failures (resolved_at) "
        "WHERE resolved_at IS NOT NULL"
    )

    # The live JWT revocation store, swept by token_blocklist_cleanup. Only the
    # UNIQUE lands: the pre-baseline schema also carried a plain btree on jti,
    # fully redundant under it, and doc 04 §7 specifies only jti UNIQUE
    # (inventory F-12).
    op.execute(
        """
        CREATE TABLE token_blocklist (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            jti        VARCHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )

    # Wired by T4.01 (doc 18 §5) — this comment read "Exists, unwired … the
    # schema carries over unchanged" until the activation landed, which is the
    # invariant-23 honesty label going stale in the direction that presents a
    # shipped path as dormant. The two added columns are the whole schema
    # cost of the activation, which doc 04 §9 caps at "adding columns to the
    # existing table, never a new table".
    #
    # `key_id` is the public half of `dmk_<key_id>_<secret>` and exists because
    # bcrypt salts per row: hashing a presented secret does not reproduce the
    # stored hash, so without an indexed lookup handle the only way to verify a
    # key is to bcrypt it against every row.
    #
    # `revoked_at` rather than a DELETE: `events.api_key_id` carries no foreign
    # key here, so removing the row would leave every call the key ever made
    # attributed to an id nothing explains.
    op.execute(
        """
        CREATE TABLE api_keys (
            id           UUID NOT NULL,
            name         VARCHAR(255) NOT NULL,
            key_id       VARCHAR(32) NOT NULL UNIQUE,
            key_hash     VARCHAR(255) NOT NULL UNIQUE,
            scopes       JSONB NOT NULL,
            profile      VARCHAR(100),
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_used_at TIMESTAMPTZ,
            expires_at   TIMESTAMPTZ,
            revoked_at   TIMESTAMPTZ,
            CONSTRAINT api_keys_pkey PRIMARY KEY (id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE conversations (
            id          UUID NOT NULL,
            title       TEXT,
            is_archived BOOLEAN NOT NULL DEFAULT false,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT conversations_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER conversations_touch_updated_at BEFORE UPDATE "
        "ON conversations FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )
    op.execute(
        """
        CREATE TABLE messages (
            id              UUID NOT NULL,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role            VARCHAR NOT NULL,
            content         TEXT NOT NULL,
            context         JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT messages_pkey PRIMARY KEY (id)
        )
        """
    )

    # Eight rows, PK (purpose), each naming a provider rather than carrying
    # its connection inline. llm_profiles and ml_profiles never exist in the
    # baseline, and their FK columns go with them (inventory §8, F-08 — none
    # was named *_ref). classifier_kind replaces the deleted ml_profiles
    # reference. llm_providers is reinstated below by the owner ruling of
    # 2026-08-20, reversing doc 04 §7's flattening.
    # The rows themselves are written by the setup wizard's finalize step
    # from app/services/llm_seed.py, never by a migration.

    # ------------------------------------------------------------------
    # llm_providers — the connection layer under the purposes
    # ------------------------------------------------------------------
    # Reinstated by the owner ruling of 2026-08-20, reversing doc 04 §7's
    # flattening. A purpose references a provider by name; resolution is one
    # query with one join and still yields a flat LLMPurposeConfig, which is
    # what keeps the benchlib cache key and the judge identity hash stable.
    op.execute(
        """
        CREATE TABLE llm_providers (
            name       VARCHAR(64) PRIMARY KEY,
            -- The sole vendor-quirk home (doc 04 §7, doc 11 §4). The `provider`
            -- column A.2 showed at HEAD is dropped (F-10, decided by T1.01):
            -- nothing ever dispatched on it — the wizard wrote it as a verbatim
            -- copy of api_kind and every read carried it along unused — so a
            -- second vendor column could only ever drift away from the one that
            -- decides behaviour.
            api_kind   VARCHAR(32)  NOT NULL DEFAULT 'openai',
            base_url   VARCHAR(512) NOT NULL DEFAULT '',
            api_key    VARCHAR(1024),
            updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE llm_purpose_configs (
            purpose         VARCHAR(64) PRIMARY KEY,
            provider_name   VARCHAR(64) NOT NULL
                REFERENCES llm_providers(name) ON UPDATE CASCADE ON DELETE RESTRICT,
            model           VARCHAR(255) NOT NULL,
            dimensions      INTEGER,
            reasoning       BOOLEAN NOT NULL DEFAULT false,
            params          JSONB NOT NULL DEFAULT '{}'::jsonb,
            classifier_kind VARCHAR(16),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT llm_purpose_configs_classifier_kind_check
                CHECK (classifier_kind IS NULL OR classifier_kind IN ('llm', 'local'))
        )
        """
    )

    # ------------------------------------------------------------------
    # documents + blocks — the PKM expansion horizon (doc 04 §8.5)
    # ------------------------------------------------------------------
    # Land empty and INERT: nothing writes them until the PKM pipeline
    # (TH1.02). They are here rather than in T0.13 because the
    # block_embeddings registry template references blocks(id), so a
    # fingerprint registration fails while the table is absent — the same
    # lands-here/labelled-there split the four templates already take
    # (T0.12c lands, T0.13 labels). T0.13 keeps repo_ids[], the inert
    # labelling, and the no-writer assertion.
    #
    # `content` is the verbatim source of record (2026-08-31 spec §5, the
    # round-trip column); `content_hash` is its change gate and
    # `blocks.char_span` indexes into it. NULLable on purpose: a source filed
    # as bytes has no text form to store, and TEXT NULL is the honest shape
    # for that rather than a lossy decode. No index -- nothing queries by
    # content, and it must never enter the list or resolve statements, which
    # is the read-amplification reason §5.1 gave for rejecting a jsonb bridge
    # on this table.
    op.execute(
        """
        CREATE TABLE documents (
            id           UUID NOT NULL,
            project      TEXT NOT NULL,
            title        TEXT,
            source_type  TEXT,
            uri          TEXT,
            content_hash TEXT,
            content      TEXT,
            properties   JSONB,
            pinned_at    TIMESTAMPTZ,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT documents_pkey PRIMARY KEY (id)
        )
        """
    )
    # Identity key: re-filing the same source finds and re-ingests the
    # existing row (content_hash gates the actual work) instead of minting a
    # duplicate. uri-less sources (ad-hoc notes) are identified by id.
    op.execute(
        "CREATE UNIQUE INDEX ux_documents_project_uri ON documents (project, uri) "
        "WHERE uri IS NOT NULL"
    )
    # The notes sidebar reads recents as (project, updated_at DESC); without
    # this it is a seq scan over the whole corpus.
    op.execute(
        "CREATE INDEX ix_documents_project_updated "
        "ON documents (project, updated_at DESC)"
    )
    op.execute(
        "CREATE TRIGGER documents_touch_updated_at BEFORE UPDATE "
        "ON documents FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    # A page is the human-authored note tree, beside `documents` rather than
    # inside it. A document is addressed by its `uri` path and files at any
    # depth unconditionally; a page is addressed by `parent_id` and refuses a
    # child whose parent row does not exist. One model serving both would have
    # to mint ancestor rows nobody authored.
    op.execute(
        """
        CREATE TABLE pages (
            id           UUID NOT NULL,
            project      TEXT NOT NULL,
            parent_id    UUID,
            order_index  INTEGER NOT NULL,
            title        TEXT,
            content      TEXT NOT NULL DEFAULT '',
            content_hash TEXT NOT NULL,
            properties   JSONB,
            deleted_at   TIMESTAMPTZ,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pages_pkey PRIMARY KEY (id),
            -- Composite rather than a plain self-FK, so a cross-project
            -- reparent is impossible in the schema and not merely refused at
            -- the door. MATCH SIMPLE skips the check when parent_id is NULL,
            -- which is what makes a root page legal. The CASCADE is the purge
            -- path only -- an ordinary delete stamps `deleted_at`.
            CONSTRAINT ux_pages_id_project UNIQUE (id, project),
            CONSTRAINT fk_pages_parent FOREIGN KEY (parent_id, project)
                REFERENCES pages (id, project) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_pages_project_parent_order "
        "ON pages (project, parent_id, order_index)"
    )
    op.execute(
        "CREATE TRIGGER pages_touch_updated_at BEFORE UPDATE "
        "ON pages FOR EACH ROW EXECUTE FUNCTION touch_updated_at()"
    )

    # Attachment metadata; the bytes live on disk, named by `id` alone. The
    # project owns an attachment, not a page: a block copied to another page
    # keeps its image, so the page link is provenance and SET NULL on purge.
    # No FK on `project`, like every scoped table (projects register lazily).
    op.execute(
        """
        CREATE TABLE page_attachments (
            id                   UUID NOT NULL,
            project              TEXT NOT NULL,
            uploaded_for_page_id UUID REFERENCES pages(id) ON DELETE SET NULL,
            filename             TEXT NOT NULL,
            content_type         TEXT NOT NULL,
            size_bytes           BIGINT NOT NULL,
            sha256               TEXT NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT page_attachments_pkey PRIMARY KEY (id),
            CONSTRAINT chk_page_attachments_filename
                CHECK (char_length(filename) BETWEEN 1 AND 255),
            CONSTRAINT chk_page_attachments_size CHECK (size_bytes >= 0)
        )
        """
    )
    op.execute("CREATE INDEX ix_page_attachments_project ON page_attachments (project)")
    op.execute("CREATE INDEX ix_page_attachments_created ON page_attachments (created_at)")

    # A block is simultaneously the chunk unit, the citation anchor, the link
    # endpoint and the transclusion target. parent_id CASCADE makes the tree
    # delete take its subtree; re-ingest strips blocks by document_id before
    # re-chunking (strip-before-rewrite generalised).
    op.execute(
        """
        CREATE TABLE blocks (
            id          UUID NOT NULL,
            document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
            page_id     UUID REFERENCES pages(id) ON DELETE CASCADE,
            parent_id   UUID REFERENCES blocks(id) ON DELETE CASCADE,
            order_index INTEGER,
            type        TEXT,
            text        TEXT,
            properties  JSONB,
            char_span   INT4RANGE,
            search_vector TSVECTOR GENERATED ALWAYS AS (
                to_tsvector(
                    'english',
                    CASE WHEN type IN ('code', 'html') THEN '' ELSE coalesce(text, '') END
                )
            ) STORED,
            CONSTRAINT blocks_pkey PRIMARY KEY (id),
            -- Dropping NOT NULL from document_id does not weaken documents:
            -- a block with no owner at all is still refused, just by this
            -- rather than by the column. The only new permitted state is a
            -- block owned by a page.
            CONSTRAINT blocks_exactly_one_owner
                CHECK (num_nonnulls(document_id, page_id) = 1)
        )
        """
    )
    # Partial rather than plain: the page half of the table will be denser and
    # more update-heavy than the document half, and each index stays out of
    # the other owner's pages entirely.
    op.execute(
        "CREATE INDEX ix_blocks_document_order ON blocks (document_id, order_index) "
        "WHERE document_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_blocks_page_order ON blocks (page_id, order_index) "
        "WHERE page_id IS NOT NULL"
    )
    op.execute("CREATE INDEX ix_blocks_parent ON blocks (parent_id)")
    op.execute("CREATE INDEX ix_blocks_search_vector ON blocks USING GIN (search_vector)")

    # Wiki-links. `target_document_id` is nullable on purpose: `[[a-page]]`
    # pointing at a note that does not exist yet is a first-class stub, and
    # ON DELETE SET NULL turns a deleted target back into one rather than
    # erasing the backlink.
    op.execute(
        """
        CREATE TABLE document_links (
            id                 UUID NOT NULL,
            source_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            source_block_id    UUID REFERENCES blocks(id) ON DELETE CASCADE,
            target_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
            target_uri         TEXT NOT NULL,
            link_text          TEXT,
            CONSTRAINT document_links_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_links_target ON document_links (target_document_id)"
    )
    op.execute(
        "CREATE INDEX ix_document_links_target_uri ON document_links (target_uri)"
    )
    op.execute(
        "CREATE INDEX ix_document_links_source ON document_links (source_document_id)"
    )

    # Documents reuse the generic `tags` registry rather than minting a second
    # vocabulary, exactly as `memory_tags` does.
    op.execute(
        """
        CREATE TABLE document_tags (
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            CONSTRAINT document_tags_pkey PRIMARY KEY (document_id, tag_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_document_tags_tag ON document_tags (tag_id)")

    # Version history: a full post-image snapshot per commit, not a delta --
    # the serialiser already produces exactly this string on every mutation,
    # and a delta format would be a second representation to keep faithful.
    # `api_key_id` carries no foreign key for the reason `events.api_key_id`
    # carries none: keys are revoked, never deleted.
    op.execute(
        """
        CREATE TABLE document_revisions (
            id           UUID NOT NULL,
            document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content      TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            actor        TEXT,
            api_key_id   UUID,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT document_revisions_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_revisions_document "
        "ON document_revisions (document_id, created_at DESC, id DESC)"
    )

    # ------------------------------------------------------------------
    # events — the durable, append-only operation stream (doc 04 §8.1)
    # ------------------------------------------------------------------
    # The ONE declaratively partitioned table in the schema. memories is
    # deliberately not partitioned (a range key would have to enter every
    # unique/PK constraint, breaking its superseded_by self-FK, memory_tags,
    # memory_crossrefs, the embedding-child FKs and the composite (id, project)
    # FK), and the per-fingerprint embedding children already ARE the embedding
    # partitioning.
    #
    # bigint key: append-heavy and never referenced by a uuid FK. The partition
    # key must sit in the PK, and nothing joins events by id, so folding
    # created_at into the composite PK costs nothing.
    #
    op.execute(
        """
        CREATE TABLE events (
            id         BIGINT GENERATED ALWAYS AS IDENTITY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            event_type TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id  UUID,
            project    TEXT,
            actor      TEXT,
            api_key_id UUID,
            source     TEXT,
            payload    JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT events_pkey PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )

    # Append-only is enforced structurally, not by convention (doc 04 §8.1).
    # Role-agnostic on purpose: a REVOKE-based owner/app split would not survive
    # dump/restore and would complicate the one-image surface.
    op.execute(
        """
        CREATE FUNCTION events_forbid_write() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'events is append-only: % is forbidden (doc 04 8.1)', TG_OP
                USING ERRCODE = 'restrict_violation';
        END $$ LANGUAGE plpgsql
        """
    )

    # Two triggers, because one cannot cover all three verbs: TRUNCATE fires
    # only statement-level, UPDATE/DELETE are guarded per row.
    op.execute(
        "CREATE TRIGGER events_forbid_row BEFORE UPDATE OR DELETE ON events "
        "FOR EACH ROW EXECUTE FUNCTION events_forbid_write()"
    )
    op.execute(
        "CREATE TRIGGER events_forbid_truncate BEFORE TRUNCATE ON events "
        "FOR EACH STATEMENT EXECUTE FUNCTION events_forbid_write()"
    )

    # Every path that creates a monthly child goes through this function, so the
    # per-child TRUNCATE guard can never be forgotten by one of them. Measured on
    # PostgreSQL 17: a row-level trigger on a partitioned parent DOES cascade to
    # children (present and future), but a statement-level BEFORE TRUNCATE
    # trigger does NOT — `TRUNCATE events_202607` on a child bypasses the
    # parent's trigger entirely and silently erases that month of the audit
    # trail. Hence a truncate trigger on the parent AND on every child.
    #
    # Concurrency: two callers can reach a fresh month at once (boot racing the
    # cleanup arm), and `CREATE TABLE IF NOT EXISTS ... PARTITION OF` is NOT
    # atomic against that — the loser raises duplicate_table. Caught and treated
    # as success, because the winner produced exactly the row this call wanted.
    op.execute(
        """
        CREATE FUNCTION events_ensure_partition(month_start date)
        RETURNS text AS $$
        DECLARE
            -- Normalise first: a mid-month argument would otherwise create a
            -- child named for the month but bounded [the 15th, the 15th), which
            -- then blocks the correctly-aligned partition forever.
            m0         date := date_trunc('month', month_start)::date;
            m1         date := (date_trunc('month', month_start) + interval '1 month')::date;
            child      text := 'events_' || to_char(m0, 'YYYYMM');
            guard      text := 'events_' || to_char(m0, 'YYYYMM') || '_forbid_truncate';
            -- Pinned to UTC midnight by construction. Rendering these back out
            -- with %L always carries an offset, so the literal denotes the same
            -- instant whatever the session TimeZone happens to be.
            lo         timestamptz := (m0::text || ' 00:00:00+00')::timestamptz;
            hi         timestamptz := (m1::text || ' 00:00:00+00')::timestamptz;
        BEGIN
            -- The bounds MUST carry an explicit UTC offset. `events.created_at`
            -- is timestamptz, so a bare date literal is resolved against the
            -- session TimeZone at DDL time: create one month under UTC and the
            -- next under a +07 session and the pair silently leaves a 7-hour
            -- hole, after which an insert in the gap raises "no partition of
            -- relation events found for row" — which propagates out through
            -- record_event and fails the request being journaled. pg_dump emits
            -- partition bounds the same way, for the same reason.
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF events '
                'FOR VALUES FROM (%L) TO (%L)', child, lo, hi);
            -- Match the trigger on the child's OID, not on a bare relname: a
            -- same-named table in any other schema would otherwise satisfy this
            -- check and the real child would silently ship unguarded.
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger t
                WHERE t.tgrelid = to_regclass(child)
                  AND t.tgname = guard
                  AND NOT t.tgisinternal
            ) THEN
                EXECUTE format(
                    'CREATE TRIGGER %I BEFORE TRUNCATE ON %I '
                    'FOR EACH STATEMENT EXECUTE FUNCTION events_forbid_write()',
                    guard, child);
            END IF;
            RETURN child;
        EXCEPTION
            WHEN duplicate_table OR duplicate_object THEN
                RETURN child;
        END $$ LANGUAGE plpgsql
        """
    )

    # A RANGE-partitioned parent with no matching child REJECTS every insert,
    # and neither doc 04 §8.1 nor doc 19 §9 says whether the baseline lands
    # month-0 (inventory F-15). It must: the first events write happens as soon
    # as the journaling ships. Create the current and next month; the boot
    # reconciliation and the partition-maintenance arm on
    # pipeline_failure_cleanup keep it ahead of need from there.
    op.execute(
        """
        SELECT events_ensure_partition(
            date_trunc('month', now() AT TIME ZONE 'UTC')::date);
        """
    )
    op.execute(
        """
        SELECT events_ensure_partition(
            (date_trunc('month', now() AT TIME ZONE 'UTC')
             + interval '1 month')::date);
        """
    )

    # Reconstructs one object's timeline. Accepted limitation: bigint-keyed
    # code-graph objects carry their key in payload, so their timelines are
    # payload-queried and cannot use this index — a deliberate trade.
    op.execute(
        "CREATE INDEX ix_events_object ON events (object_type, object_id, created_at)"
    )
    # The calendar date bucket MUST use AT TIME ZONE 'UTC': a bare
    # created_at::date on a timestamptz is only STABLE (it reads the session
    # TimeZone GUC) so it cannot be indexed, and the UTC form also fixes what
    # "a day" means on the calendar.
    op.execute(
        "CREATE INDEX ix_events_day "
        "ON events (project, ((created_at AT TIME ZONE 'UTC')::date))"
    )


def downgrade() -> None:
    # Drop every per-fingerprint child table the registry created. The set is
    # not known at migration time, so walk pg_tables for all TEN parent
    # patterns — the four that exist today, the four target-new families
    # (inventory F-17: the pre-baseline sweep covered only four and would
    # strand the rest), the page family and the work-log family.
    op.execute(
        """
        DO $$
        DECLARE
            t record;
        BEGIN
            FOR t IN
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                  AND (tablename LIKE 'memory_embeddings\\_\\_%'
                       OR tablename LIKE 'entity_embeddings\\_\\_%'
                       OR tablename LIKE 'code_chunk_embeddings\\_\\_%'
                       OR tablename LIKE 'entity_embedding_cache\\_\\_%'
                       OR tablename LIKE 'block_embeddings\\_\\_%'
                       OR tablename LIKE 'page_embeddings\\_\\_%'
                       OR tablename LIKE 'relation_embeddings\\_\\_%'
                       OR tablename LIKE 'article_embeddings\\_\\_%'
                       OR tablename LIKE 'triple_embeddings\\_\\_%'
                       OR tablename LIKE 'worklog_embeddings\\_\\_%')
            LOOP
                EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', t.tablename);
            END LOOP;
        END $$;
        """
    )

    for table in (
        # pass two — dropped before the pass-one tables they reference
        "job_runs",
        "llm_usage",
        "events",
        "llm_purpose_configs",
        "messages",
        "conversations",
        "api_keys",
        "token_blocklist",
        "pipeline_failures",
        "project_repositories",
        "code_edges",
        "code_graph_nodes",
        "code_symbols",
        "code_files",
        "repositories",
        "git_accounts",
        "worklog_entries",
        "workstreams",
        "session_checkpoints",
        "article_citations",
        "knowledge_articles",
        "fact_access_stats",
        "fact_sources",
        "knowledge_triples",
        "document_revisions",
        "document_tags",
        "document_links",
        "blocks",
        "documents",
        "page_attachments",
        "pages",
        "memory_buffer",
        "memory_community_members",
        "memory_communities",
        "memory_relations",
        "memory_access_stats",
        "memory_crossrefs",
        "projects",
        # pass one
        "entity_relations",
        "entities",
        "memory_tags",
        "tags",
        "memories",
        "embedders",
        "config",
        "llm_providers",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    op.execute("DROP FUNCTION IF EXISTS touch_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS memories_fts_trigger()")
    op.execute("DROP TYPE IF EXISTS memory_status")
