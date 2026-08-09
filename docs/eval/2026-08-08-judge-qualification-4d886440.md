# Judge qualification — 2026-08-08

- run id: `128ef51a-c25e-4682-9ddc-bb6ffc50a5af` (recorded 2026-08-08T03:34:50.432424+00:00)
- git sha: `181201f0b179430f61525ca8723e5be683f68b65`
- judge identity: `4d886440a646f176` (model `deepseek-v4-flash`, prompt v1, prompt_sha `f99151e4add69b31`)
- gold: version 1, sha256 `e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df`, 241 pairs scored
- gold_touching_attempts: 1 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Resets only when the gold file itself changes (T2.54 growth).

## Bars (stated before the run; config defaults)

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9895 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9307 → **PASS**
- `contradiction_precision_bar` = 0.95 on `contradiction_precision`: measured 0.7937 → **FAIL**

Granularity at this gold size:
- 101 gold-entailed pairs: one false accept bounds entailed-precision at 101/102 ≈ 0.990; one false reject puts recall at 100/101 ≈ 0.990.
- 55 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 55/56 ≈ 0.982.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 50 | 1 | 4 | 0 |
| entailed | 0 | 94 | 7 | 0 |
| unsupported | 13 | 0 | 72 | 0 |

- invalid responses: 0/241
- majority-class floor (three-way): 0.419

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 30 | 17 | 0.567 |
| overreach | 35 | 34 | 0.971 |
| paraphrase | 35 | 34 | 0.971 |
| temporal | 35 | 32 | 0.914 |
| unrelated | 24 | 24 | 1.000 |
| value-swap | 29 | 28 | 0.966 |
| verbatim | 24 | 24 | 1.000 |
| weakening | 29 | 23 | 0.793 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 241 calls, 96282 tokens → **399.5 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 3521 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=9 powered=False p50=None p95=None | cache n=0 powered=False p50=None p95=None
judge_call: live n=241 powered=True p50=0.9942425787448883 p95=1.4021689016371965 | cache n=0 powered=False p50=None p95=None
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.95,
      "measured": 0.7936507936507936,
      "metric": "contradiction_precision",
      "passed": false
    },
    "groundedness_gate_precision_bar": {
      "bar": 0.95,
      "measured": 0.9894736842105263,
      "metric": "entailed_precision",
      "passed": true
    },
    "groundedness_gate_recall_bar": {
      "bar": 0.9,
      "measured": 0.9306930693069307,
      "metric": "entailed_recall",
      "passed": true
    }
  },
  "bars": {
    "contradiction_precision_bar": 0.95,
    "groundedness_gate_precision_bar": 0.95,
    "groundedness_gate_recall_bar": 0.9
  },
  "eligibility": {
    "author_labelled_pairs": 0,
    "eligible": true,
    "l2_fact_pairs": 153,
    "live_pairs": 241,
    "reasons": [
      "composition: 241 live pairs; l2-fact: 153/241; author-labelled: 0/241"
    ]
  },
  "fixture_tokens": {
    "verification": {
      "cached_prompt_tokens": 2048,
      "calls": 9,
      "completion_tokens": 311,
      "prompt_tokens": 3210,
      "unknown_calls": 0
    }
  },
  "gold_sha256": "e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 61696,
      "calls": 241,
      "completion_tokens": 9402,
      "prompt_tokens": 86880,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "4d886440a646f176",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 50,
        "entailed": 1,
        "unsupported": 4
      },
      "entailed": {
        "entailed": 94,
        "unsupported": 7
      },
      "unsupported": {
        "contradicted": 13,
        "unsupported": 72
      }
    },
    "contradiction_precision": 0.7936507936507936,
    "contradiction_recall": 0.9090909090909091,
    "entailed_precision": 0.9894736842105263,
    "entailed_recall": 0.9306930693069307,
    "invalid": 0,
    "majority_class_floor": 0.4190871369294606,
    "n_pairs": 241,
    "per_slice": {
      "direction": {
        "accuracy": 0.5666666666666667,
        "correct": 17,
        "n": 30
      },
      "overreach": {
        "accuracy": 0.9714285714285714,
        "correct": 34,
        "n": 35
      },
      "paraphrase": {
        "accuracy": 0.9714285714285714,
        "correct": 34,
        "n": 35
      },
      "temporal": {
        "accuracy": 0.9142857142857143,
        "correct": 32,
        "n": 35
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 24,
        "n": 24
      },
      "value-swap": {
        "accuracy": 0.9655172413793104,
        "correct": 28,
        "n": 29
      },
      "verbatim": {
        "accuracy": 1.0,
        "correct": 24,
        "n": 24
      },
      "weakening": {
        "accuracy": 0.7931034482758621,
        "correct": 23,
        "n": 29
      }
    }
  }
}
```
