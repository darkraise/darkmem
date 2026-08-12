# Judge qualification — 2026-08-12

- run id: `7cd361f2-9fe6-4bc7-b6e0-de14c844471d` (recorded 2026-08-12T07:10:53.776178+00:00)
- git sha: `1b4b190d0de0eeb521eafb748fc018e0a0ce9c66`
- judge identity: `fd39e7b2c47fa375` (model `gpt-5.5`, prompt v1, prompt_sha `f99151e4add69b31`)
- judge invocation: `base_url=https://api.openai.com/v1` `api_kind=openai` `params={"reasoning_effort": "high"}` `dimensions=None` `reasoning=False`
- gold: version 1, sha256 `6eadba737b8cd8ee216d595f8e617f12d51bdb636ccc39fee76c0bcb79882b2e`, 402 pairs scored
- gold_touching_attempts: 2 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Keyed on the gold's PAIRS since 2026-08-12, so an edit to something no judge was shown cannot reset it.
- census independence (contradicted): 80 rows over 78 independent propositions — 2 duplicated proposition(s): [['eg-0093', 'eg-0367'], ['eg-0194', 'eg-0251']]. Against a bar of 0.95, the minimum passing score is 76/80 = 0.95 on rows and 75/78 = 0.9615 on independent propositions. The bar is expressible on this census.

## Bars (stated before the run; config defaults)

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9884 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9827 → **PASS**
- `contradiction_precision_bar` = 0.70 on `contradiction_precision`: measured 0.8875 → **PASS**
- `contradiction_recall_bar` = 0.95 on `contradiction_recall`: measured 0.8875 → **FAIL**

Granularity at this gold size:
- 173 gold-entailed pairs: one false accept bounds entailed-precision at 173/174 ≈ 0.994; one false reject puts recall at 172/173 ≈ 0.994.
- 80 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 80/81 ≈ 0.988.

## Bars on Rule B's second population

LABELLING.md's contacted-pairs rule requires every barred metric on **both** populations, with the gate verdict required to hold on both. The pairs above are all 402 live ones, of which 226 were contacted before; these are the 176 pairs (`eg-0242`+) not contacted before the grown-gold attempt.

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9857 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9583 → **PASS**
- `contradiction_precision_bar` = 0.70 on `contradiction_precision`: measured 0.9189 → **PASS**
- `contradiction_recall_bar` = 0.95 on `contradiction_recall`: measured 0.8500 → **FAIL**

Granularity on this subset — **read this before the numbers above**:
- 72 gold-entailed pairs: one false accept bounds entailed-precision at 72/73 ≈ 0.986; one false reject puts recall at 71/72 ≈ 0.986.
- 40 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 40/41 ≈ 0.976.
  A bar can only be met at a value the lattice contains. T2.110 sized the *pooled* contradicted census at 80 so that 76/80 = 0.9500 sits exactly on `contradiction_recall_bar`; that analysis was never run for this subset, whose smaller census may place the bar between two attainable values and so enforce a stricter number than the one stated. Where it does, the subset verdict is evidence about the census, not only about the judge.

## Census independence — read with the recall verdict

- 80 contradicted rows over 78 independent propositions (2 duplicated: [['eg-0093', 'eg-0367'], ['eg-0194', 'eg-0251']]).
- Measured contradiction-recall 0.8875 is 71/80 on rows. If the judge caught every correlated pair, the independent reading is at worst 69/78 = 0.8846.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 71 | 0 | 9 | 0 |
| entailed | 0 | 170 | 3 | 0 |
| unsupported | 9 | 2 | 138 | 0 |

- invalid responses: 0/402
- majority-class floor (three-way): 0.430

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 48 | 46 | 0.958 |
| overreach | 61 | 60 | 0.984 |
| paraphrase | 61 | 60 | 0.984 |
| temporal | 57 | 47 | 0.825 |
| unrelated | 42 | 42 | 1.000 |
| value-swap | 42 | 34 | 0.810 |
| verbatim | 41 | 41 | 1.000 |
| weakening | 50 | 49 | 0.980 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 402 calls, 196843 tokens → **489.7 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 4088 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=0 powered=False p50=None p95=None | cache n=9 powered=False p50=None p95=None
judge_call: live n=64 powered=True p50=3.3357950430363417 p95=7.208541227504611 | cache n=338 powered=True p50=0.00011937133967876434 p95=0.00015349127352237701
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.7,
      "measured": 0.8875,
      "metric": "contradiction_precision",
      "passed": true
    },
    "contradiction_recall_bar": {
      "bar": 0.95,
      "measured": 0.8875,
      "metric": "contradiction_recall",
      "passed": false
    },
    "groundedness_gate_precision_bar": {
      "bar": 0.95,
      "measured": 0.9883720930232558,
      "metric": "entailed_precision",
      "passed": true
    },
    "groundedness_gate_recall_bar": {
      "bar": 0.9,
      "measured": 0.9826589595375722,
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
    "l2_fact_pairs": 238,
    "live_pairs": 402,
    "reasons": [
      "composition: 402 live pairs; l2-fact: 238/402; author-labelled: 0/402"
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
  "gold_sha256": "6eadba737b8cd8ee216d595f8e617f12d51bdb636ccc39fee76c0bcb79882b2e",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 0,
      "calls": 402,
      "completion_tokens": 59974,
      "prompt_tokens": 136869,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "fd39e7b2c47fa375",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 71,
        "unsupported": 9
      },
      "entailed": {
        "entailed": 170,
        "unsupported": 3
      },
      "unsupported": {
        "contradicted": 9,
        "entailed": 2,
        "unsupported": 138
      }
    },
    "contradiction_precision": 0.8875,
    "contradiction_recall": 0.8875,
    "entailed_precision": 0.9883720930232558,
    "entailed_recall": 0.9826589595375722,
    "invalid": 0,
    "majority_class_floor": 0.43034825870646765,
    "n_pairs": 402,
    "per_slice": {
      "direction": {
        "accuracy": 0.9583333333333334,
        "correct": 46,
        "n": 48
      },
      "overreach": {
        "accuracy": 0.9836065573770492,
        "correct": 60,
        "n": 61
      },
      "paraphrase": {
        "accuracy": 0.9836065573770492,
        "correct": 60,
        "n": 61
      },
      "temporal": {
        "accuracy": 0.8245614035087719,
        "correct": 47,
        "n": 57
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 42,
        "n": 42
      },
      "value-swap": {
        "accuracy": 0.8095238095238095,
        "correct": 34,
        "n": 42
      },
      "verbatim": {
        "accuracy": 1.0,
        "correct": 41,
        "n": 41
      },
      "weakening": {
        "accuracy": 0.98,
        "correct": 49,
        "n": 50
      }
    }
  }
}
```
