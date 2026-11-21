"""KnowledgeTriple ORM model: matches the real table, never drifts silently.

Step 1 of T2.01 deleted a KnowledgeTriple model that described a schema the
database no longer had. The reflection test below compares the model against
the live reflected table (not a hardcoded list) so that drift recurring would
fail loudly instead of silently, the way it did before.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect

from app.models.graph import KnowledgeTriple

# Kept in the table with no reader or writer, and deliberately unmapped: a
# released model that maps a column is a reader, so a drop has to wait until
# a build without the mapping has shipped.
UNMAPPED_COLUMNS = {"stated_expiry"}


async def test_model_columns_match_reflected_table(session):
    connection = await session.connection()
    reflected = await connection.run_sync(
        lambda sync_conn: inspect(sync_conn).get_columns("knowledge_triples")
    )
    reflected_by_name = {col["name"]: col for col in reflected}

    model_columns = {col.name: col for col in KnowledgeTriple.__table__.columns}

    assert set(reflected_by_name) - UNMAPPED_COLUMNS == set(model_columns)
    assert UNMAPPED_COLUMNS <= set(reflected_by_name)

    for name, model_col in model_columns.items():
        reflected_col = reflected_by_name[name]
        assert reflected_col["nullable"] == model_col.nullable, (
            f"nullability mismatch on {name}: "
            f"db={reflected_col['nullable']} model={model_col.nullable}"
        )


async def test_new_instance_gets_uuidv7_id(session):
    triple = KnowledgeTriple(
        subject_name="darkmem",
        object_name="postgres",
        rel_type="USES",
        reference_time=datetime.now(timezone.utc),
        fact="darkmem uses postgres",
        triple_key="deadbeef",
    )
    session.add(triple)
    await session.flush()

    assert triple.id is not None
    assert triple.id.version == 7


async def test_subject_and_object_id_have_no_foreign_keys():
    subject_col = KnowledgeTriple.__table__.c.subject_id
    object_col = KnowledgeTriple.__table__.c.object_id

    assert len(subject_col.foreign_keys) == 0
    assert len(object_col.foreign_keys) == 0
