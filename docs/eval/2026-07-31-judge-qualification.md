# Judge qualification — 2026-07-31

> **INTERIM — this is not a qualification verdict and cannot open G-D.** The gold fails doc 17 §11's composition rule; the gate run is T2.41's, after T2.54 grows and adjudicates the gold:
> - composition: 41 live pairs; l2-fact: 0/41; author-labelled: 41/41
> - live pairs 41 < 200 (doc 17 §11 size floor)
> - synthetic-only gold rejected: l2-fact: 0/41 (doc 17 §11; real premises land with T2.54 after T2.10)
> - author-labelled: 41/41 live pairs await adjudication (doc 17 §11; T2.54's re-adjudication flips them)

- run id: `f8f8bb39-199e-4625-935a-8a131660c722` (recorded 2026-07-31T06:10:05.442682+00:00)
- git sha: `c60c0b1858a2d31ca477c4392b6ad90d9b84ecb1`
- judge identity: `66df91cee44d2415` (model `deepseek-v4-flash`, prompt v1, prompt_sha `08605a518a2b9d43`)
- gold: version 1, sha256 `3fd42fc0275776e6881c1ffb8a0ce7c330ed34aeb904b3739d63796915b7e50f`, 41 pairs scored
- gold_touching_attempts: 2 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Resets only when the gold file itself changes (T2.54 growth).

## Bars (stated before the run; config defaults)

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 1.0000 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 1.0000 → **PASS**
- `contradiction_precision_bar` = 0.95 on `contradiction_precision`: measured 0.8182 → **FAIL**

Granularity at this gold size:
- 17 gold-entailed pairs: one false accept bounds entailed-precision at 17/18 ≈ 0.944; one false reject puts recall at 16/17 ≈ 0.941.
- 10 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 10/11 ≈ 0.909.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 9 | 0 | 1 | 0 |
| entailed | 0 | 17 | 0 | 0 |
| unsupported | 2 | 0 | 12 | 0 |

- invalid responses: 0/41
- majority-class floor (three-way): 0.415

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 5 | 3 | 0.600 |
| overreach | 6 | 6 | 1.000 |
| paraphrase | 6 | 6 | 1.000 |
| temporal | 6 | 5 | 0.833 |
| unrelated | 4 | 4 | 1.000 |
| value-swap | 5 | 5 | 1.000 |
| verbatim | 4 | 4 | 1.000 |
| weakening | 5 | 5 | 1.000 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 41 calls, 16736 tokens → **408.2 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 3518 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=0 powered=False p50=None p95=None | cache n=9 powered=False p50=None p95=None
judge_call: live n=0 powered=False p50=None p95=None | cache n=41 powered=True p50=3.6621466279029846e-05 p95=4.6586617827415466e-05
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.95,
      "measured": 0.8181818181818182,
      "metric": "contradiction_precision",
      "passed": false
    },
    "groundedness_gate_precision_bar": {
      "bar": 0.95,
      "measured": 1.0,
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
    "author_labelled_pairs": 41,
    "eligible": false,
    "l2_fact_pairs": 0,
    "live_pairs": 41,
    "reasons": [
      "composition: 41 live pairs; l2-fact: 0/41; author-labelled: 41/41",
      "live pairs 41 < 200 (doc 17 \u00a711 size floor)",
      "synthetic-only gold rejected: l2-fact: 0/41 (doc 17 \u00a711; real premises land with T2.54 after T2.10)",
      "author-labelled: 41/41 live pairs await adjudication (doc 17 \u00a711; T2.54's re-adjudication flips them)"
    ]
  },
  "fixture_tokens": {
    "verification": {
      "cached_prompt_tokens": 2048,
      "calls": 9,
      "completion_tokens": 308,
      "prompt_tokens": 3210,
      "unknown_calls": 0
    }
  },
  "gold_sha256": "3fd42fc0275776e6881c1ffb8a0ce7c330ed34aeb904b3739d63796915b7e50f",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 10496,
      "calls": 41,
      "completion_tokens": 1624,
      "prompt_tokens": 15112,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "66df91cee44d2415",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 9,
        "unsupported": 1
      },
      "entailed": {
        "entailed": 17
      },
      "unsupported": {
        "contradicted": 2,
        "unsupported": 12
      }
    },
    "contradiction_precision": 0.8181818181818182,
    "contradiction_recall": 0.9,
    "entailed_precision": 1.0,
    "entailed_recall": 1.0,
    "invalid": 0,
    "majority_class_floor": 0.4146341463414634,
    "n_pairs": 41,
    "per_slice": {
      "direction": {
        "accuracy": 0.6,
        "correct": 3,
        "n": 5
      },
      "overreach": {
        "accuracy": 1.0,
        "correct": 6,
        "n": 6
      },
      "paraphrase": {
        "accuracy": 1.0,
        "correct": 6,
        "n": 6
      },
      "temporal": {
        "accuracy": 0.8333333333333334,
        "correct": 5,
        "n": 6
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 4,
        "n": 4
      },
      "value-swap": {
        "accuracy": 1.0,
        "correct": 5,
        "n": 5
      },
      "verbatim": {
        "accuracy": 1.0,
        "correct": 4,
        "n": 4
      },
      "weakening": {
        "accuracy": 1.0,
        "correct": 5,
        "n": 5
      }
    }
  }
}
```
