# Scoped re-review — the fix round for T3.14 / T3.25 / T3.19

Reviewer: Fable 5 scoped re-review, 2026-08-10. Branch `feat/e3-synthesis-and-reach`,
HEAD `bb8a71de`. Fix diff `8a0de4a1..b9293fcd`
(`.superpowers/sdd/reviews-2026-08-10/FIXES.diff`), answering
`docs/planning/reviews/2026-08-10-t3.14-t3.25-t3.19-task-review.md`.

**This is a fix verification, not a re-review of the tasks.** Every verdict below was
driven — each repaired guard was mutation-tested to confirm it now fails on the defect it
claims to catch, and every claimed behaviour was measured against the real app rather than
read. The tree was restored from a private copy of the single mutated file after each drill
and confirmed clean (`git status --short` empty) each time.

T2.114 was not touched.

---

## Overall verdict

**19 of 20 open findings ADDRESSED. One NOT ADDRESSED (I-1). Three new Important findings
and four new Minors introduced or left standing by the fixes themselves.**

The loop continues on: **I-1**, **N-1**, **N-2**, **N-3**.

---

## Verdicts, one line each

| Id | Verdict | The change that settles it |
|---|---|---|
| C-1 | **ADDRESSED** (residual N-1) | `sdks/generate.py:134` + `backend/tests/test_sdk_contract_conformance.py:86-123` |
| I-1 | **NOT ADDRESSED** | three named drills closed; a fourth and a fifth drilled and driven — below |
| I-2 | **ADDRESSED** | `sdks/generate.py:269-287`; `backend/tests/test_sdk_generator.py:196-244` |
| I-3 | **ADDRESSED** (residual N-3) | `docs/design/15-distribution-and-integration.md:241-256`; `docs/planning/tasks/E3-synthesis-and-reach.md:474` |
| I-4 | **ADDRESSED** | `scripts/gate.sh:210-216` |
| M-1 | **ADDRESSED** | `sdks/generate.py:460`; `sdks/ts/src/client.test.ts:139`; `sdks/python/tests/test_client.py:159` |
| M-2 | **ADDRESSED** | `sdks/generate.py:260`; `sdks/python/tests/test_client.py:90`; `sdks/ts/src/client.test.ts:80` |
| M-3 | **ADDRESSED** | `sdks/generate.py:474-481`; `sdks/ts/src/client.test.ts:210` |
| M-4 | **ADDRESSED** (weakly typed — N-7) | `sdks/generate.py:343` |
| M-5 | **ADDRESSED** | `sdks/python/tests/test_surface.py:193` |
| M-6 | **ADDRESSED as recorded** (thin — below) | review committed at `f392111b`; eval artifact split into `bb8a71de` |
| M-7 | **ADDRESSED** | `sdks/generate.py:82-85`, `380-384`, `504-506` |
| I-6 | **ADDRESSED** | `frontend/src/features/settings/components/distribution-tab.tsx:303-327`, `:363-366` |
| I-7 | **ADDRESSED** | `frontend/src/features/settings/__tests__/settings-distribution.real.test.tsx:28-63` |
| I-8 | **ADDRESSED** | same file, `:170-182` |
| M-8 | **ADDRESSED** | same file, `:34-48` (distinct fixture strings) |
| I-9 | **ADDRESSED** (residual N-2) | `backend/app/api/routes/distribution.py:12-17`, `:154-165` |
| M-9 | **ADDRESSED** | `distribution-tab.tsx:132-169` |
| M-10 | **ADDRESSED** | `distribution-tab.tsx:199-208` |
| M-11 | **ADDRESSED** (partial reach — N-5) | `backend/app/services/inject_adapters.py:131-151`, `:265-274`; `backend/app/api/routes/distribution.py:114-117` |

---

## The four things the brief said to attack hardest

### 1. The new `search` binding — does the declaration actually resolve on both ranks?

**Yes, on both, and the trace envelope is genuinely returned.** Driven through the real ASGI
app: `POST /api/v1/memories/search/paginated` with `X-Darkmem-Context` echoes
`envelope.context = {"declared": {...}, "declared_by": "header", "provenance": "human"}`;
with a body `context` it echoes `declared_by: "arg"`; with both, the argument wins. That is
the standing assertion in `test_sdk_contract_conformance.py`, and it is the exact control row
the original review used to prove the mechanism worked elsewhere.

**Is there a third door that would have been better?** No. Exactly three request schemas in
the whole contract declare a `context` property, and they reach three doors:
`POST /api/v1/memories/search`, `POST /api/v1/memories/search/paginated` and
`POST /api/v1/chat/completions`. The first never reads it (`MemoryService.resolve_request_context`
says so in its own docstring); the third is not a search verb and its response carries no
envelope. The bound door is the only one of the three that resolves the chain and returns the
trace, so the re-pointing is correct.

**A caveat worth stating, though not a defect of this fix:** "resolved" today means *echoed
in the trace envelope*. Nothing in ranking reads either rank —
`resolve_request_context`'s docstring is explicit that "wiring the winner into ranking is the
E2/E3 four-layer composition task's". The original review's own control accepted the echo as
the standard, so the fix meets the bar it was set; a reader should not take it as more.

**What is wrong with it anyway:** see **N-1** — the door resolves the declaration only on the
`with_trace=True` path, and the SDK supports and tests `with_trace=False`.

### 2. The consumption guard's reach

The generator's new arm refuses a context-carrying verb bound to a door whose request schema
lacks `context`, plus a second arm refusing when no verb carries the header at all
(`generate.py:194-210`). The docstring correctly states the signal is necessary and not
sufficient.

**Is the pairing with the conformance test enough?** For the re-pointing class it defends
against, yes — measured. Drill: re-point `search` to `POST /api/v1/memories/search`, the one
door that declares `context` and deliberately never reads it, then `make generate`. The
generator **did not refuse** (correct — the schema signal cannot see it), and the conformance
test caught it hard: **5 of 6 conformance tests red** plus the pinned-path test in
`test_sdk_generator.py`. There is no re-pointing among the three candidate doors that passes
both.

**The hole the pairing does not cover** is not a re-pointing at all: it is a call-site
argument. See N-1.

### 3. The surface whitelists — a fourth escape

Found two, both drilled and both driven to a live ratify. **I-1 is NOT ADDRESSED.** Details
below.

### 4. The curb journal

Correct on every question asked.

- **Transition detection with no config row yet:** `was_curbed` is read through `_policy`,
  which returns `DEFAULT_POLICY` (`curbed: False`) when the row is absent, and it is read
  *before* the row is written. A first-ever curb on a virgin install journals. Pinned by
  `test_turning_the_curb_on_journals_it`, which runs against a fresh schema.
- **One row per transition:** mutation — replace `if body.curbed and not was_curbed` with
  `if body.curbed` → `test_leaving_the_curb_on_journals_nothing_further` reddens. Mutation —
  remove the call entirely → three tests redden. Both guards are real.
- **Does a failed journal leave a half-written policy?** No. Measured with
  `record_inject_curbed` stubbed to return `False`: the PUT still answers 200 and the policy
  reads back `curbed: true`. That matches the docstring's stated contract and is the right
  call for a safety control. `record_event` never raises, so the raising case is unreachable.
- **Global tool `*`, release journals nothing** — both asserted, both correct against the
  closed `EVENT_TYPES` vocabulary.

### 5. `_resolve`'s refactor

**Same adapters for every existing caller.** Measured across twelve config-row shapes
(healthy, absolute, `~`, `..`, drive-letter, empty, missing, non-string value, non-object
entry, unknown field, override, non-Markdown suffix): the `get_adapters` return is identical
to the pre-fix behaviour in all twelve — same tools, same paths, same drops.

**One caller now pays a second query:** `GET /api/v1/distribution` calls `get_adapters` and
`get_adapter_rejections`, each of which runs `_resolve` independently. Measured: **2
`_resolve` calls, so two SELECTs of the same `config` row, per request.** See N-6.

### 6. The controlled `TokenBudgetField`

**It cannot loop.** The render-phase `setState` is React's documented adjust-state-on-prop-change
pattern: `setSeed(budget)` makes the guard false on the immediate re-render, and `budget` is a
number so its identity is stable. **A successful write re-seeds:** `useSetDistributionPolicy`'s
`onSuccess` invalidates `["distribution"]`, the refetch moves `policy.token_budget`, and the
seed comparison takes it. Mutation — restore the uncontrolled `Number(draft)` /
`Number.isFinite` guard → the new "does not write a budget of zero" test reddens. See N-7 for
the failure path.

---

## I-1 — NOT ADDRESSED

The three drills the original review named are genuinely closed. Re-run at HEAD:

| Original drill | Result now |
|---|---|
| A — TypeScript public class field `send = async (…) => {}` | **red**: `test_the_typescript_class_exposes_exactly_three_members` and the TS instance probe `puts nothing at all on the instance` |
| B1 — Python `@classmethod def open_door(...)` | **red**: `test_the_python_class_exposes_exactly_three_public_attributes` |
| B2 — Python module-level `async def send(...)` | **red**: `test_the_python_module_exposes_no_other_public_name` |

**But a fourth and a fifth escape pass every suite and drive a real ratify.** Both are
mutations to `sdks/generate.py` followed by `make generate` — the stated threat model.

**Escape 4 — a TypeScript `static` member.**

```
    static async send(
      client: Darkmem,
      path: string,
      body: Record<string, unknown>,
    ): Promise<unknown> {
      return client.#post(path, body, false);
    }
```

Measured at four-space indentation: `sdks/python` **30 passed**, `sdks/ts` **19 passed**,
`backend/tests/test_sdk_generator.py` + `test_sdk_contract_conformance.py` **28 passed**,
`make build` **green**. A scratch vitest then drove it:

```
DRILL URL  http://localhost:8000/api/v1/knowledge/facts/abc-123/ratify
DRILL AUTH Bearer jwt
DRILL OUT  {"status":"confirmed"}
```

Two independent gaps compose. First, `_typescript_class_members`' regex is anchored to
**exactly two leading spaces** (`^  `), so a member at any other indentation is invisible —
and the emitted file's formatting is written by the very thing being defended against.
Second, **neither runtime probe covers statics**: `Object.getOwnPropertyNames(Darkmem.prototype)`
misses them (a static lives on the constructor) and `Object.getOwnPropertyNames(new Darkmem({}))`
misses them too. That second gap holds even at two-space indentation — I confirmed the
two-space variant is caught by the source scan **alone** (`sdks/ts` 19 passed, `make build`
green, only `test_the_typescript_class_exposes_exactly_three_members` red). So the file's own
claim that the run-time probes "cover the TypeScript constructs a source scan reads poorly" is
false for the one construct that is neither an instance property nor a prototype method.

**Escape 5 — a Python sync dunder.**

```
    def __call__(self, path: str, body: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        with httpx.Client() as client:
            return client.post(
                f"{self.base_url}{path}", json=body, headers=headers,
            ).json()
```

Measured: `sdks/python` **30 passed**, `backend` SDK suites **28 passed**, `make build`
**green**. Driven: `Darkmem(token="jwt")("/api/v1/knowledge/facts/abc-123/ratify",
{"verdict": "confirm"})` reached the ratify door with `Authorization: Bearer jwt` and returned
`{'status': 'confirmed'}`. Every whitelist in `test_surface.py` filters names on
`startswith("_")`, so no dunder can ever appear in any of them, and
`test_the_python_body_keys_are_exactly_the_declared_fields` only walks `ast.AsyncFunctionDef`.
(The *async* variant of the same escape is caught, but only incidentally — by that body test,
because the coroutine happens to call `self._post`. Rewritten to build its own request it
passes; rewritten as a sync `def` it passes regardless.)

**Why this is NOT ADDRESSED rather than a new finding.** The finding was that the scans
cannot detect the violation they exist to detect, and the file's framing — "a fourth verb has
to survive all of them" — is still not true. The fix closed the three constructs that were
named and did not close the class.

**Sharpened fix.** TypeScript: add a third run-time probe,
`Object.getOwnPropertyNames(Darkmem)` minus `["length","name","prototype"]` must be empty, and
stop depending on indentation by scanning `Object.getOwnPropertyNames` of the prototype, the
instance and the constructor as the primary check with the regex as a secondary. Python: drop
the `startswith("_")` filter in favour of an explicit allowlist of the private names the
client is permitted to carry (`_post`, `_context`), so any new underscore or dunder member
fails. Both are cheap; neither needs a parser.

---

## New findings introduced by, or left standing after, the fixes

### N-1 (Important) — `withTrace: false` silently drops the declaration on **both** ranks, and the SDK documents the opposite

`search_memories_paginated` resolves the declared context **only** on the `with_trace=True`
branch (`backend/app/services/memory.py:498-500`, `:544`). The untraced branch never calls
`resolve_request_context`, and the response has no envelope to echo into. Measured through the
real app:

| Call | Result |
|---|---|
| `with_trace: true` + header | `envelope.context.declared_by = "header"` |
| `with_trace: false` + header | 200, `envelope: null`, declaration discarded |
| `with_trace: false` + body `context` | 200, `envelope: null`, declaration discarded |

The generated clients send the header on **every** `search` regardless of `with_trace`,
because `carries_context` is a per-verb constant (`sdks/generate.py:135`, and both `_post`
implementations gate only on it). And `withTrace: false` / `with_trace=False` is a
first-class supported argument with a dedicated test in each client suite
(`sdks/ts/src/client.test.ts:110`, `sdks/python/tests/test_client.py:132`) — so this is a
documented call shape, not a corner.

Neither guard sees it. The generator's consumption arm asks about the request schema, which
declares `context` unconditionally; the conformance test hardcodes `with_trace: True` in
every one of its four resolution cases. And the honest-limitation note the clients carry says
flatly "The header goes only to doors that take part in that chain -- today that is `search`
alone", with no mention that `search` takes part only when it is asked for the trace.

This is C-1's own failure mode — a declaration sent, accepted, and ignored with nothing said —
surviving in a narrower window that the fix's two new guards are both structurally unable to
see. Blast radius is still zero (no consumers), which is why it is a defect to close now.

Fix directions: gate the header on `with_trace` in `_post` (`carries_context && with_trace`)
so an unresolvable declaration is never sent; or state the condition in `CONTEXT_NOTE_LINES`;
or both. Resolving on the untraced path is the wrong fix — it would spend a project-registry
read per request on a value the response cannot carry, which is exactly why
`resolve_request_context` is not called there.

### N-2 (Important) — `inject_journal.py` still says it has no producer, one commit after gaining one

`backend/app/services/inject_journal.py:23-27`:

> **No producer yet, deliberately.** T3.10 owns the content fill and is held by G-D, so
> nothing calls this in the tree today. It ships as the primitive its caller will need, the
> way T2.08's placeholders and T0.13's inert partitions did (invariant 23) …

`record_inject_curbed` now has a caller — `put_policy`
(`backend/app/api/routes/distribution.py:160`). This is the same false-present-tense defect
I-9's second half was about, recreated in the module I-9 named, by the commit that fixed I-9.
A reader auditing invariant 23 would mis-triage the module; a reader wiring T3.10 would
believe the curb is unjournalled and add a second writer. One clause fixes it: `record_inject`
has no producer, `record_inject_curbed` has exactly one.

### N-3 (Important) — doc 15 §6's prose still says `capture` carries the declaration, and the amendment claims it does not

The amendment note (`docs/design/15-distribution-and-integration.md:241`) correctly records
that `capture` lost its `context?` argument, and closes: *"Both the diagram and the prose are
now aligned with what the contract serves."* Two paragraphs below, unamended:

> `declareContext` sets the session's `applies_when` context so subsequent `search`/`capture`
> calls carry it (contract 3).

and the paragraph after that:

> `declareContext` and the `context` argument on `capture`/`search` serialise to exactly doc
> 12's forms …

Both name `capture` as a context carrier, which the same section's amendment just removed and
which the generator now **refuses to emit**. This is I-3's exact shape — an amendment logged
while the document goes on saying the opposite — moved one paragraph down, with the added cost
that the amendment's own closing sentence is now false. Fix: extend the dated note's reach to
those two sentences, or amend them in place.

### N-5 (Minor) — a non-object `inject_adapters` entry is still dropped log-only

`reject_reason` covers the `context_file` shapes, so M-11's stated scope is met. But
`_resolve`'s earlier `if not isinstance(entry, dict)` branch (`inject_adapters.py:171-176`)
`continue`s with a log warning and adds nothing to `rejected`. Measured: config row
`{"rogue": "nope"}` yields `targets` without `rogue` and `rejected == []` — the operator whose
entry is a string rather than an object still watches their row vanish with the reason on the
server, which is the sentence M-11's fix was written against. The unknown-field and
non-string-value warnings are the same shape, though less severe (the tool still renders).

### N-6 (Minor) — `GET /api/v1/distribution` runs the adapter merge twice

`get_adapters(session)` and `get_adapter_rejections(session)` each call `_resolve`, so the one
caller that needs both pays two SELECTs of the same `config` row and two merges per request.
Measured: 2 `_resolve` calls per GET. `_resolve`'s own docstring says re-deriving the
rejections "would mean a second copy of the merge" — the *copy* was avoided, the *pass* was
not. Exposing `_resolve` to the route (or a `get_distribution_registry` returning both) costs
nothing and removes the duplicate.

### N-7 (Minor) — a **failed** budget write leaves the field asserting the rejected value while the banner says otherwise

`TokenBudgetField` re-seeds from `budget`, which only moves on a successful write. When the
PUT fails (e.g. a value outside the route's `ge=0, le=100_000`), `budget` never moves, the
draft keeps showing what the user typed, and the M-10 banner above it reads *"the change was
not saved — push is still whatever the server last accepted, **shown below**"* — while the
budget field shown below is not the server's value. Small, but it is the same
screen-asserts-what-is-not-in-force failure M-9 was raised about, in the failure path. Clearing
the draft back to `budget` on `setPolicy.isError` closes it.

### N-8 (Minor) — `CaptureAck.status` is typed `string`, not the literal

M-4 asked for the field and got it. `app.schemas.memory.CaptureAck` declares
`status: Literal["accepted"]`; the emitted TypeScript declares `status: string`, so the typed
surface still under-describes the door — narrowly. Recorded, not looped on.

---

## Notes on two verdicts that deserve a sentence

**M-6 — "recorded instead" is thin but real.** Commit `8a0de4a1` cannot be unbundled without a
history rewrite, so recording was the right call. What exists is the review naming M-6,
committed into the tree at `f392111b`, plus `bb8a71de` demonstrating the discipline going
forward — the post-fix retrieval eval landed as its own `chore(eval)` commit. There is no
gate-ledger deferred-minors entry. Adequate for a Minor; noted so a branch reviewer does not
go looking for one.

**I-4 — the arm is in the default gate path**, not behind `--full` (`scripts/gate.sh:210-216`,
between the `sdk typescript tests` and `benchlib` arms). Drilled: `const broken: number = "not
a number";` injected into the TypeScript template passes `sdks/ts` (**19 passed**) and reddens
only `make build`, which exits 2 with `ts/src/client.ts(70,11): error TS2322`.

---

## Verification run

Every number below was measured during this review, at HEAD, with the tree clean.

| Command | Result |
|---|---|
| `cd sdks && make generate && git diff --exit-code` | clean (`contract fad5ee9edc9b2ba0`) |
| `cd sdks && make build` | green |
| `cd sdks/python && python -m pytest -q` | **30 passed** |
| `cd sdks/ts && npm test` | **19 passed** |
| `cd backend && pytest tests/test_sdk_generator.py tests/test_sdk_contract_conformance.py tests/test_distribution.py -q` | **43 passed** |
| `cd frontend && npm test -- distribution` | **10 passed** |
| `cd frontend && npm test` | **751 passed** (111 files) |
| `cd backend && python -m pytest -q` | **4908 passed, 19 skipped** in 265.14 s |

Mutation drills run (each reverted from a private copy of the single mutated file; tree
confirmed clean after each):

| Drill | Expected | Measured |
|---|---|---|
| re-point `search` to the deaf `/api/v1/memories/search` | conformance red | 5 conformance + 1 generator test red |
| stray body key in the Python template, tuple untouched | generator suite red | `test_the_python_body_keys_are_exactly_the_declared_fields` red |
| stray body key in the TypeScript template | generator suite red | `test_the_typescript_body_keys_are_exactly_the_declared_fields` red |
| TypeScript type error in the template | `make build` red | vitest 19 passed, `make build` exit 2 (`TS2322`) |
| I-1 drill A (TS class field) | red | 2 tests red |
| I-1 drill B1 (Python classmethod) | red | 1 test red |
| I-1 drill B2 (Python module-level fn) | red | 1 test red |
| **I-1 escape 4 (TS `static`, 4-space)** | **should be red** | **all suites green; ratify driven** |
| **I-1 escape 5 (Python sync `__call__`)** | **should be red** | **all suites green; ratify driven** |
| gut the live target list | frontend red | 2 tests red (was green before the fix) |
| delete the detail-level gate | frontend red | 1 test red (was green before the fix) |
| revert the budget field to uncontrolled | frontend red | 1 test red |
| delete the `setPolicy.isError` banner | frontend red | 1 test red |
| un-gate the demo panel outside `DEMO` | frontend red | 1 test red |
| remove the curb journal call | backend red | 3 tests red |
| journal on curb *state* rather than transition | backend red | 1 test red |
| silence `get_adapter_rejections` | backend red | 1 test red |
| `with_trace: false` + declaration, driven live | should resolve | **`envelope: null` — declaration discarded (N-1)** |
| `_resolve` calls per `GET /api/v1/distribution` | 1 | **2 (N-6)** |
| `get_adapters` across 12 config shapes | unchanged | identical to pre-fix in all 12 |
