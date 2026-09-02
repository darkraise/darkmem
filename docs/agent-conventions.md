# Agent conventions for the project artifact store

How an agent session should file artifacts, checkpoint its progress and keep a
project's ledger. Every constraint below is a shipped behaviour or a stated
design decision, not a preference — the citations are so you can check rather
than trust.

This document is itself filed into the store it describes, at uri
`docs/agent-conventions.md` in project `darkmem`.

## 1. Project naming

`project = <repo-name>` for a repository's artifacts — this repo files under
`darkmem`. It matches the `project/<repo-name>` tag convention agent sessions
already use for memories, so one scope name means one thing across memories,
documents and checkpoints.

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

## 3. Checkpoint discipline

**Mint one `origin_key` per run at process boot, and declare it on every
`checkpoint_save`.** Correlation is a property of client discipline, not a
system guarantee (`backend/app/services/checkpoints.py`, module docstring). An
undeclared origin is *refused*, never merged into a shared bucket — the door
would rather fail your call than silently blend two runs into one history.

Checkpoint at each meaningful step, within these bounds (verified against
`checkpoints.py:106-117`):

| Bound | Value |
|---|---|
| `summary` | ≤ 4,000 characters |
| `next_steps` count | ≤ 50 |
| each next step | ≤ 500 characters |
| `next_steps` total | ≤ 16,384 **bytes** |

That last row is a different unit from the one above it, deliberately and with
a scar behind it: 50 × 500 *characters* of CJK text passes the per-step check
and still exceeds the byte budget.

### What the store gives back — read this before relying on it

**Only the latest checkpoint is readable.** `GET /api/v1/checkpoints/latest`
and MCP `checkpoint_latest` serve the newest digest for a run, and **no verb
anywhere serves a run's past summaries.** The `checkpoint_saved` journal event
deliberately carries no step content at all (write-time minimization), so the
history you can see is *when* saves and resumes happened — never what they
said.

So: **a checkpoint is a live watch signal, not a record.** Anything worth
keeping past the run belongs in the ledger document. If you checkpoint a
decision and never write it down anywhere else, it is gone the moment the next
checkpoint lands.

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
