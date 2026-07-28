"""The belief axis of a Layer-2 fact.

A fact runs on two orthogonal axes (doc 08 §3): the **belief** axis
(``valid_at`` / ``invalid_at`` / ``expired_at``) and the **verification** axis
(``verification_status``). They are independent — a fact can be expired yet
confirmed — so no method in this module writes ``verification_status``, and the
verification writer never touches the three timestamps. Conflating them is the
modelling error the fact-layer rebuild exists to fix.

Invalidation is a re-save on the retained row, never a delete: the retained
rows are the only thing that can answer "what did we believe as of date X".

These are primitives, not decisions. The two deterministic fact-write temporal
passes — stale-on-arrival and disjoint-window — belong to ``fact_lift``
(doc 08 §3.2), which chooses between them. The ordering contract this module
guarantees is that ``close_window()`` on the older row followed by
``insert_open()`` for the newer one satisfies the partial-unique
``ux_knowledge_triples_open``: a window-closed row leaves that index's scope
while staying live.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# "Live" is exactly this, spelled once. A window-closed row (invalid_at set) is
# still live history; only belief withdrawal removes a row from the live set.
LIVE_PREDICATE = "expired_at IS NULL"

_COLUMNS = """
    id, subject_id, object_id, subject_name, object_name, rel_type,
    valid_at, invalid_at, expired_at, reference_time, fact, project,
    triple_key, verification_status, confidence, applies_when,
    learned_in, review_state, source_file, created_at
"""


def _row_to_dict(row: Any) -> dict:
    out = dict(row)
    for key in ("id", "subject_id", "object_id"):
        value = out.get(key)
        out[key] = str(value) if value is not None else None
    learned_in = out.get("learned_in")
    out["learned_in"] = list(learned_in) if learned_in is not None else None
    return out


class KnowledgeTripleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_open(
        self,
        *,
        triple_key: str,
        subject_name: str,
        object_name: str,
        rel_type: str,
        fact: str,
        reference_time: datetime,
        project: str = "default",
        valid_at: datetime | None = None,
        subject_id: UUID | str | None = None,
        object_id: UUID | str | None = None,
        confidence: float | None = None,
        applies_when: dict | None = None,
        learned_in: list[str] | None = None,
        review_state: str | None = None,
        source_file: str | None = None,
    ) -> dict:
        """Insert an open-ended belief: ``invalid_at`` and ``expired_at`` NULL.

        ``triple_key`` is supplied by the caller — the identity function is
        ``app.services.triple_key.compute_triple_key`` and its first producer
        is fact lifting, not this layer.

        This does not look for an existing open row on the same key and close
        it. The disjoint-window case is legitimate (two employment stints at
        one company are two believed facts, both live), so the choice between
        closing the older window and leaving both live is fact lifting's.
        """
        params = {
            "id": str(new_id()),
            "subject_id": str(subject_id) if subject_id is not None else None,
            "object_id": str(object_id) if object_id is not None else None,
            "subject_name": subject_name,
            "object_name": object_name,
            "rel_type": rel_type,
            "valid_at": valid_at,
            "reference_time": reference_time,
            "fact": fact,
            "project": project,
            "triple_key": triple_key,
            "confidence": confidence,
            "applies_when": json.dumps(applies_when) if applies_when is not None else None,
            "learned_in": learned_in,
            "review_state": review_state,
            "source_file": source_file,
        }
        # verification_status is absent from the column list on purpose: the
        # database default seeds it as 'candidate' and this module never writes
        # the verification axis.
        result = await self.session.execute(
            text(f"""
                INSERT INTO knowledge_triples (
                    id, subject_id, object_id, subject_name, object_name,
                    rel_type, valid_at, reference_time, fact, project,
                    triple_key, confidence, applies_when, learned_in,
                    review_state, source_file
                )
                VALUES (
                    CAST(:id AS uuid),
                    CAST(:subject_id AS uuid),
                    CAST(:object_id AS uuid),
                    CAST(:subject_name AS text),
                    CAST(:object_name AS text),
                    CAST(:rel_type AS text),
                    CAST(:valid_at AS timestamptz),
                    CAST(:reference_time AS timestamptz),
                    CAST(:fact AS text),
                    CAST(:project AS text),
                    CAST(:triple_key AS text),
                    CAST(:confidence AS real),
                    CAST(:applies_when AS jsonb),
                    CAST(:learned_in AS text[]),
                    CAST(:review_state AS text),
                    CAST(:source_file AS text)
                )
                RETURNING {_COLUMNS}
            """),
            params,
        )
        return _row_to_dict(result.mappings().one())

    async def close_window(self, triple_id: UUID | str, invalid_at: datetime) -> dict | None:
        """Close a belief's validity window. The row stays live.

        Writes ``invalid_at`` only — ``expired_at`` is untouched, so the row
        remains in the live set as retained history while leaving the scope of
        ``ux_knowledge_triples_open``.
        """
        result = await self.session.execute(
            text(f"""
                UPDATE knowledge_triples
                SET invalid_at = CAST(:invalid_at AS timestamptz)
                WHERE id = CAST(:id AS uuid)
                RETURNING {_COLUMNS}
            """),
            {"id": str(triple_id), "invalid_at": invalid_at},
        )
        row = result.mappings().first()
        if row is None:
            logger.debug("close_window: no knowledge_triples row for id %s", triple_id)
            return None
        return _row_to_dict(row)

    async def expire(self, triple_id: UUID | str) -> dict | None:
        """Withdraw belief. A re-save on the retained row, never a delete.

        COALESCE keeps the withdrawal time from drifting on a repeated call:
        a fact was disbelieved once, and a second expire must not rewrite when.
        """
        result = await self.session.execute(
            text(f"""
                UPDATE knowledge_triples
                SET expired_at = COALESCE(expired_at, now())
                WHERE id = CAST(:id AS uuid)
                RETURNING {_COLUMNS}
            """),
            {"id": str(triple_id)},
        )
        row = result.mappings().first()
        if row is None:
            logger.debug("expire: no knowledge_triples row for id %s", triple_id)
            return None
        return _row_to_dict(row)

    async def get_live(
        self,
        *,
        triple_key: str | None = None,
        project: str | None = None,
        subject_name: str | None = None,
        rel_type: str | None = None,
        object_name: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Rows belief has not been withdrawn from.

        Disjoint validity windows legitimately leave several live rows on one
        subject/predicate/object, so this may return more than one row per key.
        """
        conditions = [LIVE_PREDICATE]
        params: dict = {"limit": limit}
        for column, value in (
            ("triple_key", triple_key),
            ("project", project),
            ("subject_name", subject_name),
            ("rel_type", rel_type),
            ("object_name", object_name),
        ):
            if value is not None:
                conditions.append(f"{column} = CAST(:{column} AS text)")
                params[column] = value

        result = await self.session.execute(
            text(f"""
                SELECT {_COLUMNS}
                FROM knowledge_triples
                WHERE {" AND ".join(conditions)}
                ORDER BY created_at, id
                LIMIT CAST(:limit AS integer)
            """),
            params,
        )
        return [_row_to_dict(row) for row in result.mappings().all()]

    async def as_of(
        self,
        t: datetime,
        *,
        triple_key: str | None = None,
        project: str | None = None,
        subject_name: str | None = None,
        rel_type: str | None = None,
        object_name: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Rows believed at time ``t``.

        The window is half-open — ``valid_at <= t < invalid_at`` — so the
        adjacent windows the disjoint-window pass produces never both match a
        single instant. NULL ``valid_at`` reads as unbounded-past and NULL
        ``invalid_at`` as open-ended.

        ``expired_at`` is deliberately not a filter here: this is the historical
        question, and a fact whose belief has since been withdrawn was still
        believed at ``t``. Filtering it would collapse the retained history that
        makes the question answerable.
        """
        conditions = [
            "(valid_at IS NULL OR valid_at <= CAST(:t AS timestamptz))",
            "(invalid_at IS NULL OR invalid_at > CAST(:t AS timestamptz))",
        ]
        params: dict = {"t": t, "limit": limit}
        for column, value in (
            ("triple_key", triple_key),
            ("project", project),
            ("subject_name", subject_name),
            ("rel_type", rel_type),
            ("object_name", object_name),
        ):
            if value is not None:
                conditions.append(f"{column} = CAST(:{column} AS text)")
                params[column] = value

        result = await self.session.execute(
            text(f"""
                SELECT {_COLUMNS}
                FROM knowledge_triples
                WHERE {" AND ".join(conditions)}
                ORDER BY created_at, id
                LIMIT CAST(:limit AS integer)
            """),
            params,
        )
        return [_row_to_dict(row) for row in result.mappings().all()]
