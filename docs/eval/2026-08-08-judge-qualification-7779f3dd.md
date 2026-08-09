# Judge qualification — 2026-08-08

- run id: `7f73229f-53d4-44bf-9f1c-d05238a00579` (recorded 2026-08-08T05:39:30.019299+00:00)
- git sha: `f3d8ac34cbe8946938b7487084a60296866cb428`
- judge identity: `7779f3dd8e451036` (model `gpt-5.5`, prompt v2, prompt_sha `1e89d1aa077e13e4`)
- gold: version 1, sha256 `e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df`, 241 pairs scored
- gold_touching_attempts: 3 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Resets only when the gold file itself changes (T2.54 growth).

## Bars (stated before the run; config defaults)

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9806 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 1.0000 → **PASS**
- `contradiction_precision_bar` = 0.95 on `contradiction_precision`: measured 0.9020 → **FAIL**

Granularity at this gold size:
- 101 gold-entailed pairs: one false accept bounds entailed-precision at 101/102 ≈ 0.990; one false reject puts recall at 100/101 ≈ 0.990.
- 55 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 55/56 ≈ 0.982.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 46 | 0 | 9 | 0 |
| entailed | 0 | 101 | 0 | 0 |
| unsupported | 5 | 2 | 78 | 0 |

- invalid responses: 0/241
- majority-class floor (three-way): 0.419

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 30 | 30 | 1.000 |
| overreach | 35 | 34 | 0.971 |
| paraphrase | 35 | 35 | 1.000 |
| temporal | 35 | 29 | 0.829 |
| unrelated | 24 | 24 | 1.000 |
| value-swap | 29 | 20 | 0.690 |
| verbatim | 24 | 24 | 1.000 |
| weakening | 29 | 29 | 1.000 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 241 calls, 155641 tokens → **645.8 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 5493 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=9 powered=False p50=None p95=None | cache n=0 powered=False p50=None p95=None
judge_call: live n=241 powered=True p50=2.4352385960519314 p95=6.222958097234368 | cache n=0 powered=False p50=None p95=None
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.95,
      "measured": 0.9019607843137255,
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
      "completion_tokens": 994,
      "prompt_tokens": 4499,
      "unknown_calls": 0
    }
  },
  "gold_sha256": "e6d5647a8cbd070ea786fe03feaec3f5030816fc94c52dee986df749aa1e60df",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 0,
      "calls": 241,
      "completion_tokens": 34449,
      "prompt_tokens": 121192,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "7779f3dd8e451036",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 46,
        "unsupported": 9
      },
      "entailed": {
        "entailed": 101
      },
      "unsupported": {
        "contradicted": 5,
        "entailed": 2,
        "unsupported": 78
      }
    },
    "contradiction_precision": 0.9019607843137255,
    "contradiction_recall": 0.8363636363636363,
    "entailed_precision": 0.9805825242718447,
    "entailed_recall": 1.0,
    "invalid": 0,
    "majority_class_floor": 0.4190871369294606,
    "n_pairs": 241,
    "per_slice": {
      "direction": {
        "accuracy": 1.0,
        "correct": 30,
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
        "accuracy": 0.8285714285714286,
        "correct": 29,
        "n": 35
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 24,
        "n": 24
      },
      "value-swap": {
        "accuracy": 0.6896551724137931,
        "correct": 20,
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
