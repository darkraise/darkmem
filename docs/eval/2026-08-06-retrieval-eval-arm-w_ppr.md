# Retrieval eval — arm ablation: `w_ppr` — 2026-08-06

- run id: `500e272d-5a61-453d-9fd0-4b71d5ede0e0` (recorded 2026-08-06T05:55:47.708404+00:00)
- git sha: `0e669cddcacf1c1e685fe3f62919c44c50c19a4e`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `ppr` (flag `w_ppr`), activation task `T2.50`
- weights: off=`0.0`, on=`0.3`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

> ## Probe magnitude: 0.3, and the first run at 1.0 is the reason
>
> **A list weight is not a factor weight.** `arm_factor` composes as
> `1 + weight * (signal - baseline)`, so 1.0 there is a moderate swing around
> identity. An RRF *list* weight is the list's whole share of the fusion, and
> the two shipped lists already split 1.0 between them (`semantic_weight` 0.7
> / keyword 0.3). A third list probed at 1.0 therefore carries more voice than
> the entire existing fusion combined.
>
> That is not hypothetical. The first `--arm w_ppr` run, taken at the
> factor-arm default of 1.0, reported an aggregate MRR delta of **-0.4742** —
> which reads as "PPR is catastrophic" and actually says "a list weighted
> above everything else dominates the order". `LIST_PROBE_WEIGHT = 0.3` (the
> keyword side's own share) is now the default for list arms, so the probe is
> one more voice of comparable size. This report is the 0.3 run.
>
> **This is the harness's first genuinely non-vacuous list-arm measurement.**
> Before T2.32's extension, `--arm w_ppr` was rejected outright; a naive
> extension would have measured an exact zero, because the bench process runs
> no snapshot job and `run_retrieval` queries project-wide while the snapshot
> is project-scoped. Both are now handled, and a run that cannot satisfy
> either refuses instead of reporting a zero.
>
> Warm cache; no live LLM calls attributed on either leg.

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.50`.

## Per-slice delta (off | on | delta)

slice                n   off.mrr   on.mrr     d.mrr    off.hit   on.hit     d.hit
exact               12    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
fact                18    1.0000   0.6190   -0.3810     1.0000   1.0000    0.0000
knowledge-update    14    0.8095   0.6395   -0.1701     0.9286   0.9286    0.0000
multi-hop           14    1.0000   0.6571   -0.3429     0.0000   0.1429    0.1429
paraphrase          18    0.5759   0.4969   -0.0790     0.9444   1.0000    0.0556
temporal            12    0.6528   0.2619   -0.3909     1.0000   0.5000   -0.5000
typo                14    1.0000   0.5388   -0.4612     1.0000   1.0000    0.0000
AGGREGATE          102    0.8582   0.5973   -0.2609     0.8431   0.8137   -0.0294

--- off leg (weight=0.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00013
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00285  p95=0.00367
keyword_search     live   n= 102  p50=0.00063  p95=0.00095
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00151  p95=0.00214
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=0.3): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00017
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00303  p95=0.00377
keyword_search     live   n= 102  p50=0.00063  p95=0.00082
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00145  p95=0.00187
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

