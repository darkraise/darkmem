# Retrieval eval — 2026-08-10

- run id: `bcc7276b-bf9d-44a4-9daf-0df5e07cf23e` (recorded 2026-08-10T12:21:03.270096+00:00)
- git sha: `948a1a2d6040d9eff91f7c2574f2fc80e0424650`
- embedder fingerprint: `qwen3-embedding:0.6b|1024`
- gate configuration: `classification_mode='simple', classifier_kind=None, relation_rescue=True`
- corpus: 94 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval retrieval_limit=94, full_context retrieval_limit=10
- live LLM calls this run: ingest=0, retrieval=0, full_context=0 (total=0)

- **multi-hop hit@10 = 0.0000 on the retrieval arm is the DESIGNED state (T0.06a), not a defect.** Every live multi-hop pair is built so its consequence memory ranks worse than k in the hybrid-only baseline -- this is the headroom a future graph-aware arm exists to close, not a bug for this runner to flag.
- **full context beats retrieval on pooled accuracy this run** (ΔMRR=+0.0487, Δhit@10=+0.0882, full-context minus retrieval) -- the honest measured result of the T0.09 comparator, stated plainly rather than buried or reframed as a cost-only win. See the cost caveats below for why the two arms' token costs are not directly subtractable.

## Comparison (human-readable)

Includes latency by channel for both arms -- see Reproducibility below for which parts of this section are expected to vary run to run and which are not.

```
=== TWO-ARM COMPARISON (k=10, min_pairs=10, n_pairs=102) ===
fetch depth: retrieval retrieval_limit=94, full_context retrieval_limit=10
context: 94/94 corpus entries in prompt, 12715 chars, policy=no-truncation
CAVEAT [latency-no-live-samples]: no arm measured live latency: every end_to_end sample in both arms was cache-served, so these p50/p95 figures describe a warm replay of a recorded run, not a system anybody runs.
CAVEAT [cost-kind-asymmetry]: the two arms' token blocks are different KINDS of quantity and must not be subtracted or ratioed: the full_context arm billed exactly one call per scored pair (102), so its token cost recurs in full on every run of the query set, while the retrieval arm's 94 call(s) are not per-pair -- they are one-time indexing work, paid once per corpus and amortised over every future query. The retrieval arm's own per-query cost is 102 query-embedding call(s), which carry no token accounting and appear in no token block here at all.

--- accuracy per slice (retrieval | full-context | delta) ---
slice                n    r.mrr   f.mrr    d.mrr     r.hit   f.hit    d.hit
exact               12   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
fact                18   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
knowledge-update    14   0.8095  0.8214   0.0119    0.9286  0.9286   0.0000
multi-hop           14   1.0000  1.0000   0.0000    0.0000  0.9286   0.9286
paraphrase          18   0.5759  0.9444   0.3685    0.9444  0.9444   0.0000
temporal            12   0.6528  0.5000  -0.1528    1.0000  0.6667  -0.3333
typo                14   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
AGGREGATE          102   0.8582  0.9069   0.0487    0.8431  0.9314   0.0882

--- retrieval: latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00011  p95=0.00014
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00238  p95=0.00310
keyword_search     live   n= 102  p50=0.00034  p95=0.00043
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00138  p95=0.00165
semantic_search    cache  no samples
--- retrieval: token cost by purpose ---
  extraction: {'live_calls': 0, 'live_prompt_tokens': 0, 'live_completion_tokens': 0, 'live_cached_prompt_tokens': 0, 'live_unknown_calls': 0, 'cache_known_calls': 94, 'cache_known_prompt_tokens': 927166, 'cache_known_completion_tokens': 11996, 'cache_known_cached_prompt_tokens': 926080, 'cache_unknown_calls': 0}

--- full_context: latency by channel (seconds, nearest-rank, min_samples=20) ---
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00007  p95=0.00008
full_context_call  live   no samples
full_context_call  cache  n= 102  p50=0.00007  p95=0.00008
--- full_context: token cost by purpose ---
  reasoning: {'live_calls': 0, 'live_prompt_tokens': 0, 'live_completion_tokens': 0, 'live_cached_prompt_tokens': 0, 'live_unknown_calls': 0, 'cache_known_calls': 102, 'cache_known_prompt_tokens': 472558, 'cache_known_completion_tokens': 3899, 'cache_known_cached_prompt_tokens': 452608, 'cache_unknown_calls': 0}

--- full-context id audit ---
  duplicate_rate: 0.0
  hallucinated_rate: 0.0
  ids_duplicate: 0
  ids_hallucinated: 0
  ids_kept: 137
  ids_malformed: 0
  ids_over_limit: 0
  ids_returned: 137
  kept_rate: 1.0
  malformed_rate: 0.0
  queries: 102
  responses_all_dropped: 0
  responses_empty: 5
  responses_truncated: 0
  responses_unparseable: 0
```

## Reproducibility

Two consecutive runs on an unchanged tree, against an unchanged warm LLM cache, must reproduce the JSON block below byte-for-byte: every accuracy figure (per slice and aggregate, both arms), every token-cost figure, the full-context id audit, the context description, and the set of caveat kinds. **Latency is excluded on purpose** (p50/p95 by channel, in the comparison above): it is a wall-clock measurement of a cache read or a live model round trip, and is expected to differ run to run even when nothing else does -- only its live-vs-cache population membership is a claim this report makes, never the exact figure.

```json
{
  "caveat_kinds": [
    "cost-kind-asymmetry",
    "latency-no-live-samples"
  ],
  "deltas": {
    "aggregate": {
      "hit_at_k": 0.08823529411764708,
      "mrr": 0.04869281045751639
    },
    "direction": "full_context minus retrieval",
    "slices": {
      "exact": {
        "hit_at_k": 0.0,
        "mrr": 0.0
      },
      "fact": {
        "hit_at_k": 0.0,
        "mrr": 0.0
      },
      "knowledge-update": {
        "hit_at_k": 0.0,
        "mrr": 0.011904761904761862
      },
      "multi-hop": {
        "hit_at_k": 0.9285714285714286,
        "mrr": 0.0
      },
      "paraphrase": {
        "hit_at_k": 0.0,
        "mrr": 0.36851851851851847
      },
      "temporal": {
        "hit_at_k": -0.33333333333333337,
        "mrr": -0.1527777777777778
      },
      "typo": {
        "hit_at_k": 0.0,
        "mrr": 0.0
      }
    }
  },
  "full_context_context": {
    "complete": true,
    "context_chars": 12715,
    "corpus_entries": 94,
    "dropped_entries": 0,
    "dropped_ids": [],
    "included_entries": 94,
    "policy": {
      "kind": "no-truncation",
      "max_prompt_chars": null,
      "on_overflow": "raise"
    }
  },
  "full_context_id_audit": {
    "duplicate_rate": 0.0,
    "hallucinated_rate": 0.0,
    "ids_duplicate": 0,
    "ids_hallucinated": 0,
    "ids_kept": 137,
    "ids_malformed": 0,
    "ids_over_limit": 0,
    "ids_returned": 137,
    "kept_rate": 1.0,
    "malformed_rate": 0.0,
    "queries": 102,
    "responses_all_dropped": 0,
    "responses_empty": 5,
    "responses_truncated": 0,
    "responses_unparseable": 0
  },
  "full_context_score": {
    "aggregate_hit_at_k": 0.9313725490196079,
    "aggregate_mrr": 0.9068627450980392,
    "aggregate_powered": true,
    "k": 10,
    "min_pairs": 10,
    "n_pairs": 102,
    "retrieval_limit": 10,
    "slices": {
      "exact": {
        "hit_at_k": 1.0,
        "mrr": 1.0,
        "n_pairs": 12,
        "powered": true
      },
      "fact": {
        "hit_at_k": 1.0,
        "mrr": 1.0,
        "n_pairs": 18,
        "powered": true
      },
      "knowledge-update": {
        "hit_at_k": 0.9285714285714286,
        "mrr": 0.8214285714285714,
        "n_pairs": 14,
        "powered": true
      },
      "multi-hop": {
        "hit_at_k": 0.9285714285714286,
        "mrr": 1.0,
        "n_pairs": 14,
        "powered": true
      },
      "paraphrase": {
        "hit_at_k": 0.9444444444444444,
        "mrr": 0.9444444444444444,
        "n_pairs": 18,
        "powered": true
      },
      "temporal": {
        "hit_at_k": 0.6666666666666666,
        "mrr": 0.5,
        "n_pairs": 12,
        "powered": true
      },
      "typo": {
        "hit_at_k": 1.0,
        "mrr": 1.0,
        "n_pairs": 14,
        "powered": true
      }
    }
  },
  "full_context_tokens_by_purpose": {
    "reasoning": {
      "cache_known_cached_prompt_tokens": 452608,
      "cache_known_calls": 102,
      "cache_known_completion_tokens": 3899,
      "cache_known_prompt_tokens": 472558,
      "cache_unknown_calls": 0,
      "live_cached_prompt_tokens": 0,
      "live_calls": 0,
      "live_completion_tokens": 0,
      "live_prompt_tokens": 0,
      "live_unknown_calls": 0
    }
  },
  "k": 10,
  "min_pairs": 10,
  "n_pairs": 102,
  "retrieval_score": {
    "aggregate_hit_at_k": 0.8431372549019608,
    "aggregate_mrr": 0.8581699346405228,
    "aggregate_powered": true,
    "k": 10,
    "min_pairs": 10,
    "n_pairs": 102,
    "retrieval_limit": 94,
    "slices": {
      "exact": {
        "hit_at_k": 1.0,
        "mrr": 1.0,
        "n_pairs": 12,
        "powered": true
      },
      "fact": {
        "hit_at_k": 1.0,
        "mrr": 1.0,
        "n_pairs": 18,
        "powered": true
      },
      "knowledge-update": {
        "hit_at_k": 0.9285714285714286,
        "mrr": 0.8095238095238095,
        "n_pairs": 14,
        "powered": true
      },
      "multi-hop": {
        "hit_at_k": 0.0,
        "mrr": 1.0,
        "n_pairs": 14,
        "powered": true
      },
      "paraphrase": {
        "hit_at_k": 0.9444444444444444,
        "mrr": 0.575925925925926,
        "n_pairs": 18,
        "powered": true
      },
      "temporal": {
        "hit_at_k": 1.0,
        "mrr": 0.6527777777777778,
        "n_pairs": 12,
        "powered": true
      },
      "typo": {
        "hit_at_k": 1.0,
        "mrr": 1.0,
        "n_pairs": 14,
        "powered": true
      }
    }
  },
  "retrieval_tokens_by_purpose": {
    "extraction": {
      "cache_known_cached_prompt_tokens": 926080,
      "cache_known_calls": 94,
      "cache_known_completion_tokens": 11996,
      "cache_known_prompt_tokens": 927166,
      "cache_unknown_calls": 0,
      "live_cached_prompt_tokens": 0,
      "live_calls": 0,
      "live_completion_tokens": 0,
      "live_prompt_tokens": 0,
      "live_unknown_calls": 0
    }
  }
}
```
