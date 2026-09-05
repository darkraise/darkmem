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

**Amended 2026-09-05: this section is historical framing, kept for the
measurement it records rather than for its present-tense claims, which
are now false and are the reason the owner later ruled the way §5 and
§6 describe.** At the time this was written, `document_connections.py`
did read `entities` plus the lift's provenance and did return nothing
with zero entities present, and lifting was ruled in scope to fix that.
Neither is true today: the lift and the entity-derived connections basis
are both retired, and `document_connections.py` is re-based onto cosine
similarity over block vectors (§6.2), which is not vacuous against an
empty entity graph because it never reads the entity graph at all.

Two consequences, both load-bearing **as of this section's original
writing**:

1. **Related-memories cannot work by reading the graph, because there is no
   graph.** Any design that joins documents to memories through entities
   returns empty for all 475 documents.
2. **The shipped Connections feature is already vacuous for the same reason.**
   `document_connections.py` reads `entities` + the lift's provenance; with
   zero entities it returns nothing, silently, today.

This is the same hole that blocked G-E and `T3.22` ("pending a corpus"). The
documents were imported; nothing was ever lifted.

**Owner ruling, 2026-09-03: lifting is in scope for this project.**
Building related-memories without it would ship an empty panel and call
it a feature. **That ruling was itself reversed on 2026-09-05** — see
§6.1 and §6.2 — once the priced sample showed the lift's actual output
shape made it unusable regardless of the empty-panel problem it was
meant to solve.

## 3. Layout and interaction — the UI/UX, which is the point of the revamp

The page becomes a three-pane browser. **Every primitive below already exists
in `darkraise-ui`; this spec adds no local component**, per CLAUDE.md's
library-first rule. The inventory was checked: `tree-view`, `resizable`,
`scroll-area`, `context-menu`, `breadcrumb`, `command`, `dropdown-menu`,
`sheet`, `toolbar`, `separator`, `badge`, `empty-state`, `skeleton`, `sonner`.

### 3.1 Frame

**Amended 2026-09-05: the `lift-all` toolbar button below was never built —
the lift and its bulk script are retired (§6.1).** The toolbar carries
project, search and view-toggle only.

```
┌─ toolbar: project · search · view toggle ──────────────────────────┐
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
- **Folder rows show a child count.** **Amended 2026-09-05: this said
  document rows show a `badge` "when the document is not lifted" (§6) —
  there is no lifted/unlifted state any more.** The related-memories basis is
  now cosine over block vectors (§6.2), whose empty state is
  `comparable_memories = 0`, not "not lifted"; a badge for that state, if
  one ships, would read that way instead.
- `ContextMenu` on every row — open, summarize, copy URI, delete.
  **Amended 2026-09-05: `lift` is removed from this list; there is no lift
  action.** This
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
3. **Every list item renders `•`.** **Corrected 2026-09-03 while
   implementing increment 2: this defect's stated premise was false.**
   `properties` does *not* carry the marker on a filed document —
   `parse_markdown` writes `properties: None` for every list block, and
   discards the `bullet_list_open` / `ordered_list_open` distinction as
   "transparent" on purpose. So nothing on the read surface can tell an
   ordered list from a bullet one, and rendering it is not a frontend change:
   it needs the **parser** to write the marker, plus a **re-import of all 475
   filed documents**, on the same widening rule CLAUDE.md records for
   `divider`. The `marker` key does already exist and has one writer — the
   block editor's `promote()` — so an *edited* block carries it and a parsed
   one does not, which is the split-brain a partial fix would ship.
   **Owner ruling 2026-09-03: deferred to its own increment**, which owns the
   parser change and the re-import together. Increment 2 shipped 1, 2 and 4
   and deliberately left the bullet as-is rather than rendering half the
   corpus correctly.
   **Shipped 2026-09-04 as increment 5**, with two findings the deferral did
   not anticipate. First, the `marker` key is **shared with
   `block_serializer`**, which defines it as the marker *as spelled* (`"3."`,
   not `"."`) and reads it back on every block-first conversion — writing
   markdown-it's bare `markup` would have made every ordered item the parser
   produces read as a bullet on the way out, silently rewriting ordered lists.
   The parser now imports `DEFAULT_LIST_MARKER` from that module and a test
   pins the two conventions together. Second, **a re-import does not reparse
   anything**: `content_hash` is the change gate, so re-pushing a document's
   own bytes returns `unchanged` and never touches a block. That needed a new
   mechanism — `force_reparse`, off on every door, set only by
   `backend/scripts/reparse_documents.py`, which reads `documents.content`
   (the stored source of record) and re-files in place, so it needs neither
   the original files nor a login. Its cost is re-embedding, not parsing:
   filing mints fresh block ids, so every block embeds again.
4. **Blocks render flat.** `document-reader.tsx` states this is deliberate —
   defensible for a reader, wrong for a browser, and it means nested lists lose
   their nesting. **Corrected 2026-09-03: the mechanism named here was wrong,
   and the real one is exact rather than inferred.** Nesting is not
   reconstructed from `properties` + `order_index`: `blocks.parent_id` exists,
   is written by the parser and is indexed by the baseline — it was simply
   absent from the read surface (`BlockRow` / `BlockRowModel`), so every
   reader saw a flat list. Increment 2 puts it on the surface (both doors get
   it free: MCP's `document_get` serialises with `vars(r)`).
   Depth counts **`list` ancestors only**, never the parent-chain length:
   every block under a heading carries that heading as its parent, so a raw
   chain length would indent an entire document body under its title. Counting
   list ancestors also catches what a chain length would miss — a code block
   inside a list item indents with its item. Rendered as indentation on the
   existing flat sibling list rather than as semantic `<ul>`/`<ol>` grouping,
   because without defect 3's marker every `<ol>` would be a guess, and
   because the flat list is what `focusBlockId`'s scroll query and the
   outline's `#id` anchors address.

**Not in scope:** a markdown editor. Increment 8's block verbs already provide
editing and this spec surfaces them (§5); a WYSIWYG surface is a separate
project.

## 5. Document management — mostly wiring

Every route below is shipped and unused by this page, **except the summarize
POST, which did not exist at all** — this section's original title said "wiring,
not new backend" and was wrong for exactly one row (corrected 2026-09-04):

| Action | Route | Note |
|---|---|---|
| Update | `POST /api/v1/documents` | The `(project, uri)` upsert **is** update. Send `expected_hash` — it is a compare-and-set and answers 409 on a stale hash |
| Delete | `DELETE /documents/{id}` | Removes the row and cascades its blocks and their vectors. **Amended 2026-09-05: this row read "Withdraws fact provenance, then expires facts left unsourced" — true only while the retired block-to-fact bridge existed. Nothing mints a fact from a block, so delete withdraws no provenance, expires no fact, and journals nothing (`routes/documents.py:667`: no delete event type).** |
| Summarize | **`POST /{id}/summary`** (new), then `GET /{id}/summary` | **Corrected 2026-09-04 while implementing increment 3.** `summarise_document` shipped with **no caller anywhere in `backend/app`** — no route, no job, no MCP tool — so the GET read a property nothing in the tree could ever write and the summary panel was empty by construction on every install. Wiring it needed one new route, not wiring. It spends an LLM call on the `summarization` purpose, so it carries `refuse_when_read_only` beside `require_auth`, and answers 422 rather than an empty 200 for a document with no blocks |
| Per-block edit | `PATCH/POST/DELETE .../blocks/…` | Increment 8's four verbs |
| Connections | `GET /{id}/connections` | **Amended 2026-09-05: this row read "Vacuous until lifting (§2)". The lift is retired; connections are re-based onto cosine over block vectors (§6.2) and are not vacuous.** |
| Grounded Q&A | `POST /documents/qa` | G-F cleared 2026-09-03, so it may now serve a grounded label |

**Delete is confirmed through `alert-dialog`, never a bare button. Amended
2026-09-05: this paragraph said the dialog states that delete "withdraws
block sources and expires any fact left with no surviving source" — false
now that the block-to-fact bridge is retired.** Nothing mints a fact from a
block, so delete has no provenance to withdraw; the dialog must say only
what deletion actually does — remove the document and cascade its blocks
and their vectors, with no other effect and no undo.

**Update uses `expected_hash` from the last read.** Omitting it is
last-writer-wins, which is the wrong default for a surface where an agent and a
human edit the same document.

## 6. Lifting and related memories — the only new backend

### 6.1 The lift door — retired

**This section proposed `POST /api/v1/documents/{id}/lift` and a one-shot bulk
lift script. Neither shipped as a permanent surface: the owner retired the
on-demand proposition lift entirely (ruling 2026-09-05), on the pricing
measurement §6.3 records below.** The section is kept for its reasoning
rather than deleted, because that reasoning — a route is the easiest way for
something to call a lift on a schedule, so the door should stay human-invoked
— is still correct about doors in general; it is moot only because there is
no lift door of any kind left to guard. `lift_document`,
`block_fact_sources` (the bridge a lift's output would have crossed into the
vault through) and every caller of either are deleted. There is no route
from a block to a fact at all, not a gated or on-demand one.

### 6.2 Related memories — re-based onto cosine, entity basis reversed

**This section originally read related memories off the lifted propositions'
entities, via `entities.memory_ids[]`. That basis is gone with the lift
(§6.1), and `related-memories` and `document-connections` are now re-based
onto cosine similarity over block vectors instead** — `document_related`
goes document → block vectors → nearest *memory* vectors by cosine;
`document_connections` is one hop further out and goes document → block
vectors → nearest *other documents'* block vectors, per its own docstring.
Neither reads the entity graph and neither reaches a lifted proposition
anywhere on its path.

- **No LLM call** still holds, and for the same reason: the moment a
  connections feature generates prose it has become unbadged synthesis and
  belongs to doc 09. Cosine ordering is not prose.
- **No new table** still holds — the read is over embeddings already
  written for retrieval.
- **It still never touches the block channel's write side** — reading block
  *vectors* to rank memories is the surface `test_block_retrieval.py`'s scans
  were written to police, and they were extended rather than bypassed: no
  block row crosses into `HybridSearchService` or `LayerCompositionService`'s
  ranking, and no fact is minted from a block.
- **"Shared-entity count is evidence, not a score" is reversed by the same
  2026-09-05 ruling, and §8 names the reversal explicitly.** With the entity
  basis gone there is nothing left to count; the replacement is a cosine
  similarity number, which is exactly the "similarity score" §8 originally
  ruled out building. See §8 for the stated constraint that ships instead of
  the badge or percentage that ruling was guarding against.

**The UI presents this as a maintenance surface, because that is the owner's
stated purpose:** for each related memory, show what it shares with the
document and give the actions that are actually available. **Amended
2026-09-05: this said an unlifted document "says so and offers the lift" —
there is no lift to offer any more.** A document with no comparable memory
under the cosine basis (`comparable_memories = 0`, per
`2026-09-05-retire-proposition-lift-design.md` §3.5's states table) says so
and renders an empty state; there is no lift action to fall back to.

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

### 6.3 The cost of lifting 475 documents — measured, and it is what retired the feature

**This section priced the bulk lift before it was committed. The pricing
sample is what retired it, not a follow-up decision made afterward: the
binding constraint turned out to be corpus composition, not call price or
token volume, which is a different failure mode than the one this section
was budgeting against.**

The sample: 7 documents minted 2,058 memories against a corpus of 50
documents. Extrapolated across the corpus's 47,811 non-empty blocks, a full
run was on the order of 104,000 memories from roughly 152,000 LLM calls, at a
sample spend of $0.72. The per-call and per-token cost was unremarkable — the
number that mattered was the *memory count* the corpus's document composition
would produce, which was disproportionate to the corpus's actual size and
made the lift's output unusable as a memory population regardless of what it
cost to generate. Pricing the calls and tokens, which is what this section
set out to do, answered the wrong question; the measurement that actually
decided the outcome was what the sample's *output shape* revealed about the
corpus, not its bill.

The mitigations this section listed — idempotent re-lift, per-document
partial-run safety — are moot along with the feature they protected;
`lift_document` and `strip_document_lift` are deleted.

## 7. Sequencing

Five increments. **1 and 2 are independently shippable and need no LLM spend**,
which is deliberate: the owner's loudest complaints are navigational and should
not wait behind one. (This read "need no backend" and named four increments
until 2026-09-03; both were corrected while implementing 2 — see §4's defects 3
and 4. Increment 2 turned out to need one read-surface field, and defect 3 was
split out as increment 5 because it needs a parser change and a corpus
re-import.)

| # | Increment | Backend | Depends on |
|---|---|---|---|
| 1 | **Frame and tree** — full-bleed layout, resizable panes, scroll areas, real `TreeView` with persisted expansion, breadcrumb | none | — |
| 2 | **Rendering** — `block-view` defects 1, 2 and 4 (§4): real heading levels, headings through `<Markdown>`, list nesting | `blocks.parent_id` onto the block read surface (one field, both doors) | — |
| 5 | **List markers** — defect 3 (§4): the parser writes a list block's marker, and the 475 filed documents are reparsed so existing rows carry it | parser + `force_reparse` + a maintenance script | 2 |
| 3 | **Management** — wire delete / summarize / block edit / connections, with the confirm dialog (§5) | the summarize POST (one route) | 1 |
| 4 | **Related memories** — the related-memories read, the priced bulk-lift measurement that retired the lift route itself (§6) | new read (cosine over block vectors, §6.2) | 1, and §6.3's measurement |

Increment 4 is the only one that can be blocked by a decision, which is why it
is last rather than first. Increment 5 is unblocked but deliberately unsequenced
against 3 and 4: it is the only one that rewrites the corpus, so it should not
share a change with work the owner is reviewing visually.

## 8. What NOT to build

- **A markdown WYSIWYG editor.** Block verbs already edit; a rich editor is its
  own project.
- **Prose over several documents.** That is doc 09's articles, with grounding,
  citations and a ladder. Connections and related-memories return rows.
- **A similarity score — reversed by owner ruling, 2026-09-05.** This bullet
  ruled out rendering a similarity score, on the entity-count basis §6.2
  originally used. With that basis retired and related-memories re-based onto
  cosine (§6.2), a similarity score is exactly what the surface now shows —
  but under a stated constraint that is the actual guard this bullet was
  reaching for: the score is an ordering key rendered as a **raw cosine value
  to three decimals**, never normalised into a percentage, never rendered as
  a bar, and never a pass/fail badge. The corpus's cosine distribution is
  continuous with no seam to badge against (p50 0.503, p90 0.612, p99
  0.750), so any percentage, bar or badge would manufacture a threshold the
  data does not have.
- **A scheduled lift.** §6.1 argued the route should stay human-invoked
  rather than reachable from a schedule. **Amended 2026-09-05: this
  bullet said "the whole reason the route was withheld" — the route was
  not withheld, it was built** (`POST /{document_id}/lift`,
  `backend/app/api/routes/documents.py:44`), measured, and then deleted
  along with the rest of the lift on the owner's retirement ruling. The
  anti-scheduling argument is what kept it out of `JobRegistry` while it
  existed; it is moot now that no lift route exists to schedule at all.
- **A second global Ctrl+K.** See §3.2.
- **The Progress board.** §10.

## 9. Testing

TDD throughout. The load-bearing tests:

- **Structural relatedness pin (shipped, Task 8):** nothing under
  `app/services` imports either relatedness surface's ranking module — this
  guards the services layer, not the route: `api/routes/documents.py`
  legitimately imports both surfaces to serve them and sits outside the
  scan by design. The pin replaces a route-reachability test against a lift
  door that no longer exists.
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

**Written 2026-09-04: `2026-09-04-progress-board-design.md`.** Its two
load-bearing findings, both measured rather than assumed: the epic files'
done-when checkboxes are **not maintained (806 unchecked, 17 checked)**, so a
board deriving completion from them would report ~2% done for a project that
is substantially complete — `progress.md`'s Status column is the only
completion signal. And the honest answer to the cost question is that a board
adds **no new data at all**; what it adds is that three questions currently
answerable only by hand-joining two files become one read. That is why the
spec makes it a **projection, never a store** — a writable board would put
task state in a database while the ledger that gates merges stays in git.

## 11. Rulings this spec does reverse

Recorded here so they are visible rather than discovered:

1. **"No lift door"** (`documents.py`) — reversed, with the anti-scheduling
   reason preserved as a test (§6.1). **Amended 2026-09-05: that reversal was
   itself reversed by the owner's retirement ruling the same day — the lift
   door never shipped as a permanent surface, and there is no lift of any
   kind, scheduled or on-demand, left in the tree.**
2. **"Blocks render flat"** (`document-reader.tsx`) — reversed for the browser
   (§4, defect 4).

Neither touches a gate, a bar or an invariant.
