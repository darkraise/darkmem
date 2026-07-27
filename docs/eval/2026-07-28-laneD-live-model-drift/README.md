# 2026-07-28 — the T0.05 extraction cache no longer reproduces live

Evidence for the gate-ledger risk recorded on 2026-07-26 as *"'same model' is asserted, not
verifiable"*. It is now verified, and the answer is that the model changed.

Re-ran all 36 `gold.json` + `gold_heldout.json` contents live against
`deepseek-v4-flash`, with the pinned extraction system prompt (sha256[:16]
`775ca7c45ed9a06a`), the same content-derived seed, and the same purpose config
`benchlib.run_smoke.purpose_config_specs` seeds (`params={}`). The committed cache under
`backend/scripts/extraction_bench/.cache/` was **not** modified.

## Result

- **32 of 36** raw outputs differ from the cached ones.
- **15 of 36 (42%)** differ *semantically*, i.e. after `clean_extraction` the entity and
  relation key sets the scorer consumes are not the same:
  `e3 e8 e13 e14 e15 e20 e22 e23 e26 h3 h5 h7 h8 h9 h10`.

Drift runs in both directions — `h3` loses three entities and six relations, `h8` gains an
entity the cache missed. This is a different model, not a uniformly worse one.

## It is drift, not sampling noise

- Same content + same seed repeated 3× (`h3`, `h8`): byte-identical each time, and each time
  different from the cache in the same way.
- A `temperature=0` control on the differing items: 4 of 5 still differ, so the divergence is
  not explained by the baseline having been recorded at a different temperature.

## Served-model metadata (recorded for the first time)

The 2026-07-26 Tier-2 amendment asked the G-B runner to capture served-model metadata,
because the cache stores parsed JSON only. It is capturable:

- `model`: `deepseek-v4-flash` — the alias is unchanged and therefore uninformative.
- `system_fingerprint`: `fp_8b330d02d0_prod0820_fp8_kvcache_20260402` — **identical across all
  159 live calls made this day.** Future re-measurements should pin and compare this string;
  a change in it is positive proof of a serving-stack swap.

Per-call model, fingerprint and token usage: `live-raw/_meta.json`.

## Three arms, because a naive parity check confounds three variables

The recorded T0.05 numbers no longer reproduce from the **cache** either — the Phase-1
deterministic passes have improved them since G-A. Isolating the two effects:

| Arm | Algorithm | Raw source | gold ent_nt / ent_n / rel_full / rel_pair | held-out |
|---|---|---|---|---|
| A — recorded T0.05 / G-A | 2026-07-26 | cache | 0.925 / 0.955 / 0.865 / 0.892 | 0.893 / 0.929 / 0.667 / 0.667 |
| B — current algo, cached raw | `dbde017` | cache | 0.940 / 0.970 / 0.895 / 0.921 | 0.949 / 0.983 / 0.872 / 0.872 |
| C — current algo, live raw | `dbde017` | live | 0.925 / 0.970 / 0.921 / 0.921 | 0.862 / 0.931 / 0.765 / 0.765 |

- **B − A** is the deterministic passes' gain: gold `+0.015/+0.015/+0.030/+0.029`,
  held-out `+0.056/+0.054/+0.205/+0.205`.
- **C − B** is the isolated model drift: gold `−0.015/0.000/+0.026/0.000`,
  held-out **`−0.087/−0.052/−0.107/−0.107`**.

Drift is roughly neutral on `gold.json` and materially negative on `gold_heldout.json`.

## Against the stated G-B floors: all eight cells still pass

Arm C clears every floor (gold 0.881/0.910/0.784/0.811, held-out 0.786/0.821/0.485/0.485).
Two things must be read alongside that pass:

1. Against baseline A, one cell declines — held-out entity name+type, `0.893 → 0.862`. At that
   cell's flip cost of `2/56 = 0.0357`, model drift alone has spent **0.87 of the tolerance's
   1.0-flip "silent vendor-side model update" allowance**, measured once.
2. **The deterministic passes are masking the drift.** On held-out relations the algorithm
   gained `+0.205` while the model lost `−0.107`, netting `+0.098` against A. A G-B parity
   check measured against A will pass partly because T1.24's gains are paying for model
   regression, and it will not show that.

Suggested consequence for G-B (owner's call): report the C-vs-B delta alongside C-vs-A, and
pin `system_fingerprint` in the ledger row. Otherwise "parity held" is not a statement about
the prompt change, which is what G-B exists to measure.

## Also observed: the per-content seed is not bit-deterministic

`e8` returned three distinct raw bodies across three identical same-seed requests, differing
only in the relation `weight` (`0.5` / `0.8` / `0.7`); entity and relation structure was
stable. The scorer ignores `weight`, so no number moves — but CLAUDE.md's Reproducibility
section claims the seed makes the same input produce the same JSON, and against today's
DeepSeek that holds for structure and not for numeric fields.

## Files

- `live-raw/` — the 36 live extraction outputs, keyed by the bench's own
  `sha256(content + "\0" + system_prompt)[:16]`, plus `_meta.json` (model, fingerprint, usage).
- `armB-cached-raw-current-algo.txt` — `run_bench.py --algo-only` over the committed cache.
- `armC-live-raw-current-algo.txt` — the same scorer over `live-raw/`.

Arm A is `docs/eval/2026-07-27-T0.17-ga-evidence/f1-gold.txt` and `f1-heldout.txt`.
