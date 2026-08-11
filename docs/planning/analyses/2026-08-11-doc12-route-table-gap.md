# Analysis — doc 12's route table vs the tree (2026-08-11 brief)

**Ruled tier: 3.** The T3.06 filing as Tier 2 was an under-tiering: doc 12 declares itself the
complete external contract and measurement shows it is not — "a design doc is wrong" is runbook
§5's Tier-3 test verbatim. The E3 amendment-log row should read Tier 3 (the controller's edit).

## 1. The filed finding, verified rather than inherited

Both of the implementer's claims hold, checked against the app itself, not against route files:

- `GET /api/v1/knowledge/facts` and `GET /api/v1/knowledge/articles` are both live
  (`backend/app/api/routes/facts.py:39`, `articles.py:34`), both behind `Depends(require_auth)`
  (`facts.py:48`, `articles.py:39`), both classified in `test_door_parity.py`
  (`knowledge.facts_list`, `knowledge.articles_list`, REST single-door with stated reasons), and
  tested (`test_articles_read_surface.py`, `test_api/test_rest_conformance.py`, the parity suite).
- Doc 12 §2's knowledge-vault additions row named six routes and neither list door. Confirmed
  against the pre-amendment text.

## 2. The sweep — method and both-direction diff

**Method.** The live surface was derived from `app.main:app`'s router flattened to `APIRoute`
leaves exactly as `test_door_parity.py::_iter_api_routes` does (HEAD excluded), and the FastMCP
registry via `mcp.list_tools()` — imported in-process, no database, no `rg` over route files.
Result: **135 method-path REST routes, 27 MCP tools.** Every route doc 12 names anywhere
(§2 both tables, §3, §7) was then checked against that set, and every live route against the doc.

### Shipped but unlisted — 34 routes, 2 tools

Routes appearing nowhere in doc 12 before the amendment, with the arithmetic:

| Group | Routes | Count |
|---|---|---|
| Checkpoints | `POST /checkpoints`, `GET /checkpoints/latest` | 2 |
| Memory-buffer triage | `GET ""`, `GET /stats`, `DELETE /{id}`, `POST /{id}/requeue` | 4 |
| Distribution | `GET /distribution`, `PUT /distribution/policy` | 2 |
| Review queue | `GET /facts`, `/articles`, `/counts`, `POST /facts/{id}/reject`, `/dismiss-suspicion` | 5 |
| Hygiene queue | 5 reads + 3 bulk actions | 8 |
| Dream digest | 2 reads + 2 undo doors | 4 |
| Knowledge topics | 3 reads + accept/dismiss | 5 |
| Auth reads | `GET /auth/audit`, `GET /auth/security-posture` | 2 |
| Vault list doors | `GET /knowledge/facts`, `GET /knowledge/articles` | 2 |
| **Total** | | **34** |

Rechecked mechanically against the live dump (script in the session): the seven group prefixes
yield 2+4+2+5+8+4+5 = 30, plus the 4 individual routes = 34. MCP: doc 12's families count
10 memory + 11 code + 4 shipped vault = 25 of 27; the 2 unlisted tools are `checkpoint_save` /
`checkpoint_latest` (two-door with the checkpoint routes, per the parity table).

The §2 group table's header says "Representative routes", so per-route omissions inside a listed
group (e.g. `PUT /jobs/{key}`, `GET /config/llm`, the `/setup/fs/*` steps) were **not** counted —
the table's own granularity is the group, and every group-level claim it made was true. The 34
are routes in groups with **no row at all** (or, for the four individual ones, surfaces the named
row demonstrably tried to enumerate and missed).

### Listed but absent — 5 routes, 2 tools, in two very different classes

All five verified absent from the live router:

1. **Phantoms superseded by shipped design (the dangerous class):**
   - `GET /knowledge/review` — shipped as the three `/review-queue` reads.
   - `PATCH /knowledge/facts/{id}/review` ("clear or set `review_state`") — never built, and its
     semantics contradict the settled corpus: `review_state` is total-derived
     (`verification_ladder.derive_review_state`, `REVIEW_OPENERS`), "adding an opener is appending
     a predicate, never adding a writer". The shipped human actions are
     `POST /review-queue/facts/{id}/reject` and `/dismiss-suspicion`. This is a doc-versus-corpus
     contradiction, not just a stale path — doc 12 was the odd one out against docs 08/09 and the
     tree, which agree with each other, so amending doc 12 is the resolution.
2. **Honest targets, still unshipped, correctly labelled target-new:**
   `GET /knowledge/facts/{id}/dispute` + `dispute_inspect`, `POST /knowledge/context/validate` +
   `context_validate`, `POST /knowledge/articles/{id}/ratify`. No contradiction — but now that the
   additions table's other rows have shipped, they needed explicit still-unshipped marking so the
   table cannot be read as uniformly live.

No phantom was found in the §2 group table: every route it named exists (`GET /code/wiki/{id}`
differs only in parameter name from `/code/wiki/{repo_id}`). The three dropped LLM-indirection
routes are measured gone, as the subtraction row claims.

## 3. The tier ruling, with the runbook's own test

Runbook §5: Tier 2 is "the change reaches beyond this task" — true here, but insufficient.
Tier 3 is "the discovery contradicts the design corpus or the roadmap: a design doc is wrong or
ambiguous". That is this finding exactly, three times over:

1. **Doc 12 §1's completeness claim is falsified by measurement** — 34 routes and 2 tools of the
   shipped surface unnamed, in a doc whose first bolded sentence is "every REST route and MCP tool".
2. **Doc 12 §2/§3 name routes that do not and (for `PATCH .../review`) must not exist** — the
   review-resolution write's stated semantics contradict docs 08/09's settled no-writer derivation.
3. **The honesty-tag arm of Tier 3 is literally engaged**: the additions table's target-new rows
   include six routes that have since shipped; leaving them untagged misleads in the opposite
   direction (a reader assuming `GET /knowledge/facts/{id}` is still unbuilt, as T3.06's reader
   nearly did in reverse).

**Precedent seals it:** the two prior corrections to exactly these claims in exactly this doc —
T1.42a (§5's source-resolution chain) and T1.42d (§3's "each with a REST twin" tool claim) — were
both filed **Tier-3, resolved on measurement**. The same class of finding in the same document
cannot be Tier 2 the third time.

**What Tier 3 obliges that Tier 2 did not:**
- **Stop-and-escalate before closing.** The implementer must record, not fill — which T3.06's
  implementer in fact did ("recorded rather than silently filled"), so the under-tiering cost
  nothing in behaviour, only in filing. The Fable-tier analysis Tier 3 requires is this dispatch.
- **The amendment must be a ruled, dated, in-place note in the doc's own amendment idiom**
  (the T1.42a/T1.42d form), never a silent table edit — done, see §4 below.
- **The E3 amendment-log row's tier should be corrected 2 → 3** — the controller's edit; the log
  is out of this task's lane.
- **The corpus-doc-wins default needed an explicit resolution** for the `PATCH .../review`
  contradiction: doc 12 loses to the docs-08/09-plus-tree majority, recorded in the amendment
  rather than decided silently.

## 4. What was amended (doc 12 only, uncommitted)

All edits in `docs/design/12-api-and-mcp-contract.md`, in its own voice and amendment idiom:

- **§2 group table**: seven new rows (Checkpoints, Memory-buffer triage, Distribution, Review
  queue, Hygiene queue, Dream digest, Knowledge topics); the Auth row gains `GET /audit` and
  `GET /security-posture`; an italic provenance line ties the additions to the dated note.
- **§2 additions table**: the knowledge-vault row gains both list doors with a dated marker; the
  review-and-ratify row gains a bold dated pointer to the supersession note.
- **§2 dated amendment note** (before "The three documented deviations…"): the measurement method,
  the 135/27 numbers, the 34-route arithmetic shown, the two phantoms and their shipped
  replacements, the three still-honest targets, the shipped-status reclassification of the
  additions rows, and the 25-of-27 tool arithmetic pointing at §3.
- **§3 dated amendment note** (before the tool-families diagram): the 27-tool count with
  `checkpoint_save`/`checkpoint_latest` named, and the `PATCH .../review` correction with the
  derived-`review_state` reasoning and the shipped action doors.

Nothing else was edited. Doc 09, the E3 log, `progress.md`, and the parity artefacts are untouched.

## 5. Can the table be kept honest mechanically? Yes — with a carve-out for targets

**Yes, and the machinery already exists in the repo.** `test_door_parity.py` proves the pattern
twice over: it enumerates the live router (so an unclassified route fails the build) and it pins a
committed markdown table to a generated render between `BEGIN/END` markers
(`test_the_committed_table_is_the_enforced_table`), so `docs/two-door-parity.md` cannot drift.

**What the test would assert for doc 12.** Doc 12 differs from the parity doc in one load-bearing
way: it deliberately names *target* routes that do not exist, so a naive `listed == live`
assertion would fail on every honest target. The workable shape is three assertions:

1. **Coverage**: every live route (and MCP tool) resolves to a group/row in a small
   machine-readable inventory — most cheaply, reuse `PARITY_TABLE` itself as the source (it is
   already exhaustive over both doors) and render a generated appendix into doc 12 between
   markers, exactly as `render_markdown()` does for the parity doc. A new route then fails
   `test_every_rest_route_is_classified` first and the doc regenerates from the same edit.
2. **No phantoms among exists-today claims**: every route the doc marks exists-today (the group
   table plus any additions row not tagged still-unshipped) must be in the live set. This is the
   check that would have caught `GET /knowledge/review` the day `/review-queue` shipped.
3. **Targets are exempt but enumerated**: routes tagged target-new live outside the generated
   block in a short explicit list, so the exemption is visible rather than structural.

The cost is that part of §2 becomes generated rather than authored, and doc 12's prose tables
would need either markers or a companion appendix. The benefit is exactly what this sweep shows
is needed: the doc went stale by 34 routes across at least seven landings with nobody looking.
Recommended, not built (per the brief).

## 6. Adjacent findings

- `docs/two-door-parity.md` + `PARITY_TABLE` are **not** stale — every live route is classified
  there. The mechanical pin works where it exists; doc 12 is the surface without one.
- Doc 13 line 140's `/knowledge/review` is a *frontend* route (target-new UI path), not the API
  path — the amendment says so explicitly to prevent a future sweep misreading it as the same
  phantom.
- The §2 group table's "Representative routes" header quietly caps what any completeness claim
  can mean for it; if the mechanical pin of §5 is built, that header's escape hatch should close
  with it.

## 7. Verification record

- Live-surface derivation run twice (initial dump + independent recheck script): 135 routes,
  27 tools, group counts 2/4/2/5/8/4/5, individual 4, total 34; all five listed-but-absent routes
  confirmed absent (`phantoms absent from live: True`).
- No gate run was live during the sweep (`pgrep -f gate.sh` matched only the probe's own shell);
  no database was touched; no processes left running.
- No test suite was run: this task changes one design doc and adds one analysis file — nothing
  the floor compiles or collects. The floor's last state on this branch is the controller's
  record; nothing here could have changed it.
- Work left uncommitted per the brief.
