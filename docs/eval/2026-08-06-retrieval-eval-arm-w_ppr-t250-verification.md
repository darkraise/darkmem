# Retrieval eval — arm ablation: `w_ppr` — 2026-08-06
> **T2.50 judge verification run** — independent re-run of the recorded `500e272d`
> ablation (same protocol, probe 0.3), on the clean committed sha below, from an
> isolated lane worktree and lane database `darkmem_bench_t250`. Written under a
> distinct filename because the harness overwrites same-date/same-arm reports and
> the canonical `2026-08-06-retrieval-eval-arm-w_ppr.md` carries curated banners.
>
> **Reproduces the recorded run in sign and size, not byte-for-byte**: aggregate
> dMRR -0.2608 vs recorded -0.2609; per-slice MRR wobbles up to ~0.04 (e.g. typo
> -0.4982 vs -0.4612) while every sign and both hit@10 flips (multi-hop +0.1429,
> temporal -0.5000) match exactly. The off legs are identical, so the wobble is in
> the arm itself: the snapshot's synonymy KNN (`LIMIT :top_k` with no deterministic
> tie-break) and reseeded ingest order can differ across builds. A caveat for any
> future exact-parity claim on this arm, recorded in the activation-log entry.

- run id: `fc32a172-07b7-4993-b581-80eb8f83b9d1` (recorded 2026-08-06T07:35:33.208566+00:00)
- git sha: `594db59e3bb94a11083b0f1dfbfd51ca48bd96ce`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `ppr` (flag `w_ppr`), activation task `T2.50`
- weights: off=`0.0`, on=`0.3`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.50`.

## Per-slice delta (off | on | delta)

slice                n   off.mrr   on.mrr     d.mrr    off.hit   on.hit     d.hit
exact               12    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
fact                18    1.0000   0.6163   -0.3837     1.0000   1.0000    0.0000
knowledge-update    14    0.8095   0.6752   -0.1344     0.9286   0.9286    0.0000
multi-hop           14    1.0000   0.6476   -0.3524     0.0000   0.1429    0.1429
paraphrase          18    0.5759   0.5069   -0.0690     0.9444   1.0000    0.0556
temporal            12    0.6528   0.2639   -0.3889     1.0000   0.5000   -0.5000
typo                14    1.0000   0.5018   -0.4982     1.0000   1.0000    0.0000
AGGREGATE          102    0.8582   0.5973   -0.2608     0.8431   0.8137   -0.0294

--- off leg (weight=0.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00012  p95=0.00019
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00315  p95=0.00578
keyword_search     live   n= 102  p50=0.00067  p95=0.00136
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00174  p95=0.00287
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=0.3): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00012  p95=0.00017
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00330  p95=0.00563
keyword_search     live   n= 102  p50=0.00067  p95=0.00108
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00156  p95=0.00277
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

