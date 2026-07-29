# Retrieval eval — arm ablation: `w_importance` — 2026-07-29

- run id: `86eae7d9-9153-4fc9-b380-6be5505b0f00` (recorded 2026-07-29T07:14:28.579402+00:00)
- git sha: `549c1d09b356384373ed4c366462bf08dcef1f4a`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `importance` (flag `w_importance`), activation task `T2.30`
- weights: off=`0.0`, on=`1.0`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.30`.

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
embed_query        cache  n= 102  p50=0.00011  p95=0.00016
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00187  p95=0.00344
keyword_search     live   n= 102  p50=0.00025  p95=0.00095
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00132  p95=0.00216
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=1.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00012
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00224  p95=0.00289
keyword_search     live   n= 102  p50=0.00027  p95=0.00032
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00126  p95=0.00155
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

