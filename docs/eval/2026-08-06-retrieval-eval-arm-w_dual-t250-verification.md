# Retrieval eval — arm ablation: `w_dual` — 2026-08-06
> **T2.50 judge verification run** — independent re-run of the recorded `a1b2b903`
> ablation (same protocol, probe 0.3), on the clean committed sha below, from an
> isolated lane worktree and lane database `darkmem_bench_t250`; 62 relation
> vectors embedded before the legs, as in the recorded run. Written under a
> distinct filename because the harness overwrites same-date/same-arm reports.
>
> **Byte-identical per-slice deltas to the recorded run**, now attributed to a
> clean committed sha — this repairs the recorded row's dirty-tree caveat (its
> `e4768c8f` predates the preparation commit `3f67152a` whose code it executed).

- run id: `cfcd0a50-6669-4383-851b-285e449b42a6` (recorded 2026-08-06T07:36:00.599099+00:00)
- git sha: `594db59e3bb94a11083b0f1dfbfd51ca48bd96ce`
- embedder fingerprint: `qwen3-embedding:0.6b|1024` (pinned across both legs)
- arm: `dual` (flag `w_dual`), activation task `T2.50`
- weights: off=`0.0`, on=`0.3`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval_limit=94

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
embed_query        cache  n= 102  p50=0.00012  p95=0.00016
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00313  p95=0.00537
keyword_search     live   n= 102  p50=0.00046  p95=0.00122
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00175  p95=0.00305
semantic_search    cache  no samples
--- off leg: token cost by purpose ---
  (no LLM calls attributed)

--- on leg (weight=0.3): latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00014  p95=0.00017
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00462  p95=0.00751
keyword_search     live   n= 102  p50=0.00049  p95=0.00067
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00179  p95=0.00323
semantic_search    cache  no samples
--- on leg: token cost by purpose ---
  (no LLM calls attributed)

