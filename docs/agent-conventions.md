# Agent conventions for the project artifact store

How an agent session should file artifacts, record its progress in the work
log and keep a project's ledger. Every constraint below is a shipped behaviour
or a stated design decision, not a preference — the citations are so you can
check rather than trust.

This document is itself filed into the store it describes, at uri
`docs/agent-conventions.md` in project `darkmem`.

## 1. Project naming

`project = <repo-name>` for a repository's artifacts — this repo files under
`darkmem`. It matches the `project/<repo-name>` tag convention agent sessions
already use for memories, so one scope name means one thing across memories,
documents and the work log.

Personal notes with no repository stay in `default`. That is the boundary: the
project field is the separation, not a label inside the payload.

## 2. Uri scheme

The uri is **the repo-relative path the file had** — `docs/planning/progress.md`,
not a slug, not a title, not a uuid.

**Re-filing the same `(project, uri)` updates that document in place.** The
upsert is the document's identity, which is the opposite of memory capture,
where all four doors append a row per call and `origin_key` is corroboration
identity rather than a dedup key. A document has one row per path; capturing
the same fact twice gives you two memories on purpose.

Two consequences worth internalising:

- Re-running an import is safe. Unchanged files short-circuit on the
  content hash.
- There is no "file this again as a new copy". If you want a second document,
  give it a second uri.

## 3. Work-log discipline

Working data — checkpoints, ledger text, notes to the next session — goes to
the work log, never to `memory_add` (`backend/app/services/worklog.py`, module
docstring). One workstream per piece of work, keyed by a name the client
chooses; dr-superpowers uses the plan or design slug.

**Mint one run identity per process at boot, and declare it on every
`worklog_append`**, as `run_key` or the `X-Darkmem-Origin` header. An
undeclared run is *refused*, never merged into a shared bucket: two runs
sharing one key would each resume the other's work as their own
(`worklog.resolve_run_key`).

Bounds, enforced at the door and again by CHECK constraints (the constants at
the top of `worklog.py`):

| Bound | Value |
|---|---|
| entry `body` | 1–65,536 characters, stored verbatim |
| entries per append | 1–100, in one transaction |
| `properties` | ≤ 12,288 bytes of encoded JSON at the door |

**Resume at session start, checkpoint at every stop.** `worklog_resume`
answers the latest checkpoint, the newest 50 notes and the last 20 ledger
entries. Every entry stays readable through `worklog_entries` and
`worklog_search` until the workstream is purged or, closed and not retained,
ages past the `worklog_cleanup` window (90 days by default).

After a checkpoint, file the durable facts the run established with
`memory_add`, one per memory: the work log keeps how the work went, memories
keep what is now true.

## 4. Ledger shape

One `planning/progress.md`-style document per project, updated at milestones
through `document_put`.

- **Headings and prose.** Never mega-tables: a single GFM table used to parse
  into one 235,716-character block that the embedder silently truncated. Tables
  now parse structurally into rows, but a table is still the worst shape for
  something meant to be retrieved by meaning.
- **Never per-step appends.** An edit re-embeds the *whole* document — there is
  no diffing and no partial re-embed, so editing one paragraph of a large
  ledger costs the same as filing it from scratch. Update at milestones.

## 5. Index document per project

Each project maintains an `index.md` naming its filed uris.

This exists because there is no good way to enumerate a project's documents
today: MCP has no `document_list` by ruling (`docs/two-door-parity.md`), and
the REST list route clamps at 200 with no total in its response, so a client
cannot even tell it was truncated. The workspace UI pages and stitches around
that; an agent has no such affordance.

If this chafes, the fix is an owner ruling amendment — not a quietly added
tool.

## 6. The `properties.kind` label — aspirational, not available

A `"artifact"` / `"note"` label on `properties` is designed for later UI
filtering. **Neither put door accepts `properties` today**, so sending it does
nothing: the field is dropped, not stored.

Stated here rather than omitted, because the alternative is an agent following
a convention that silently has no effect. The project boundary is the real
separation until a door serves the label.

## 7. Round-trip honesty

`document_get` returns **block text, not source.** The parser strips markdown
syntax on the way in: heading markers are gone, tables are flattened to
cell-joined rows, and thematic breaks and raw HTML blocks mint no block at all.

The source *is* retrievable, but only if you ask: `include_content=true` on
`GET /api/v1/documents/{id}` (and its `by-uri` twin) adds the verbatim filed
text as `content`, and MCP `document_get` with `include_content=True` answers
`{content, blocks}` instead of its bare array. It is off by default because a
document can be a megabyte.

**So: do not get-edit-put a document and expect the source back unless you
asked for content explicitly.** Round-tripping through blocks alone will
rewrite the file without its markers.

If you intend to edit, precondition the write: `document_put` takes an optional
`expected_hash`, and files only if the document still holds that
`content_hash`. A stale hash answers 409 on REST and a `hash_conflict` envelope
on MCP, both naming the hash that actually won, so you can re-read and retry.
Omit it for last-writer-wins.

### Block-first documents are the inverse — do not `put` them at all

Everything above describes a **content-first** document, which is every
document ever filed through `document_put`.

A document edited through the block verbs becomes **block-first**, and then
`document_put` at that uri is refused outright: 409 on REST, a
`direction_conflict` envelope on MCP. Its `content` is a serialisation of its
blocks, so a content push would strip every block and rewrite what the
serialiser was reading from.

To change one, use the block verbs with ids from `document_get`:
`block_update`, `block_insert`, `block_move`, `block_delete`. Send
`block_update` the block's **source** — the field `document_get` returns
alongside `text` — because `text` is marker-stripped and putting it back would
demote every heading to a paragraph.

The conversion happens on the first block verb and is one-way. It is also
**refused** for a document whose source the block model cannot represent — a
raw HTML block, or a link-reference definition — because converting would
regenerate the content without it. Those documents stay content-first and
`document_put` remains the way to edit them.
