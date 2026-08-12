# The verdicts-directory leak — identification and removal (T2.122)

Audit performed 2026-08-12 against
`backend/scripts/benchlib/entailment/verdicts/` in the main checkout, before
any file in it was deleted. This document is the auditable record the T2.122
"done when" requires: every file removed, with its filename, judge identity,
gold sha256, pair count, and the entailed-precision / contradiction-recall
that file's own recorded per-pair verdicts score against its own recorded
gold verdicts (recomputed directly from each file's `verdicts: {pid: {gold,
judged}}` block — no external gold file needed).

## Scope correction to the brief

The dispatch brief (`docs/planning/briefs/2026-08-12-t2.122-verdicts-directory-leak.md`)
and the task text measured **80 files at the top level of the directory, 79
residue**. A full recursive listing done for this audit found a **second,
previously undocumented population**: a stray subdirectory
`entailment/verdicts/verdicts/` holding **16 more residue files**, all dated
2026-08-10, all under the same deepseek identity `4d886440a646f176`. Its
directory mtime (19:36:03 on 2026-08-10) sits exactly between two top-level
files' timestamps, consistent with an earlier, undocumented, incomplete
attempt to quarantine residue by hand that was never finished and never
recorded anywhere. This is a Tier-1 amendment (task-local: same defect
category, a more complete count) — the epic file's amendment log records it.

**Total: 96 files. 1 genuine. 95 residue** (79 top-level + 16 nested), not 80/79.

## The genuine artifact

| File | Identity | Gold sha256 | Pairs | Entailed precision | Contradiction recall | sha256 |
|---|---|---|---|---|---|---|
| `2026-08-12-fd39e7b2-6eadba73.json` | `fd39e7b2c47fa375` (`gpt-5.5`) | `6eadba737b8cd8ee216d595f8e617f12d51bdb636ccc39fee76c0bcb79882b2e` | 402 | 0.9884 | 0.8875 | `80ac5451c080b68649ea8524a3387b126dd30f96a4f69625acf2fb8252281962` |

These numbers reproduce `docs/eval/2026-08-12-judge-qualification-fd39e7b2.md`
exactly (entailed precision 0.9884, contradiction recall 0.8875), which is
the authentication test R2 requires before this file may be re-scored to
mint the entailment role's record. This file was **not** deleted; its
sha256 is recorded here, in that eval report, and in `gate-ledger.md`, all
outside the artifact itself, per the "done when" requirement.

## The 95 residue files — removed, identified before deletion

Every metric combination found among the residue is garbage relative to the
genuine artifact and to deepseek's own published entailment numbers
(entailed precision 0.9938): either a trivial 1.0/1.0 (200-pair files,
matching the `eligible_gold` 200-pair test fixture scored by a stub that
always answers with the gold's own verdict — the shape used by gate-mode
rehearsal tests) or a near-random ~0.37-0.41 / ~0.31-0.35 (402-pair files,
matching the real, current gold scored by a round-robin stub with no
knowledge of the gold's actual verdicts — the shape used by the happy-path
and latency-channel tests). All 95 carry the real deepseek identity
`4d886440a646f176`, and several carry the real gold's current sha256
(`6eadba73...`) or recent prior shas — i.e. exactly what a genuine deepseek
run on this gold would look like from the filename alone.

### Top-level (79 files)

| File | Identity | Gold sha256 | Pairs | Entailed precision | Contradiction recall | mtime |
|---|---|---|---|---|---|---|
| `2026-08-10-4d886440-08edea81.json` | `4d886440a646f176` | `08edea8130ccb63c33c669c5aa843f10c98e1d759684ef3ddd593c1c82d96461` | 200 | 1.0 | 1.0 | 2026-08-10T19:53:57.941724 |
| `2026-08-10-4d886440-12ce6b91.json` | `4d886440a646f176` | `12ce6b911156f147372d876e50e3f2c826a910e4ad4952a6144948d007def57b` | 402 | 0.4104 | 0.35 | 2026-08-10T20:00:12.511231 |
| `2026-08-10-4d886440-1758513e.json` | `4d886440a646f176` | `1758513e3b0111f95b2bc76f7194d54e37e0ff77c14e96aea69da5e1e4afde1d` | 200 | 1.0 | 1.0 | 2026-08-10T21:56:38.981390 |
| `2026-08-10-4d886440-18127851.json` | `4d886440a646f176` | `181278513ae3cf370b61f94ee6d4e6d06961e078642eaa8084dbcc160d7d8a70` | 200 | 1.0 | 1.0 | 2026-08-10T20:06:22.222152 |
| `2026-08-10-4d886440-1845e589.json` | `4d886440a646f176` | `1845e5895905d274308cfeb3bf15f1e7942d0c914dee6f9065f70e28322d6a10` | 200 | 1.0 | 1.0 | 2026-08-10T20:00:06.351409 |
| `2026-08-10-4d886440-19fe6699.json` | `4d886440a646f176` | `19fe6699e837242ee47a4016a9756ad04e35c493d26bc1496ac68742360f12f5` | 200 | 1.0 | 1.0 | 2026-08-10T19:50:15.981039 |
| `2026-08-10-4d886440-284c0077.json` | `4d886440a646f176` | `284c0077767f418435a037b6a3aa95c9f32530264448396569b2965624fb7c3c` | 200 | 1.0 | 1.0 | 2026-08-10T22:39:56.737528 |
| `2026-08-10-4d886440-2c068125.json` | `4d886440a646f176` | `2c068125291e7aa1c100603ede2f781086e88dd05f4e56e73229fab7aa475f79` | 200 | 1.0 | 1.0 | 2026-08-10T22:20:07.170755 |
| `2026-08-10-4d886440-39ac2a94.json` | `4d886440a646f176` | `39ac2a94d3a23a5cb86c8b9a477387f14500227ac849560393bbc24c770ac51d` | 200 | 1.0 | 1.0 | 2026-08-10T20:08:39.791044 |
| `2026-08-10-4d886440-4b370655.json` | `4d886440a646f176` | `4b370655791a8ff8cfa385f59da367f43bb5f4fa3bafa4f4f118ab12adb7aef2` | 200 | 1.0 | 1.0 | 2026-08-10T22:29:15.277357 |
| `2026-08-10-4d886440-4b82737e.json` | `4d886440a646f176` | `4b82737efbdb4d61ef4a5ea25877b8e560b5ede6239a88c7149fb78ba9316b92` | 200 | 1.0 | 1.0 | 2026-08-10T20:00:12.495997 |
| `2026-08-10-4d886440-4bc1b585.json` | `4d886440a646f176` | `4bc1b585abc6fd706549048d7777f299d115ab5e2627b6a564bde120fe48b5de` | 200 | 1.0 | 1.0 | 2026-08-10T20:02:02.235469 |
| `2026-08-10-4d886440-7b22adc2.json` | `4d886440a646f176` | `7b22adc2d8e93c4a94c90475ce0e39fcb41558834c5a154913b29688a5b8b66d` | 200 | 1.0 | 1.0 | 2026-08-10T21:39:11.851754 |
| `2026-08-10-4d886440-7cd33390.json` | `4d886440a646f176` | `7cd3339055a15c1fa95ba959c55419c1e1446de1df5fcd94f34a1d8a7e21d89c` | 200 | 1.0 | 1.0 | 2026-08-10T22:57:54.902487 |
| `2026-08-10-4d886440-81e48502.json` | `4d886440a646f176` | `81e485022f92f43b408afecd97abbe8f9da57918d4614e6cedb12e298199ddc0` | 200 | 1.0 | 1.0 | 2026-08-10T23:59:37.855171 |
| `2026-08-10-4d886440-87bb5454.json` | `4d886440a646f176` | `87bb54540ede269d871ca6c1e85e0a47205e8373514b51a602062c839ecf0449` | 200 | 1.0 | 1.0 | 2026-08-10T23:52:42.671892 |
| `2026-08-10-4d886440-8b660c74.json` | `4d886440a646f176` | `8b660c745c79eae7b333f8ca3f8f32c3574cf805432aa55ec429b9bd1b4d1527` | 402 | 0.4104 | 0.35 | 2026-08-10T19:55:03.577087 |
| `2026-08-10-4d886440-98fc4b49.json` | `4d886440a646f176` | `98fc4b49f787c29c91cd720115735a64265d09c486bd350c88a780cacf4c1ff7` | 402 | 0.3731 | 0.3125 | 2026-08-10T23:59:37.871795 |
| `2026-08-10-4d886440-b0ac4840.json` | `4d886440a646f176` | `b0ac48407f78dfb6ca8adbfdf0f8688e2153add741516ba694dd885f6f3b32b6` | 200 | 1.0 | 1.0 | 2026-08-10T19:52:18.126293 |
| `2026-08-10-4d886440-b369fd83.json` | `4d886440a646f176` | `b369fd835d52ee4800ed3d3cd8efa0954254913b7da69ebfbfd2c94cb04a94d2` | 200 | 1.0 | 1.0 | 2026-08-10T20:16:36.793862 |
| `2026-08-10-4d886440-bfed780b.json` | `4d886440a646f176` | `bfed780b8e007bdcec1aeaee4131d94c00670780bbaf7e29ed5b662a5207a939` | 200 | 1.0 | 1.0 | 2026-08-10T20:04:02.580569 |
| `2026-08-10-4d886440-def6801b.json` | `4d886440a646f176` | `def6801ba1f11464141a7a5c3c85d5af804999414ef10cf0171987ba8025e052` | 200 | 1.0 | 1.0 | 2026-08-10T19:55:03.559556 |
| `2026-08-10-4d886440-e42db1e9.json` | `4d886440a646f176` | `e42db1e9a12d6df1de352db41ed6db472af2d3133e0324da766f686669a123b7` | 200 | 1.0 | 1.0 | 2026-08-10T23:20:46.768100 |
| `2026-08-10-4d886440-eaa2e695.json` | `4d886440a646f176` | `eaa2e6952d47c29a4091d0fc4d8bde94b07e6105715c403986bb899094e164db` | 200 | 1.0 | 1.0 | 2026-08-10T19:53:39.158992 |
| `2026-08-11-4d886440-15f09634.json` | `4d886440a646f176` | `15f09634ceaedd3fd0006ad19638ad12252317e0483df08e5924d9da6cdb29fc` | 200 | 1.0 | 1.0 | 2026-08-11T00:46:56.077487 |
| `2026-08-11-4d886440-2ec40f5d.json` | `4d886440a646f176` | `2ec40f5d790efaa6ada514cb14ad34e31e803e82b6d7dcdcaf31d9d1ccd35e6c` | 200 | 1.0 | 1.0 | 2026-08-11T20:01:29.492316 |
| `2026-08-11-4d886440-559c659b.json` | `4d886440a646f176` | `559c659b5d71504400b76d37d194fd222f3ecb86a0fd9e05448fe8298aeda837` | 200 | 1.0 | 1.0 | 2026-08-11T21:41:57.232487 |
| `2026-08-11-4d886440-61d8bac5.json` | `4d886440a646f176` | `61d8bac5326739ab09c67e06484a25bd556a85f076e35a09acf0f1f65eb48e58` | 200 | 1.0 | 1.0 | 2026-08-11T01:07:37.701419 |
| `2026-08-11-4d886440-73b3e8d0.json` | `4d886440a646f176` | `73b3e8d06ab3addadb193640259bce0f4523b05ac44cfc719c04585411c893d2` | 200 | 1.0 | 1.0 | 2026-08-11T11:34:28.973911 |
| `2026-08-11-4d886440-7977e2d2.json` | `4d886440a646f176` | `7977e2d2183dc6175f020b23bef3a3b49cbda146ac0fdb3bb076a6886fa6963c` | 200 | 1.0 | 1.0 | 2026-08-11T10:48:11.713091 |
| `2026-08-11-4d886440-7ec862cf.json` | `4d886440a646f176` | `7ec862cfa4933a731c9718e3485b7a2d035c8446ce3e7c71bad052fcea9a929f` | 200 | 1.0 | 1.0 | 2026-08-11T11:01:20.461352 |
| `2026-08-11-4d886440-7fcd9e40.json` | `4d886440a646f176` | `7fcd9e4030a4f3bdde6765cd5be1c8e3a5a25a1813c49f18e4244f11c180f906` | 200 | 1.0 | 1.0 | 2026-08-11T22:14:56.832183 |
| `2026-08-11-4d886440-83c878e4.json` | `4d886440a646f176` | `83c878e4a602f3bce9f2232d388e65a702fda675951e7b76e5c038798ae9dca0` | 200 | 1.0 | 1.0 | 2026-08-11T00:17:34.848110 |
| `2026-08-11-4d886440-85a13d23.json` | `4d886440a646f176` | `85a13d23f557e83edaa07bc5dd4ad5a0d7cb24401c1e7a2ce30644bf563e24db` | 200 | 1.0 | 1.0 | 2026-08-11T21:35:33.320026 |
| `2026-08-11-4d886440-93cbfc0f.json` | `4d886440a646f176` | `93cbfc0fd8af4074ba316d857c30ce03a31cb21e1dff5b919c80f12a5455c95a` | 200 | 1.0 | 1.0 | 2026-08-11T10:19:35.652490 |
| `2026-08-11-4d886440-951eba0e.json` | `4d886440a646f176` | `951eba0e9aebb0755fc0a88f78cba00c0a67580f63011333bf4b19379374f3e8` | 200 | 1.0 | 1.0 | 2026-08-11T13:42:02.068740 |
| `2026-08-11-4d886440-98fc4b49.json` | `4d886440a646f176` | `98fc4b49f787c29c91cd720115735a64265d09c486bd350c88a780cacf4c1ff7` | 402 | 0.3731 | 0.3125 | 2026-08-11T22:14:56.848682 |
| `2026-08-11-4d886440-aa6ae460.json` | `4d886440a646f176` | `aa6ae46011d3f6863e4c0e9cf039be05ef1e3733ffefdba58acdf6f4bb698034` | 200 | 1.0 | 1.0 | 2026-08-11T14:59:10.305250 |
| `2026-08-11-4d886440-b5c3fcc2.json` | `4d886440a646f176` | `b5c3fcc21a77ae33d9ee1a5b3ff944a3f34d476209844911ddb420bca32502e2` | 200 | 1.0 | 1.0 | 2026-08-11T11:21:24.068469 |
| `2026-08-11-4d886440-d6f90562.json` | `4d886440a646f176` | `d6f9056250d5932a035135ba757e26c1156aa8ad2906e9e601923c1da2e00bf7` | 200 | 1.0 | 1.0 | 2026-08-11T21:32:17.491523 |
| `2026-08-11-4d886440-d7cd01e3.json` | `4d886440a646f176` | `d7cd01e3c56eef585c85fce1bb5b5fd08a918b23589fbe0ae62442f64bdb8ba8` | 200 | 1.0 | 1.0 | 2026-08-11T15:09:57.531097 |
| `2026-08-11-4d886440-deaed738.json` | `4d886440a646f176` | `deaed7383b1c47c67ed22c12eb9962476e58134e1a09b0d2aade56823d13d594` | 200 | 1.0 | 1.0 | 2026-08-11T13:15:24.740297 |
| `2026-08-11-4d886440-fa487396.json` | `4d886440a646f176` | `fa487396eb403bee5b09e138e9e2ab5c17fb2f3ffdc209d0e886758f5a33160c` | 200 | 1.0 | 1.0 | 2026-08-11T21:28:27.713590 |
| `2026-08-11-4d886440-fdd57df2.json` | `4d886440a646f176` | `fdd57df2c7f5aae0eb490dce5c7260bcf84a95299a31a5b68e4a5e9cfe4784ac` | 200 | 1.0 | 1.0 | 2026-08-11T21:29:41.988225 |
| `2026-08-12-4d886440-0b950717.json` | `4d886440a646f176` | `0b95071789b175c4122519be8bd73f5f65f81f01d86c69771dd46b127ae561ef` | 200 | 1.0 | 1.0 | 2026-08-12T14:29:34.213570 |
| `2026-08-12-4d886440-1478a953.json` | `4d886440a646f176` | `1478a95349d124bf377087e8978ae82bcf05654775cb547f511c703457eda922` | 200 | 1.0 | 1.0 | 2026-08-12T12:12:52.121636 |
| `2026-08-12-4d886440-1b5bba20.json` | `4d886440a646f176` | `1b5bba20546d56c91275e9acaa5b4da627703f9e40b93f4fafcb91251a07902a` | 200 | 1.0 | 1.0 | 2026-08-12T11:50:58.421227 |
| `2026-08-12-4d886440-1ba20893.json` | `4d886440a646f176` | `1ba20893b42dd1d2425c98bf7c93a59e7b44060920392e5c0c758f85a4fe7b6b` | 200 | 1.0 | 1.0 | 2026-08-12T10:52:18.568571 |
| `2026-08-12-4d886440-1dbfd15a.json` | `4d886440a646f176` | `1dbfd15ad9f9a69b29704688b5ad48241949b711b8b9528473f5fbee041d63e5` | 200 | 1.0 | 1.0 | 2026-08-12T12:55:42.935432 |
| `2026-08-12-4d886440-231a7ae2.json` | `4d886440a646f176` | `231a7ae24f6bc2585736cb1e7327e52b94d3b691085d9183ea1390f3a3c037f9` | 200 | 1.0 | 1.0 | 2026-08-12T00:47:38.378136 |
| `2026-08-12-4d886440-2c0d22a6.json` | `4d886440a646f176` | `2c0d22a6523be6198befa4341b04a48ab1eebbbfc8792de879c6c2b707096f06` | 200 | 1.0 | 1.0 | 2026-08-12T12:57:50.329863 |
| `2026-08-12-4d886440-3620565a.json` | `4d886440a646f176` | `3620565a531d5fd29545d02239c54428cf3cc263df1cfdd1ae5d5f2d0a77681a` | 200 | 1.0 | 1.0 | 2026-08-12T11:51:07.814626 |
| `2026-08-12-4d886440-36dc3e83.json` | `4d886440a646f176` | `36dc3e838b9117e09ec44f16767ece46edcf61686464bac9eaea60934ae86117` | 200 | 1.0 | 1.0 | 2026-08-12T13:20:25.870189 |
| `2026-08-12-4d886440-3c0c90cb.json` | `4d886440a646f176` | `3c0c90cb0106d8b8567a7bb9edf9b0a7b5b3c7e406c1e34bb979423eca16b186` | 200 | 1.0 | 1.0 | 2026-08-12T11:52:43.144513 |
| `2026-08-12-4d886440-4df8f547.json` | `4d886440a646f176` | `4df8f547b379548651ea7dd20e2314d4935480b895934ffcd51eb705b3f09b87` | 200 | 1.0 | 1.0 | 2026-08-12T10:51:56.650665 |
| `2026-08-12-4d886440-5618072f.json` | `4d886440a646f176` | `5618072f6c48667823086794c673b997677fd323c0827ca65b68c9b87b675ce8` | 200 | 1.0 | 1.0 | 2026-08-12T13:28:32.836207 |
| `2026-08-12-4d886440-5975a0fd.json` | `4d886440a646f176` | `5975a0fd79eb57b3aa4a7adf8c8fae167ba8dfa87d227627452ceffdb907b013` | 200 | 1.0 | 1.0 | 2026-08-12T14:35:22.614290 |
| `2026-08-12-4d886440-5caca092.json` | `4d886440a646f176` | `5caca092b276999d56da505ea26cba0253d09cfef51aedd49e61e5bf42d8ca0f` | 200 | 1.0 | 1.0 | 2026-08-12T03:15:58.764853 |
| `2026-08-12-4d886440-6eadba73.json` | `4d886440a646f176` | `6eadba737b8cd8ee216d595f8e617f12d51bdb636ccc39fee76c0bcb79882b2e` | 402 | 0.3731 | 0.3125 | 2026-08-12T14:35:22.634734 |
| `2026-08-12-4d886440-6fbb679a.json` | `4d886440a646f176` | `6fbb679a0a5cbc20841856e5a562a98517e214a629e457f65c3e571cb445aebe` | 200 | 1.0 | 1.0 | 2026-08-12T13:19:40.573660 |
| `2026-08-12-4d886440-7c8aaae0.json` | `4d886440a646f176` | `7c8aaae0c4b84f972441ff0ddce777924b4bc4df97f790362a1ab54ebd227e43` | 200 | 1.0 | 1.0 | 2026-08-12T13:20:33.931664 |
| `2026-08-12-4d886440-8cc14af5.json` | `4d886440a646f176` | `8cc14af50c71f8226701451d322ab6778b5bbaec9f44a1dc3041ef1679c28d26` | 200 | 1.0 | 1.0 | 2026-08-12T10:55:16.990656 |
| `2026-08-12-4d886440-958d7323.json` | `4d886440a646f176` | `958d732389e761ddf8ceea2d935512903bfa2f4706d987e5617ceb7e6622d779` | 200 | 1.0 | 1.0 | 2026-08-12T12:56:29.548874 |
| `2026-08-12-4d886440-98fc4b49.json` | `4d886440a646f176` | `98fc4b49f787c29c91cd720115735a64265d09c486bd350c88a780cacf4c1ff7` | 402 | 0.3731 | 0.3125 | 2026-08-12T03:15:58.785256 |
| `2026-08-12-4d886440-9bf7cdad.json` | `4d886440a646f176` | `9bf7cdadf17c9dddc71ee2bcd88a4a57aa5912eee40c51b2baf666a0eaba5eea` | 200 | 1.0 | 1.0 | 2026-08-12T10:53:04.915440 |
| `2026-08-12-4d886440-9f564528.json` | `4d886440a646f176` | `9f56452807532f1c14c701234e7a00b83a08a5cb32f2a06ea7c6000e042a4451` | 200 | 1.0 | 1.0 | 2026-08-12T10:49:07.073546 |
| `2026-08-12-4d886440-a020f2ca.json` | `4d886440a646f176` | `a020f2ca683e0fc9f3b30c6263fa88fcd74b048da2922c32357f8f0c06257dff` | 200 | 1.0 | 1.0 | 2026-08-12T10:51:27.394448 |
| `2026-08-12-4d886440-a73dba22.json` | `4d886440a646f176` | `a73dba22990c6e1d717969a6459d69f600518fd0ddb9860ac7594ad4486ed8af` | 200 | 1.0 | 1.0 | 2026-08-12T11:28:41.617704 |
| `2026-08-12-4d886440-adba0e2f.json` | `4d886440a646f176` | `adba0e2fbf32251fb37c2a2b0c29635e2083d487da8f9ff8fd2dbf46e137c6a3` | 402 | 0.3731 | 0.3125 | 2026-08-12T10:49:07.093037 |
| `2026-08-12-4d886440-b0d6d327.json` | `4d886440a646f176` | `b0d6d327ec50337937d93ceebbb36952b44f69673d647944a2d520efb4332c19` | 200 | 1.0 | 1.0 | 2026-08-12T12:56:48.042263 |
| `2026-08-12-4d886440-b95871fb.json` | `4d886440a646f176` | `b95871fb5017c71e1cfd8ff3dfcbf4953f323106767de615a8e07a383f6c4619` | 200 | 1.0 | 1.0 | 2026-08-12T11:50:39.991644 |
| `2026-08-12-4d886440-c8e6d7b6.json` | `4d886440a646f176` | `c8e6d7b67567e9622ac66b061ee8707b0e626737d3b343d2ac5cb65a14cbac13` | 200 | 1.0 | 1.0 | 2026-08-12T13:21:54.852682 |
| `2026-08-12-4d886440-d0a67f8b.json` | `4d886440a646f176` | `d0a67f8b2cbc1e581f20898a5f466f6a7533d94a4f77fb441f99673ac9a8130b` | 200 | 1.0 | 1.0 | 2026-08-12T12:01:14.259700 |
| `2026-08-12-4d886440-d12223d2.json` | `4d886440a646f176` | `d12223d25c3d1cb120854c84a3341ed159328738e24677651de5f08fe402695e` | 200 | 1.0 | 1.0 | 2026-08-12T12:22:53.592867 |
| `2026-08-12-4d886440-de1c883a.json` | `4d886440a646f176` | `de1c883a31f0589fe4df9c347bcf144ca2fb5885042db3456f2d04a68f7931c1` | 200 | 1.0 | 1.0 | 2026-08-12T10:50:05.891764 |
| `2026-08-12-4d886440-e712ec3c.json` | `4d886440a646f176` | `e712ec3c3764aacb0154115dd92d3c1a3950785f83a9e4c194c275af72c16185` | 200 | 1.0 | 1.0 | 2026-08-12T00:40:25.260792 |
| `2026-08-12-4d886440-ecdd2da5.json` | `4d886440a646f176` | `ecdd2da567be9e38677081cfc1c85732d8532caae127857c2f1c8046ac68b080` | 200 | 1.0 | 1.0 | 2026-08-12T10:52:07.712379 |
| `2026-08-12-4d886440-edc067d2.json` | `4d886440a646f176` | `edc067d286afdb74a993e5687e8e860c027b4c597b5a01649f98cb16a9b51dc8` | 200 | 1.0 | 1.0 | 2026-08-12T13:20:06.320580 |
| `2026-08-12-4d886440-f3a01acc.json` | `4d886440a646f176` | `f3a01accc3b8910e6f40a78b1f06dafd8b1b71b4e3dab6673c1ff272e0992fa3` | 200 | 1.0 | 1.0 | 2026-08-12T11:37:35.865593 |

### Nested (16 files, under `entailment/verdicts/verdicts/` — the undocumented population)

| File | Identity | Gold sha256 | Pairs | Entailed precision | Contradiction recall | mtime |
|---|---|---|---|---|---|---|
| `verdicts/2026-08-10-4d886440-0a74c745.json` | `4d886440a646f176` | `0a74c745a9917122254f2d06fe672ffc1a66553bf391e5c1d6ea29df55ad9bc5` | 200 | 1.0 | 1.0 | 2026-08-10T13:50:04.960627 |
| `verdicts/2026-08-10-4d886440-0c743101.json` | `4d886440a646f176` | `0c74310149a01601bb6134077178f89c0a1094f26ab5be1bc9a04ac76629e1a7` | 200 | 1.0 | 1.0 | 2026-08-10T19:36:03.757912 |
| `verdicts/2026-08-10-4d886440-122011b3.json` | `4d886440a646f176` | `122011b3d97c889dd7808d1c2215a0131d4a7fe467bf20861e8ddc13d10793f7` | 200 | 1.0 | 1.0 | 2026-08-10T18:17:09.392190 |
| `verdicts/2026-08-10-4d886440-1872d27c.json` | `4d886440a646f176` | `1872d27c4520c3cf77bd50743e62a8a35a27737c0d8cd35189744a7656cec27d` | 200 | 1.0 | 1.0 | 2026-08-10T14:09:47.709891 |
| `verdicts/2026-08-10-4d886440-507a0872.json` | `4d886440a646f176` | `507a0872e73bc58e917caa5c9e7477653bb9eec7114863c26207fab3ee8c6b95` | 200 | 1.0 | 1.0 | 2026-08-10T18:57:49.215251 |
| `verdicts/2026-08-10-4d886440-50a5e80a.json` | `4d886440a646f176` | `50a5e80a2511c95a9cb8d386c972ab33f4f6d752720bccbddfb50b011e01c3e5` | 200 | 1.0 | 1.0 | 2026-08-10T19:20:03.794708 |
| `verdicts/2026-08-10-4d886440-5892f50d.json` | `4d886440a646f176` | `5892f50dd07f0d0201087658afe35028ded29c87de566923fa12da996ea7b616` | 200 | 1.0 | 1.0 | 2026-08-10T16:39:37.286865 |
| `verdicts/2026-08-10-4d886440-5ae2586f.json` | `4d886440a646f176` | `5ae2586f4b9231ff893dccc727b90797f45ac9c468701779d553e9bf44f23715` | 200 | 1.0 | 1.0 | 2026-08-10T16:04:09.999304 |
| `verdicts/2026-08-10-4d886440-60c8e469.json` | `4d886440a646f176` | `60c8e469da30a860272b0adb3dc959ee895ca7e3482269d3a6da6fbb566563c2` | 200 | 1.0 | 1.0 | 2026-08-10T14:41:56.194430 |
| `verdicts/2026-08-10-4d886440-98fc4b49.json` | `4d886440a646f176` | `98fc4b49f787c29c91cd720115735a64265d09c486bd350c88a780cacf4c1ff7` | 402 | 0.3731 | 0.3125 | 2026-08-10T19:36:03.773946 |
| `verdicts/2026-08-10-4d886440-a9aad74a.json` | `4d886440a646f176` | `a9aad74aaf4bc3f66a5edef2f7a2b17ed1a3e3722da7a486c17ea090b3b67ec6` | 200 | 1.0 | 1.0 | 2026-08-10T14:50:32.731531 |
| `verdicts/2026-08-10-4d886440-ba1aa2a3.json` | `4d886440a646f176` | `ba1aa2a32621a2e659f9a1ca9f3cbada2407f9739fb4f507d27848acd0cfff7b` | 200 | 1.0 | 1.0 | 2026-08-10T19:05:51.303072 |
| `verdicts/2026-08-10-4d886440-c4ac56e9.json` | `4d886440a646f176` | `c4ac56e9fb61a491d2a217f50556e2b095e09291d16763488deb88ce4407e545` | 200 | 1.0 | 1.0 | 2026-08-10T15:29:01.674729 |
| `verdicts/2026-08-10-4d886440-c71d5d9a.json` | `4d886440a646f176` | `c71d5d9a57bb79fecfc6eec9f41468ff35ed21c8eed699483fa0e86193ea221e` | 200 | 1.0 | 1.0 | 2026-08-10T18:06:04.958399 |
| `verdicts/2026-08-10-4d886440-d3845adf.json` | `4d886440a646f176` | `d3845adf22612d5d4709fedc4fa16549e437332d76972553a61f9ca8d441bf96` | 200 | 1.0 | 1.0 | 2026-08-10T17:44:20.212350 |
| `verdicts/2026-08-10-4d886440-fc601cd4.json` | `4d886440a646f176` | `fc601cd43586a9d9a6dc83deb1611eb3d066ed1fb7f6a4b0aef574072d7a2933` | 200 | 1.0 | 1.0 | 2026-08-10T16:12:02.386758 |

## Leak source, found before any fix was written

`run_judge_qualification.py`'s `VERDICTS_DIR` was a module-level constant
(`entailment_gold.ENTAILMENT_DIR / "verdicts"`, itself derived from
`__file__` — always the real, fixed, on-disk path) read directly at the
write site (`run_qualification`, the per-pair-verdicts write). Unlike
`report_dir`, `cache_dir` and `ledger_path`, which are `run_qualification`
keyword parameters the test suite's `_run` helper (`test_judge_qualification.py`)
already overrode to a `tmp_path` subdirectory, `verdicts_dir` had no such
parameter — every test that drove a stub judge to scoring completion wrote
its stub verdicts into the real directory under whatever identity the stub's
config carried (the default `deepseek-v4-flash`, identity `4d886440a646f176`,
when a test does not override the judge model — which none of the leaking
tests do).

This matches the audit exactly: 200-pair/1.0/1.0 files are gate-mode
rehearsal tests using the 200-pair `eligible_gold` fixture and a stub that
always answers with the gold's own verdict; 402-pair/~0.37-0.41 files are
happy-path/latency tests that use the real, current gold (`gold_path` is
never overridden in `_run`'s defaults) with a round-robin stub that has no
knowledge of the gold's actual answers.

**Reproduced dynamically**, isolated to this worktree's own (gitignored,
untracked) copy of `entailment/verdicts/`, which is a separate directory
from the main checkout's real one and was never at risk of contaminating
it: running `pytest scripts/benchlib/tests/test_judge_qualification.py -k
test_happy_path_two_ledger_rows_and_report` before any code change produced
`entailment/verdicts/2026-08-12-4d886440-6eadba73.json` — identity
`4d886440a646f176`, gold sha `6eadba73...`, i.e. exactly the same signature
as the real directory's residue. That file was deleted immediately after
confirming the mechanism; it is not counted in the 95 above (it never
existed in the real, main-checkout directory).

## The fix

`run_qualification` now takes a `verdicts_dir` keyword parameter (default
`VERDICTS_DIR`, unchanged for production/CLI use — there is no CLI flag for
it, matching `report_dir`'s existing precedent), and the write site uses it
instead of the module constant. The test suite's `_run` helper now passes
`verdicts_dir=tmp_path / "verdicts"`, so every existing test that
previously leaked now writes to a throwaway directory instead.

A new regression test,
`test_a_completed_run_never_writes_into_the_real_verdicts_directory`,
monkeypatches `rjq.VERDICTS_DIR` to a canary path standing in for "the real
directory" and asserts nothing was ever created there after a completed
run. Proven to catch the regression: reverting the write site back to
`Path(VERDICTS_DIR)` made the test fail, with the canary path holding a
freshly written `2026-08-12-4d886440-6eadba73.json` — the test was then
restored to green with the fix back in place.

## Deletion

All 95 files listed above, plus the now-empty `entailment/verdicts/verdicts/`
subdirectory, were deleted from
`backend/scripts/benchlib/entailment/verdicts/` in the main checkout after
this document was written and committed. Only
`2026-08-12-fd39e7b2-6eadba73.json` remains.
