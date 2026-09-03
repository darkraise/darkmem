# Retrieval eval — 2026-09-03

- run id: `27c62f21-4236-4d3f-a59b-0867c2533b27` (recorded 2026-09-03T06:49:08.171221+00:00)
- git sha: `e97b04f0d4bc508740a6da4bf0433bc148447790`
- embedder fingerprint: `qwen3-embedding:0.6b|1024`
- gate configuration: `classification_mode='simple', classifier_kind=None, relation_rescue=True`
- corpus: 178 memories, gold v4, 118 pairs authored (102 live)
- protocol: k=10, min_pairs=10, retrieval retrieval_limit=178, full_context retrieval_limit=10
- live LLM calls this run: ingest=0, retrieval=0, full_context=0 (total=0)

- **multi-hop hit@10 = 0.0000 on the retrieval arm is the DESIGNED state (T0.06a), not a defect.** Every live multi-hop pair is built so its consequence memory ranks worse than k in the hybrid-only baseline -- this is the headroom a future graph-aware arm exists to close, not a bug for this runner to flag.
- **full context beats retrieval on pooled accuracy this run** (ΔMRR=+0.0685, Δhit@10=+0.1078, full-context minus retrieval) -- the honest measured result of the T0.09 comparator, stated plainly rather than buried or reframed as a cost-only win. See the cost caveats below for why the two arms' token costs are not directly subtractable.

## Comparison (human-readable)

Includes latency by channel for both arms -- see Reproducibility below for which parts of this section are expected to vary run to run and which are not.

```
=== TWO-ARM COMPARISON (k=10, min_pairs=10, n_pairs=102) ===
fetch depth: retrieval retrieval_limit=178, full_context retrieval_limit=10
context: 178/178 corpus entries in prompt, 25539 chars, policy=no-truncation
CAVEAT [latency-no-live-samples]: no arm measured live latency: every end_to_end sample in both arms was cache-served, so these p50/p95 figures describe a warm replay of a recorded run, not a system anybody runs.
CAVEAT [cost-kind-asymmetry]: the two arms' token blocks are different KINDS of quantity and must not be subtracted or ratioed: the full_context arm billed exactly one call per scored pair (102), so its token cost recurs in full on every run of the query set, while the retrieval arm's 178 call(s) are not per-pair -- they are one-time indexing work, paid once per corpus and amortised over every future query. The retrieval arm's own per-query cost is 102 query-embedding call(s), which carry no token accounting and appear in no token block here at all.

--- accuracy per slice (retrieval | full-context | delta) ---
slice                n    r.mrr   f.mrr    d.mrr     r.hit   f.hit    d.hit
exact               12   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
fact                18   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
knowledge-update    14   0.8095  0.8571   0.0476    0.8571  0.8571   0.0000
multi-hop           14   1.0000  1.0000   0.0000    0.0000  0.9286   0.9286
paraphrase          18   0.4547  0.9167   0.4620    0.8889  0.9444   0.0556
temporal            12   0.6528  0.4861  -0.1667    1.0000  0.7500  -0.2500
typo                14   1.0000  1.0000   0.0000    1.0000  1.0000   0.0000
AGGREGATE          102   0.8368  0.9052   0.0685    0.8235  0.9314   0.1078

--- retrieval: latency by channel (seconds, nearest-rank, min_samples=20) ---
embed_query        live   no samples
embed_query        cache  n= 102  p50=0.00026  p95=0.00226
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00346  p95=0.00547
keyword_search     live   n= 102  p50=0.00037  p95=0.00055
keyword_search     cache  no samples
reranker           live   no samples
reranker           cache  no samples
semantic_search    live   n= 102  p50=0.00211  p95=0.00262
semantic_search    cache  no samples
--- retrieval: token cost by purpose ---
  extraction: {'live_calls': 0, 'live_prompt_tokens': 0, 'live_completion_tokens': 0, 'live_cached_prompt_tokens': 0, 'live_unknown_calls': 0, 'cache_known_calls': 178, 'cache_known_prompt_tokens': 1619848, 'cache_known_completion_tokens': 26849, 'cache_known_cached_prompt_tokens': 1617664, 'cache_unknown_calls': 0}

--- full_context: latency by channel (seconds, nearest-rank, min_samples=20) ---
end_to_end         live   no samples
end_to_end         cache  n= 102  p50=0.00024  p95=0.00029
full_context_call  live   no samples
full_context_call  cache  n= 102  p50=0.00024  p95=0.00029
--- full_context: token cost by purpose ---
  reasoning: {'live_calls': 0, 'live_prompt_tokens': 0, 'live_completion_tokens': 0, 'live_cached_prompt_tokens': 0, 'live_unknown_calls': 0, 'cache_known_calls': 102, 'cache_known_prompt_tokens': 929926, 'cache_known_completion_tokens': 4861, 'cache_known_cached_prompt_tokens': 899200, 'cache_unknown_calls': 0}

--- full-context id audit ---
  duplicate_rate: 0.0
  hallucinated_rate: 0.0
  ids_duplicate: 0
  ids_hallucinated: 0
  ids_kept: 176
  ids_malformed: 0
  ids_over_limit: 0
  ids_returned: 176
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
    "latency-no-live-samples"
  ],
  "deltas": {
    "aggregate": {
      "hit_at_k": 0.10784313725490202,
      "mrr": 0.06845238095238093
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
        "mrr": 0.04761904761904756
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
        "mrr": -0.16666666666666669
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
    "ids_kept": 176,
    "ids_malformed": 0,
    "ids_over_limit": 0,
    "ids_returned": 176,
    "kept_rate": 1.0,
    "malformed_rate": 0.0,
    "queries": 102,
    "responses_all_dropped": 0,
    "responses_empty": 4,
    "responses_truncated": 0,
    "responses_unparseable": 0
  },
  "full_context_score": {
    "aggregate_hit_at_k": 0.9313725490196079,
    "aggregate_mrr": 0.9052287581699346,
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
        "hit_at_k": 0.8571428571428571,
        "mrr": 0.8571428571428571,
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
        "mrr": 0.4861111111111111,
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
      "cache_known_cached_prompt_tokens": 899200,
      "cache_known_calls": 102,
      "cache_known_completion_tokens": 4861,
      "cache_known_prompt_tokens": 929926,
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
      "cache_known_cached_prompt_tokens": 1617664,
      "cache_known_calls": 178,
      "cache_known_completion_tokens": 26849,
      "cache_known_prompt_tokens": 1619848,
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
