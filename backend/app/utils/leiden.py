"""The one bounded, seeded Leiden call this repo makes.

Two clustering callers exist — the code graph (`CommunityDetector`, scoped by
`repo_id`) and the memory graph (topics, scoped by `project`). Everything above
this module differs between them: node identity, edge derivation, storage,
rewrite shape and label source. What is provably common is exactly this: the
import guard, the `igraph.Graph` build, and one bounded seeded partition.

It lives here rather than being written twice because `CLAUDE.md` already
records what happens otherwise — `code_query.py` declares its own `RRF_K = 60`
rather than using `rank_fusion.py`'s, "the two constants can drift and no task
owns closing that". Two independent `find_partition(..., seed=0, timeout=60)`
call sites are that defect in advance.

**The timeout bounds the await, not the work.** `asyncio.wait_for` around
`loop.run_in_executor` does not cancel the running thread: `leidenalg` keeps
burning CPU to completion after the await returns. The real bound on runaway
CPU is the caller's graph size. What the dedicated single-thread executor buys
is isolation — a leaked computation cannot starve the default executor asyncio
also uses for other blocking calls.

**`unavailable` and `timeout` are different outcomes and must stay
distinguishable.** A bare `None` cannot tell them apart, and their callers do
opposite things: a timeout means the graph was real but the clustering did not
finish, so a single community over it is a degraded answer; a missing library
means *nothing was computed*, so writing one would fabricate a result.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_SEED = 0


@dataclass(frozen=True)
class PartitionResult:
    membership: list[int] | None
    outcome: Literal["ok", "timeout", "unavailable"]


def _make_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix="leiden")


async def partition_graph(
    n_nodes: int,
    edges: Sequence[tuple[int, int]],
    *,
    weights: Sequence[float] | None = None,
    resolution: float = 1.0,
    n_iterations: int = -1,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    seed: int = DEFAULT_SEED,
) -> PartitionResult:
    try:
        import igraph
        import leidenalg
    except ImportError:
        logger.warning(
            "igraph or leidenalg is not installed; clustering is unavailable"
        )
        return PartitionResult(None, "unavailable")

    graph = igraph.Graph(n=n_nodes, edges=list(edges), directed=False)
    kwargs: dict = {
        "resolution_parameter": resolution,
        "n_iterations": n_iterations,
        "seed": seed,
    }
    if weights is not None:
        kwargs["weights"] = list(weights)

    executor = _make_executor()
    try:
        loop = asyncio.get_running_loop()
        partition = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                lambda: leidenalg.find_partition(
                    graph, leidenalg.RBConfigurationVertexPartition, **kwargs
                ),
            ),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "Leiden exceeded %.1fs on a %d-node graph", timeout_seconds, n_nodes
        )
        return PartitionResult(None, "timeout")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return PartitionResult(list(partition.membership), "ok")
