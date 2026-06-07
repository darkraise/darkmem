# API REST conventions

The darkmem HTTP API (`/api/v1/*`) follows REST for true resources and a small,
consistent set of pragmatic patterns for everything else. This document is the
contract: new endpoints should match it, and the documented deviations should
not regress.

## Resource CRUD

True resources use standard verbs and status codes:

| Action | Verb | Status |
| --- | --- | --- |
| Create | `POST /collection` | `201 Created` |
| Read one | `GET /collection/{id}` | `200` |
| Read list | `GET /collection` | `200` |
| Replace / update | `PUT /collection/{id}` (full), `PATCH` (partial) | `200` |
| Delete | `DELETE /collection/{id}` | `204 No Content` (no body) |

Examples: `memories`, `repos`, `chat/conversations`, the config singletons.
Collections are plural nouns; sub-resources nest (`/repos/{id}/tasks`).

## Status codes

- `201` on create, `204` on delete, **`202 Accepted`** for async work that is
  queued but not finished (reindex, reembed, retry), **`409 Conflict`** when a
  request can't proceed because the resource is in a conflicting state (e.g. a
  repo that is already indexing), `404` for missing resources.

## Accepted pragmatic patterns (these are conventional REST, not violations)

- **Search / computation with a complex body → `POST .../search`** (and
  `/search/paginated`, `code/search`, `code/blast-radius`). A GET query string
  can't cleanly or safely carry rich filters or credentials.
- **Non-CRUD actions as `POST` sub-resources** — verbs in the path are fine for
  actions that are not plain CRUD: `/{id}/merge`, `/{key}/trigger`,
  `/{id}/reindex`, `/{name}/test`, `/{id}/retry`, `/reprocess`, `/reason`,
  `/completions`, and the auth flows (`/login`, `/logout`, `/refresh`).
- **Bulk operations via `POST` with a body** — `POST /memories/batch` (bulk
  create) and `POST /memories/delete` (bulk delete). `DELETE`-with-body is poorly
  supported by clients/proxies; the bulk-delete reply reports per-id results
  (`{deleted, not_found}`) because a missing id is non-fatal. The bulk delete is
  also processed server-side **in series** to avoid the graph-cleanup deadlock
  that concurrent per-row deletes hit.
- **`PUT` on a config singleton/collection** to replace it wholesale
  (`/config/llm-providers`, `/llm-profiles`, `/feature-flags`, `/system-prompts`,
  `/repos-path`) — idempotent full-replace.

## Naming

- **Casing:** lowercase **kebab-case** for every multi-word path segment
  (`llm-providers`, `feature-flags`, `pipeline-failures`, `system-prompts`,
  `prune-cache`, `retry-all`, `blast-radius`). No snake_case or camelCase appears
  in any path. New segments must follow this.
- **Pluralization:** collections are plural (`memories`, `repos`, `tags`,
  `jobs`, `vectors`, `conversations`, `pipeline-failures`); a sub-resource that
  is one-per-parent is singular (`code/graph/{id}`, `code/wiki/{id}`,
  `vectors/projection`, `config/*`).
- **Nouns for resources, verbs only on action sub-resources** (see the action
  pattern above).

Three verb-flavoured names remain (breaking to rename, so left as-is):
`/reembed` (a verb-named maintenance namespace — a noun model would be
`/embeddings` with refresh actions), `/code/symbols/lookup` (a name-based query
better expressed as a filter on `/symbols`), and `/system/fs/list` (reads
imperative; `/fs/entries` would be noun-ish). All are used by the frontend.

## GET is safe and idempotent

A `GET` must never change server state. Wiki generation used to run inside
`GET /code/wiki/{repo_id}`; it is now **read-only** (returns the cached wiki or
`null`). Generation is an explicit action: `POST /repos/{repo_id}/reindex` with
`generate_wiki=true`.

## Known deviations (intentional, not yet changed — breaking to fix)

These are minor verb/consistency deviations left as-is because changing them
would break existing frontend clients for marginal benefit. Fix only with a
coordinated client update:

- `POST /config/llm` sets the six-purpose LLM config (idempotent full replace);
  for symmetry with its `PUT` siblings it should be `PUT /config/llm`.
- `DELETE /repos/{repo_id}/tasks/{task_id}` cancels a running task; a clearer
  model is `POST /repos/{repo_id}/tasks/{task_id}/cancel` (cancel ≠ remove, and
  it isn't idempotent in the DELETE sense).
- `PUT /repos/{repo_id}` is a partial update; `PATCH` would be more precise and
  would harmonize with `PATCH /chat/conversations/{id}`.

## 2026-06-04 audit fixes

A full-surface RESTful audit (all ~70 endpoints) confirmed the posture above and
landed three fixes: `GET /code/wiki` made read-only (safe GET); `POST
/repos/{id}/reindex` now returns `202` (and `409` when already indexing);
`DELETE /pipeline-failures/{id}` now returns `204`.
