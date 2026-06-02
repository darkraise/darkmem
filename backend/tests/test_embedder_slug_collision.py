"""register must refuse a fingerprint whose partition slug collides with an
already-registered, different fingerprint.

_partition_slug folds every non-alphanumeric run to '_', so distinct models
differing only by a separator (m-a|512 vs m.a|512) map to the same child table
with the same dims. Both would write incompatible vectors into one vector(N)
column, corrupting every cosine result. Until a hash-qualified slug + migration
lands, fail loud at registration instead of silently sharing the column.
"""
from __future__ import annotations

import pytest

from app.services.embedder_registry import EmbedderInfo, EmbedderRegistry, _partition_slug


def test_slug_folding_makes_these_two_collide():
    assert _partition_slug("m-a|512") == _partition_slug("m.a|512")


@pytest.mark.asyncio
async def test_register_rejects_slug_collision(session):
    reg = EmbedderRegistry()  # fresh instance; don't touch the global cache
    await reg.register(
        session, EmbedderInfo(fingerprint="m-a|512", model_id="m-a", dims=512, source="llm"),
    )
    with pytest.raises(RuntimeError, match="collision"):
        await reg.register(
            session, EmbedderInfo(fingerprint="m.a|512", model_id="m.a", dims=512, source="llm"),
        )
