# Runbook — exposing darkmem beyond the LAN

**Who this is for.** An operator putting darkmem behind a TLS proxy so it is
reachable from outside the trusted LAN. Everything here is additive: every LAN
rule below still holds underneath (doc 18 §9).

**darkmem does not terminate TLS and never will.** It has no certificate
handling, no ACME client and no HTTP→HTTPS redirect. The certificate, the
renewal, and the redirect are the operator's proxy's job. If you have not put a
TLS proxy in front, you are not in this posture — stay on the LAN defaults.

## 1. The one switch, and everything it moves

`TRUST_PROXY_HEADERS=true` is the exposed-deployment switch. It is not only a
rate-limiter setting:

| | LAN default (off) | Exposed (on) |
|---|---|---|
| Login rate-limit bucket | the transport peer | `X-Real-IP`, else the **rightmost** `X-Forwarded-For` hop |
| `cookie_secure` | tri-state: unset ⇒ Secure only when `ENVIRONMENT=production` | **enforced** — an explicit `COOKIE_SECURE=false` is overridden |

The leftmost `X-Forwarded-For` is read in **neither** posture. It is
client-supplied, so a limiter keyed on it would let an attacker rotate the
value per guess and never lock out.

Setting `COOKIE_SECURE=false` alongside `TRUST_PROXY_HEADERS=true` is not an
error and does not stop the app — the value is clamped to `true`, a warning is
logged at startup, and `GET /api/v1/auth/security-posture` reports
`cookie_secure_clamped: true`. If you genuinely serve plain HTTP, leave
`TRUST_PROXY_HEADERS` off; the two settings describe the same fact and must
agree.

**One topology is unsupported, and it is worth saying plainly: a reverse proxy
that does not terminate TLS.** Neither setting is right for it. With the switch
on, the clamped Secure cookie is dropped by the browser over plain HTTP and
login silently loops. With it off, every client shares the proxy's single
limiter bucket, so one attacker locks out everyone. Put TLS on the proxy, or
put nothing in front and let the app be the edge.

**If login loops after you turn the switch on, suspect the clamp first.** Every
report of it except the startup log — the posture endpoint, the settings card —
sits behind the login it just broke, so the boot warning is the one you can
still read. Check the container log for `COOKIE_SECURE=false is clamped`.

## 2. What your proxy must do

- **Terminate TLS**, and redirect plain HTTP to it.
- **Set `X-Real-IP` to its own view of the peer**, overwriting whatever the
  client sent. If the client can supply this header through your proxy, the
  lockout is defeated and turning the switch on has made things worse than
  leaving it off.
- **Append to `X-Forwarded-For`, never replace it** — the app reads the
  rightmost hop, which must be the one your proxy added.
- **Send the credential as `Authorization: Bearer`.** The webhook authenticates
  the *caller*, not a signature over the payload — which it never parses, since
  the pipeline re-derives the true state with its own `git pull` and HEAD
  compare. The consequence to plan around: **GitHub.com's native webhook
  delivery cannot set an `Authorization` header**, so it cannot reach this
  receiver. Self-hosted senders that can — Gitea, a `post-receive` script,
  a small relay — can.
- **Do not route `/mcp` from the public side** — and the app refuses it rather
  than trusting you not to. **Every `/mcp` call requires
  `Authorization: Bearer dmk_<key_id>_<secret>`, scoped per tool (doc 18 §5,
  shipped 2026-08-26)** — that closes the old "any LAN peer can call any tool"
  gap, but it does not make public exposure safe, and this runbook still
  enforces the same "do not route it" rule rather than relaxing it now that a
  key is required. Three reasons. First, the guard below does not consult the
  bearer at all — a proxied `/mcp` request is refused whether or not it
  carries a valid key, because the guard answers "did this arrive from
  outside", not "is this caller allowed in". Second, MCP auth has no
  login-style lockout: nothing slows or blocks repeated bad credentials.
  Third, every attempt — including an invented key — costs one fixed-cost
  `bcrypt` verification (`app/services/api_keys.py`'s constant-time-miss
  design) run off the same shared thread executor that also serves git
  subprocesses, code parsing and local classification; roughly 20 concurrent
  junk credentials is enough to saturate it, so a public `/mcp` is a cheap way
  to degrade unrelated work well before an attacker needs a real key. So with
  `TRUST_PROXY_HEADERS=true`, a `/mcp` request carrying proxy headers is
  answered `403 mcp_not_exposed` and journalled as `mcp_proxied_refused`
  (throttled to one row a minute, so a scanner cannot grow the journal).
  Restrict it at the proxy as well; this guard is the backstop, not the plan.

  **Extending `MCP_ALLOWED_HOSTS` does not lift it.** That is deliberate. The
  standing advice for a LAN `421` is to extend the allowlist, and without this
  guard that advice — correct for its own problem — was one entry away from
  publishing `/mcp`. A LAN or local agent reaching the box directly is
  untouched in both postures.

## 3. Credentials for programmatic callers

Non-human callers use an API key — `Authorization: Bearer dmk_<key_id>_<secret>`
— minted from the settings UI, with a closed scope set (`capture`, `read`,
`admin`). The plaintext is shown once at issue. `ratify` is not a scope and
never becomes one: confirming a fact stays a human cookie session on the REST
door.

**What each scope reaches, exactly.** REST's scope-gated surface is small on
purpose, and it is the surface the minimal client speaks:

| Scope | Routes |
|---|---|
| `capture` | `POST /memories`, `POST /memories/batch`, `POST /documents`, `POST /worklog/entries`, `PATCH /worklog/workstreams/{id}` |
| `read` | `POST /memories/search/paginated`, `GET /documents/by-uri`, `GET /documents/manifest`, `GET /documents/{id}/revisions`, `GET /documents/{id}/revisions/{revision_id}`, `GET /worklog/resume`, `GET /worklog/workstreams`, `GET /worklog/workstreams/{id}/entries`, `POST /worklog/search` |
| `admin` | `POST /repos/{id}/webhook`, `POST /repos/{id}/reindex-files`, `DELETE /worklog/workstreams/{id}` |

**`/mcp` is scoped far more widely, and separately** (doc 18 §5's second
activation, 2026-08-26): of its 46 tools, 14 require `capture`, 29 require
`read` and three require `admin`, so a `capture`-scoped key reaches all 14 MCP
writer tools — `memory_add`, `memory_batch_add`, `memory_update`,
`memory_delete`, `document_put`, `document_update`, `document_delete`,
`research_run`, `block_update`, `block_insert`, `block_move`, `block_delete`,
`worklog_append`, `worklog_update` — not only the REST routes above, and a
`read`-scoped key reaches the 29 readers. The table above is REST's reach
only; do not read it as the whole reach of a key of any scope.

**A leaked `admin` key now reaches `/mcp` too, which it did not before
2026-08-28 — and since 2026-09-07 its blast radius includes destroying your
data.** Three tools are `admin`-scoped, and the second and third erase data:

- `code_reindex` (2026-08-28) can trigger a repository index at will, which
  spends embedder budget per run, and on a *clone* repository the run's own
  `pull_repo` executes `git reset --hard` against the fetched head —
  uncommitted work in darkmem's clone directory does not survive it. It
  rebuilds the code graph and asserts nothing into the memory graph.
- `document_delete_subtree` (2026-09-07) **deletes every document under any
  `(project, uri_prefix)` the caller names, in one call**. It cascades each
  document's blocks and their vectors, and there is no undo: the `events`
  journal records one `documents_deleted` row per document, naming the key
  that ran it, but a journal row is an audit trail and not a backup, and
  **there is no corpus-scoped undo**. The only documented recovery is
  `scripts/restore.sh` (`docs/wiki/deployment-guide.md`, `README.md`), which
  replays a `backup.sh` or `backup_ship` dump into a side database and swaps
  it in — and that is a rollback of *everything*: every memory, fact and event
  since the dump you restore goes back with the documents, including the
  `documents_deleted` rows the paragraph below tells you to read, so read and
  save them first. Documents filed since that dump are lost either way.
  Nothing documents a selective restore of `documents` → `blocks` → the
  per-fingerprint `block_embeddings__<slug>` children. **Choose the newest
  dump taken *before* the erase, not the newest dump on disk** — the
  `created_at` on the first `documents_deleted` row is the cutoff, which is
  the other reason to read those rows first. The two producers run an hour
  apart and write to different directories, so an erase falling between them
  leaves the newest file on disk already missing the documents, and restoring
  it recovers nothing. A caller needs no id and no prior read — a project name
  and a prefix guess are the whole address.
- `worklog_purge` (2026-09-23) **erases one workstream and every entry in it
  — checkpoints, ledger, notes — irrecoverably**, addressed by `(project,
  key)`; its REST twin `DELETE /worklog/workstreams/{id}` is `admin`-scoped
  too. It journals one `workstream_purged` row naming the key and the entry
  count *before* the delete and refuses when that row does not land, but there
  is no undo: the only recovery is the same whole-database `scripts/restore.sh`
  rollback described above.

So the three's radius is: spend budget, discard uncommitted work in the clone
directory, and **erase filed documents and work-log workstreams
irrecoverably**. None can mint a credential (no MCP tool can) and none reaches
`confirmed` power. **Rotate an exposed `admin` key immediately and treat the
corpus as suspect until you have checked the journal** — `GET /events`
filtered to `documents_deleted` and `workstream_purged` tells you what was
erased and under which key name. Do not rotate on the
older "its blast radius is the same as the webhook's" basis, and do not rotate
on the older-still "admin reaches no MCP tool" one; both understate this.

Everything else stays human-session-only. That is a deliberate boundary rather
than an oversight: widening `read` to the fact vault or the code graph decides
what a leaked key can exfiltrate, so it happens when something needs it. Grant
the narrowest scope that does the job — a webhook sender needs `admin` and
nothing else.

Revoke a key from the same surface. Revocation sets `revoked_at` and keeps the
row rather than deleting it, so calls the key already made keep a resolvable
name instead of pointing at an id nothing explains.

**Detecting a key you did not expect to be in use.** Every keyed delivery
journals a `repo_webhook_received` event carrying the key id and its label —
including deliveries that are refused as conflicts or that name a repository
that does not exist, which is what a probing credential mostly produces. The
settings card's last-used column is the quick signal; the events journal is the
record. A key whose last-used time moves when you are not deploying is the
signal to revoke.

A `capture`-scoped key can write memories today, on REST and on MCP, and every
such call — either door — stamps `events.api_key_id`/`actor` on the journal
row, so a memory captured by a key you did not expect to be active is visible
there too, not only in webhook activity.

## 4. Verify the posture you think you have

With an authenticated session, read the live posture rather than assuming it:

```
GET /api/v1/auth/security-posture
```

Expect, in this posture:

- `trust_proxy_headers: true`
- `cookie_secure: true` (and `cookie_secure_clamped: true` if you also set
  `COOKIE_SECURE=false`)
- `mcp_allowed_hosts` listing exactly the hosts you intend

Then confirm the limiter is really keyed on the proxied address: make
`rate_limit_max_failures` failed logins from one client, confirm the next
attempt returns `429`, and confirm a request from a different source address
still returns `401`. If the `429` never arrives, your proxy is not setting
`X-Real-IP` the way §2 requires.

## 5. What does not change

The MCP Host allowlist (a foreign Host is `421`, fixed by extending the
allowlist — never by setting `*`), trust-on-first-use setup then `403`,
single-door ratification, and the single-worker invariant. Exposure layers on
top of these; it replaces none of them.
