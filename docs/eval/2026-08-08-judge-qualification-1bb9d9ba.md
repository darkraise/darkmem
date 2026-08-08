# Judge qualification — 2026-08-08

- run id: `a02cacd5-f69a-4967-b1a9-d3cce4a6b8e4` (recorded 2026-08-08T04:35:05.053300+00:00)
- git sha: `027b55012326fed4dd29d3d33e08589c2b4b2936`
- judge identity: `1bb9d9bae62eb9d8` (model `gpt-5.5`, prompt v1, prompt_sha `f99151e4add69b31`)
- gold: version 1, sha256 `e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df`, 241 pairs scored
- gold_touching_attempts: 2 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Resets only when the gold file itself changes (T2.54 growth).

## Bars (stated before the run; config defaults)

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9806 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 1.0000 → **PASS**
- `contradiction_precision_bar` = 0.95 on `contradiction_precision`: measured 0.8814 → **FAIL**

Granularity at this gold size:
- 101 gold-entailed pairs: one false accept bounds entailed-precision at 101/102 ≈ 0.990; one false reject puts recall at 100/101 ≈ 0.990.
- 55 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 55/56 ≈ 0.982.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 52 | 0 | 3 | 0 |
| entailed | 0 | 101 | 0 | 0 |
| unsupported | 7 | 2 | 76 | 0 |

- invalid responses: 0/241
- majority-class floor (three-way): 0.419

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 30 | 27 | 0.900 |
| overreach | 35 | 34 | 0.971 |
| paraphrase | 35 | 35 | 1.000 |
| temporal | 35 | 30 | 0.857 |
| unrelated | 24 | 24 | 1.000 |
| value-swap | 29 | 26 | 0.897 |
| verbatim | 24 | 24 | 1.000 |
| weakening | 29 | 29 | 1.000 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 241 calls, 119352 tokens → **495.2 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 4007 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=0 powered=False p50=None p95=None | cache n=9 powered=False p50=None p95=None
judge_call: live n=241 powered=True p50=2.410026891157031 p95=5.311076417565346 | cache n=0 powered=False p50=None p95=None
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.95,
      "measured": 0.8813559322033898,
      "metric": "contradiction_precision",
      "passed": false
    },
    "groundedness_gate_precision_bar": {
      "bar": 0.95,
      "measured": 0.9805825242718447,
      "metric": "entailed_precision",
      "passed": true
    },
    "groundedness_gate_recall_bar": {
      "bar": 0.9,
      "measured": 1.0,
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
      "cached_prompt_tokens": 0,
      "calls": 9,
      "completion_tokens": 966,
      "prompt_tokens": 3041,
      "unknown_calls": 0
    }
  },
  "gold_sha256": "e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 0,
      "calls": 241,
      "completion_tokens": 37202,
      "prompt_tokens": 82150,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "1bb9d9bae62eb9d8",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 52,
        "unsupported": 3
      },
      "entailed": {
        "entailed": 101
      },
      "unsupported": {
        "contradicted": 7,
        "entailed": 2,
        "unsupported": 76
      }
    },
    "contradiction_precision": 0.8813559322033898,
    "contradiction_recall": 0.9454545454545454,
    "entailed_precision": 0.9805825242718447,
    "entailed_recall": 1.0,
    "invalid": 0,
    "majority_class_floor": 0.4190871369294606,
    "n_pairs": 241,
    "per_slice": {
      "direction": {
        "accuracy": 0.9,
        "correct": 27,
        "n": 30
      },
      "overreach": {
        "accuracy": 0.9714285714285714,
        "correct": 34,
        "n": 35
      },
      "paraphrase": {
        "accuracy": 1.0,
        "correct": 35,
        "n": 35
      },
      "temporal": {
        "accuracy": 0.8571428571428571,
        "correct": 30,
        "n": 35
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 24,
        "n": 24
      },
      "value-swap": {
        "accuracy": 0.896551724137931,
        "correct": 26,
        "n": 29
      },
      "verbatim": {
        "accuracy": 1.0,
        "correct": 24,
        "n": 24
      },
      "weakening": {
        "accuracy": 1.0,
        "correct": 29,
        "n": 29
      }
    }
  }
}
```
