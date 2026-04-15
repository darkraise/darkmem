"""One-off emitter for shared-base batch-085 — ai_coding domain (AI pair-programming slice: Copilot, Cursor, Claude Code, Aider, Cody, Continue.dev, prompt patterns, agent loops, MCP integrations, project rule files, context-window management, hallucination guardrails).

Writes 50 rows to data/v2/shared/batch_085.tmp.jsonl with ids shared-04201..04250.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_085.tmp.jsonl"
ID_OFFSET = 4200

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the team off Copilot and onto Cursor for the monorepo work; the project-wide context the new editor builds out of .cursor/rules made the Copilot one-file window feel blind.", "decision", "ai_coding", False,
     [("Copilot", "tool"), ("Cursor", "tool"), (".cursor/rules", "file"), ("monorepo", "pattern")],
     [("Cursor", "Copilot", "REPLACES")],
     "which AI editor swap landed for the monorepo work and what tipped the call",
     "cursor replace copilot monorepo project rules context window"),
    # --- 2 ---
    ("Added a CLAUDE.md at the repo root pinning the test runner, the lint command, and the never-touch-generated-files rule; Claude Code stopped re-formatting the protobuf output on every session.", "milestone", "ai_coding", False,
     [("CLAUDE.md", "file"), ("Claude Code", "tool"), ("protobuf", "technology")],
     [],
     "which project rule file did we ship to stop Claude Code from reformatting generated protobuf output",
     "claude md project rule lint test runner generated file ignore"),
    # --- 3 ---
    ("Switched the agent loop in Aider from auto-commit to a stage-and-review flow; the noisy single-line WIP commits were drowning the real history during bisects.", "problem", "ai_coding", False,
     [("Aider", "tool"), ("auto-commit", "pattern"), ("bisect", "command")],
     [],
     "why did we disable Aider auto-commit and what flow replaced it",
     "aider auto commit disable stage review bisect history noise"),
    # --- 4 ---
    ("Standardised on Continue.dev with a self-hosted Ollama backend for the offline-only laptops; Copilot was a non-starter once the airgap policy landed for the regulated workspace.", "decision", "ai_coding", False,
     [("Continue.dev", "tool"), ("Ollama", "service"), ("Copilot", "tool"), ("airgap", "pattern")],
     [("Continue.dev", "Copilot", "REPLACES"), ("Continue.dev", "Ollama", "USES")],
     "which AI assistant replaced Copilot on the airgapped laptops and what backend powers it",
     "continue dev ollama self host airgap regulated copilot ban"),
    # --- 5 ---
    ("Wrote a slim MCP server exposing the internal feature-flag API to Claude Code; the agent now reads flag state in plan mode instead of guessing from stale grep results.", "architecture", "ai_coding", False,
     [("MCP", "protocol"), ("Claude Code", "tool"), ("feature-flag API", "api")],
     [("Claude Code", "MCP", "USES")],
     "how did we give Claude Code first-class access to the live feature-flag state during planning",
     "mcp server feature flag api claude code plan mode read live"),
    # --- 6 ---
    ("Cody Enterprise's repo-wide context retrieval beat Copilot Workspace on a side-by-side cold-repo onboarding test; ship-blocker was Copilot's inability to find the auth helper across packages.", "fact", "ai_coding", False,
     [("Cody", "tool"), ("Copilot Workspace", "tool"), ("auth helper", "pattern")],
     [("Cody", "Copilot Workspace", "IMPROVES_ON")],
     "which assistant won the cold-repo onboarding shootout and what failure mode broke the loser",
     "cody enterprise repo wide context copilot workspace shootout"),
    # --- 7 ---
    ("Pinned the Cursor model router to claude-3.7-sonnet for refactors and gpt-4o-mini for autocomplete; the mixed routing cut spend roughly in half without anyone complaining about quality.", "preference", "ai_coding", False,
     [("Cursor", "tool"), ("claude-3.7-sonnet", "technology"), ("gpt-4o-mini", "technology"), ("model router", "pattern")],
     [],
     "which Cursor model-router split did the team settle on and what did it do to spend",
     "cursor router sonnet refactor gpt 4o mini autocomplete cost"),
    # --- 8 ---
    ("Tabnine's local model went out the door once Copilot Business shipped per-file context retrieval; the offline-completion argument mattered less than the cross-file recall gap.", "decision", "ai_coding", False,
     [("Tabnine", "tool"), ("Copilot Business", "tool")],
     [("Copilot Business", "Tabnine", "REPLACES")],
     "why did Copilot Business displace Tabnine for the team and what feature tipped it",
     "tabnine local model copilot business cross file context recall"),
    # --- 9 ---
    ("Codeium's free tier covered the contractors fine for a year; we moved them onto a paid Codeium Teams seat once the security review demanded SSO and audit log retention.", "milestone", "ai_coding", False,
     [("Codeium", "tool"), ("Codeium Teams", "tool"), ("SSO", "protocol")],
     [],
     "which Codeium tier change did the contractors hit and what drove the upgrade",
     "codeium free teams sso audit log security review contractor"),
    # --- 10. noise ---
    ("The mug on the desk grew a small ring of dried tea that nobody felt motivated to clean today.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Windsurf's cascade mode handles the long-horizon refactor better than Cursor's composer for our case; the diff plan it surfaces before edits is what sold the platform team.", "fact", "ai_coding", False,
     [("Windsurf", "tool"), ("Cursor", "tool"), ("cascade", "pattern"), ("composer", "pattern")],
     [("Windsurf", "Cursor", "IMPROVES_ON")],
     "which long-horizon refactor flow beat Cursor composer in our trial and why",
     "windsurf cascade cursor composer long horizon refactor diff plan"),
    # --- 12 ---
    ("Adopted Zed AI for the Rust crate work; the edit-prediction latency on a Mac is noticeably tighter than VS Code with Copilot once the file crosses 2k lines.", "preference", "ai_coding", False,
     [("Zed AI", "tool"), ("Rust", "language"), ("VS Code", "tool"), ("Copilot", "tool")],
     [("Zed AI", "VS Code", "IMPROVES_ON")],
     "which editor felt fastest for large Rust files and what did it beat",
     "zed ai rust crate latency vs code copilot large file edit"),
    # --- 13 ---
    ("Wrote an AGENTS.md alongside CLAUDE.md so both Codex and Claude Code pick up the same canonical instructions; duplication beats divergence when two agents share the repo.", "architecture", "ai_coding", False,
     [("AGENTS.md", "file"), ("CLAUDE.md", "file"), ("Codex", "tool"), ("Claude Code", "tool")],
     [],
     "how do Codex and Claude Code share the same project rules in this repo",
     "agents md claude md codex shared instruction duplicate canonical"),
    # --- 14 ---
    ("The hallucination guardrail in the agent loop is a tool-existence check: before invoking any shell command the agent must confirm the binary is on PATH, no inventing flags.", "architecture", "ai_coding", False,
     [("agent loop", "pattern"), ("PATH", "config"), ("hallucination", "pattern")],
     [],
     "which guardrail keeps the coding agent from inventing CLI flags or non-existent binaries",
     "hallucination guardrail tool existence path check binary verify"),
    # --- 15 ---
    ("Allowlisted only git, pytest, ruff, and the project's make targets in the Claude Code permissions file; everything else prompts and the prompts get logged for audit.", "preference", "ai_coding", False,
     [("Claude Code", "tool"), ("git", "tool"), ("pytest", "tool"), ("ruff", "tool"), ("make", "tool")],
     [],
     "which command allowlist does Claude Code run under in this repo and how are denials handled",
     "claude code permission allowlist git pytest ruff make audit prompt"),
    # --- 16 ---
    ("Context-window pressure on the legacy 800k-LOC Java repo got fixed by handing the agent a repo-map index instead of raw tree dumps; tokens per turn dropped four-fold.", "problem", "ai_coding", False,
     [("repo-map", "pattern"), ("Java", "language"), ("Context-window", "concept")],
     [],
     "how did we shrink token usage on the legacy Java monorepo agent runs",
     "context window repo map index tree dump token saving java"),
    # --- 17 ---
    ("Prompt template for bug-fixes pins three sections: failing test, suspected file list, and the narrowest possible diff brief; freeform prompts produced sprawling unrelated edits.", "decision", "ai_coding", False,
     [("Prompt template", "pattern"), ("diff", "pattern")],
     [],
     "which prompt structure cut down sprawling AI bug-fix edits",
     "prompt template bug fix failing test file list narrow diff brief"),
    # --- 18 ---
    ("Banned Copilot from generating new SQL by route; the lint config rejects model-authored sql files unless a human review tag is present in the commit trailer.", "preference", "ai_coding", False,
     [("Copilot", "tool"), ("SQL", "language"), ("commit trailer", "pattern")],
     [],
     "which guardrail forces human review on Copilot-authored SQL changes",
     "copilot ban sql route lint commit trailer human review tag"),
    # --- 19 ---
    ("Rolled out a code-review bot built on Claude Code that posts inline comments on PRs; humans still approve, the bot just front-loads the obvious style and contract issues.", "milestone", "ai_coding", False,
     [("Claude Code", "tool"), ("PR", "concept"), ("code-review bot", "service")],
     [("code-review bot", "Claude Code", "USES")],
     "which AI bot now front-loads obvious PR review issues and who has the final say",
     "code review bot claude code inline comment pr style contract"),
    # --- 20 ---
    ("Real-PR eval harness scores each model's diff against the human-merged version using a syntactic plus behavioural test; sonnet currently leads on backend, gpt-4o on frontend.", "fact", "ai_coding", False,
     [("eval harness", "method"), ("sonnet", "technology"), ("gpt-4o", "technology")],
     [],
     "how do we evaluate model code quality against real merged PRs and which leads where",
     "real pr eval harness diff score behavioural test sonnet gpt 4o"),
    # --- 21 ---
    ("Cursor's apply-edits got disabled on terraform files after a model rewrote a moved block and detached state; the .cursor/rules now includes a hard ignore for *.tf.", "problem", "ai_coding", False,
     [("Cursor", "tool"), ("terraform", "tool"), (".cursor/rules", "file"), ("*.tf", "pattern")],
     [],
     "which Cursor incident on terraform led to a hard ignore in the project rules",
     "cursor terraform moved block state detach ignore tf rule fix"),
    # --- 22 ---
    ("MCP server for the internal Sentry project lets Claude Code pull error frequencies and stack traces straight into the planning prompt; ad-hoc curl gymnastics are gone.", "architecture", "ai_coding", False,
     [("MCP", "protocol"), ("Sentry", "service"), ("Claude Code", "tool")],
     [("Claude Code", "Sentry", "COMMUNICATES_WITH")],
     "how does Claude Code now pull live Sentry data into a planning prompt",
     "mcp sentry claude code error frequency stack trace plan integrate"),
    # --- 23 ---
    ("Aider's repo-map mode beat hand-crafted file lists for the cross-cutting auth refactor; the model picked the right adjacent files we'd have missed if we curated by hand.", "fact", "ai_coding", False,
     [("Aider", "tool"), ("repo-map", "pattern"), ("auth", "pattern")],
     [("Aider", "repo-map", "USES")],
     "when did Aider's automatic repo-map outperform our hand-curated file list",
     "aider repo map auth refactor adjacent file pick hand curate"),
    # --- 24 ---
    ("Disabled Copilot ghost-text inside test files for a sprint after observing engineers passively accept obviously-wrong assertions; the typing-through-it autopilot effect is real.", "decision", "ai_coding", False,
     [("Copilot", "tool"), ("ghost-text", "pattern"), ("autopilot", "pattern")],
     [],
     "why did we briefly switch off Copilot ghost-text in test files and what behaviour drove it",
     "copilot ghost text disable test file passive accept autopilot bias"),
    # --- 25 ---
    ("Claude Code subagent dispatch for parallel refactors works once each subagent gets its own worktree; sharing the working copy turned into a stomping race the first time we tried.", "architecture", "ai_coding", False,
     [("Claude Code", "tool"), ("subagent", "pattern"), ("worktree", "command")],
     [],
     "what made parallel Claude Code subagents safe and what blew up first",
     "claude code subagent parallel worktree race shared working copy"),
    # --- 26 ---
    ("Wrote a slash command, /security-review, that wraps the OWASP-top-10 prompt template and runs against the staged diff; the team uses it as a pre-push gate.", "milestone", "ai_coding", False,
     [("/security-review", "command"), ("OWASP", "organization"), ("staged diff", "pattern")],
     [],
     "which slash command wraps the OWASP prompt as a pre-push security gate",
     "security review slash command owasp top ten staged diff gate"),
    # --- 27 ---
    ("Continue.dev profile per language: codestral for Rust, qwen2.5-coder for Go, llama3.1 for shell glue; one model per surface beat one-model-fits-all on hit rate.", "preference", "ai_coding", False,
     [("Continue.dev", "tool"), ("codestral", "technology"), ("qwen2.5-coder", "technology"), ("llama3.1", "technology")],
     [],
     "how did the team split Continue.dev models per language and what did the split improve",
     "continue dev codestral qwen coder llama profile language hit rate"),
    # --- 28 ---
    ("Hallucinated import paths got caught by a post-edit tsc --noEmit hook; the agent loop refuses to advance to the next step until the type check is clean.", "architecture", "ai_coding", False,
     [("tsc", "command"), ("agent loop", "pattern"), ("import", "pattern")],
     [],
     "which post-edit check stops the coding agent from advancing on hallucinated imports",
     "tsc no emit post edit hook agent loop hallucinated import gate"),
    # --- 29 ---
    ("Decided against letting the agent push branches; the loop ends at git commit and a human runs the push once the diff and tests look right.", "decision", "ai_coding", False,
     [("agent", "pattern"), ("git commit", "command"), ("push", "command")],
     [],
     "where does the agent loop stop in our git workflow and why",
     "agent commit push human gate diff review safety branch policy"),
    # --- 30 ---
    ("Added a .cursor/rules entry forbidding edits to migrations/ unless the prompt explicitly says new-migration; the model used to retroactively edit applied migrations and break alembic history.", "problem", "ai_coding", False,
     [(".cursor/rules", "file"), ("migrations/", "file"), ("alembic", "library")],
     [],
     "which .cursor/rules entry stopped the model from retro-editing applied alembic migrations",
     "cursor rules migrations forbid edit alembic history protect"),
    # --- 31 ---
    ("Engineer satisfaction with the AI tooling jumped after the team standardised on Cursor; the daily flow felt less fragmented than juggling Copilot and a separate Claude tab.", "fact", "ai_coding", False,
     [("Cursor", "tool"), ("Copilot", "tool"), ("satisfaction", "emotion")],
     [],
     "what happened to engineer satisfaction once Cursor became the standard",
     "engineer satisfaction cursor standard copilot fragmentation flow"),
    # --- 32 ---
    ("Frustration spiked the week Claude Code rate-limits hit during a release crunch; the workaround was a fallback Continue.dev profile pointed at a self-hosted Mistral.", "problem", "ai_coding", False,
     [("Claude Code", "tool"), ("Continue.dev", "tool"), ("Mistral", "technology"), ("Frustration", "emotion")],
     [],
     "what fallback rescued the release week when Claude Code hit rate limits",
     "claude code rate limit release crunch continue dev mistral fallback"),
    # --- 33 ---
    ("Tested GitHub Copilot Workspace on a real bug; it produced the right plan but the patch missed two call sites that Cody picked up cleanly the next try.", "fact", "ai_coding", False,
     [("GitHub Copilot Workspace", "tool"), ("Cody", "tool"), ("call sites", "pattern")],
     [("Cody", "GitHub Copilot Workspace", "IMPROVES_ON")],
     "what did the head-to-head between Copilot Workspace and Cody on a real bug show",
     "copilot workspace cody bug fix call site coverage compare"),
    # --- 34 ---
    ("Set the goal of getting AI-authored commits to 30% of the total by end of quarter; tracking it via a commit trailer Co-Authored-By: <model> grep on main.", "decision", "ai_coding", False,
     [("AI-authored", "pattern"), ("Co-Authored-By", "config"), ("main", "pattern")],
     [],
     "which AI-adoption goal are we tracking this quarter and how is the metric collected",
     "goal ai authored commit thirty percent co authored by trailer"),
    # --- 35 ---
    ("Demo day on 2026-03-30 showed the platform team's MCP-driven agent loop closing a real on-call ticket end to end; that was the moment leadership stopped asking if the tooling was real.", "milestone", "ai_coding", False,
     [("2026-03-30", "date"), ("MCP", "protocol"), ("on-call ticket", "concept"), ("agent loop", "pattern")],
     [],
     "which demo flipped leadership opinion on the agent tooling and when did it happen",
     "demo day march mcp agent loop on call ticket leadership"),
    # --- 36 ---
    ("Added a CONTRIBUTING note that AI-generated code must include a short rationale comment only when the choice is non-obvious; otherwise comment-spam from models pollutes diffs.", "preference", "ai_coding", False,
     [("CONTRIBUTING", "file"), ("AI-generated", "pattern"), ("rationale comment", "pattern")],
     [],
     "which CONTRIBUTING rule trims comment spam from AI-generated diffs",
     "contributing ai generated rationale comment non obvious diff clean"),
    # --- 37 ---
    ("Plan-mode in Claude Code is mandatory for any change touching billing/; the dry-run output goes into the PR description so reviewers see the agent's intent before reading the diff.", "architecture", "ai_coding", False,
     [("Claude Code", "tool"), ("billing/", "file"), ("Plan-mode", "pattern"), ("PR", "concept")],
     [],
     "which Claude Code mode is mandatory on billing changes and how does the plan reach reviewers",
     "claude code plan mode billing pr description reviewer intent"),
    # --- 38 ---
    ("Sarah on the platform team ran the first MCP-server bake-off; her writeup picked the typescript SDK over python for hot-path tools because the cold-start was four times faster.", "fact", "ai_coding", False,
     [("Sarah", "person"), ("MCP", "protocol"), ("typescript", "language"), ("python", "language")],
     [("typescript", "python", "PREFERS")],
     "who ran the MCP SDK bake-off and which language won for hot-path tools",
     "sarah platform mcp sdk typescript python cold start hot path"),
    # --- 39 ---
    ("Aider's voice mode lasted exactly one demo before the team killed it; the latency was fine but the misheard variable names produced impressively confident garbage edits.", "decision", "ai_coding", False,
     [("Aider", "tool"), ("voice mode", "pattern")],
     [],
     "why did the team retire Aider voice mode after one demo",
     "aider voice mode latency mis hear variable name garbage edit"),
    # --- 40 ---
    ("Built a small evals dataset of 80 internal bugs with hidden ground-truth diffs; we re-run it nightly against the current model lineup and Slack-post the regression deltas.", "milestone", "ai_coding", False,
     [("evals dataset", "method"), ("Slack", "platform"), ("ground-truth", "pattern")],
     [],
     "how does the team track model regressions on internal bug fixes nightly",
     "evals dataset internal bug ground truth diff nightly slack regression"),
    # --- 41 ---
    ("Claude Code's auto-commit hook writes a JSON block to .claude/log per run; the file is gitignored but ships to S3 nightly so we can replay any agent action.", "architecture", "ai_coding", False,
     [("Claude Code", "tool"), (".claude/log", "file"), ("S3", "service"), ("auto-commit", "pattern")],
     [],
     "where does Claude Code's per-run audit log live and how does it reach long-term storage",
     "claude code auto commit hook json log gitignore s3 nightly replay"),
    # --- 42 ---
    ("Disabled Copilot Chat in IDEs after a sensitive prompt got logged to GitHub's telemetry under the old enterprise plan; switched to Claude Code where the data residency is contractually pinned.", "decision", "ai_coding", False,
     [("Copilot Chat", "tool"), ("Claude Code", "tool"), ("telemetry", "pattern"), ("data residency", "concept")],
     [("Claude Code", "Copilot Chat", "REPLACES")],
     "which AI-chat tool got pulled over telemetry concerns and what replaced it",
     "copilot chat disable telemetry residency claude code enterprise"),
    # --- 43 ---
    ("Anthropic published a tool-use best-practices doc that we now reference in the MCP server style guide; the parallel-tool-call guidance in particular cleaned up our agent latency.", "reference", "ai_coding", False,
     [("Anthropic", "organization"), ("tool-use", "concept"), ("MCP", "protocol")],
     [],
     "which Anthropic guidance does the MCP server style guide cite and what did it improve",
     "anthropic tool use best practice mcp style guide parallel call"),
    # --- 44 ---
    ("Long-codebase context for the 1.2M-LOC Python service uses semantic chunking plus a BM25 first stage; pure embeddings missed the right module on cross-cutting changes.", "architecture", "ai_coding", False,
     [("BM25", "algorithm"), ("Python", "language"), ("semantic chunking", "method")],
     [("BM25", "semantic chunking", "IMPROVES_ON")],
     "which retrieval combo handles the giant Python service's context window best",
     "bm25 semantic chunking embedding cross cutting python context"),
    # --- 45 ---
    ("Aider got replaced by Claude Code for agentic flows once the bash-tool plus subagent dispatch landed; Aider stays for one-shot single-file edits where the simpler loop wins.", "decision", "ai_coding", False,
     [("Aider", "tool"), ("Claude Code", "tool"), ("bash-tool", "pattern"), ("subagent", "pattern")],
     [("Claude Code", "Aider", "REPLACES")],
     "where did Claude Code replace Aider and where does Aider still earn its place",
     "claude code replace aider agentic bash tool subagent one shot"),
    # --- 46 ---
    ("MCP-server allowlist enforces that only the read-only Postgres tool is exposed in customer-support sessions; the write tool ships in a separate engineering-only profile.", "preference", "ai_coding", False,
     [("MCP", "protocol"), ("Postgres", "database"), ("allowlist", "pattern")],
     [],
     "how do we keep the support agent from getting write access to Postgres via MCP",
     "mcp allowlist postgres read only support engineering profile split"),
    # --- 47 ---
    ("The Cursor team chat showed a 40% drop in stop-sign moments after we taught everyone to write a one-paragraph spec before invoking composer; vague prompts produced rework loops.", "fact", "ai_coding", False,
     [("Cursor", "tool"), ("composer", "pattern"), ("spec", "pattern")],
     [],
     "which prompt habit cut Cursor composer rework loops by a measurable margin",
     "cursor composer one paragraph spec rework loop drop habit"),
    # --- 48 ---
    ("Hallucination guardrail for library calls: the agent must produce a doc-link tool call resolving the symbol before generating any new import; missing docs means refuse-and-ask.", "architecture", "ai_coding", False,
     [("doc-link", "pattern"), ("agent", "pattern"), ("import", "pattern"), ("Hallucination", "pattern")],
     [],
     "which guardrail forces the agent to verify a library symbol exists before importing it",
     "hallucination guardrail doc link symbol resolve import refuse ask"),
    # --- 49. noise ---
    ("The thunderstorm last night knocked out the porch light bulb but somehow the wifi held all the way through.", "fact", "noise", True, [], [], None, None),
    # --- 50 ---
    ("Code-review integration with Claude Code now leaves a single top-level summary comment plus inline nits; the prior per-file essay format buried the actually-blocking issues under noise.", "preference", "ai_coding", False,
     [("Claude Code", "tool"), ("inline nits", "pattern"), ("summary comment", "pattern")],
     [],
     "how did the AI code-review comment shape change to surface blockers above noise",
     "claude code review summary comment inline nit blocker visibility"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
