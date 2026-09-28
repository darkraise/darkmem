# Usage Guide

Day-to-day work: writing memories worth keeping, finding them again, wiring up
an agent, and reading the code and knowledge layers.

Assumes darkmem is running and set up — see [Quick Start](quick-start.md).

---

## Memories

### What makes a good one

The system is only as useful as what you put in it. A memory earns its place
when it is **durable** (still true next month) and **not derivable** (not
already obvious from the code or the git log).

Good:

> We use bridge networking in production rather than host networking, because
> host mode ignores every `ports:` mapping without erroring, so a regression
> would be silent.

Poor:

> Fixed the bug in `auth.py`.

The first survives; the second is in the commit history already and says
nothing a month later.

Write **one fact per memory**. Two facts in one row cannot be superseded,
corroborated or contradicted independently.

### The fields that matter

| Field | Why it matters |
| --- | --- |
| `content` | The claim itself, in plain language |
| `project` | **The supersession scope.** A memory only ever replaces another in the same project. Default is `default`. |
| `memory_type` | One of `fact`, `decision`, `preference`, `problem`, `reference`, `architecture`, `milestone`, `episodic`, `procedural` |
| `source` | Where it came from (`mcp`, `api`, a named client) — resolved for you |
| `expires_at` | Optional expiry, for things true only for a while |

Type is a closed vocabulary. Send something else and it is mapped to the
nearest match, or falls back to `fact`.

### Capture is buffered

Every write returns **`202 Accepted`** with an id, immediately. Embedding,
extraction and classification happen in a background job a moment later. Your
agent is never blocked behind a model call.

Need the processed result inline? Ask for it:

```bash
POST /api/v1/memories?wait_process=true    # 201 with the finished memory
```

Watch the queue at **Settings → Pipeline**, and triage anything that failed
there — a poisoned row settles alone with the real error attached rather than
taking a whole batch down.

### Supersession

When a new memory says it replaces something — an extracted `REPLACES`,
`IMPROVES_ON` or `BUILDS_ON` relationship — darkmem retires the old one
automatically. It flips to `superseded` with a pointer to its replacement, and
drops out of the default view without being deleted.

Guardrails worth knowing:

- Same project only.
- The candidate must be **older**, and within a 90-day window.
- They must share a technology, so unrelated notes are untouched.
- **Speculation does not count.** "We might switch to Redis" leaves the Redis
  memory alone; "we replaced Redis with Postgres" retires it. The check is
  scoped per target, so an unrelated hedge elsewhere in the text does not
  suppress a definite replacement.

### Deletion is not a purge

Deleting a memory removes the row. It does **not** remove the audit trail, and
that is deliberate — the journal is append-only, and an application path that
rewrote history would put "make this never have happened" one bug away from the
audit substrate.

Residue can survive in event payloads, refine summaries, the fact vault and
briefly in the capture buffer. **If a secret is ever pasted into a memory,
deleting it is not enough** — rotate the secret, and use the operator procedure
in `docs/runbook-content-purge.md` if the copies themselves must go.

---

## Finding things

### Search

Search is **hybrid**: meaning and keywords at once. A vector search over
embeddings finds "how do we store vectors" against a memory that says
"pgvector"; a Postgres full-text search catches the exact identifier a vector
search would blur. The two rankings are fused, and an optional reranking pass
re-scores the top results with a model.

```bash
POST /api/v1/memories/search
{ "query": "why did we choose our database", "limit": 10, "project": "darkmem" }
```

Complex queries are `POST .../search` rather than a long query string —
consistent across the API.

Practical notes:

- **Ask in natural language.** The vector arm is the half that rewards a real
  question; keywords are already covered by the other arm.
- **Scope by project** when you know it. It is the cheapest precision win.
- Results carry a fused score. Prefer it over any single-arm score.

### Chat

**Chat** answers questions over the corpus and cites what it used. It runs the
same retrieval path as the search page — deliberately, so the two doors cannot
rank one corpus differently.

### The graph

**Memory Graph** shows entities and their relationships. Entities are *not*
scoped to a single memory: each one records every memory that asserts it, so a
node's weight is genuine corroboration rather than a duplicate row per mention.
Both vocabularies are closed — 15 entity types, 16 relationship types — so a
model's invented label is normalized rather than stored.

---

## Facts and the verification ladder

Facts (**Knowledge → Facts**) are claims promoted out of the graph once enough
independent sources agree. Every fact carries a rung:

| Status | Meaning |
| --- | --- |
| `candidate` | Seen, not yet corroborated |
| `corroborated` | Enough independent sources agree — **the machine's ceiling** |
| `confirmed` | A human ratified it. Only a human can write this. |
| `disputed` | Something contradicts it |

**Independence is counted, not assumed.** Corroboration counts *distinct
origins*, not rows: the same page fetched twice, re-run, or paraphrased is one
origin, because the URL is aggressively canonicalized first. Three independent
origins promote a claim, or two if they differ in kind or are at least seven
days apart. Anonymous sources collapse into one bucket that counts once.

**One contradiction beats any amount of corroboration.** The veto is absolute
and has no configuration on its path.

### The review queue

**Knowledge → Review** is where facts needing a human land: disputed ones,
ones that lost their sourcing, ones flagged as contradicted, and ungrounded
articles. Each row states *why* it opened. Ratifying is the one action that
mints `confirmed`.

---

## Code

Register a repository (**Code → Repositories**), point it at a local git path
and index it. darkmem extracts symbols, call edges and imports into a graph you
can query.

| Surface | Use it for |
| --- | --- |
| **Code Graph** | Visual exploration of symbols and their edges |
| **Code Wiki** | Generated prose about the repository, read-only |
| `code_search` | Find code by description |
| `code_blast_radius` | Everything that transitively depends on a symbol — check before refactoring |
| `code_context` | Callers, callees, heritage and community for one symbol in a single call |

Reindexing is incremental: an unchanged HEAD short-circuits. When a run
re-traces the callers of changed files it caps the work, and **persists the
overflow as debt** rather than dropping it — later runs fold that queue back in
until it reaches zero, because a graph with silently missing callers has no
symptom.

---

## Wiring up an agent

`/mcp` is the agent surface. Mint a key first in Settings → API keys (both
`capture` and `read` for a normal agent; the secret is shown once), then add
the server with that key on the `Authorization` header:

```bash
claude mcp add --transport http darkmem http://localhost:8000/mcp \
  --header "Authorization: Bearer dmk_<key_id>_<secret>"
```

Without the header every call is refused with `401`. A key that authenticates
but lacks a tool's scope is refused with JSON-RPC error `-32003` — that is a
scope problem, not a retry.

### The tools

| Group | Tools |
| --- | --- |
| Memory | `memory_add`, `memory_batch_add`, `memory_search`, `memory_get`, `memory_update`, `memory_delete`, `memory_find_duplicates`, `memory_stats`, `memory_tags`, `memory_overview`, `memory_reason` |
| Code | `code_search`, `code_symbol`, `code_file_symbols`, `code_blast_radius`, `code_dependencies`, `code_context`, `code_changes`, `code_communities`, `code_processes`, `code_rename`, `list_repos` |
| Knowledge | `knowledge_search`, `fact_get`, `article_get` |
| Documents | `document_put`, `document_search`, `document_outline`, `document_get`, `document_delete` |
| Work log | `worklog_append`, `worklog_resume`, `worklog_workstreams`, `worklog_entries`, `worklog_search`, `worklog_update`, `worklog_purge` |
| Research | `research_run` |

### Patterns that work

**Search before deciding.** The highest-value habit: have the agent query
darkmem at the start of a task, before it re-derives something already settled.

**Write when something is decided, not continuously.** Capture the conclusion
and its reasoning, not a running commentary.

**Keep working data in the work log.** `worklog_append` files a checkpoint, ledger text or a note under a workstream; `worklog_resume` picks the work back up in the next session.

**Search a document before reading it off disk.** `document_put` files a
markdown or plain-text file under its repo-relative path, and `document_search`
answers with the matching sections rather than the whole file. The keyed verbs
take that path instead of an id — `document_outline(project, uri)` gives the
heading map and `document_get` pulls only the blocks you name — so an agent
resuming work needs the filename it already knows and nothing it saw in a
previous session.

**Batch related captures.** `memory_batch_add` takes up to 100 in one
round-trip, which is one buffered batch rather than 100.

### Identity

Writes record where they came from. An explicit `source`, an
`X-Darkmem-Client` header and the client's user agent are consulted in that
order. Set the header if you run several agents and want to tell their writes
apart later.

### Research runs

`research_run` files evidence an agent gathered itself. It exists only on MCP,
and only because the caller has to *be* the gatherer — darkmem ships no
web-fetching implementation, so a REST route would be dishonest about what it
does. It refuses until you enable it in settings, and every row it files is
stamped with its own source identity so manufactured corroboration is not
possible.

---

## The SDKs

For applications rather than agents, a small generated client covers the three
verbs most callers need:

```python
from darkmem_sdk import Darkmem

client = Darkmem(base_url="http://localhost:8000", api_key="...")
await client.capture(content="...", project="myapp")
results = await client.search(query="...", limit=10)
```

TypeScript is the same shape. **Both clients are generated** from the live API
description — edit `sdks/generate.py` and run `make generate` in `sdks/`, never
the emitted files. The generator refuses to emit a call the API does not
actually serve, which is the whole reason it is generated rather than written.

---

## Projects

`project` partitions the corpus. It is the supersession scope, a search filter,
and how you keep unrelated work from colliding.

It is **not** a permission boundary. Anyone who can reach the API can read every
project.

---

## Next

- [Deployment Guide](deployment-guide.md) — backups, upgrades, exposure
- [Introduction](introduction.md) — how the layers fit together
- `CLAUDE.md` — the internal contract, if you are changing the code
