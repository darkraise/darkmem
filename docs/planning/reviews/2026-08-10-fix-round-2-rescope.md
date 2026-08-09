# Scoped re-review — fix round 2 for T3.14 / T3.19

Reviewer: Fable 5 scoped re-review, 2026-08-10. Branch `feat/e3-synthesis-and-reach`,
HEAD `3ac96d4d`. Fix diff `bb8a71de..3ac96d4d`
(`.superpowers/sdd/reviews-2026-08-10/FIXES-2.diff`), answering
`docs/planning/reviews/2026-08-10-fix-round-rescope.md`.

**Third pass.** Round 1 found a Critical; round 1's fixes introduced three Importants and
left one finding open. That prior held: this round's fixes close seven of eight findings and
introduce two new Importants and five new Minors of their own.

Every verdict below was driven. Each new guard was mutation-tested to confirm it reddens on
the defect it claims to catch; each claimed behaviour was measured against the real app or
the real emitted client rather than read. The tree was restored from a private copy of the
single mutated file after each drill and confirmed clean each time.

T2.114 was not touched.

---

## Overall verdict

**7 of 8 open findings ADDRESSED. One NOT ADDRESSED (I-1), for the third round running.**
**Two new Important findings and five new Minors, all introduced by this round's fixes.**

The loop continues on: **I-1**, **NEW-1**, **NEW-2**.

---

## Verdicts, one line each

| Id | Verdict | The change that settles it |
|---|---|---|
| I-1 | **NOT ADDRESSED** | escapes 4 and 5 closed; a **sixth and seventh** drilled and driven to ratify — below |
| N-1 | **ADDRESSED** (residual NEW-1, NEW-3) | `sdks/generate.py:255`, `:265`, `:439-445`; `sdks/python/darkmem_sdk/client.py:79-86`; `backend/tests/test_sdk_contract_conformance.py:194-201` |
| N-2 | **ADDRESSED** | `backend/app/services/inject_journal.py:23-31` |
| N-3 | **ADDRESSED** (residual NEW-1, NEW-7) | `docs/design/15-distribution-and-integration.md:260`, `:262` |
| N-5 | **ADDRESSED** (regression NEW-2) | `backend/app/services/inject_adapters.py:174-181`; `backend/tests/test_distribution.py:255-268` |
| N-6 | **ADDRESSED** (residual NEW-4) | `backend/app/services/inject_adapters.py:274-284`; `backend/app/api/routes/distribution.py:102`, `:116` |
| N-7 | **ADDRESSED** (residual NEW-5) | `frontend/src/features/settings/components/distribution-tab.tsx:147`, `:153-156` |
| N-8 | **ADDRESSED** (pinned against nothing — deferred) | `sdks/generate.py:347`; `sdks/ts/src/client.ts:21` |

---

## The five things the brief said to attack hardest

### 1. The surface scans, a third time — a sixth and a seventh escape

**Found two more, both driven to a real ratify URL with the bearer token, both with every
suite green.** Threat model as stated: a mutation to `sdks/generate.py` followed by
`make generate`. The test files are hand-written, not generated (`generate.py:635-638` writes
only the two clients), so the threat model is the right one — the attacker does not control
the tests.

**Escape 6 — a `Symbol.for`-keyed TypeScript member.** This is the one that matters, because
it defeats all **four** TypeScript checks at once, including the constructor probe this round
added.

```
const SEND: unique symbol = Symbol.for("darkmem.send");
...
  [SEND](
    path: string,
    body: Record<string, unknown>,
  ): Promise<unknown> {
    return this.#post<unknown>(path, body, false);
  }
```

Measured at HEAD with this mutation applied and regenerated: `sdks/python` **31 passed**,
`sdks/ts` **20 passed**, `backend/tests/test_sdk_generator.py` +
`test_sdk_contract_conformance.py` **30 passed**, `make build` **green**. A scratch vitest
then drove it:

```
DRILL URL  http://localhost:8000/api/v1/knowledge/facts/abc-123/ratify
DRILL AUTH Bearer jwt
DRILL BODY {"verdict":"confirm"}
DRILL OUT  {"status":"confirmed"}
```

Four independent gaps compose, and the round's own fix does not touch any of them:

- `Object.getOwnPropertyNames` **does not enumerate symbol keys** in any of its three homes.
  All three run-time probes use it, so the prototype probe, the instance probe and the new
  constructor probe are each blind to the same construct. `getOwnPropertySymbols` is the
  missing call.
- The source regex requires the member name to start `[A-Za-z_$#]`; a computed key starts
  `[`, so `_typescript_class_members` never matches it.
- `const SEND` is not `export`ed, so `_typescript_exports` does not see it, and it sits above
  `export class Darkmem {` so the class-body split does not reach it.
- `Symbol.for` uses the **global** symbol registry, so the key is reachable by any caller who
  can type the string — this is not a private member in any sense.

The file's own claim (`test_surface.py:34-36`) that the probes "cover all three JavaScript
homes a member can have — prototype, instance, constructor" is true about *where* a member can
live and false about *how it can be keyed*. That is the same error as the previous two rounds:
the enumeration is of the instances someone thought of.

**Escape 7 — a Python instance-level verb.** The Python client has **no instance probe at
all**, which is the asymmetry the round's own TypeScript work makes visible: `client.test.ts`
asserts `Object.getOwnPropertyNames(new Darkmem({}))` is empty, and nothing does the
equivalent for Python.

```
        self.send = lambda path, body: httpx.post(
            f"{self.base_url}{path}",
            json=body,
            headers={"Authorization": f"Bearer {self.token}"},
        ).json()
```

Measured: `sdks/python` **31 passed**, `sdks/ts` **20 passed**, backend SDK suites **30
passed**, `make build` **green**. Driven:

```
DRILL URL   http://localhost:8000/api/v1/knowledge/facts/abc-123/ratify
DRILL AUTH  Bearer jwt
DRILL OUT   {'status': 'confirmed'}
vars(Darkmem) unchanged: ['__dict__', '__doc__', '__firstlineno__', '__init__', '__module__',
                          '__static_attributes__', '__weakref__', '_post', 'capture',
                          'declare_context', 'search']
instance dict: ['_context', 'base_url', 'project', 'send', 'token']
```

`set(vars(Darkmem)) == PY_CLASS_MEMBERS` is byte-identical to the whitelist because the new
verb is not on the class. This round replaced the `startswith("_")` filter with an exact
`vars()` whitelist — a real improvement that closes the dunder escape — but `vars(Darkmem)`
is the **class** dict, and the escape that defeated the TypeScript scan in round 1 (drill A,
a public instance property holding a function) has never been closed on the Python side.

**A third, supporting result: the source scan can be silenced outright.** The brief asked
whether a literal can collide with a `__STR0__` placeholder. It can, two ways, both measured:

- **Placeholder re-substitution.** `_typescript_without_comments` restores literals in
  increasing index order with `str.replace`, so a literal whose *content* is a later
  placeholder gets substituted a second time. Input `const b = "__STR1__";\nconst a = "{";`
  returns `const b = ""{"";\nconst a = "{";` — a brace that was inside a string is now
  outside one.
- **Escaped quotes.** `_STRING_LITERAL` is `"[^"\n]*"`, which stops at an escaped quote:
  `"\"{"` masks as `"\"` and leaves a bare `{`.

Either one unbalances the depth walk. Placed *before* the verbs it fails loudly (the scan
reports `['constructor']` only). Placed *after* them it is silent — measured on a class body
with the corruption inside `#post`:

```
members seen : ['#post', 'capture', 'constructor', 'declareContext', 'search']
SCAN PASSES  : True      ('#post' still asserted present)
'send' HIDDEN: True
```

So `test_the_typescript_class_exposes_exactly_three_members` and
`test_the_typescript_transport_is_hard_private` both pass while a fourth verb declared after
the corruption is invisible. This does not escape the run-time probes on its own (a plain
prototype method still shows up); it matters because it removes the source scan as
independent evidence, leaving the probes alone — and escape 6 walks past those.

**Why this is NOT ADDRESSED rather than a new finding.** Identical reasoning to round 1's.
The finding is that the scans cannot detect the class of violation they exist to detect. Two
more named instances were closed and the class was not. The docstring's framing — "no check
here filters by kind *or* by name shape any more" — is not true: the run-time probes filter by
key *type* (string, never symbol), and the Python checks filter by *where* the member lives
(class, never instance).

**Sharpened fix, third attempt.** Make the checks total rather than enumerated:

- TypeScript: on each of the three homes assert `getOwnPropertyNames(x).concat(
  getOwnPropertySymbols(x).map(String))` against the whitelist, not `getOwnPropertyNames`
  alone. Three one-line changes, and they close escape 6 in every home at once.
- Python: add the instance probe the TypeScript side already has —
  `set(vars(Darkmem(base_url="x"))) == {"base_url", "token", "project", "_context"}`.
- Optional but cheap: delete `_typescript_class_members`' hand-rolled masking and depth walk.
  It is now the weakest link in the file, and once the symbol probes exist it carries no
  evidence the run-time probes do not.

### 2. N-1's completeness — is the untraced shape actually unreachable?

**Yes, from both clients, verified rather than read.**

- TypeScript: `with_trace: true` is a literal in the emitted body (`client.ts:143`), and
  `#post`'s payload filter drops only `undefined`/`null`, so `true` always reaches the wire.
- Python: `with_trace` is gone from the signature entirely (`client.py:79-86`);
  `search("q", with_trace=False)` raises `TypeError` at call time, asserted at
  `sdks/python/tests/test_client.py:146-147`.

**Is the new conformance test measuring the right thing?** Partly. Driven:

| Assertion | Verdict |
|---|---|
| `test_an_untraced_search_discards_the_declaration` | **Real.** Drives the live door; asserts 200 and `envelope is None`. Cannot pass vacuously — a missing `envelope` key would `KeyError`. |
| `TS_EXPRESSIONS["with_trace"] == "true"` | **Real.** Mutation: restore `"options.withTrace ?? true"` → red. |
| `PY_EXPRESSIONS["with_trace"] == "True"` | **Real.** |
| the emitted-Python-signature check | **Real.** Mutation: re-add `with_trace: bool = True` to the template signature → red. |

**But the guard is one-sided, and the missing side is exploitable.** See **NEW-3**: nothing
asserts the *TypeScript* signature. A mutation that puts `withTrace?: boolean` back into the
options type while leaving `TS_EXPRESSIONS["with_trace"] == "true"` passes `make build`,
`sdks/ts` 20, `sdks/python` 31 and the backend's 30 — and produces a client that
type-accepts `withTrace: false` and posts `with_trace: true` anyway. Measured:

```
DRILL-C BODY {"query":"q","with_trace":true}
```

That is the caller's explicit argument being discarded by the client rather than by the
server — narrower than N-1 but the same silent-drop family, and it is what the round's
Python-only pin fails to cover.

### 3. The comment-stripper fix

Answered under item 1 above. Both collisions the brief asked about are real; a nested literal
is handled correctly (the restore order is safe when a literal's content names an *earlier*
placeholder, and only breaks on a *later* one); an unterminated literal on one line simply
does not mask, which is benign for braces but leaves the `//` stripper exposed the same way
the docstring's own `http://` bug was.

### 4. N-5 / N-6's refactor

**`get_adapters` is unchanged for every existing caller.** `_resolve`'s adapters half is
untouched by this diff — the only edit adds a key to `rejected`, which `get_adapters`
discards. Verified by inspection of the diff and by `tests/test_inject_adapters.py` (its 
seven `get_adapters` call sites) staying green.

**`get_registry` returns exactly `_resolve`'s tuple**, one merge per GET. The counting test is
real: mutation restoring `get_adapters(...) , get_adapter_rejections(...)` →
`test_the_registry_is_merged_once_per_request` red.

**But not every previously-rejected shape still gets the right treatment, and one newly
rejected shape is wrong.** See **NEW-2**: the new arm rejects from the *raw* loop while the
shipped default survives into the *merged* loop, so a non-object override of a **known** tool
puts that tool in `targets` and `rejected` simultaneously. The shipped test picks
`{"stringly": "nope"}` — an unknown tool — which is the one shape that cannot expose it.

### 5. N-7's render-phase setState

**It cannot loop, and it does not swallow a committed edit.** Both guards are
adjust-state-on-prop-change with a scalar comparison, so each is false on the immediate
re-render; React would raise "Too many re-renders" otherwise, and the suite is green. Walked
every ordering:

| Sequence | Behaviour |
|---|---|
| write fails → `rejected` false→true | draft reset to `budget`. Correct — this is the fix. |
| user re-edits, blurs → `mutate` sets pending, `isError` false | `sawRejection` true→false, **no** reset. The edit survives. |
| second failure | reset again. Correct. |
| success | `seed !== budget` takes over and re-seeds. Correct. |
| failure *and* a refetch moving `budget` in one render | both guards fire, both `setDraft(String(budget))`. Same value, no loop. |

Mutation: delete `if (sawRejection !== rejected) {...}` → the new test reddens (1 failed | 10
passed). The guard is real.

**One interaction it does introduce**: `rejected={setPolicy.isError}` cannot tell which
control failed, and the curb switch shares the same mutation. See **NEW-5**.

---

## New findings introduced by this round's fixes

### NEW-1 (Important) — doc 15 §6's diagram and its own amendment still declare `withTrace?`, which this fix removed

`docs/design/15-distribution-and-integration.md:243`:

> `SRCH["search(query, project?, context?, withTrace?)"]`

and `:255`, inside the amendment block:

> **`search` lost `fused?` and **gained `withTrace?`**, and its arrow now names a specific
> door.**

Both are now false — the generator emits `search(query, {project?, limit?, context?})` in
TypeScript and `search(self, query, *, project, limit, context)` in Python. Worse, the
amendment block opens with *"The signatures above are the ones the generator emits"*, which
this round made untrue for the second time.

This is I-3's shape and then N-3's shape, now a third time, and this occurrence was **created
by the fix**: round 1's amendment wrote `withTrace?` into the diagram, and round 2 deleted the
argument from both clients without returning to it. Nothing pins doc 15 against the generator
— §6 is cited in prose all over `sdks/` and `backend/tests/`, but the filename
`15-distribution` appears in neither, so no test reads the document it is conforming to.

A reader implementing against §6 writes `withTrace: false`, and on TypeScript today the
compiler rejects it while the doc promises it. Fix: amend the diagram label and the bullet,
and state the reason (the door resolves the declaration only on the traced branch) where the
argument used to be named.

### NEW-2 (Important) — a non-object entry for a **known** tool now appears as live and refused at the same time

The new arm at `inject_adapters.py:174-181` writes `rejected[tool]` from the loop over the
**raw** config row, but the shipped default for that tool is already in `merged` and survives
into the adapters loop untouched. Every other rejection path `continue`s out of the *merged*
loop, so a rejected tool is genuinely absent from `targets`; this one is not.

Measured through the real app with `inject_adapters = {"cursor": "nope"}`:

```
DRILL targets : ['claude-code', 'cline', 'codex', 'cursor']
DRILL rejected: [('cursor', 'the entry is str, not an object — an ada...')]
DRILL in BOTH lists: ['cursor']
```

The tab renders both at once (`distribution-tab.tsx:249-281`): `cursor →
.cursor/rules/darkmem.mdc` under "Managed block per target", and directly below,
*"1 configured target refused — **no block is written for it**: cursor: the entry is str, not
an object"*. A block **is** written for cursor, at the default path. The screen asserts
something that is not in force — the exact class M-9, M-10 and N-7 were raised about, now on
the surface that was being fixed.

It is also a **regression**: before this diff the same config produced `targets` with cursor
and `rejected == []`, which was correct.

The control case is fine — `{"stringly": "nope"}` names an unknown tool, which is absent from
`targets` and present in `rejected`, and that is the shape
`test_a_non_object_entry_is_named_too` asserts. The test cannot fail on the defect.

Fix: reject only when the entry has no surviving default (`if tool not in merged`), or say
something different for the override case — *"the entry is not an object; the shipped default
is still in force"* — which is the true sentence and is what the operator needs.

### NEW-3 (Minor) — the `withTrace` pin covers Python's signature and not TypeScript's

`test_the_clients_never_send_that_shape` asserts both expression constants and the *emitted
Python* signature. There is no TypeScript equivalent, and Drill C above shows the gap is
walkable: `withTrace?: boolean` back in the options type passes `make build`, `sdks/ts` 20,
`sdks/python` 31 and backend 30, and silently ignores the caller.

Structural, not just an omission: `sdks/ts` has **no `tsconfig.json`**, `make build`
typechecks `ts/src/client.ts` alone, and `npm test` is `vitest run` (transpile, no
typecheck) — so there is no place in the gate where a `// @ts-expect-error` on the test side
could fail the build. The cheap fix is a source assertion in the same test:
`"withTrace" not in sdk_generate.render_typescript("digest")`.

### NEW-4 (Minor) — `get_adapter_rejections` now has zero callers, and `reject_reason`'s docstring still says it renders the surface

The N-6 fix re-pointed the one caller to `get_registry`. `get_adapter_rejections` is now
reachable from nothing — not `backend/app`, not `backend/tests` — while staying in `__all__`
(`inject_adapters.py:54`). And `reject_reason`'s docstring (`:135-137`) still reads:

> One predicate with two readers — the registry below and :func:`get_adapter_rejections`,
> **which the distribution surface renders**.

The distribution surface renders `get_registry`. This is N-2's own defect — a docstring in the
present tense about a producer that moved — recreated by the commit that fixed N-2, one file
over. Either delete the function or say it has no caller.

### NEW-5 (Minor) — a failed **curb** write wipes an uncommitted **budget** edit

`rejected={setPolicy.isError}` (`distribution-tab.tsx:289`) is the mutation's error state, and
the curb switch (`:236-238`) shares that mutation. A human mid-edit on the budget who then
flips the curb, and whose curb write fails, loses their typing. Measured:

```
DRILL budget field after failed CURB write: 2000   (typed: 5000)
```

The screen stays internally consistent — the banner shows and the field does show server
truth — so this is genuinely Minor. But it is new: before this diff the draft survived.
Closing it means distinguishing which control failed, e.g. keying the reset on the budget
mutation's own variables rather than on the shared `isError`.

### NEW-6 (Minor) — `_mask_strings` corrupts on a placeholder collision and on an escaped quote

Both reproductions are in item 1 above. Consequence is a silently truncated class-member scan
rather than a false pass on its own, but it removes the source scan's independence from the
run-time probes, which is exactly the redundancy `test_surface.py`'s docstring claims.

### NEW-7 (Minor) — doc 15 §6 still has `capture` declaring context, one clause after the amendment

The fix corrected both sentences N-3 named. The **same sentence** it edited closes:

> These are the three surfaces every distribution client needs — the browser extension
> captures, an embedded agent searches, **and both declare context** — and nothing more
> belongs in a *minimal* SDK.

A browser extension that only captures cannot usefully declare context: `capture` carries no
header and the door reads none. The clause is one remove from N-3's claim rather than a
restatement of it, which is why it is Minor and not a re-open — but it is the fourth time an
amendment in this section has left a neighbouring sentence saying the opposite.

---

## Deferred minors — real, out of this fix's scope, recorded not looped on

- **The SDK's response types are hand-written with no contract binding at all.** N-8's fix is
  correct today (`CaptureAck.status` is `Literal["accepted"]` at
  `backend/app/schemas/memory.py:81`), but nothing pins it: `POST /api/v1/memories` declares a
  bare `200` with an **empty** schema `{}` in the live OpenAPI document, `CaptureAck` is not in
  `components.schemas`, and `_hash` therefore cannot move when the literal drifts. The
  generator's premise — "the SDK cannot expose a behaviour the contract does not" — holds for
  request bodies and not for responses. Pre-dates this round.
- **`docs/eval/2026-08-10-retrieval-eval.md` is modified in the working tree at HEAD** (run id
  and three latency percentiles differ from the committed `bb8a71de` artifact). Pre-existing
  when this review started; not produced by any drill here. It means the eval artifact is not
  reproducible run-to-run, so `git diff --exit-code` cannot be used on it the way it is on the
  SDK output.

---

## Verification run

Every number measured during this review, at HEAD, tree clean apart from the pre-existing
eval artifact noted above.

| Command | Result |
|---|---|
| `cd sdks && make generate && git diff --exit-code -- .` | clean (`contract fad5ee9edc9b2ba0`) |
| `cd sdks && make build` | green |
| `cd sdks/python && python -m pytest -q` | **31 passed** |
| `cd sdks/ts && npm test` | **20 passed** |
| `cd backend && pytest -q tests/test_sdk_generator.py tests/test_sdk_contract_conformance.py` | **30 passed** |
| `cd backend && pytest -q tests/test_distribution.py` | **17 passed** |
| `cd frontend && npm test` | **752 passed** (111 files) |
| `cd backend && python -m pytest -q` | **4912 passed, 19 skipped** |

Mutation drills (each reverted from a private copy of the single mutated file; tree confirmed
clean after each):

| Drill | Expected | Measured |
|---|---|---|
| **I-1 escape 6 (TS `Symbol.for`-keyed member)** | **should be red** | **all suites green; ratify driven** |
| **I-1 escape 7 (Python instance `send`)** | **should be red** | **all suites green; ratify driven** |
| source scan: placeholder collision `"__STR1__"` + `"{"` | scan intact | scan sees `['constructor']` only |
| source scan: escaped quote `"\"{"` | scan intact | scan sees `['constructor']` only |
| source scan: escaped quote placed after the three verbs | scan red | **scan passes; fourth verb hidden** |
| **N-1 partial re-add (`withTrace?` in the TS type only)** | **should be red** | **all suites green; `withTrace:false` discarded** |
| N-1 full re-add (signature + both expressions) | red | `test_the_clients_never_send_that_shape` red |
| N-1 Python signature re-add | red | same test red |
| **N-5 non-object override of a known tool** | one list | **`cursor` in `targets` AND `rejected`** |
| N-5 guard: delete the `rejected[tool]` assignment | red | `test_a_non_object_entry_is_named_too` red |
| N-6 guard: restore the two-pass `get_registry` | red | `test_the_registry_is_merged_once_per_request` red |
| N-7 guard: delete the `sawRejection` reset | red | 1 failed / 10 passed in the distribution file |
| **N-7 interaction: failed curb write vs uncommitted budget edit** | edit survives | **draft wiped to `2000`** |
