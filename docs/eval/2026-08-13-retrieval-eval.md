# Retrieval eval — 2026-08-13

- run id: `8b9d7aa0-4601-4a41-bf59-a4a71daf45ea` (recorded 2026-08-13T06:53:22.637254+00:00)
- git sha: `d71ccb2556df38f4b1e7ac9f65ef684162f2642f`
- embedder fingerprint: `qwen3-embedding:0.6b|1024`
- gate configuration: `classification_mode='simple', classifier_kind=None, relation_rescue=True`
- corpus: 178 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval retrieval_limit=178, full_context retrieval_limit=10
- live LLM calls this run: ingest=101, retrieval=0, full_context=102 (total=203)

- **multi-hop hit@10 = 0.0000 on the retrieval arm is the DESIGNED state (T0.06a), not a defect.** Every live multi-hop pair is built so its consequence memory ranks worse than k in the hybrid-only baseline -- this is the headroom a future graph-aware arm exists to close, not a bug for this runner to flag.
- **full context beats retrieval on pooled accuracy this run** (ΔMRR=+0.0799, Δhit@10=+0.1176, full-context minus retrieval) -- the honest measured result of the T0.09 comparator, stated plainly rather than buried or reframed as a cost-only win. See the cost caveats below for why the two arms' token costs are not directly subtractable.

## Comparison (human-readable)

Includes latency by channel for both arms -- see Reproducibility below for which parts of this section are expected to vary run to run and which are not.

```
=== TWO-ARM COMPARISON (k=10, min_pairs=10, n_pairs=102) ===
fetch depth: retrieval retrieval_limit=178, full_context retrieval_limit=10
context: 178/178 corpus entries in prompt, 25539 chars, policy=no-truncation
CAVEAT [latency-not-like-for-like]: cross-arm latency is not like-for-like: every end_to_end sample in the retrieval arm was cache-served (a disk read) while the full_context arm paid a live model call, so any ratio between the two arms' p50/p95 overstates the retrieval arm's advantage. Compare within a population, never across one.
CAVEAT [cost-kind-asymmetry]: the two arms' token blocks are different KINDS of quantity and must not be subtracted or ratioed: the full_context arm billed exactly one call per scored pair (102), so its token cost recurs in full on every run of the query set, while the retrieval arm's 178 call(s) are not per-pair -- they are one-time indexing work, paid once per corpus and amortised over every future query. The retrieval arm's own per-query cost is 102 query-embedding call(s), which carry no token accounting and appear in no token block here at all.

--- accuracy per slice (retrieval | full-context | delta) ---
slice                n    r.mrr   f.mrr    d.mrr     r.hit   f.hit    d.hit
exact               12   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
fact                18   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
knowledge-update    14   0.8095  0.8929   0.0833    0.8571  0.9286   0.0714
multi-hop           14   1.0000  1.0000   0.0000    0.0000  0.9286   0.9286
paraphrase          18   0.4547  0.9167   0.4620    0.8889  0.9444   0.0556
temporal            12   0.6528  0.5417  -0.1111    1.0000  0.7500  -0.2500
typo                14   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
AGGREGATE          102   0.8368  0.9167   0.0799    0.8235  0.9412   0.1176

--- retrieval: latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00023  p95=0.00245
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00333  p95=0.00580
keyword_search     live   n= 102  p50=0.00037  p95=0.00074
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00201  p95=0.00245
semantic_search    cache  no samples
--- retrieval: token cost by purpose ---
  extraction: {'live_calls': 84, 'live_prompt_tokens': 829030, 'live_completion_tokens': 16159, 'live_cached_prompt_tokens': 817152, 'live_unknown_calls': 0, 'cache_known_calls': 94, 'cache_known_prompt_tokens': 927166, 'cache_known_completion_tokens': 11996, 'cache_known_cached_prompt_tokens': 926080, 'cache_unknown_calls': 0}

--- full_context: latency by channel (seconds, nearest-rank, min_samples=20) ---
end_to_end         live   n= 102  p50=1.02117  p95=1.66368
end_to_end         cache  no samples
full_context_call  live   n= 102  p50=1.02116  p95=1.66368
full_context_call  cache  no samples
--- full_context: token cost by purpose ---
  reasoning: {'live_calls': 102, 'live_prompt_tokens': 929926, 'live_completion_tokens': 4893, 'live_cached_prompt_tokens': 904960, 'live_unknown_calls': 0, 'cache_known_calls': 0, 'cache_known_prompt_tokens': 0, 'cache_known_completion_tokens': 0, 'cache_known_cached_prompt_tokens': 0, 'cache_unknown_calls': 0}

--- full-context id audit ---
  duplicate_rate: 0.0
  hallucinated_rate: 0.0
  ids_duplicate: 0
  ids_hallucinated: 0
  ids_kept: 177
  ids_malformed: 0
  ids_over_limit: 0
  ids_returned: 177
  kept_rate: 1.0
  malformed_rate: 0.0
  queries: 102
  responses_all_dropped: 0
  responses_empty: 4
  responses_truncated: 0
  responses_unparseable: 0
```

## Reproducibility

Two consecutive runs on an unchanged tree, against an unchanged warm LLM cache, must reproduce the JSON block below byte-for-byte: every accuracy figure (per slice and aggregate, both arms), every token-cost figure, the full-context id audit, the context description, and the set of caveat kinds. **Latency is excluded on purpose** (p50/p95 by channel, in the comparison above): it is a wall-clock measurement of a cache read or a live model round trip, and is expected to differ run to run even when nothing else does -- only its live-vs-cache population membership is a claim this report makes, never the exact figure.

```json
{
  "caveat_kinds": [
    "cost-kind-asymmetry",
    "latency-not-like-for-like"
  ],
  "deltas": {
    "aggregate": {
      "hit_at_k": 0.11764705882352944,
      "mrr": 0.07989028944911292
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
        "hit_at_k": 0.07142857142857151,
        "mrr": 0.08333333333333337
      },
      "multi-hop": {
        "hit_at_k": 0.9285714285714286,
        "mrr": 0.0
      },
      "paraphrase": {
        "hit_at_k": 0.05555555555555558,
        "mrr": 0.4619708994708994
      },
      "temporal": {
        "hit_at_k": -0.25,
        "mrr": -0.11111111111111116
      },
      "typo": {
        "hit_at_k": 0.0,
        "mrr": 0.0
      }
    }
  },
  "full_context_context": {
    "complete": true,
    "context_chars": 25539,
    "corpus_entries": 178,
    "dropped_entries": 0,
    "dropped_ids": [],
    "included_entries": 178,
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
    "ids_kept": 177,
    "ids_malformed": 0,
    "ids_over_limit": 0,
    "ids_returned": 177,
    "kept_rate": 1.0,
    "malformed_rate": 0.0,
    "queries": 102,
    "responses_all_dropped": 0,
    "responses_empty": 4,
    "responses_truncated": 0,
    "responses_unparseable": 0
  },
  "full_context_score": {
    "aggregate_hit_at_k": 0.9411764705882353,
    "aggregate_mrr": 0.9166666666666666,
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
        "mrr": 0.8928571428571429,
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
        "mrr": 0.9166666666666666,
        "n_pairs": 18,
        "powered": true
      },
      "temporal": {
        "hit_at_k": 0.75,
        "mrr": 0.5416666666666666,
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
      "cache_known_cached_prompt_tokens": 0,
      "cache_known_calls": 0,
      "cache_known_completion_tokens": 0,
      "cache_known_prompt_tokens": 0,
      "cache_unknown_calls": 0,
      "live_cached_prompt_tokens": 904960,
      "live_calls": 102,
      "live_completion_tokens": 4893,
      "live_prompt_tokens": 929926,
      "live_unknown_calls": 0
    }
  },
  "k": 10,
  "min_pairs": 10,
  "n_pairs": 102,
  "retrieval_score": {
    "aggregate_hit_at_k": 0.8235294117647058,
    "aggregate_mrr": 0.8367763772175537,
    "aggregate_powered": true,
    "k": 10,
    "min_pairs": 10,
    "n_pairs": 102,
    "retrieval_limit": 178,
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
        "hit_at_k": 0.8571428571428571,
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
        "hit_at_k": 0.8888888888888888,
        "mrr": 0.4546957671957672,
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
      "live_cached_prompt_tokens": 817152,
      "live_calls": 84,
      "live_completion_tokens": 16159,
      "live_prompt_tokens": 829030,
      "live_unknown_calls": 0
    }
  }
}
```
