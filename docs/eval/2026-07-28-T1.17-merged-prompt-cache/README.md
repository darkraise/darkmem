# 2026-07-28 — T1.17 Pass B cache (merged gate, stripped prompt)

The 36 raw extraction outputs behind the F1 merge gate as of T1.17, plus
`manifest.json`. This is the **current** generation: `run_bench.py --algo-only` replays it
and nothing else.

| | |
|---|---|
| Gate | `merged` (`with_classification=True`) — the default shipping configuration |
| System prompt | `sha256[:16] = f59a62d1be7273a8` (the stripped prompt) |
| Schema | `sha256[:16] = 34e62626caafa8c8` (9-type `MEMORY_TYPES`) |
| Model | `deepseek-v4-flash` |
| `system_fingerprint` | `fp_8b330d02d0_prod0820_fp8_kvcache_20260402` on all 36 calls |
| Recorded | 2026-07-28, 36 live calls (26 `gold.json` + 10 `gold_heldout.json`) |

## Restoring a red F1 gate in another worktree

`backend/scripts/extraction_bench/.cache/` is machine-local and gitignored, so every other
worktree goes red at the F1 gate the moment it picks up T1.17's prompt change. To re-green:

```bash
cp docs/eval/2026-07-28-T1.17-merged-prompt-cache/*.json \
   backend/scripts/extraction_bench/.cache/
```

Copy `manifest.json` too — `--algo-only` refuses to replay a cache whose manifest does not
describe the current assembly, and exits with the mismatching field named. That refusal is
the guard, not a bug: it is what stops the gate replaying outputs produced by a request the
code would no longer send.

## Cache key

Entries are keyed on `sha256` of the **whole assembled request** (system message plus user
message), truncated to 16 hex characters. The user message carries the schema string, so a
taxonomy widening or a gate flip now changes the key. The previous key covered the system
message only, which is why the 2026-07-26 archive kept being served after T1.23 widened
`MEMORY_TYPES` from 7 to 9.

Each entry is `{"raw": …, "meta": {"model", "usage", "system_fingerprint", "recorded_at"}}`.
The reader also accepts a bare raw dict, which is the pre-T1.17 shape.

## Earlier generations

- `docs/eval/2026-07-28-T1.17-passA-cache/` — Pass A, same gate and model, **unchanged**
  prompt (`775ca7c45ed9a06a`). The other arm of the decomposition.
- `docs/eval/2026-07-26-T0.05-extraction-baseline-cache/` — the T0.05 baseline. Replayable
  only at a commit **before** T1.17: both the key definition and the prompt changed.
