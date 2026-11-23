# Introduction

darkmem is a **centralized memory system for AI agents**. It gives agents one
place to write down what they learn and one place to look it up again, so
knowledge survives past the end of a conversation.

You run it yourself. It is a single container plus Postgres, it serves its own
web UI, and every model it talks to is one you configure.

> New here? Read this page, then [Quick Start](quick-start.md) to get it
> running. [Usage Guide](usage-guide.md) covers day-to-day work and
> [Deployment Guide](deployment-guide.md) covers running it for real.

---

## The problem it solves

An agent's context window ends when the session does. Everything it worked out
— the root cause it found, the decision you made, the shape of your codebase —
is gone the next time you start. The usual patch is to paste a summary into the
next prompt, which does not scale and does not accumulate.

darkmem makes that memory durable and shared. Any agent that speaks MCP or HTTP
can write to it and read from it, and they all see the same corpus.

## What is stored

Four layers, each built from the one below it.

| Layer | What it holds | How it gets there |
| --- | --- | --- |
| **L0 — memories** | The raw natural-language note, with its source, project and type | Written directly by an agent or by you |
| **L1 — graph** | Entities and the relationships between them | Extracted from every memory by an LLM |
| **L2 — facts** | Claims promoted from the graph once enough independent sources agree | Derived, then verified against a ladder |
| **L3 — articles** | Longer synthesized write-ups over facts | Synthesized on a schedule |

Alongside those sits a **code layer**: point darkmem at a git repository and it
indexes the symbols, the call graph and the imports, so an agent can ask what
calls a function or what a change would touch.

The layering is what makes the system more than a note pile. A single memory is
just something someone said. A fact is a claim that **several independent
sources** agreed on, and darkmem tracks which sources, how independent they
were, and whether anything contradicts them.

## How memory gets in

Capture is **buffered**. Every write — REST or MCP — is validated, queued and
acknowledged immediately with `202`; a background job then embeds it, extracts
its entities and classifies it. Your agent is never blocked behind an LLM call.
If you do want to wait, ask for it explicitly with `wait_process=true`.

## How memory comes out

Retrieval is **hybrid**: a vector search over embeddings and a keyword search
over a Postgres full-text index, combined with reciprocal rank fusion, with an
optional LLM reranking pass over the top results. The same path serves the
search UI, the chat answer and the agent-facing tools, so two doors cannot rank
the same corpus differently.

## Ways in

- **MCP** (`/mcp`) — the agent-facing surface, 48 tools covering memory,
  documents, code, facts, checkpoints and research. This is how Claude Code,
  Codex and similar clients talk to it. Every call needs a bearer API key,
  scoped per tool.
- **REST** (`/api/v1/...`) — 130-odd endpoints. The web UI is built on it, and
  a small generated SDK (Python and TypeScript) wraps the two verbs an
  application usually needs.
- **Web UI** — served by the same container on the same port. Browse memories,
  inspect the graph, review facts, search code, watch jobs.
- **Browser extension** — capture from a page as you read it.

## What it is not

- **Not multi-tenant.** One admin, one operator. There are no user accounts,
  roles or per-user isolation. Projects scope memories, not permissions.
- **Not a hosted service.** You run the container and you own the data.
- **Not an LLM.** It orchestrates models you point it at — OpenAI-compatible
  endpoints, Ollama, Anthropic, Google, DeepSeek, z.ai. Embeddings can run
  entirely on a local Ollama box.
- **Not zero-config.** It needs at least an embedding model and a chat model
  before ingestion does anything useful.

## Design commitments

A few decisions are load-bearing and unlikely to change:

- **The audit journal is append-only.** Every capture, promotion and
  verification writes an `events` row that is never edited or deleted. Deleting
  a memory removes the row, not its history — see the note on residue in the
  [Usage Guide](usage-guide.md#deletion-is-not-a-purge).
- **A machine cannot mark a fact `confirmed`.** The automated ladder tops out
  at `corroborated`; the top rung is human-only.
- **One contradiction beats any amount of corroboration.** The veto is absolute
  and has no configuration on its path.
- **Single worker, single replica.** The scheduler, the WebSocket fan-out and
  the rate limiter all assume one process. Scaling out is a deliberate,
  documented decision, not a flag.

---

## Where to go next

| You want to | Read |
| --- | --- |
| Get it running in ten minutes | [Quick Start](quick-start.md) |
| Run it as a real deployment | [Deployment Guide](deployment-guide.md) |
| Use it day to day, wire up an agent | [Usage Guide](usage-guide.md) |
| Change the code | [CONTRIBUTING.md](../../CONTRIBUTING.md) |
| Understand the internals | `CLAUDE.md` and `docs/design/` |
