# Judge qualification — 2026-08-17

- run id: `da9ecec8-8ecd-4199-8693-7cc9dc8692a0` (recorded 2026-08-17T07:40:04.086348+00:00)
- git sha: `60953e70f1abbf7a5151b49840007392f44d2dd5`
- judge identity: `fd39e7b2c47fa375` (model `gpt-5.5`, prompt v1, prompt_sha `f99151e4add69b31`)
- judge invocation: `base_url=https://api.openai.com/v1` `api_kind=openai` `params={"reasoning_effort": "high"}` `dimensions=None` `reasoning=False`
- gold: version 1, sha256 `fdbe2af9967970b6c80ee9cf1b9e3699584118f1eb6aac15c3b023b7b365f071`, 280 pairs scored
- gold_touching_attempts: 1 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Keyed on the gold's PAIRS since 2026-08-12, so an edit to something no judge was shown cannot reset it.
- census independence (contradicted): 80 rows over 80 independent propositions — rows == propositions. Against a bar of 0.95, the minimum passing score is 76/80 = 0.95 on rows and 76/80 = 0.95 on independent propositions. The bar is expressible on this census.
- census independence (entailed): 110 rows over 101 independent propositions — 9 duplicated proposition(s): [['eg-0427', 'eg-0561'], ['eg-0424', 'eg-0558'], ['eg-0423', 'eg-0557'], ['eg-0463', 'eg-0590'], ['eg-0418', 'eg-0554'], ['eg-0452', 'eg-0580'], ['eg-0479', 'eg-0607'], ['eg-0426', 'eg-0560'], ['eg-0456', 'eg-0584']]. Against a bar of 0.9, the minimum passing score is 99/110 = 0.9 on rows and 91/101 = 0.901 on independent propositions. The bar is expressible on this census.

## Bars (stated before the run; config defaults)

These are `verification_judge.VERIFICATION_BAR_DEFAULTS` verbatim. This runner reads no database, so no `verification_bar_licences` row was consulted and no bar could have been clamped or licensed here — the app-side floor governs `judge()`, never this measurement. Stated rather than left to be inferred from an unchanged number (T2.128).

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9906 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9545 → **PASS**
- `contradiction_precision_bar` = 0.70 on `contradiction_precision`: measured 0.9692 → **PASS**
- `contradiction_recall_bar` = 0.95 on `contradiction_recall`: measured 0.7875 → **FAIL**

Granularity at this gold size:
- 110 gold-entailed pairs: one false accept bounds entailed-precision at 110/111 ≈ 0.991; one false reject puts recall at 109/110 ≈ 0.991.
- 80 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 80/81 ≈ 0.988.

## Bars on Rule B's second population

LABELLING.md's contacted-pairs rule requires every barred metric on **both** populations, with the gate verdict required to hold on both. The pairs above are all 280 live ones, of which 0 were contacted before; these are the 280 pairs (`eg-0242`+) not contacted before the grown-gold attempt.

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9906 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9545 → **PASS**
- `contradiction_precision_bar` = 0.70 on `contradiction_precision`: measured 0.9692 → **PASS**
- `contradiction_recall_bar` = 0.95 on `contradiction_recall`: measured 0.7875 → **FAIL**

Granularity on this subset — **read this before the numbers above**:
- 110 gold-entailed pairs: one false accept bounds entailed-precision at 110/111 ≈ 0.991; one false reject puts recall at 109/110 ≈ 0.991.
- 80 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 80/81 ≈ 0.988.
  A bar can only be met at a value the lattice contains. T2.110 sized the *pooled* contradicted census at 80 so that 76/80 = 0.9500 sits exactly on `contradiction_recall_bar`; that analysis was never run for this subset, whose smaller census may place the bar between two attainable values and so enforce a stricter number than the one stated. Where it does, the subset verdict is evidence about the census, not only about the judge.

## Census independence (contradicted) — rows == propositions

- 80 contradicted rows over 80 independent propositions: no two rows assert one proposition, so the bar means on propositions exactly what it means on rows and no independence reading is owed.

## Census independence (entailed) — read with the recall verdict

- 110 entailed rows over 101 independent propositions (9 duplicated: []).
- Measured entailed-recall 0.9545 is 105/110 on rows. If the judge caught every correlated pair, the independent reading is at worst 96/101 = 0.9505.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 63 | 0 | 17 | 0 |
| entailed | 0 | 105 | 5 | 0 |
| unsupported | 2 | 1 | 87 | 0 |

- invalid responses: 0/280
- majority-class floor (three-way): 0.393

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 34 | 34 | 1.000 |
| overreach | 41 | 41 | 1.000 |
| paraphrase | 41 | 39 | 0.951 |
| temporal | 41 | 38 | 0.927 |
| unrelated | 28 | 28 | 1.000 |
| value-swap | 34 | 17 | 0.500 |
| verbatim | 27 | 27 | 1.000 |
| weakening | 34 | 31 | 0.912 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 280 calls, 145533 tokens → **519.8 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 4030 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=0 powered=False p50=None p95=None | cache n=9 powered=False p50=None p95=None
judge_call: live n=280 powered=True p50=2.883799724280834 p95=9.487309087067842 | cache n=0 powered=False p50=None p95=None
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.7,
      "measured": 0.9692307692307692,
      "metric": "contradiction_precision",
      "passed": true
    },
    "contradiction_recall_bar": {
      "bar": 0.95,
      "measured": 0.7875,
      "metric": "contradiction_recall",
      "passed": false
    },
    "groundedness_gate_precision_bar": {
      "bar": 0.95,
      "measured": 0.9905660377358491,
      "metric": "entailed_precision",
      "passed": true
    },
    "groundedness_gate_recall_bar": {
      "bar": 0.9,
      "measured": 0.9545454545454546,
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
    "l2_fact_pairs": 218,
    "live_pairs": 280,
    "reasons": [
      "composition: 280 live pairs; l2-fact: 218/280; author-labelled: 0/280"
    ]
  },
  "fixture_tokens": {
    "verification": {
      "cached_prompt_tokens": 0,
      "calls": 9,
      "completion_tokens": 989,
      "prompt_tokens": 3041,
      "unknown_calls": 0
    }
  },
  "gold_sha256": "fdbe2af9967970b6c80ee9cf1b9e3699584118f1eb6aac15c3b023b7b365f071",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 0,
      "calls": 280,
      "completion_tokens": 49322,
      "prompt_tokens": 96211,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "fd39e7b2c47fa375",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 63,
        "unsupported": 17
      },
      "entailed": {
        "entailed": 105,
        "unsupported": 5
      },
      "unsupported": {
        "contradicted": 2,
        "entailed": 1,
        "unsupported": 87
      }
    },
    "contradiction_precision": 0.9692307692307692,
    "contradiction_recall": 0.7875,
    "entailed_precision": 0.9905660377358491,
    "entailed_recall": 0.9545454545454546,
    "invalid": 0,
    "majority_class_floor": 0.39285714285714285,
    "n_pairs": 280,
    "per_slice": {
      "direction": {
        "accuracy": 1.0,
        "correct": 34,
        "n": 34
      },
      "overreach": {
        "accuracy": 1.0,
        "correct": 41,
        "n": 41
      },
      "paraphrase": {
        "accuracy": 0.9512195121951219,
        "correct": 39,
        "n": 41
      },
      "temporal": {
        "accuracy": 0.926829268292683,
        "correct": 38,
        "n": 41
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 28,
        "n": 28
      },
      "value-swap": {
        "accuracy": 0.5,
        "correct": 17,
        "n": 34
      },
      "verbatim": {
        "accuracy": 1.0,
        "correct": 27,
        "n": 27
      },
      "weakening": {
        "accuracy": 0.9117647058823529,
        "correct": 31,
        "n": 34
      }
    }
  }
}
```
