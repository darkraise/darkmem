# Quick Start

Get darkmem running, capture your first memory, and connect an agent. About ten
minutes, most of it waiting on downloads.

**Prerequisites:** Docker with Compose v2, and access to at least one embedding
model and one chat model (a local [Ollama](https://ollama.com) is enough for
both).

---

## 1. Get the files

```bash
git clone https://github.com/darkraise/darkmem.git
cd darkmem
cp .env.example .env
```

## 2. Set the two secrets

Edit `.env`:

```bash
DB_PASSWORD=$(openssl rand -base64 24)     # paste the value in
JWT_SECRET=$(openssl rand -hex 32)         # must be 32+ characters
```

The app refuses to boot on a short or placeholder `JWT_SECRET`, which is
deliberate — a weak session key is worse than a failed start.

**Reaching the UI over plain HTTP** (localhost or a LAN address rather than
HTTPS)? Also set:

```bash
COOKIE_SECURE=false
```

Otherwise the session cookie is marked `Secure`, the browser never sends it
back, and login appears to succeed and then silently fails.

## 3. Start it

```bash
docker compose up -d
```

Two containers come up. Postgres starts first; the app waits for it to be
healthy, runs its database migrations, verifies the schema matches the code,
then serves on **port 8000**.

Watch it come up:

```bash
docker compose logs -f darkmem
```

Check it is ready:

```bash
curl http://localhost:8000/health
# {"status":"ok","pipeline":true,"services":{"pgvector":true,"llm":true}}
```

`"llm":false` here is expected before you finish setup — nothing is configured
yet.

## 4. Run the setup wizard

Open **http://localhost:8000** and complete `/setup`.

> `/setup` is **trust-on-first-use**. It stays open until an admin password
> exists, and the first caller to finish claims the account. Do this
> immediately after first boot, on a network you trust.

The wizard walks three steps:

1. **Admin password.** You authenticate as a single admin; there are no other
   accounts.
2. **Models.** Add a provider, then assign a model to each *purpose*. There are
   eight — `embedding`, `extraction`, `classification`, `reasoning`,
   `summarization`, `reranker`, `verification`, `synthesis`. Each purpose
   carries its own model, base URL and key, so cheap work and expensive work
   can sit on different providers.
3. **A repository** (optional) — a local git path to index.

**The two that matter on day one** are `embedding` and `extraction`. Nothing is
searchable without embeddings, and no graph is built without extraction.

> **Choose your embedding model deliberately.** Every embedding is stored in a
> table keyed to the model that produced it, and vectors from two different
> models are not comparable. Changing it later means re-embedding the whole
> corpus — supported, but not free. Pick one and stay on it.

LLM configuration lives in the database, not in environment variables. There
are no `LLM_*` settings in `.env`.

## 5. Capture your first memory

In the UI: **Memories → New**. Or over HTTP:

```bash
# Log in and keep the session cookie
curl -c jar.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"YOUR_ADMIN_PASSWORD"}'

# Capture
curl -b jar.txt -X POST http://localhost:8000/api/v1/memories \
  -H 'Content-Type: application/json' \
  -d '{
        "content": "We chose Postgres over MongoDB for darkmem because pgvector keeps the vectors next to the relational data.",
        "project": "darkmem",
        "memory_type": "decision"
      }'
```

You get **`202 Accepted`** with an id. That is correct: the capture is durably
queued, and a background job embeds and extracts it a moment later. Add
`?wait_process=true` to block until processing finishes and get `201` with the
finished memory instead.

## 6. Search it

```bash
curl -b jar.txt -X POST http://localhost:8000/api/v1/memories/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"why did we pick our database","limit":5}'
```

Complex queries are `POST .../search` rather than a long query string — that is
the REST convention throughout.

## 7. Connect an agent over MCP

The MCP endpoint is `http://localhost:8000/mcp`. For Claude Code:

```bash
claude mcp add --transport http darkmem http://localhost:8000/mcp
```

Or in a client's config file:

```json
{
  "mcpServers": {
    "darkmem": { "type": "http", "url": "http://localhost:8000/mcp" }
  }
}
```

The agent gets tools for memory (`memory_add`, `memory_search`, `memory_get`,
…), code (`code_search`, `code_symbol`, `code_blast_radius`, …), facts and
session checkpoints.

> **`/mcp` is unauthenticated.** Its only defence is a Host allowlist, and by
> default that allows **localhost only**. An agent on another machine gets
> `421` until you add its host — see below. Never route `/mcp` in from the
> public internet.

**Agent on another LAN machine?** Add the host and port it dials:

```bash
# in .env
MCP_ALLOWED_HOSTS=192.168.1.50:8000
docker compose up -d
```

Fix a `421` by extending that allowlist, never by setting `*`.

## 8. Index a repository (optional)

**Repositories → Add**, give it a local path, then reindex. darkmem walks the
tree, extracts symbols and call edges, and makes them searchable:

```bash
# The id is a UUID from GET /api/v1/repos, not a sequence number.
curl -b jar.txt -X POST http://localhost:8000/api/v1/repos/$REPO_ID/reindex \
  -H 'Content-Type: application/json' -d '{"full": true}'
```

Your agent can now ask `code_search`, `code_symbol` and `code_blast_radius`
about it.

---

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Login seems to work, then you are logged out | `COOKIE_SECURE=true` on plain HTTP. Set it to `false` or use HTTPS. |
| App will not start, complains about `JWT_SECRET` | Shorter than 32 characters or still the placeholder. |
| `/health` says `"llm": false` | No model configured yet, or the provider is unreachable. Finish `/setup`. |
| MCP client gets `421` | Its `Host` header is not in `MCP_ALLOWED_HOSTS`. Add `host:port`. |
| Memories stay unprocessed | The buffer flush job needs a working embedding model. Check **Settings → Pipeline** and **Jobs**. |
| Container is `unhealthy` | It cannot reach Postgres, or the schema guard refused to start. Read `docker compose logs darkmem`. |

---

## Next

- [Usage Guide](usage-guide.md) — projects, search, facts, code, agent patterns
- [Deployment Guide](deployment-guide.md) — backups, upgrades, exposing it safely
