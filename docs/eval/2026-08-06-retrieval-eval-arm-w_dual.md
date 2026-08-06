# Retrieval eval — arm ablation: `w_dual` — 2026-08-06

- run id: `a1b2b903-becc-4695-9ec1-dbdde2310421` (recorded 2026-08-06T06:18:48.368303+00:00)
- git sha: `e4768c8f39e01bc634cdb4f01d6c0a0725fa9222`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `dual` (flag `w_dual`), activation task `T2.50`
- weights: off=`0.0`, on=`0.3`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

> ## An earlier run today reported all-zeros. It was vacuous, and this is not.
>
> `relation_embeddings` is written by a Tier-C refresh job that never runs in a
> bench process, so the first `--arm w_dual` run — taken immediately after
> T2.94 removed the arm's blocked reason — ranked against an **empty
> partition**. The arm returned no candidates, both legs retrieved identically,
> and every slice reported exactly 0.0000. That reads like a measured "no win"
> and is nothing of the kind. **A ledger row from that run exists and should be
> disregarded**; the append-only ledger keeps it, so it is named here instead.
>
> The cause was a gap in the unblocking, not in the channel: `w_ppr` had been
> given a preparation step (build the snapshot) and `w_dual` had not. Both arms
> now declare `needs_artifact`, so preparation is part of resolving the arm
> rather than something a runner must remember, and a run that cannot build the
> artefact refuses instead of reporting a zero. This run embedded **62 relation
> vectors** before the legs, printed in its own output.
>
> Probe weight is `LIST_PROBE_WEIGHT` (0.3), the keyword side's own share —
> see the `w_ppr` report for why a list weight of 1.0 measures the probe rather
> than the arm.
>
> Warm cache; no live LLM calls attributed on either leg.

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.50`.

## Per-slice delta (off | on | delta)

slice                n   off.mrr   on.mrr     d.mrr    off.hit   on.hit     d.hit
exact               12    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
fact                18    1.0000   0.8889   -0.1111     1.0000   0.8889   -0.1111
knowledge-update    14    0.8095   0.5264   -0.2832     0.9286   0.8571   -0.0714
multi-hop           14    1.0000   0.8039   -0.1961     0.0000   0.0714    0.0714
paraphrase          18    0.5759   0.5481   -0.0278     0.9444   0.8889   -0.0556
temporal            12    0.6528   0.0833   -0.5694     1.0000   0.0833   -0.9167
typo                14    1.0000   0.7857   -0.2143     1.0000   0.7857   -0.2143
AGGREGATE          102    0.8582   0.6715   -0.1867     0.8431   0.6765   -0.1667

--- off leg (weight=0.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00013
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00253  p95=0.00360
keyword_search     live   n= 102  p50=0.00037  p95=0.00096
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00146  p95=0.00184
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=0.3): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00016
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00371  p95=0.00452
keyword_search     live   n= 102  p50=0.00039  p95=0.00050
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00144  p95=0.00185
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

