"""Default ML profile seed.

Following the same pattern set by ``llm_seed.py`` (commit b09e461),
this module owns the default ML profiles instead of an Alembic
migration. The startup hook in ``app.main`` ensures the seed exists
the first time the backend starts against an empty ``ml_profiles``
table — fresh installs and existing installs both pick it up
without any manual migration step.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MLProfileSeed:
    name: str
    model_repo: str
    ttl_seconds: int  # 0 = never evict, >0 = evict after N idle seconds


DEFAULT_ML_PROFILES: list[MLProfileSeed] = [
    MLProfileSeed(
        name="default-classifier",
        model_repo="darkraise/darkmem-classifier-v1",
        ttl_seconds=0,
    ),
]
