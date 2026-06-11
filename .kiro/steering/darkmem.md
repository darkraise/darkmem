---
inclusion: always
---

# darkmem — centralized memory and code knowledge

darkmem (MCP server `darkmem`) stores facts, decisions, debugging insights,
and indexed codebases so agents keep context across sessions. Kiro does not
read MCP server instructions, so this steering file is the contract: use the
darkmem tools as described here.

## Memory tools

### memory_search — always start here

Search stored memories before making decisions, debugging, or answering
questions about past work. Supports semantic queries plus tag filtering
(`tags_any` / `tags_all`).

Use at the start of a task, before architectural decisions, when the user
references past work, and when a bug looks like something solved before.

### memory_add — save knowledge worth remembering

Store decisions (with the why), debugging root causes, preferences,
constraints, and infrastructure details. Be specific and include context —
a memory should make sense to an agent with no session history.

- Always include `project/<repo-name>` in `tags` (slash notation, e.g.
  `project/darkmem`, `debug/root-cause`, `infra/services`).
- Set `project` to the repo/product name — it scopes supersession so a
  newer memory can replace an outdated one. Tags do NOT feed this.
- `memory_type`: fact, decision, preference, problem, architecture,
  reference, or milestone.
- Do NOT pass `source` or `source_agent` — attribution is automatic via
  the `X-Darkmem-Client` header in this workspace's MCP config. Passing a
  source only overrides correct attribution.
- Several related memories at once → one `memory_batch_add` call.

Save after solving a bug (the root cause, not the symptom), when a decision
is made, and when the user states a preference or constraint.

### memory_reason — question answering

Ask a natural-language question; darkmem retrieves relevant memories and
synthesizes a cited answer. Prefer it over manual search when you need an
answer rather than raw records.

## Code knowledge tools

Indexed repositories are searchable by meaning and structure. Use these
BEFORE reading files directly — they return focused results and save tokens.

1. **code_search** — find relevant code by natural-language description. Start here.
2. **code_file_symbols** — list all functions/classes in a file.
3. **code_symbol** — look up a function/class by name: source, summary, signature.
4. **code_context** — 360° view of a symbol: callers, callees, heritage,
   accesses, processes, community.
5. **code_blast_radius** — before refactoring, what transitively depends on a symbol.
6. **code_rename** — every reference to a symbol for cross-file rename.
7. **code_dependencies** — import relationships for a file or repository.
8. **code_processes** / **code_communities** — traced execution flows /
   clustered modules.
9. **code_changes** — map uncommitted git changes to affected symbols.
10. **list_repos** — which repositories are indexed.

Why: `code_search` returns snippets instead of whole files (saves 80-90% of
tokens); `code_symbol` carries a pre-generated summary; `code_blast_radius`
walks the call graph transitively — faster and more complete than manually
tracing callers.
