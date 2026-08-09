# Judge qualification — 2026-08-08

- run id: `fba35e0c-edc0-4826-85e7-e0ce615e9c8d` (recorded 2026-08-08T15:50:15.957764+00:00)
- git sha: `e69895cb677cd66c7a33f2b3307f03a69cc81207`
- judge identity: `fd39e7b2c47fa375` (model `gpt-5.5`, prompt v1, prompt_sha `f99151e4add69b31`)
- judge invocation: `base_url=https://api.openai.com/v1` `api_kind=openai` `params={"reasoning_effort": "high"}` `dimensions=None` `reasoning=False`
- gold: version 1, sha256 `800d4d91dce4e373ae64ba63d78482222190eddc5c32ffa16d9dd731f9730d78`, 351 pairs scored
- gold_touching_attempts: 1 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Resets only when the gold file itself changes (T2.54 growth).

## Bars (stated before the run; config defaults)

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9932 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9932 → **PASS**
- `contradiction_precision_bar` = 0.70 on `contradiction_precision`: measured 0.9012 → **PASS**
- `contradiction_recall_bar` = 0.95 on `contradiction_recall`: measured 0.9125 → **FAIL**

Granularity at this gold size:
- 146 gold-entailed pairs: one false accept bounds entailed-precision at 146/147 ≈ 0.993; one false reject puts recall at 145/146 ≈ 0.993.
- 80 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 80/81 ≈ 0.988.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 73 | 0 | 7 | 0 |
| entailed | 0 | 145 | 1 | 0 |
| unsupported | 8 | 1 | 116 | 0 |

- invalid responses: 0/351
- majority-class floor (three-way): 0.416

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 44 | 42 | 0.955 |
| overreach | 51 | 51 | 1.000 |
| paraphrase | 51 | 51 | 1.000 |
| temporal | 51 | 44 | 0.863 |
| unrelated | 35 | 35 | 1.000 |
| value-swap | 42 | 35 | 0.833 |
| verbatim | 35 | 35 | 1.000 |
| weakening | 42 | 41 | 0.976 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 351 calls, 172555 tokens → **491.6 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 4088 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=0 powered=False p50=None p95=None | cache n=9 powered=False p50=None p95=None
judge_call: live n=351 powered=True p50=2.529273260384798 p95=5.481495875865221 | cache n=0 powered=False p50=None p95=None
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.7,
      "measured": 0.9012345679012346,
      "metric": "contradiction_precision",
      "passed": true
    },
    "contradiction_recall_bar": {
      "bar": 0.95,
      "measured": 0.9125,
      "metric": "contradiction_recall",
      "passed": false
    },
    "groundedness_gate_precision_bar": {
      "bar": 0.95,
      "measured": 0.9931506849315068,
      "metric": "entailed_precision",
      "passed": true
    },
    "groundedness_gate_recall_bar": {
      "bar": 0.9,
      "measured": 0.9931506849315068,
      "metric": "entailed_recall",
      "passed": true
    }
  },
  "bars": {
    "contradiction_precision_bar": 0.7,
    "contradiction_recall_bar": 0.95,
    "groundedness_gate_precision_bar": 0.95,
    "groundedness_gate_recall_bar": 0.9
  },
  "eligibility": {
    "author_labelled_pairs": 0,
    "eligible": true,
    "l2_fact_pairs": 235,
    "live_pairs": 351,
    "reasons": [
      "composition: 351 live pairs; l2-fact: 235/351; author-labelled: 0/351"
    ]
  },
  "fixture_tokens": {
    "verification": {
      "cached_prompt_tokens": 0,
      "calls": 9,
      "completion_tokens": 1047,
      "prompt_tokens": 3041,
      "unknown_calls": 0
    }
  },
  "gold_sha256": "800d4d91dce4e373ae64ba63d78482222190eddc5c32ffa16d9dd731f9730d78",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 0,
      "calls": 351,
      "completion_tokens": 53253,
      "prompt_tokens": 119302,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "fd39e7b2c47fa375",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 73,
        "unsupported": 7
      },
      "entailed": {
        "entailed": 145,
        "unsupported": 1
      },
      "unsupported": {
        "contradicted": 8,
        "entailed": 1,
        "unsupported": 116
      }
    },
    "contradiction_precision": 0.9012345679012346,
    "contradiction_recall": 0.9125,
    "entailed_precision": 0.9931506849315068,
    "entailed_recall": 0.9931506849315068,
    "invalid": 0,
    "majority_class_floor": 0.41595441595441596,
    "n_pairs": 351,
    "per_slice": {
      "direction": {
        "accuracy": 0.9545454545454546,
        "correct": 42,
        "n": 44
      },
      "overreach": {
        "accuracy": 1.0,
        "correct": 51,
        "n": 51
      },
      "paraphrase": {
        "accuracy": 1.0,
        "correct": 51,
        "n": 51
      },
      "temporal": {
        "accuracy": 0.8627450980392157,
        "correct": 44,
        "n": 51
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 35,
        "n": 35
      },
      "value-swap": {
        "accuracy": 0.8333333333333334,
        "correct": 35,
        "n": 42
      },
      "verbatim": {
        "accuracy": 1.0,
        "correct": 35,
        "n": 35
      },
      "weakening": {
        "accuracy": 0.9761904761904762,
        "correct": 41,
        "n": 42
      }
    }
  }
}
```
