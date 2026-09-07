# Increment 2 — the workspace shell

Epic spec: `2026-09-07-personal-notes-workspace-design.md`, whose §12 describes
this increment in one line: "**Workspace shell.** `/notes` route, tree with
drag-to-move, create, rename, delete, pin. Usable as a notes app; editing is
still the shipped textarea."

Increments 1a–1e are shipped, merged and deployed (v1.7.0 and v1.8.0). This
document exists because that one line hides three backend gaps, an ordering
constraint that makes the frontend land broken if taken in the wrong order, and
a scope hazard on the only genuinely new capability.

Reviewed adversarially before any code was written; the review's twelve
findings are folded in below rather than appended, and the two claims it
falsified are marked where they bit.

## 1. What is reachable today, and what is not

**The personal space exists and nothing can reach it.** `projects` carries the
`notes` row at `kind='personal'` (seeded at boot, guarded by the partial unique
index `ux_projects_one_personal`), `GET /api/v1/projects` serves it even while
it holds nothing, and both project-shaped surfaces deliberately filter it out —
`project-switcher.tsx:53` and `projects.tsx:70`, the latter's sibling comment in
`use-projects-api.ts:7` saying "It has its own route". That route does not
exist. v1.7.0 shipped the half that hides the space and not the half that opens
it.

**`/documents` renders empty.** The route hard-pins `project="default"`
(`documents.tsx:20`) under a comment calling it "the personal one" — the AS §2
position the epic spec's §14 reverses. Every filed document lives in project
`darkmem`; `default` is not a `projects` row at all.

**`ProjectWorkspace` is already the workspace this increment needs.** 423 lines
at `features/documents/components/project-workspace.tsx`, taking `project` as a
prop, remounted per project by `key={project}` (`projects_.$project.tsx:42`),
carrying tree, selection and search. `document-tree.tsx` already wraps
darkraise-ui's `TreeView` thinly, per CLAUDE.md's library-first rule.

## 2. Decisions

Taken by the owner from presented options:

1. `/notes` **reuses `ProjectWorkspace`** behind a capability prop, rather than
   a purpose-built shell or an extracted shared core.
2. Drag-to-move uses **`@dnd-kit`** rather than native HTML5 DnD or deferring
   drag. Narrowed to `@dnd-kit/core` only: `buildUriTree` derives order from the
   uri path and sorts folders-first then `localeCompare` (`uri-tree.ts:28-36`),
   so there is no user-defined ordering for `@dnd-kit/sortable` to persist.
3. Folder delete gets a **real subtree-delete verb** mirroring
   `rename_documents`, rather than no folder delete or a client-side fan-out.
4. `/documents` gets a **project picker** in this increment.
5. The subtree delete is a **separate MCP tool at `admin` scope**, not a mode on
   `document_delete`. Scopes are per tool (`api/mcp/scopes.py`), so a mode would
   inherit `capture` and let any capture key erase a project's corpus. This
   moves the catalogue 39 → 40 and the count guards with it.
6. The subtree delete **journals**. See §4.

## 3. Backend

### 3.1 Serve `pinned_at` — on the list item only

`pinned_at` is written by `document_update` and read by nothing:
`_PIN_ASSIGNMENT` (`document_door.py:80`) is its only mention in `backend/app`,
and `_LIST_SQL` does not select it. A pin control with no readable state is not
shippable.

Serve it on the **list item only**, not on the keyed reads. The keyed reads
(`GET /documents/{id}` and the `by-uri` twin) are `documents.retrieval`,
TWO_DOOR, and MCP `document_get` answers a bare array or a boxed
`{content, content_hash, blocks}` with no metadata slot — adding a field to the
REST half alone is a wire divergence that would need a recorded parity reason or
a mirrored tool change. The list route is `documents.reads`, REST-only already,
so the field costs no parity at all. Since this increment does not build the
pinned list (§7), the list item is the only place the tree reads from.

### 3.2 `delete_documents`

```
delete_documents(session, *, project: str, uri_prefix: str) -> int
```

in `app/services/document_door.py`, beside `rename_documents` and deliberately
shaped like it:

- The same match, and for the same reason: `uri = :u OR left(uri, length(:u)+1)
  = :u || '/'`. LIKE is avoided because `_` and `%` are metacharacters there and
  a prefix of `notes/a_b` would over-match `notes/axb`.
- **The two-step lock, not a bare `DELETE … WHERE <prefix>`.** `SELECT … ORDER
  BY id FOR UPDATE` to take the rows in id order, then `DELETE … WHERE id =
  ANY(:ids)`. A single statement locks in index-scan order and can deadlock
  against a concurrent `rename_documents`, which takes the same rows in id
  order.
- **No depth ordering.** Unlike the rename, deletes cannot collide through the
  unique index, so the iteration order of the delete itself is free.
- Refuses an empty `uri_prefix`: at the SQL an empty prefix degenerates to
  `left(uri, 1) = '/'` and silently matches nothing, which would report a
  successful delete of zero rows rather than a refusal.

### 3.3 Doors

**REST: `POST /api/v1/documents/delete`.** POST rather than DELETE because
`DELETE`-with-body is poorly supported by clients and proxies, and because the
reply is a count — the precedent is `POST /memories/delete`, named as the bulk
delete in `docs/api-rest-conventions.md`. (The earlier draft justified the POST
as "the body carries the address"; that reasoning was wrong, since
`DELETE /documents/by-uri` already carries its whole address in the query
string. The count reply is the real reason.)

**MCP: `document_delete_subtree`, `admin` scope.** A new tool, not a mode. It is
the second tool ever held at `admin` — the scope that today reaches only
`code_reindex` — on the same principle: this is repository-scale control, not
memory writing. A `capture` key keeps the single-document `document_delete` it
has today.

Settle a deferred minor from the 1d/1e run while here: `document_delete` raises
`DocumentTargetUnresolved` as a tool error where `document_update` answers a
structured envelope. Both become envelopes, and the new tool matches.

## 4. The delete journals

`delete_document` journals nothing today, and `document_door.py`'s own docstring
records why: there is no delete event type, and a document's blocks corroborate
no fact so there is no provenance to withdraw. That reasoning covers deleting
one note. It does not survive a bulk delete.

`events` is by contract the **sole** append-only audit substrate. Every other
document mutation journals — `document_filed`, `blocks_edited`,
`document_updated`, and `rename_documents` journals one row per moved document.
A subtree delete is unrecoverable, cascades blocks and their vectors, and over
MCP the event's `api_key_id` and `actor` are the only record of who did it.
Shipping it unjournaled and raising the audit question afterwards opens a window
in which deletions are the one invisible mutation.

So: **`documents_deleted` joins `EVENT_TYPES`, and the verb journals one row per
deleted document**, mirroring the rename rather than inventing an object type
for "a subtree". Write-time minimisation is trivially met — ids and the prefix,
no content. Taxonomy-first, as CLAUDE.md requires: the value lands in
`EVENT_TYPES` and in `event-taxonomy.ts`'s capture tab beside its three
siblings, in the same commit as its emitter.

## 5. Frontend

### 5.1 The ordering constraint

**`selectedId` before the mutations.** `ProjectWorkspace` stores the selected
`DocumentListItem` *object* (`:107`, `:187-191`). Every mutation this increment
adds invalidates that snapshot: after a move the breadcrumbs render the old uri
and the reveal effect — keyed on `revealedFor.current === selected.id`
(`:171-180`) — never expands the new folder; after a folder delete containing
the selection the reader 404s and the detail panel fires summary and connections
reads against a dead id. The existing reset lives only in `DocumentActions`
(`document-actions.tsx:108-113`) and does not cover these paths.

Refactor to a `selectedId` plus a lookup from `items` **first**. Taken in any
other order, rename, move and delete each land visibly broken.

### 5.2 The capability prop

Name it for what it gates: **tree management**, not `editable`.
`/projects/$project` is already editable — it has the block editor and delete —
so `editable` would conflate two things.

Off (the default), `/projects/$project` renders unchanged, and a test asserts
the default render exposes no context menu and no create button. On, tree rows
gain New note, New folder, Rename, Move to…, Pin/Unpin, Delete, and the header
gains a create button.

**"New folder" files a note, because a folder is not an object.** Folders are
derived from the uri path (epic spec §2), so an empty one cannot exist — there
is no row to carry it. The command takes a folder name and files one seeded
note inside it (`<folder>/untitled.md`), which is what makes the folder appear.

Four branch points the flag has to answer beyond the menu, all of which the
component renders unconditionally today:

- the Artifacts/Progress tab strip and its `CheckpointsTab`,
- the `useProgressCorpus` scan, which would fetch ledger contents on every
  `/notes` mount for nothing,
- the "File a document whose path ends in `planning/progress.md`" empty state
  (`:400-419`),
- the tree's own empty state (`document-tree.tsx:163-172`), which **returns
  before `nodeActions` renders** — so an empty notes space, which is exactly the
  state `/notes` opens in today, would have no create affordance at all. This is
  the first thing a user sees and it must be fixed here.

Whether `/notes` shows the Progress tab is a decision this increment takes
explicitly rather than inherits.

### 5.3 Create, rename, move

**`document_put` is an upsert, not a create.** Identity is `(project, uri)`, so
a second "New note" at the same seeded uri hits the content-hash gate and
returns `unchanged` with the *existing* document's id. The client mints a unique
uri (`untitled.md`, `untitled-2.md`, …) against the loaded tree; there is no
create-only precondition on the door, since `expected_hash` only preconditions
an existing hash.

Content is seeded `# Untitled\n` because `DocumentPutRequest.content` is
`Field(min_length=1)` on the REST door. (Note the MCP `document_put` carries no
such bound — the asymmetry is pre-existing and out of scope here.)

**Rename PATCHes `uri`, not `title`.** The tree renders the uri's last segment
(`document-tree.tsx:200,226`) while `_resolve_title` derives the title from the
first heading. A title PATCH changes nothing visible in the tree, which would
read as a broken rename.

Folder rename is `POST /documents/rename`; both verbs shipped in 1e.

### 5.4 `/notes` and `/documents`

`/notes` resolves its project from `GET /projects` where `kind === 'personal'`
rather than hardcoding `"notes"` — the singleton index guarantees at most one.
Nav entry goes in the `Projects` group of `_authenticated.tsx:62-70`, beside the
comment recording that `/documents` shipped with no nav entry and was
unreachable — the same mistake this route is currently making.

`/documents` takes a project `Select` in its header, filtering out
`kind === 'personal'` the way the switcher and projects list already do. Default
to the first project **holding documents**: `useProjects` orders busiest-first by
a different measure, so the default needs its own `document_count > 0` filter.

### 5.5 Drag

`@dnd-kit/core` only. A new frontend dependency; none of `@dnd-kit/*` is present
today.

**Listeners go on an inner handle, never spread onto the library's rows.**
`TreeViewItem` and `TreeViewBranchControl` do spread `...props` onto their DOM
elements, but that spread lands *after* `ref` (which registers the row for the
tree's focus management), `role="treeitem"`, the roving `tabIndex` and the
`aria-*` attributes. Spreading `useDraggable().attributes` (`role="button"`,
`tabIndex=0`) and `listeners` over those breaks the accessible tree and the
arrow-key traversal `TreeViewTree` handles by bubbling; `ref` is not in the
typed props, so `setNodeRef` would not typecheck there either. Use an inner
wrapper for `setNodeRef` and the listeners, a `PointerSensor` with an activation
distance so a click still selects, and do not spread `attributes`.

Record the library gap in code, per CLAUDE.md: darkraise-ui's `TreeView` ships
no drag support, and this local drag layer exists for that gap and should be
retired if a later version closes it.

Every drop resolves to a target prefix and dispatches a verb that already
ships — a document drop is `PATCH` with a new uri, a folder drop is
`POST /rename`. Droppables that are descendants of the dragged folder are
disabled during the drag, so the UI refuses what the backend would otherwise
have to disambiguate. Folder operations are disabled on the `(no path)` orphan
bucket (`uri-tree.ts:41-43`), which is a tree node with no uri and would
otherwise send `uri_prefix="(no path)"`.

The target computation is a pure function,
`moveTarget(dragged, dropTarget) -> {kind, uri} | null`, so the interesting
logic is unit-testable without a DOM drag.

## 6. Guards

A new REST route, a new MCP tool and a new response field move more full-list
guards than any single change in this epic so far. **The route, its parity row,
its content-surfaces entry, the conformance map and the regenerated
`two-door-parity.md` must land in one commit** — each fails the instant the
route exists without its entry.

Backend: `test_content_surface_scoping` (both the route and the tool
classification), `test_door_parity` (route classification, the enforced table,
and the headline counts sentence that sits *outside* the generated block),
`test_api/test_rest_conformance` (the EXPECTED map), `test_prompt_agent_instructions`
(the roster, whose served descriptions carry an ≥80-char floor),
`test_event_taxonomy_map` (`documents_deleted`), `test_sdk_generator`, plus
CLAUDE.md's own 39 → 40 catalogue count and the `admin`-scope sentence.

Frontend: `FULL_HEIGHT_ROUTES` (`_authenticated.tsx:151`) needs `/notes` or the
resizable split falls to the 60vh floor; `DEMO_ROUTES`
(`tests/demo-makes-no-api-calls.spec.ts`) gains `/notes`; `query-keys.ts`
classification for any new `queryKey` literal; and `DocumentListItem` gaining
`pinned_at` breaks `tsc -b` in four fixture files unless the field is optional
or every fixture is updated.

Then the leg recorded in CLAUDE.md's Commands section, plus `make generate` in
`sdks/`.

## 7. Not in this increment

The editor stays the shipped textarea (increment 3). No links, backlinks or
`[[` autocomplete (4). No recents/pinned rail, Ctrl+K or tag browser (5) —
`pinned_at` is served so a pin renders in the tree, but the pinned list is not
built. No attachments (6), no graph (7).

**Recorded for increment 4.** Only `rename_documents` re-resolves
`document_links` stubs; `put_document` never does. So a note deleted and
re-filed at the same uri regains its backlinks only if something later renames
it. Inert today — nothing in `backend/app` inserts a `document_links` row — but
it is the links increment's obligation and is written down here so it is not
rediscovered.
