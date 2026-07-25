# End-to-end test plan

**Scope.** What gets end-to-end coverage, with which fixtures, at which merge gate — and
just as importantly, what deliberately does *not*, so the suite stays fast enough to
actually run.

## Where e2e sits in the gate posture

There is no hosted CI; the gate is a **scripted discipline** (doc 17 §9). Three rings:

| Ring | Command | When | Blocks |
|---|---|---|---|
| **Floor** | `python -m pytest -q` · `npm run typecheck && npm test && npm run build` | Every merge | Every merge |
| **Extraction** | `python scripts/extraction_bench/run_bench.py --algo-only` | Any change touching the extraction surface | That merge |
| **E2E** | `npm run test:e2e` + the API e2e suite | Release candidates, and any task whose acceptance names an e2e spec | The release |

`scripts/gate.sh` (T0.16) runs rings 1–2; `scripts/gate.sh --full` adds ring 3.

**E2E is not a merge gate and should not become one.** Browser tests are the slowest,
flakiest signal in the stack; making them block every merge trades real velocity for
marginal confidence. They gate *releases*, where their cost is proportionate.

---

## The three databases

Never blur these. A test pointed at the wrong one is a defect regardless of whether it
passes.

| Database | Owner | Lifecycle | Used by |
|---|---|---|---|
| `darkmem` | The real instance | Never reset | Nothing automated. Ever. |
| `darkmem_test` | pytest | `DROP SCHEMA public CASCADE` + `alembic upgrade head` per run | Backend unit + API e2e |
| `darkmem_bench` | benchlib | Same reset discipline, separate database | Eval corpora, gate probes |

Frontend e2e runs against **demo mode** by default (the `DEMO` flag and `src/demo/`
fixtures) and against a live stack only for the flows marked *live* below.

---

## Fixture strategy

Three fixture tiers, chosen by what the test is actually asserting:

1. **Demo store** (`src/demo/`) — deterministic, in-browser, no backend. Use for UI
   behaviour: layout, navigation, virtualization, empty states, honesty labels rendering.
   Fast and stable; the majority of frontend e2e belongs here.
2. **Seeded live stack** — `darkmem_test` seeded through the **ordinary capture front
   door**, never by direct SQL insert. Use for flows whose value is the round trip
   (capture → pipeline → retrieval → UI). Seeding through the front door is what makes the
   fixture prove the contract rather than bypass it.
3. **Bench corpora** (`darkmem_bench`) — for gate probes only, never for functional e2e.

**Fixture rule:** a fixture that inserts a row the pipeline would never produce is a
fixture that tests a state the system cannot reach. Prefer the front door.

---

## Coverage by flow

One row per business flow (F1–F11). "Ring" is where the coverage lives.

| Flow | What e2e must prove | Ring | Fixture | Lands with |
|---|---|---|---|---|
| **F1 Capture** | A capture through REST *and* through MCP lands in the buffer, flushes, and appears in search with its `origin_key` intact | API e2e | Seeded live | T1.13 |
| **F2 Extract** | A captured memory produces the expected graph; re-processing it is idempotent | API e2e | Seeded live | T1.26 |
| **F3 Retrieve** | Search returns fused, labelled rows; the trace carries per-channel contribution; exclusion counts render on zero results | API e2e + browser | Both | T1.44 |
| **F4 Supersede** | A REPLACES memory flips its predecessor, the amber badge renders, and the successor link navigates | Browser | Seeded live | T1.47 |
| **F5 Expire** | A TTL'd memory expires; its dependents demote before deletion rather than aborting the batch | API e2e | Seeded live | T1.37 |
| **F6 Consolidate** | A dream cycle produces a digest; per-action and per-batch undo restore exact prior state | API e2e + browser | Seeded live | T2.38 |
| **F7 Auto-research** | A research run files evidence through the ordinary capture door and refetching one source does not add an origin | API e2e | Seeded live | T3.08 |
| **F8 Documents** | Grounded Q&A cites spans; a below-threshold answer is labelled or withheld, never served as grounded | API e2e + browser | Seeded live | TH1.16 |
| **F9 Observe** | Every phase's surface renders its signal — this is the F9 callout per epic, covered by that epic's UI tasks | Browser | Demo | Per epic |
| **F10 Inject** | The managed block is rewritten between markers, user text outside survives, and the inject journals | API e2e | Seeded live | T3.12 |
| **F11 Index code** | An index run produces a graph; a forced failure leaves the last-good graph labelled stale rather than wiping it | API e2e | Seeded live | T1.38 |

---

## The honesty suite

A small, permanent set of specs asserting the rules that are cheap to assert and
catastrophic to regress (doc 17 §9). **These never get deleted or skipped**, and each
should fail loudly if its rule is removed.

| Spec | Asserts | Owning task |
|---|---|---|
| `honesty/labels-always-render` | Verification badges, layer labels, and superseded/stale labels render in **both** Simple and Advanced modes | T1.48 |
| `honesty/exclusions-on-empty` | Exclusion counts render even when the result list is empty | T1.44 |
| `honesty/no-silent-drop` | A filtered channel reports its count; no row disappears uncounted | T1.33 |
| `honesty/veto-absolute` | One contradiction beats any number of corroborations | T2.04 |
| `honesty/human-only-confirmed` | No machine path reaches `confirmed` | T2.05 |
| `honesty/demote-before-delete` | Reordering the TTL sweep's demote/delete breaks the constraint | T1.37 |
| `honesty/superseded-pointer` | `status='superseded'` without `superseded_by` is impossible | T1.36 |
| `honesty/withheld-not-grounded` | A below-threshold answer is never served as grounded | TH1.09 |

---

## Determinism boundaries

Tests must respect what this system cannot promise (doc 17 §7). Violating these produces
permanent flakes that get skipped, and a skipped test is worse than no test.

- **Never pin exact Leiden community membership.** The measured residual is −0.4%
  modularity / 98.4% agreement even between implementations of the same algorithm. Assert
  properties (community count in range, a known pair co-clustered), never identity.
- **Never compare embeddings across fingerprints** (invariant 2). Cross-fingerprint cosine
  distance has no defined meaning.
- **Pin the gate configuration** in pipeline tests. The merged extract+classify path
  changes the prompt, so the same content under a different gate state is not
  bit-identical (T1.17).
- **Extraction is reproducible via the content seed** — `sha256(content)[:8]` forwarded as
  a 32-bit int. Anthropic ignores it, which is harmless; removing the forwarding makes
  extraction e2e flaky.

---

## Process hygiene

Every e2e run spawns browsers, servers, and test hosts. **Reaping them is part of the
test, not cleanup afterwards** — orphaned hosts accumulate across runs and have taken
machines down.

- Playwright runs must close their browser context even on failure.
- Any spec that starts a dev server owns killing its process tree.
- `scripts/gate.sh --full` verifies no listener remains on the dev ports before exiting
  zero.

---

## What is deliberately not covered

Naming these keeps the omissions honest rather than accidental:

- **Cross-browser matrix.** Chromium only. A LAN-local single-maintainer tool does not
  earn a browser matrix; revisit if the surface is ever publicly exposed (E4).
- **Visual regression.** No screenshot diffing. The UI is under active redesign; pinned
  screenshots would be pure churn.
- **Load and soak.** Out of scope while the system is single-worker by design
  (invariant 13). Revisit with the T4.10 multi-replica decision, not before.
- **The `darkmem` production database.** Nothing automated ever touches it.
