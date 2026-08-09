# Retrieval eval — arm ablation: `w_dual` — 2026-08-06
> **T2.50 diagnostic leg, pre-registered** (`docs/planning/analyses/`
> `2026-08-06-t2.50-preregistration.md`, M4) — `w_dual` at weight 0.1, run to
> separate the temporal collapse's structure from its magnitude, **not** to search
> for a passing weight; no magnitude scan can activate an arm under the
> pre-registered anti-bar-shopping rule. Outcome matched the pre-stated
> prediction: temporal dMRR still -0.3470 at a third of the probe voice (11 of 12
> pairs demoted), aggregate dMRR still negative (-0.1285). The multi-hop flip
> moved to a different pair than at 0.3 (rg-0104, vs rg-0108 there) — the
> instability the activation-log entry reads as perturbation, not reach.

- run id: `7310cdb0-ae48-42ff-b4bf-05543d701385` (recorded 2026-08-06T07:37:32.492105+00:00)
- git sha: `594db59e3bb94a11083b0f1dfbfd51ca48bd96ce`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `dual` (flag `w_dual`), activation task `T2.50`
- weights: off=`0.0`, on=`0.1`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

This report states the measured delta only. Whether it clears any bar, and whether the arm ships at a nonzero weight, is out of scope here (runbook §2) -- that judgment belongs to `T2.50`.

## Per-slice delta (off | on | delta)

slice                n   off.mrr   on.mrr     d.mrr    off.hit   on.hit     d.hit
exact               12    1.0000   1.0000    0.0000     1.0000   1.0000    0.0000
fact                18    1.0000   0.9061   -0.0939     1.0000   1.0000    0.0000
knowledge-update    14    0.8095   0.7071   -0.1024     0.9286   0.9286    0.0000
multi-hop           14    1.0000   0.8168   -0.1832     0.0000   0.0714    0.0714
paraphrase          18    0.5759   0.5306   -0.0453     0.9444   0.9444    0.0000
temporal            12    0.6528   0.3058   -0.3470     1.0000   1.0000    0.0000
typo                14    1.0000   0.8262   -0.1738     1.0000   1.0000    0.0000
AGGREGATE          102    0.8582   0.7297   -0.1285     0.8431   0.8529    0.0098

--- off leg (weight=0.0): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00013  p95=0.00017
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00332  p95=0.00625
keyword_search     live   n= 102  p50=0.00049  p95=0.00139
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00184  p95=0.00364
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=0.1): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00013  p95=0.00018
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00459  p95=0.00762
keyword_search     live   n= 102  p50=0.00049  p95=0.00074
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00179  p95=0.00316
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

