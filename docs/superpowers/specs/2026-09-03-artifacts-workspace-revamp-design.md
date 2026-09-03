# The Artifacts workspace — a document browser, not a document list

**Date:** 2026-09-03. **Status:** design, owner-approved in shape, awaiting
spec review. **Scope:** the Artifacts tab of `/projects/$project`.

**The Progress tab is deliberately not in this spec.** It is a separate
project with a different shape and one unmade ruling of its own (§10).

## 1. What is wrong today

The owner's report, each item traced to code rather than restated:

| Complaint | What it actually is |
|---|---|
| "docs tree does not render as a file browser tree" | **Corrected 2026-09-03 after reading the component.** It already uses the full `TreeView` primitive — branches, disclosure indicators, keyboard nav all come from the library. Its actual defect is that it **expands every folder on every render**: `allFolderPaths` is collected and passed as the expanded set, so 475 documents under one root, five levels deep, render as one ~475-row wall. Expansion is uncontrolled and unpersisted |
| "expand to full width (not view-width)" | The pane is a fixed `w-72` rail beside `flex-1`, inside the standard chrome container |
| "md file does not render correctly" | Four named defects in `block-view.tsx` — see §4 |
| "no ability to manage docs" | Every route exists and none is wired — see §5 |
| "validate with the memories" | Redefined by the owner: *show which memories relate to this doc, so an agent amending it knows which memories to update, replace or deprecate* (§6) |

## 2. The finding that shapes everything

**Production holds 475 documents and 49,310 blocks, and 0 memories,
0 entities, 0 facts.**

Two consequences, both load-bearing:

1. **Related-memories cannot work by reading the graph, because there is no
   graph.** Any design that joins documents to memories through entities
   returns empty for all 475 documents.
2. **The shipped Connections feature is already vacuous for the same reason.**
   `document_connections.py` reads `entities` + the lift's provenance; with
   zero entities it returns nothing, silently, today.

This is the same hole that blocks G-E and `T3.22` ("pending a corpus"). The
documents were imported; nothing was ever lifted.

**Owner ruling, 2026-09-03: lifting is in scope for this project.** Building
related-memories without it would ship an empty panel and call it a feature.

## 3. Layout and interaction — the UI/UX, which is the point of the revamp

The page becomes a three-pane browser. **Every primitive below already exists
in `darkraise-ui`; this spec adds no local component**, per CLAUDE.md's
library-first rule. The inventory was checked: `tree-view`, `resizable`,
`scroll-area`, `context-menu`, `breadcrumb`, `command`, `dropdown-menu`,
`sheet`, `toolbar`, `separator`, `badge`, `empty-state`, `skeleton`, `sonner`.

### 3.1 Frame

```
┌─ toolbar: project · search · view toggle · lift-all ──────────────┐
├──────────┬──────────────────────────────────┬────────────────────┤
│ tree     │ reader                           │ inspector (toggle) │
│ (resiz.) │ breadcrumb + outline + blocks    │ summary / memories │
│          │                                  │ / connections      │
└──────────┴──────────────────────────────────┴────────────────────┘
```

- **Full-bleed.** The route opts out of the centred chrome container. A file
  browser needs horizontal room; today the reader is squeezed beside a fixed
  288px rail inside a max-width page.
- **`ResizablePanelGroup` / `ResizablePanel` / `ResizableHandle`** for the two
  splits, with widths persisted per project in `localStorage`. A browser whose
  panes reset on every visit is not a browser.
- **`ScrollArea` per pane.** Independent scrolling is what makes a long tree
  usable beside a long document; today the whole page scrolls as one.
- The inspector is collapsible and **closed by default** — it is a third pane
  of chrome and most reading does not need it.

### 3.2 The tree

- **The primitive stays.** `DocumentTree` already renders `TreeViewBranch` /
  `TreeViewBranchControl` / `TreeViewBranchIndicator` / `TreeViewItem`, so
  disclosure and keyboard navigation are already correct and are not rebuilt.
- **Expansion becomes controlled and persisted.** Today `allFolderPaths`
  expands everything on every render, which is why 475 documents read as a
  wall. `TreeView` accepts `expanded: string[]` + `onExpandedChange`, so the
  component takes the controlled pair and the workspace persists it per
  project in `localStorage`.
- **Default expansion is the path to the selected document, not everything.**
  With nothing selected, only the root level opens. This is the single change
  that turns the current wall into something navigable.
- **Folder rows show a child count**; document rows show a **`badge` when the
  document is not lifted** (§6), because that is the state that explains an
  empty inspector.
- `ContextMenu` on every row — open, summarize, lift, copy URI, delete. This
  is the affordance a file browser is expected to have and is where document
  management lives (§5).
- `Command` palette for quick-open by path, the way Ctrl+P works in VS Code.
  The tree is for browsing; the palette is for going somewhere known.
  **The chord is deliberately left unbound in this spec.** A grep of
  `frontend/src` finds no Ctrl+K handler, which means the chord is owned inside
  `darkraise-ui` rather than by this app — and CLAUDE.md records exactly one
  past regression here: a hand-rolled palette that suppressed the library's
  built-in Ctrl+K and became a duplicate search box. Implementation verifies
  the live binding in the running app first, then either scopes this palette to
  the workspace route or takes a different chord. **Adding a second global
  Ctrl+K is the one outcome this bullet exists to prevent.**

### 3.3 The reader

- `Breadcrumb` across the top showing the document's URI path, each segment
  clicking back into the tree.
- The existing outline rail stays, but becomes sticky within its `ScrollArea`
  so it is usable in a long document.
- The block body renders per §4.
- A search hit scrolls to and marks its block — already shipped 2026-09-03 via
  `focusBlockId`; this spec keeps it and adds the breadcrumb context around it.

### 3.4 States

Every pane distinguishes **loading / failed / empty / populated**, using
`skeleton` for the first and an explicit destructive line for the second. This
is not decoration: a sweep on 2026-09-03 found nine surfaces rendering a
positive claim ("no documents", "no repositories") on a failed read. The tree,
reader and each inspector panel each get all four states.

## 4. Markdown rendering — four defects, named

`block-view.tsx` is 96 lines and handles seven block types. The defects:

1. **Every heading renders `<h3>`.** `properties.level` is on the read surface
   (`BlockRowModel.properties`, added by increment 8) and unused, so an `h1`
   and an `h4` are visually identical. Render the real level.
2. **Heading text bypasses `<Markdown>`**, so inline code in a heading shows
   literal backticks.
3. **Every list item renders `•`.** `properties` carries the marker; an
   ordered list renders as bullets.
4. **Blocks render flat.** `document-reader.tsx` states this is deliberate —
   defensible for a reader, wrong for a browser, and it means nested lists lose
   their nesting. Reconstruct nesting from `properties` + `order_index`.

**Not in scope:** a markdown editor. Increment 8's block verbs already provide
editing and this spec surfaces them (§5); a WYSIWYG surface is a separate
project.

## 5. Document management — wiring, not new backend

Every route below is shipped and unused by this page:

| Action | Route | Note |
|---|---|---|
| Update | `POST /api/v1/documents` | The `(project, uri)` upsert **is** update. Send `expected_hash` — it is a compare-and-set and answers 409 on a stale hash |
| Delete | `DELETE /documents/{id}` | Withdraws fact provenance, then expires facts left unsourced |
| Summarize | `GET /{id}/summary` | `document_summary.py`, on the `summarization` purpose |
| Per-block edit | `PATCH/POST/DELETE .../blocks/…` | Increment 8's four verbs |
| Connections | `GET /{id}/connections` | Vacuous until lifting (§2) |
| Grounded Q&A | `POST /documents/qa` | G-F cleared 2026-09-03, so it may now serve a grounded label |

**Delete is confirmed through `alert-dialog`, never a bare button**, and the
dialog states what delete does beyond removing the row: it withdraws block
sources and expires any fact left with no surviving source.

**Update uses `expected_hash` from the last read.** Omitting it is
last-writer-wins, which is the wrong default for a surface where an agent and a
human edit the same document.

## 6. Lifting and related memories — the only new backend

### 6.1 The lift door

`documents.py` records: *"**No lift door.** `lift_document` is on-demand by
design and a route is the easiest way for something to call it on a schedule;
nothing in EH1 needs one **before a human asks**."*

**This spec is the human asking, so the route is added — and the reason the
note gives is preserved rather than discarded.** The concern is *scheduled*
calling, not human calling. So:

- `POST /api/v1/documents/{id}/lift`, behind `require_auth` and
  `refuse_when_read_only` (it writes, and it dials out through the LLM).
- **It declares no `config_schema` and is registered in no `JobRegistry` job.**
  A test asserts the route is unreachable from the job registry, so the hazard
  the note names cannot arrive later by accident.
- Idempotent by construction: `lift_document` strips the prior lift keyed on
  `document_id` before rewriting, so a second lift replaces the first.
- Returns the `LiftResult`; `None` (no blocks) is reported as "nothing to
  lift", never as success.

A **bulk lift** for the 475 already-filed documents runs as a one-shot host
script through this route, not as a job — same reasoning.

### 6.2 Related memories

Given a lifted document, the entities its propositions minted carry
`entities.memory_ids[]`, which names every memory asserting the same thing.
That is the whole read.

- **No LLM call**, matching `document_connections.py`, whose module contract
  says the moment a connections feature generates prose it has become unbadged
  synthesis and belongs to doc 09.
- **No new table.**
- **It never touches the block channel**, so `test_block_retrieval.py`'s three
  scans and the retrieval firewall are untouched. The read goes
  document → lifted propositions → entities → memories; no block row crosses
  into ranking and no fact is minted.
- **Shared-entity count is evidence, not a score.** Ordering is by how many
  entities are shared, and nothing normalises that into a similarity number —
  the rule `document_connections.py` already states for itself.

**The UI presents this as a maintenance surface, because that is the owner's
stated purpose:** for each related memory, show what it shares with the
document and give the actions that are actually available. An unlifted document
says so and offers the lift, rather than rendering an empty list.

**Three of the four maintenance actions exist; "supersede" does not, and this
spec's first draft wrongly promised it.** `PUT /memories/{id}` accepts
`content`, `tags`, `memory_type`, `importance`, `metadata`, `expires_at`,
`is_archived`, `project` and `status` — but `routes/memories.py:205`
**explicitly refuses `status='superseded'`**: *"managed by the pipeline and
cannot be set directly"*. That refusal is correct and must not be worked
around: `chk_superseded_has_pointer` forbids `superseded` without an
atomically-set `superseded_by`, and the update schema carries no such field.

So the available actions are **update**, **deprecate** (`status='deprecated'`,
which the guard permits), **delete**, and **merge**
(`POST /memories/{id}/merge`). Replacement is not a status edit at all — the
sanctioned path is capturing a *new* memory carrying a REPLACES-family
relation, which is what `detect_supersessions` acts on. The UI offers that as
"replace with a new memory", never as a status toggle.

### 6.3 The cost of lifting 475 documents, stated before it is spent

`lift_document` takes an `llm` and extracts propositions per document, so the
bulk lift of the existing corpus is a **real spend, not a migration**. 475
documents over 49,310 blocks is the largest single LLM expenditure this project
has proposed, and nothing in this tree has measured it.

**So it is measured before it is committed:** the bulk script runs a sample of
20 documents first and reports live calls, tokens and wall-clock through the
existing cost twin, and the full run happens only on the owner's say-so with
that number in hand. A run that quietly spends an unmeasured amount on a
corpus nobody has priced is exactly the shape this project's gate ledger
refuses elsewhere.

Two mitigations that are properties of the code, not hopes: the lift is
idempotent (`strip_document_lift` keyed on `document_id`, so a re-run replaces
rather than doubles), and it is per-document, so a partial run is not a broken
state — it is a smaller corpus.

## 7. Sequencing

Four increments. **1 and 2 are independently shippable and need no backend**,
which is deliberate: the owner's loudest complaints are navigational and should
not wait behind an LLM spend.

| # | Increment | Backend | Depends on |
|---|---|---|---|
| 1 | **Frame and tree** — full-bleed layout, resizable panes, scroll areas, real `TreeView` with persisted expansion, breadcrumb | none | — |
| 2 | **Rendering** — the four `block-view` defects (§4), including nesting | none | — |
| 3 | **Management** — wire update / delete / summarize / block edit / connections, with the context menu and confirm dialogs (§5) | none | 1 |
| 4 | **Lift and related memories** — the lift route, the guard test, the related-memories read, the priced bulk run (§6) | new route + read | 1, and §6.3's measurement |

Increment 4 is the only one that can be blocked by a decision, which is why it
is last rather than first.

## 8. What NOT to build

- **A markdown WYSIWYG editor.** Block verbs already edit; a rich editor is its
  own project.
- **Prose over several documents.** That is doc 09's articles, with grounding,
  citations and a ladder. Connections and related-memories return rows.
- **A similarity score.** See §6.2.
- **A scheduled lift.** See §6.1 — the whole reason the route was withheld.
- **A second global Ctrl+K.** See §3.2.
- **The Progress board.** §10.

## 9. Testing

TDD throughout. The load-bearing tests:

- The lift route is **not reachable from `JobRegistry`** — the hazard §6.1
  inherits.
- `test_block_retrieval.py`'s existing scans still pass, proving related-memories
  did not open a path from blocks into ranking or fact-minting.
- Each pane renders four distinct states (loading / failed / empty / populated),
  asserted separately — a failed read must never render as an empty one.
- Heading levels, list markers and nesting render from `properties`, per §4.
- `expected_hash` conflict surfaces as a 409 the UI explains, not a silent
  overwrite.

## 10. The Progress tab, and the ruling it needs

Out of scope here, and it carries a decision this spec must not make quietly:
**spec §7 of the artifact-store design rules out "a task/issue/kanban model"**,
on the owner's own concession that it is heavier than the need and that the
checkpoint + ledger pair covers the requirement. The requested Progress revamp
— parsing task documents into a board with epic links, filters and view
switching — **is** that model.

**RULED 2026-09-03: the owner reverses it.** Asked to distinguish "follow the
existing model" from "follow the project-management model", the owner
confirmed the latter — *"I want the progress can be visually show on the
project board"*, then *"Confirm!"* against the explicit question "reverse §7 —
build the task board". So the artifact-store spec's §7 non-goal is withdrawn
for the Progress surface.

The reversal is recorded here because this is where the question was raised,
but **the design belongs to the Progress spec**, which must carry: the parsers
for the ledger formats actually in the corpus, the board model and its link to
epics/features in the artifact docs, view switching and filters — and, since
the original ruling turned on cost, an honest statement of what a task model
adds that the checkpoint + ledger pair does not.

## 11. Rulings this spec does reverse

Recorded here so they are visible rather than discovered:

1. **"No lift door"** (`documents.py`) — reversed, with the anti-scheduling
   reason preserved as a test (§6.1).
2. **"Blocks render flat"** (`document-reader.tsx`) — reversed for the browser
   (§4, defect 4).

Neither touches a gate, a bar or an invariant.
