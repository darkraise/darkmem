# 2026-07-28 — T1.17 Pass A cache (merged gate, **unchanged** prompt)

The 36 raw extraction outputs recorded live with the extraction system prompt still
byte-identical to T0.05's, so the merged classification fields are the only thing that
changed relative to lane D's arm C. Archived as gate evidence, not as a replay target:
`--algo-only` will refuse this generation once the prompt is stripped, which is correct.

| | |
|---|---|
| Gate | `merged` (`with_classification=True`) |
| System prompt | `sha256[:16] = 775ca7c45ed9a06a` (unchanged from T0.05) |
| Schema | `sha256[:16] = 34e62626caafa8c8` (9-type `MEMORY_TYPES`) |
| Model | `deepseek-v4-flash` |
| `system_fingerprint` | `fp_8b330d02d0_prod0820_fp8_kvcache_20260402` on all 36 calls |
| Recorded | 2026-07-28, 36 live calls |

## Why it exists

G-B's evidence is a decomposition, not a single number. Pass A isolates the merged
classification fields (against lane D's arm C, same day, same schema width, same prompt);
Pass B minus Pass A isolates the prompt strip. Keeping the raws rather than only the scored
cells means both arms can be re-scored against a future pass chain for free.

To score this generation, restore it into `backend/scripts/extraction_bench/.cache/` at a
commit whose prompt fingerprint is `775ca7c45ed9a06a`.
