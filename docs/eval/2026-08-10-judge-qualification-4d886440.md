# Judge qualification — 2026-08-10

- run id: `b26c10e8-81ac-47f1-811b-115198e90481` (recorded 2026-08-10T06:55:07.155870+00:00)
- git sha: `26b0930e04f56f43496005b138b1ae677c131951`
- judge identity: `4d886440a646f176` (model `deepseek-v4-flash`, prompt v1, prompt_sha `f99151e4add69b31`)
- judge invocation: `base_url=https://api.deepseek.com/v1` `api_kind=deepseek` `params={"max_tokens": 256, "temperature": 0, "thinking": {"type": "disabled"}}` `dimensions=None` `reasoning=False`
- gold: version 1, sha256 `98fc4b49f787c29c91cd720115735a64265d09c486bd350c88a780cacf4c1ff7`, 402 pairs scored
- gold_touching_attempts: 1 — counts gold CONTACTS for this gold_sha256 across all judge identities, including warm cache replays (a verification rerun increments it on one live pass); live-vs-replay per contact is reconstructible from each scored row's twin. Resets only when the gold file itself changes (T2.54 growth).

## Bars (stated before the run; config defaults)

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 0.9938 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9249 → **PASS**
- `contradiction_precision_bar` = 0.70 on `contradiction_precision`: measured 0.8065 → **PASS**
- `contradiction_recall_bar` = 0.95 on `contradiction_recall`: measured 0.9375 → **FAIL**

Granularity at this gold size:
- 173 gold-entailed pairs: one false accept bounds entailed-precision at 173/174 ≈ 0.994; one false reject puts recall at 172/173 ≈ 0.994.
- 80 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 80/81 ≈ 0.988.

## Bars on Rule B's second population

LABELLING.md's contacted-pairs rule requires every barred metric on **both** populations, with the gate verdict required to hold on both. The pairs above are all 402 live ones, of which 226 were contacted before; these are the 176 pairs (`eg-0242`+) not contacted before the grown-gold attempt.

- `groundedness_gate_precision_bar` = 0.95 on `entailed_precision`: measured 1.0000 → **PASS**
- `groundedness_gate_recall_bar` = 0.90 on `entailed_recall`: measured 0.9167 → **PASS**
- `contradiction_precision_bar` = 0.70 on `contradiction_precision`: measured 0.8837 → **PASS**
- `contradiction_recall_bar` = 0.95 on `contradiction_recall`: measured 0.9500 → **PASS**

Granularity on this subset — **read this before the numbers above**:
- 72 gold-entailed pairs: one false accept bounds entailed-precision at 72/73 ≈ 0.986; one false reject puts recall at 71/72 ≈ 0.986.
- 40 gold-contradicted pairs: one manufactured contradiction bounds contradiction-precision at 40/41 ≈ 0.976.
  A bar can only be met at a value the lattice contains. T2.110 sized the *pooled* contradicted census at 80 so that 76/80 = 0.9500 sits exactly on `contradiction_recall_bar`; that analysis was never run for this subset, whose smaller census may place the bar between two attainable values and so enforce a stricter number than the one stated. Where it does, the subset verdict is evidence about the census, not only about the judge.

## Confusion (gold rows × predicted columns)

| gold \ predicted | contradicted | entailed | unsupported | invalid |
|---|---|---|---|---|
| contradicted | 75 | 1 | 4 | 0 |
| entailed | 0 | 160 | 13 | 0 |
| unsupported | 18 | 0 | 131 | 0 |

- invalid responses: 0/402
- majority-class floor (three-way): 0.430

## Per-slice accuracy (three-way exact match)

| slice | n | correct | accuracy |
|---|---|---|---|
| direction | 48 | 31 | 0.646 |
| overreach | 61 | 60 | 0.984 |
| paraphrase | 61 | 60 | 0.984 |
| temporal | 57 | 53 | 0.930 |
| unrelated | 42 | 42 | 1.000 |
| value-swap | 42 | 41 | 0.976 |
| verbatim | 41 | 41 | 1.000 |
| weakening | 50 | 38 | 0.760 |

## Cost twin (doc 11 §6 Tier-C bound)

- gold pass: 402 calls, 160281 tokens → **398.7 tokens/claim** (the per-claim bound; excludes the fixture stage)
- fixture stage (plumbing overhead, 9 pairs): 9 calls, 3521 tokens

Latency by channel (live/cache populations, wall-clock — expected to vary run to run):

```
fixture_call: live n=0 powered=False p50=None p95=None | cache n=9 powered=False p50=None p95=None
judge_call: live n=174 powered=True p50=0.8933883830904961 p95=1.1338116843253374 | cache n=228 powered=True p50=3.187917172908783e-05 p95=4.6117231249809265e-05
```

## Reproducibility

Two consecutive runs on an unchanged tree with a warm cache must reproduce this block byte-for-byte. Token figures are serving-invariant totals (live + cache_known) so a live-vs-warm diff cannot fail on bucket shift; latency, timestamps and the attempt counter are excluded on purpose.

```json
{
  "bar_results": {
    "contradiction_precision_bar": {
      "bar": 0.7,
      "measured": 0.8064516129032258,
      "metric": "contradiction_precision",
      "passed": true
    },
    "contradiction_recall_bar": {
      "bar": 0.95,
      "measured": 0.9375,
      "metric": "contradiction_recall",
      "passed": false
    },
    "groundedness_gate_precision_bar": {
      "bar": 0.95,
      "measured": 0.9937888198757764,
      "metric": "entailed_precision",
      "passed": true
    },
    "groundedness_gate_recall_bar": {
      "bar": 0.9,
      "measured": 0.9248554913294798,
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
      "cached_prompt_tokens": 2048,
      "calls": 9,
      "completion_tokens": 311,
      "prompt_tokens": 3210,
      "unknown_calls": 0
    }
  },
  "gold_sha256": "98fc4b49f787c29c91cd720115735a64265d09c486bd350c88a780cacf4c1ff7",
  "gold_tokens": {
    "verification": {
      "cached_prompt_tokens": 102656,
      "calls": 402,
      "completion_tokens": 15517,
      "prompt_tokens": 144764,
      "unknown_calls": 0
    }
  },
  "gold_version": 1,
  "identity_hash": "4d886440a646f176",
  "n_fixtures": 9,
  "score": {
    "confusion": {
      "contradicted": {
        "contradicted": 75,
        "entailed": 1,
        "unsupported": 4
      },
      "entailed": {
        "entailed": 160,
        "unsupported": 13
      },
      "unsupported": {
        "contradicted": 18,
        "unsupported": 131
      }
    },
    "contradiction_precision": 0.8064516129032258,
    "contradiction_recall": 0.9375,
    "entailed_precision": 0.9937888198757764,
    "entailed_recall": 0.9248554913294798,
    "invalid": 0,
    "majority_class_floor": 0.43034825870646765,
    "n_pairs": 402,
    "per_slice": {
      "direction": {
        "accuracy": 0.6458333333333334,
        "correct": 31,
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
        "accuracy": 0.9298245614035088,
        "correct": 53,
        "n": 57
      },
      "unrelated": {
        "accuracy": 1.0,
        "correct": 42,
        "n": 42
      },
      "value-swap": {
        "accuracy": 0.9761904761904762,
        "correct": 41,
        "n": 42
      },
      "verbatim": {
        "accuracy": 1.0,
        "correct": 41,
        "n": 41
      },
      "weakening": {
        "accuracy": 0.76,
        "correct": 38,
        "n": 50
      }
    }
  }
}
```
