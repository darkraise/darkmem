# Retrieval eval — arm ablation: `w_heat` — 2026-08-06

- run id: `813554e3-5148-4477-84e5-ed023ee95b8d` (recorded 2026-08-06T07:44:31.840493+00:00)
- git sha: `36fcf23653a03ff0e7449ade21dd28910a2ad0b7`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `heat` (flag `w_heat`), activation task `T2.31`
- weights: off=`0.0`, on=`1.0`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.31`.

## Per-slice delta (off | on | delta)

slice                n   off.mrr   on.mrr     d.mrr    off.hit   on.hit     d.hit
exact               12    1.0000   0.9583   -0.0417     1.0000   1.0000    0.0000
fact                18    1.0000   0.7024   -0.2976     1.0000   0.8333   -0.1667
knowledge-update    14    0.8095   0.5794   -0.2302     0.9286   0.7857   -0.1429
multi-hop           14    1.0000   0.4702   -0.5298     0.0000   0.2143    0.2143
paraphrase          18    0.5759   0.4185   -0.1574     0.9444   0.7778   -0.1667
temporal            12    0.6528   0.3299   -0.3229     1.0000   0.6667   -0.3333
typo                14    1.0000   0.4119   -0.5881     1.0000   0.7143   -0.2857
AGGREGATE          102    0.8582   0.5500   -0.3082     0.8431   0.7157   -0.1275

--- off leg (weight=0.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00014
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00259  p95=0.00358
keyword_search     live   n= 102  p50=0.00039  p95=0.00076
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00149  p95=0.00189
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=1.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00017
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00325  p95=0.00503
keyword_search     live   n= 102  p50=0.00036  p95=0.00056
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00138  p95=0.00205
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

