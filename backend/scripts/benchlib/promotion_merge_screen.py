"""T2.131 — the entity-merge screen over the promotion corpus's entity names.

The diversity arm buys one corroboration per (repo, dependency) claim, and it
buys it only while the memory's entity and the deriver's entity stay two
distinct rows for two distinct dependencies. Phase 4 dedups on an ANN probe at
cosine **0.85** under the ``names_distinct`` gate, so two dependency names that
sit above that threshold with no discriminating token between them collapse to
one entity — and the claim that named the losing one silently holds at a single
origin. That is the same silent-shrink class ``validate_diversity_group_against_fixture``
refuses one file down, except the mechanism is the embedder rather than the
authoring, so no offline predicate over the corpus can see it.

This screen is the instrument that saw it. It embeds every distinct entity name
the fleet mints through the **same embedder the corpus prep uses** and reports
every pair at or above 0.85 that ``names_distinct`` would let merge.

It is a screen, not a gate: a pair listed here is a *candidate* collapse, not a
demonstrated one. The committed calibration says why — ``bcrypt``/``cryptography``
sit at 0.8618 and both converged in the measured census, so the screen
over-predicts near its own threshold and its output is read as a shortlist to
adjudicate, never as a count of lost claims.

**What it does not see, stated rather than left to be discovered.** The screened
population is the two name sets the corpus carries *structurally* — the fleet's
dependency names and its repository names. A claim's **subject** is not in that
set: it is whatever noun phrase the extractor promotes out of the capture's
prose, so reproducing it here would mean committing a parse and screening the
parse instead of the corpus. The known consequence is that the recorded latent
hazard ``atlas-ingest``/``atlas-query`` (0.8582, harmless only because no two
atlas claims share an object name) is a subject-name pair and this screen cannot
return it. A subject-side screen is a different instrument and is not this one
wearing a wider scope.

Run from ``backend/`` (needs the LAN Ollama the bench embedder is seeded to):

    python scripts/benchlib/promotion_merge_screen.py > scripts/benchlib/promotion/merge_screen.txt

Committed output: ``scripts/benchlib/promotion/merge_screen.txt``. T2.131's owed
review (finding M1, 2026-08-16) found the screen's figures resting on an
uncommitted offline pass — its effects were verifiable in the data, its method
was not re-runnable — and this file is that finding's close.
"""
from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import httpx  # noqa: E402

from app.services.code_deriver import dependency_name  # noqa: E402
from app.services.relations import names_distinct  # noqa: E402
from app.services import llm_seed  # noqa: E402
from benchlib import promotion_corpus as pc  # noqa: E402

#: Phase 4's ANN dedup threshold. Not a knob of this screen — the screen is
#: only meaningful while it reads the same number ``find_similar_entity`` does.
MERGE_THRESHOLD = 0.85

#: The bench embedder, as ``llm_seed`` seeds the ``embedding`` purpose. A screen
#: run against a different embedder measures a different fingerprint's geometry
#: and says nothing about what the corpus prep will do.
EMBED_MODEL = "qwen3-embedding:0.6b"

#: ``llm_seed`` states the base URL in its OpenAI-compat spelling because that
#: is the wire the orchestrator uses; the embeddings call below is Ollama's
#: native one, so the ``/v1`` suffix comes off. Taking the host from the same
#: place the seed does is what keeps a screen run and a corpus prep pointed at
#: one embedder.
OLLAMA_HOST = llm_seed.OLLAMA_BASE_URL.rstrip("/").removesuffix("/v1")


def fleet_names() -> list[str]:
    """Every entity name the fleet mints structurally: dependencies and repos."""
    names: set[str] = set()
    for fixture in pc.load_repo_fixtures():
        names.add(fixture["repo"]["name"].strip().lower())
        for edge in fixture.get("imports", ()):
            name = dependency_name(edge["target_key"])
            if name is not None:
                names.add(name.lower())
    return sorted(names)


async def embed(names: list[str]) -> dict[str, list[float]]:
    vectors: dict[str, list[float]] = {}
    async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=60.0) as client:
        for name in names:
            response = await client.post(
                "/api/embeddings", json={"model": EMBED_MODEL, "prompt": name}
            )
            response.raise_for_status()
            vectors[name] = response.json()["embedding"]
    return vectors


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


async def main() -> int:
    names = fleet_names()
    vectors = await embed(names)

    hits = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if names_distinct(a, b):
                continue
            score = cosine(vectors[a], vectors[b])
            if score >= MERGE_THRESHOLD:
                hits.append((score, a, b))
    hits.sort(reverse=True)

    print(f"embedder: {EMBED_MODEL} @ {OLLAMA_HOST}")
    print(f"threshold: {MERGE_THRESHOLD} (Phase 4's find_similar_entity)")
    print(f"names screened: {len(names)}  pairs compared: {len(names) * (len(names) - 1) // 2}")
    print(f"mergeable pairs at or above threshold: {len(hits)}")
    print()
    for score, a, b in hits:
        print(f"{score:.4f}  {a} <-> {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
