# Retrieval eval — arm ablation: `w_heat` — 2026-08-06

- run id: `83f4c11b-ddb3-44ad-99ed-f5b11c3a466b` (recorded 2026-08-06T05:09:01.779107+00:00)
- git sha: `2b2dd99e2e5b04bf60b7d7dbc9d5c31e89998879`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `heat` (flag `w_heat`), activation task `T2.31`
- weights: off=`0.0`, on=`1.0`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

> ## ⚠ NOT AN ACTIVATION MEASUREMENT — THE ARM HAS NO SIGNAL WIRED
>
> **Read the zero delta below as "the probe had nothing to move", not as "heat
> does not help".** `ProcessingPipeline._apply_rank_fusion_factor` feeds only
> `confidence` and `importance` into the signal dict; its own docstring records
> that "the heat/recency arms have no signal source wired yet (T2.31) and
> contribute exactly 1.0". So `arm_factor` returns 1.0 for every row at any
> weight, and both legs are the same ranking by construction — a zero delta on
> every slice is the arithmetic, not a finding about the signal.
>
> T2.29 landed the substrate (`memory_access_stats`, with `access_count` and
> `last_accessed`); nothing yet reads it at rank time. **T2.31 therefore has to
> wire the signal before it can measure it**, and this run is evidence of that
> gap rather than a number for the arm-activation log. Recording it as a
> measured "no win" would put exactly the kind of hollow number in the ledger
> that the ledger exists to keep out.
>
> Run cost nothing live: the cache was warm and no LLM calls were attributed.
>
> Logged 2026-08-06 while executing T2.32/T2.49; T2.31 remains `todo`.

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.31`.

## Per-slice delta (off | on | delta)

slice                n   off.mrr   on.mrr     d.mrr    off.hit   on.hit     d.hit
exact               12    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
fact                18    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
knowledge-update    14    0.8095   0.8095    0.0000     0.9286   0.9286    0.0000
multi-hop           14    1.0000   1.0000    0.0000     0.0000   0.0000    0.0000
paraphrase          18    0.5759   0.5759    0.0000     0.9444   0.9444    0.0000
temporal            12    0.6528   0.6528    0.0000     1.0000   1.0000    0.0000
typo                14    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
AGGREGATE          102    0.8582   0.8582    0.0000     0.8431   0.8431    0.0000

--- off leg (weight=0.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00025  p95=0.00262
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00280  p95=0.00586
keyword_search     live   n= 102  p50=0.00036  p95=0.00073
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00156  p95=0.00220
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=1.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00018
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00299  p95=0.00401
keyword_search     live   n= 102  p50=0.00038  p95=0.00051
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00143  p95=0.00206
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

