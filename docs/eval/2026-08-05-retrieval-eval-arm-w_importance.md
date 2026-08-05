# Retrieval eval — arm ablation: `w_importance` — 2026-08-05

- run id: `a7c01d25-4b55-4d0c-a76c-b165b720398a` (recorded 2026-08-05T05:29:50.655745+00:00)
- git sha: `aad5dbbfa7ff59ac6b169db92b7fd7475f0613e7`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `importance` (flag `w_importance`), activation task `T2.30`
- weights: off=`0.0`, on=`1.0`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.30`.

## Per-slice delta (off | on | delta)

slice                n   off.mrr   on.mrr     d.mrr    off.hit   on.hit     d.hit
exact               12    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
fact                18    1.0000   0.5372   -0.4628     1.0000   0.9444   -0.0556
knowledge-update    14    0.8095   0.6431   -0.1664     0.9286   0.8571   -0.0714
multi-hop           14    1.0000   0.2255   -0.7745     0.0000   0.1429    0.1429
paraphrase          18    0.5759   0.2223   -0.3536     0.9444   0.7222   -0.2222
temporal            12    0.6528   0.3684   -0.2844     1.0000   0.7500   -0.2500
typo                14    1.0000   0.3347   -0.6653     1.0000   0.9286   -0.0714
AGGREGATE          102    0.8582   0.4602   -0.3980     0.8431   0.7647   -0.0784

--- off leg (weight=0.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00017
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00258  p95=0.00373
keyword_search     live   n= 102  p50=0.00037  p95=0.00067
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00150  p95=0.00223
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=1.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00017
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00284  p95=0.00394
keyword_search     live   n= 102  p50=0.00034  p95=0.00047
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00136  p95=0.00198
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

