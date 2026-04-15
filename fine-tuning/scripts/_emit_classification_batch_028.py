"""One-off emitter for classification top-up batch-028 — short_ambiguous mode, ai_coding dev-workflow slice.

Writes 100 rows to data/v2/classification/batch_028.tmp.jsonl with ids class-02701..02800.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_028.tmp.jsonl"
ID_OFFSET = 2700

# (text, domain, memory_type) — no pair_id
ROWS: list[tuple[str, str, str]] = [
    # --- fact (~14) ---
    ("Copilot uses VS Code's inline completion API.", "ai_coding", "fact"),
    ("Cursor forks VS Code under the hood.", "ai_coding", "fact"),
    ("Claude Code runs as a terminal CLI.", "ai_coding", "fact"),
    ("ESLint flat config replaces .eslintrc.", "ai_coding", "fact"),
    ("Prettier 3 dropped CommonJS plugin loading.", "ai_coding", "fact"),
    ("Husky 9 stores hooks under .husky/.", "ai_coding", "fact"),
    ("pre-commit hooks run before every commit.", "ai_coding", "fact"),
    ("Vitest runs tests in worker threads.", "ai_coding", "fact"),
    ("pytest collects files matching test_*.py.", "ai_coding", "fact"),
    ("ripgrep respects .gitignore by default.", "ai_coding", "fact"),
    ("zsh autosuggestions come from oh-my-zsh.", "ai_coding", "fact"),
    ("VS Code stores settings in settings.json.", "ai_coding", "fact"),
    ("GitHub Actions runners mount /home/runner.", "ai_coding", "fact"),
    ("tmux prefix defaults to Ctrl-b.", "ai_coding", "fact"),

    # --- decision (~14) ---
    ("Switching editor from Cursor to Zed.", "ai_coding", "decision"),
    ("Going with Claude Code for refactors.", "ai_coding", "decision"),
    ("Team adopting Biome instead of ESLint.", "ai_coding", "decision"),
    ("We'll enforce Prettier in CI this week.", "ai_coding", "decision"),
    ("Dropping Copilot, sticking with Claude.", "ai_coding", "decision"),
    ("Moving from bash to fish shell.", "ai_coding", "decision"),
    ("Using conventional commits from now on.", "ai_coding", "decision"),
    ("We'll require two reviewers per PR.", "ai_coding", "decision"),
    ("Switching test runner from Jest to Vitest.", "ai_coding", "decision"),
    ("Adopting lefthook over Husky team-wide.", "ai_coding", "decision"),
    ("Going with squash merges only.", "ai_coding", "decision"),
    ("We'll ban force-push on main branches.", "ai_coding", "decision"),
    ("Standardizing on .editorconfig across repos.", "ai_coding", "decision"),
    ("Cursor tab is now the default completion.", "ai_coding", "decision"),

    # --- preference (~14) ---
    ("I prefer vim bindings in VS Code.", "ai_coding", "preference"),
    ("I like Cursor over Copilot for diffs.", "ai_coding", "preference"),
    ("Prefer rebase over merge commits.", "ai_coding", "preference"),
    ("I like short, imperative commit subjects.", "ai_coding", "preference"),
    ("Prefer zsh with starship prompt.", "ai_coding", "preference"),
    ("I like Claude Sonnet for daily coding.", "ai_coding", "preference"),
    ("Prefer fd over find for quick searches.", "ai_coding", "preference"),
    ("I like inline review comments, not batch.", "ai_coding", "preference"),
    ("Prefer running tests on save.", "ai_coding", "preference"),
    ("I like small PRs under 200 lines.", "ai_coding", "preference"),
    ("Prefer type-first refactors before tests.", "ai_coding", "preference"),
    ("I like tmux over terminal tabs.", "ai_coding", "preference"),
    ("Prefer eza over ls for listing.", "ai_coding", "preference"),
    ("I like dark themes in every IDE.", "ai_coding", "preference"),

    # --- problem (~14) ---
    ("Copilot suggestions ignore project types.", "ai_coding", "problem"),
    ("Cursor agent loops on failing tests.", "ai_coding", "problem"),
    ("Claude Code hangs on large file reads.", "ai_coding", "problem"),
    ("ESLint crashes on monorepo symlinks.", "ai_coding", "problem"),
    ("Prettier reformats generated files.", "ai_coding", "problem"),
    ("pre-commit hook skips on --no-verify.", "ai_coding", "problem"),
    ("CI fails only on Windows runners.", "ai_coding", "problem"),
    ("Vitest watcher misses new test files.", "ai_coding", "problem"),
    ("VS Code eats CPU after long sessions.", "ai_coding", "problem"),
    ("zsh startup takes three seconds now.", "ai_coding", "problem"),
    ("git hooks break after fresh clone.", "ai_coding", "problem"),
    ("PR checks time out on large diffs.", "ai_coding", "problem"),
    ("Husky can't find node in CI.", "ai_coding", "problem"),
    ("Cursor tab conflicts with Emmet.", "ai_coding", "problem"),

    # --- reference (~14) ---
    ("See CONTRIBUTING.md for PR guidelines.", "ai_coding", "reference"),
    ("Editor config lives in .vscode/settings.json.", "ai_coding", "reference"),
    ("Shell aliases are in ~/.zshrc.", "ai_coding", "reference"),
    ("Lint rules documented in eslint.config.js.", "ai_coding", "reference"),
    ("CI workflow is .github/workflows/ci.yml.", "ai_coding", "reference"),
    ("See CLAUDE.md at the repo root.", "ai_coding", "reference"),
    ("Dotfiles repo is github.com/user/dotfiles.", "ai_coding", "reference"),
    ("Test runner config in vitest.config.ts.", "ai_coding", "reference"),
    ("Commit hook scripts under .husky/.", "ai_coding", "reference"),
    ("PR template in .github/pull_request_template.md.", "ai_coding", "reference"),
    ("Cursor rules stored in .cursorrules.", "ai_coding", "reference"),
    ("See tmux.conf for pane shortcuts.", "ai_coding", "reference"),
    ("Formatter config in .prettierrc.", "ai_coding", "reference"),
    ("See docs/dev-setup.md for onboarding.", "ai_coding", "reference"),

    # --- architecture (~14) ---
    ("Editor plugins talk to a local LSP.", "ai_coding", "architecture"),
    ("Copilot proxies requests through GitHub.", "ai_coding", "architecture"),
    ("Claude Code spawns tool subprocesses.", "ai_coding", "architecture"),
    ("Pre-commit runs hooks in isolated envs.", "ai_coding", "architecture"),
    ("CI pipeline fans out per-package jobs.", "ai_coding", "architecture"),
    ("PR bot posts checks via webhooks.", "ai_coding", "architecture"),
    ("Lint runs before type-check in CI.", "ai_coding", "architecture"),
    ("Test shards split across four runners.", "ai_coding", "architecture"),
    ("Cursor agent queues tool calls locally.", "ai_coding", "architecture"),
    ("Dotfiles sync via a chezmoi repo.", "ai_coding", "architecture"),
    ("Shell history syncs through atuin server.", "ai_coding", "architecture"),
    ("Editor settings layer user over workspace.", "ai_coding", "architecture"),
    ("Hooks chain: lint, format, then test.", "ai_coding", "architecture"),
    ("Review bot blocks merges on red checks.", "ai_coding", "architecture"),

    # --- milestone (~16 to reach 100) ---
    ("Migrated all repos to Biome today.", "ai_coding", "milestone"),
    ("Finished rolling out Claude Code team-wide.", "ai_coding", "milestone"),
    ("Cut CI time from twelve to four minutes.", "ai_coding", "milestone"),
    ("Every repo now has a CLAUDE.md.", "ai_coding", "milestone"),
    ("Hit zero lint errors across the monorepo.", "ai_coding", "milestone"),
    ("Shipped the shared ESLint preset v1.0.", "ai_coding", "milestone"),
    ("All commits now pass conventional check.", "ai_coding", "milestone"),
    ("Dropped Copilot seats last Friday.", "ai_coding", "milestone"),
    ("Moved every hook from Husky to lefthook.", "ai_coding", "milestone"),
    ("Finished dotfiles migration to chezmoi.", "ai_coding", "milestone"),
    ("PR median review time under four hours.", "ai_coding", "milestone"),
    ("Every PR now blocks on test coverage.", "ai_coding", "milestone"),
    ("Shipped the first Cursor rules file.", "ai_coding", "milestone"),
    ("Zed rollout complete across the team.", "ai_coding", "milestone"),
    ("Finished onboarding script for new devs.", "ai_coding", "milestone"),
    ("Closed out the editor-config unification.", "ai_coding", "milestone"),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (text, domain, mt) in enumerate(ROWS, start=1):
            row_id = f"class-{ID_OFFSET + i:05d}"
            f.write(
                json.dumps(
                    {"id": row_id, "domain": domain, "text": text, "memory_type": mt},
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
