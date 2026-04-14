"""One-off emitter for shared-base batch-041 — ai_coding domain (developer experience / IDEs / editors / shells / dotfiles slice).

Writes 50 rows to data/v2/shared/batch_041.tmp.jsonl with ids shared-02001..02050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_041.tmp.jsonl"
ID_OFFSET = 2000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Helix's built-in multi-cursor and tree-sitter textobjects meant we stopped reaching for three Neovim plugins; the tradeoff is the smaller plugin surface.", "decision", "ai_coding", False,
     [("Helix", "tool"), ("Neovim", "tool"), ("tree-sitter", "library")],
     [("Helix", "Neovim", "PREFERS")],
     "which modal editor replaced a stack of Neovim plugins and what was given up",
     "editor bundled feature tree-sitter plugin surface tradeoff"),
    # --- 2 ---
    ("Switched the Python LSP from pyright to basedpyright; the stricter defaults matched our codebase's invariants without a giant config override block.", "decision", "ai_coding", False,
     [("pyright", "tool"), ("basedpyright", "tool"), ("Python", "language"), ("LSP", "protocol")],
     [("basedpyright", "pyright", "REPLACES")],
     "which Python language server did we adopt for stricter default typechecking",
     "python language server strict default fork override reduce"),
    # --- 3 ---
    ("jedi-language-server is still the right pick on legacy Python 2.7 pockets; pyright refuses to touch that runtime at all.", "fact", "ai_coding", False,
     [("jedi-language-server", "tool"), ("pyright", "tool"), ("Python 2.7", "language")],
     [],
     "which language server handles the ancient Python runtime that pyright refuses",
     "legacy python LSP compat runtime fallback pick"),
    # --- 4 ---
    ("Migrated all Neovim configs from packer.nvim to lazy.nvim; startup dropped to 28 ms thanks to on-demand plugin loading.", "milestone", "ai_coding", False,
     [("Neovim", "tool"), ("packer.nvim", "library"), ("lazy.nvim", "library")],
     [("lazy.nvim", "packer.nvim", "REPLACES")],
     "which plugin manager swap drove Neovim startup below 30 milliseconds",
     "plugin manager migration lazy load startup speed nvim"),
    # --- 5 ---
    ("VSCode workspace settings should only hold project-scoped overrides; theme and keybindings belong in user settings or they churn across clones.", "preference", "ai_coding", False,
     [("VSCode", "tool")],
     [],
     "how should editor settings be split between workspace and user scopes",
     "editor settings scope workspace user theme keybinding separation"),
    # --- 6 ---
    ("JetBrains Gateway lets a thin client drive a dev container running on the build box; the 32 GB RAM laptop finally stopped swapping.", "fact", "ai_coding", False,
     [("JetBrains Gateway", "tool"), ("dev container", "pattern")],
     [],
     "which JetBrains tool let a laptop offload heavy dev containers to a build server",
     "remote IDE thin client dev container memory offload"),
    # --- 7 ---
    ("JetBrains Toolbox sync keeps SDK paths and keymap consistent across my three machines; manual settings export is officially retired.", "fact", "ai_coding", False,
     [("JetBrains Toolbox", "tool")],
     [],
     "which sync mechanism replaced the manual JetBrains settings export workflow",
     "IDE sync cross machine SDK path keymap settings export retire"),
    # --- 8 ---
    ("Zed's multiplayer editing got tested during the incident review; two engineers editing the runbook live beat screen-share plus a shared Google Doc.", "fact", "ai_coding", False,
     [("Zed", "tool"), ("Google Doc", "service")],
     [],
     "when did collaborative editor multiplayer prove itself during an incident",
     "collaborative editor multiplayer real time incident review runbook"),
    # --- 9 ---
    ("Team-wide fish adoption stalled because the POSIX gap broke copy-paste from StackOverflow; kept zsh as the default but allow fish for opt-in.", "problem", "ai_coding", False,
     [("fish", "tool"), ("zsh", "tool"), ("StackOverflow", "service")],
     [],
     "why did the fish shell rollout stop short of replacing zsh as default",
     "shell adoption POSIX gap copy paste compatibility opt in policy"),
    # --- 10. noise ---
    ("Ran out of coffee again; probably time to order the next bag.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Replaced oh-my-zsh with starship on 2026-02-05; prompt render time dropped from 140 ms to 8 ms on the same machine.", "milestone", "ai_coding", False,
     [("oh-my-zsh", "tool"), ("starship", "tool"), ("2026-02-05", "date")],
     [("starship", "oh-my-zsh", "REPLACES")],
     "when did the prompt framework swap cut per-command render latency",
     "shell prompt swap render latency drop date starship oh-my-zsh"),
    # --- 12 ---
    ("atuin shell history sync made the CTRL-R experience finally span machines; end-to-end encryption means the server only sees blobs.", "fact", "ai_coding", False,
     [("atuin", "tool")],
     [],
     "which tool unified CTRL-R command search across several machines",
     "shell history sync cross machine ctrl-r end to end encryption"),
    # --- 13 ---
    ("fzf plus CTRL-T gives us interactive file picking in every shell; CTRL-G extended for git-tracked files only, which is the bulk of real use.", "fact", "ai_coding", False,
     [("fzf", "tool"), ("CTRL-T", "command"), ("CTRL-G", "command")],
     [],
     "which fuzzy-finder bindings cover file picking and git-tracked file picking",
     "fuzzy finder binding file pick git filter shortcut"),
    # --- 14 ---
    ("Migrated the pair-programming setup from tmux to Zellij; the discoverable keybinding bar removed the 'what was the prefix again' question for new hires.", "decision", "ai_coding", False,
     [("tmux", "tool"), ("Zellij", "tool")],
     [("Zellij", "tmux", "PREFERS")],
     "which terminal multiplexer's UI cured the prefix-key memory problem for onboarding",
     "multiplexer swap keybinding discoverability onboarding new hire"),
    # --- 15 ---
    ("direnv with per-repo .envrc kept secrets out of shell rc files; the use_flake helper wires Nix dev shells in cleanly without manual sourcing.", "architecture", "ai_coding", False,
     [("direnv", "tool"), (".envrc", "file"), ("Nix", "tool")],
     [],
     "how do per-repo environment variables and Nix dev shells load without shell rc edits",
     "directory environment per repo dotenv nix dev shell auto load"),
    # --- 16 ---
    ("Consolidated asdf, rbenv and nvm onto mise; single .tool-versions file and noticeably faster cold-shell startup.", "decision", "ai_coding", False,
     [("asdf", "tool"), ("rbenv", "tool"), ("nvm", "tool"), ("mise", "tool")],
     [("mise", "asdf", "REPLACES")],
     "which unified version manager replaced the separate runtime version tools",
     "runtime version manager unify tool versions cold start speed"),
    # --- 17 ---
    ("proto handles Rust toolchain swaps better than mise on Apple Silicon; kept proto for Rust-heavy repos and mise everywhere else.", "preference", "ai_coding", False,
     [("proto", "tool"), ("mise", "tool"), ("Rust", "language"), ("Apple Silicon", "platform")],
     [],
     "which tool version manager handles Rust toolchain swaps best on Apple Silicon",
     "version manager rust toolchain apple silicon split preference"),
    # --- 18 ---
    ("Repo-local pre-commit hooks live in .pre-commit-config.yaml and run the same ruff and mypy passes as CI; dev-laptop fails now match CI fails.", "architecture", "ai_coding", False,
     [(".pre-commit-config.yaml", "file"), ("ruff", "tool"), ("mypy", "tool"), ("CI", "infrastructure")],
     [],
     "how do we keep local pre-commit hooks aligned with pipeline lint stages",
     "pre commit hook config ruff mypy CI parity local failure"),
    # --- 19 ---
    ("chezmoi beat YADM and bare-git dotfile strategies for us; templated files with host-specific sections avoid a fork per machine.", "decision", "ai_coding", False,
     [("chezmoi", "tool"), ("YADM", "tool"), ("bare-git", "pattern")],
     [("chezmoi", "YADM", "PREFERS")],
     "which dotfile manager won for multi-host templating without forking",
     "dotfile manager template host specific section multi machine"),
    # --- 20 ---
    ("Brewfile snapshots gave us a reproducible macOS base; brew bundle dump after a clean install, then diff against HEAD to catch drift.", "fact", "ai_coding", False,
     [("Brewfile", "file"), ("brew bundle", "command"), ("macOS", "platform")],
     [],
     "which file enabled reproducible macOS package installs and drift detection",
     "brew bundle snapshot dump reproducible drift detect macOS"),
    # --- 21 ---
    ("WezTerm's Lua config lets us define per-domain launch profiles; SSH hosts get their own color scheme to prevent prod typos.", "fact", "ai_coding", False,
     [("WezTerm", "tool"), ("Lua", "language"), ("SSH", "protocol")],
     [],
     "which terminal emulator uses Lua to color production sessions differently",
     "terminal emulator lua config domain color prod safety"),
    # --- 22 ---
    ("Alacritty stayed on our low-spec boxes; zero ligatures and minimal features mean 60 fps even on the Pi 4 cluster dashboard.", "fact", "ai_coding", False,
     [("Alacritty", "tool"), ("Pi 4", "platform")],
     [],
     "which minimal GPU terminal kept running smoothly on the Raspberry Pi dashboard",
     "minimal terminal GPU accelerated low spec hardware smooth"),
    # --- 23 ---
    ("Ghostty adoption happened fast on the macOS side; native framework integration means zero tearing on external 4K monitors.", "fact", "ai_coding", False,
     [("Ghostty", "tool"), ("macOS", "platform")],
     [],
     "which new terminal landed cleanly on macOS with 4K display support",
     "ghostty terminal macos native 4k display adoption"),
    # --- 24 ---
    ("Warp's AI side panel saves a copy-paste step for quick shell lookups but its block-based history breaks tmux copy-mode selection; keep it off the remote hosts.", "problem", "ai_coding", False,
     [("Warp", "tool"), ("tmux", "tool")],
     [],
     "where does the AI-enabled terminal's block model conflict with existing tmux flows",
     "warp terminal ai panel block history tmux copy mode conflict"),
    # --- 25 ---
    ("SSH ProxyJump replaced the nested ssh -t pattern for bastion hops; one Host entry with ProxyJump bastion documents the topology.", "decision", "ai_coding", False,
     [("ProxyJump", "pattern"), ("SSH", "protocol"), ("ssh -t", "command")],
     [("ProxyJump", "ssh -t", "REPLACES")],
     "which SSH config pattern cleanly supersedes nested ssh -t through a bastion",
     "ssh proxy jump bastion host nested t replace clean"),
    # --- 26 ---
    ("ssh_config Match blocks by exec let us swap the IdentityFile when inside the VPN; outside the VPN the deploy key is simply unreachable.", "architecture", "ai_coding", False,
     [("ssh_config", "file"), ("Match", "pattern"), ("IdentityFile", "config"), ("VPN", "infrastructure")],
     [],
     "how does the SSH client pick a different identity based on VPN presence",
     "ssh config match exec identity conditional vpn state"),
    # --- 27 ---
    ("The gh extension model let us install gh-dash and gh-copilot without polluting $PATH; uninstall is gh extension remove, no cleanup.", "fact", "ai_coding", False,
     [("gh", "tool"), ("gh-dash", "library"), ("gh-copilot", "library")],
     [],
     "which GitHub CLI mechanism keeps extensions isolated from PATH pollution",
     "github cli extension isolation install remove no path"),
    # --- 28 ---
    ("lazygit plus gh-dash became our default git UI; the keystroke feedback loop beats the IntelliJ git panel when batch-rebasing stacked branches.", "preference", "ai_coding", False,
     [("lazygit", "tool"), ("gh-dash", "library"), ("IntelliJ", "tool")],
     [("lazygit", "IntelliJ", "PREFERS")],
     "which terminal git UI beat the IDE git panel for stacked branch rebases",
     "git tui rebase stacked branch ide panel comparison preference"),
    # --- 29 ---
    ("delta turned the git pager into a syntax-highlighted side-by-side view; two-line config under .gitconfig and core.pager = delta lights up.", "fact", "ai_coding", False,
     [("delta", "tool"), (".gitconfig", "file"), ("core.pager", "config")],
     [],
     "which pager turned git diff into a highlighted side-by-side layout with minimal config",
     "git diff pager side by side syntax highlight config minimal"),
    # --- 30 ---
    ("Reached for gron when the jq expression got deep; flattened JSON into greppable paths turns a one-liner battle into a grep pipe.", "fact", "ai_coding", False,
     [("gron", "tool"), ("jq", "tool"), ("JSON", "technology")],
     [],
     "which tool flattens JSON when a jq query starts fighting you",
     "json flatten grep path gron escape hatch jq complex"),
    # --- 31 ---
    ("yq reads YAML with jq-style expressions; moved kustomize value edits away from sed hacks once the schema stabilised.", "fact", "ai_coding", False,
     [("yq", "tool"), ("jq", "tool"), ("kustomize", "tool"), ("sed", "tool")],
     [("yq", "sed", "REPLACES")],
     "which tool replaced sed for structured YAML edits in kustomize overlays",
     "yaml edit yq kustomize sed replace structured tool"),
    # --- 32 ---
    ("Centralising ripgrep defaults into .ripgreprc with --smart-case and --hidden stopped everyone's home-grown wrapper shell functions.", "architecture", "ai_coding", False,
     [("ripgrep", "tool"), (".ripgreprc", "file")],
     [],
     "which config file removed the home-grown rg wrapper functions across the team",
     "ripgrep config file smart case hidden defaults wrapper retire"),
    # --- 33 ---
    ("fd's default ignore of .gitignore plus hidden files matched what find -not -path was doing; the new alias is simply fd for everyone.", "fact", "ai_coding", False,
     [("fd", "tool"), ("find", "tool"), (".gitignore", "file")],
     [("fd", "find", "REPLACES")],
     "which faster find alternative respects gitignore defaults out of the box",
     "find alternative gitignore default hidden fd alias"),
    # --- 34 ---
    ("eza replaced lsd on half the team machines; git-status columns per row made the extra adoption friction worth it.", "decision", "ai_coding", False,
     [("eza", "tool"), ("lsd", "tool")],
     [("eza", "lsd", "PREFERS")],
     "which ls alternative won for its per-row git status column",
     "ls replacement git status column eza lsd choice"),
    # --- 35 ---
    ("ssh_config Include directives split the 400-line file into per-account fragments; the deploy-key fragment is symlinked from the vault, read-only.", "architecture", "ai_coding", False,
     [("ssh_config", "file"), ("Include", "pattern")],
     [],
     "how did the giant ssh_config file get broken into per-account pieces",
     "ssh config include fragment split account vault symlink"),
    # --- 36 ---
    ("mise tasks replaced the Makefile on the sample repo; .mise.toml [tasks.check] runs lint and test without the leading-tab fragility.", "decision", "ai_coding", False,
     [("mise", "tool"), ("Makefile", "file"), (".mise.toml", "file")],
     [("mise", "Makefile", "REPLACES")],
     "which tool replaced Makefile for task running without tab-indent fragility",
     "task runner make replacement mise toml task lint test"),
    # --- 37 ---
    ("Zed's language-server process reuse broke with our Python monorepo; each worktree spawned its own basedpyright and ate 4 GB before lunch.", "problem", "ai_coding", False,
     [("Zed", "tool"), ("Python", "language"), ("basedpyright", "tool")],
     [],
     "where did the editor's LSP reuse break down inside a Python monorepo",
     "editor language server reuse monorepo worktree spawn memory blow"),
    # --- 38 ---
    ("Neovim's built-in LSP client finally caught up with coc.nvim on completion ergonomics; kept coc only on the legacy JS stack because of its ecosystem.", "decision", "ai_coding", False,
     [("Neovim", "tool"), ("coc.nvim", "library"), ("LSP", "protocol")],
     [("Neovim", "coc.nvim", "REPLACES")],
     "which Neovim completion approach won over coc.nvim and where did coc stay",
     "neovim builtin lsp coc ecosystem legacy split"),
    # --- 39 ---
    ("IdeaVim keymaps cover 90% of Vim muscle memory inside IntelliJ; the remaining 10% are visual-block edge cases that an ~/.ideavimrc Plug handles.", "fact", "ai_coding", False,
     [("IdeaVim", "library"), ("IntelliJ", "tool"), ("~/.ideavimrc", "file")],
     [],
     "which IntelliJ plugin approximates Vim keybindings plus how to patch the gaps",
     "ideavim IntelliJ vim keymap plug file visual block edge"),
    # --- 40 ---
    ("Sublime Text 4 still boots under 300 ms on the ancient build server; kept it as the post-mortem editor for 2 GB log tailing.", "fact", "ai_coding", False,
     [("Sublime Text 4", "tool")],
     [],
     "which editor still wins for giant log files on an old build server",
     "sublime text fast boot large log tail specific use"),
    # --- 41 ---
    ("bat pages source files with syntax highlighting and git blame gutters; --style=plain swap keeps it piping-friendly into fzf preview.", "fact", "ai_coding", False,
     [("bat", "tool"), ("fzf", "tool")],
     [],
     "which cat replacement powers the fzf file preview with highlighted source",
     "bat syntax highlight cat alternative fzf preview pipe"),
    # --- 42 ---
    ("zoxide replaced the z script on everyone's dotfiles; the Rust rewrite respects XDG dirs and jumps by frecency without the bash hooks overhead.", "decision", "ai_coding", False,
     [("zoxide", "tool"), ("z", "tool"), ("XDG", "pattern")],
     [("zoxide", "z", "REPLACES")],
     "which directory jumper replaced the old z shell function on everyone's setup",
     "zoxide z replace directory jump frecency xdg rust"),
    # --- 43 ---
    ("nushell adoption is still experimental; we love the structured pipelines but too many muscle-memory scripts assume POSIX, so keep it opt-in.", "fact", "ai_coding", False,
     [("nushell", "tool")],
     [],
     "which new shell offers structured pipelines but is still held back from default",
     "nushell structured pipeline POSIX muscle memory experimental"),
    # --- 44 ---
    ("Co-pilot CLI suggestions via gh copilot suggest save a man-page round-trip for obscure tar flags; the shell-native aware mode makes the paste safe.", "fact", "ai_coding", False,
     [("gh copilot", "tool"), ("tar", "command")],
     [],
     "which CLI AI helper explains obscure tar flags safely inside the shell",
     "gh copilot suggest tar flag man page alternative safe paste"),
    # --- 45 ---
    ("Warp plus tmux led to garbled 256-color output on nested ssh; switched to Ghostty or kitty on any box that needs tmux inside.", "problem", "ai_coding", False,
     [("Warp", "tool"), ("tmux", "tool"), ("Ghostty", "tool"), ("kitty", "tool")],
     [],
     "which terminals handle tmux-inside-ssh color output where Warp fell over",
     "terminal tmux ssh color 256 corruption alternative switch"),
    # --- 46 ---
    ("Neovim's tree-sitter textobjects unlock fast refactors: vaf to select a function, daf to delete it, without needing a Python-aware plugin.", "fact", "ai_coding", False,
     [("Neovim", "tool"), ("tree-sitter", "library"), ("Python", "language")],
     [],
     "which Neovim feature replaced language-specific textobject plugins for function edits",
     "tree sitter textobject function select delete language agnostic"),
    # --- 47 ---
    ("Set Neovim's spell-check to medical-dictionary + project glossary via spellfile; CI-time typo catches in Markdown dropped to near zero.", "milestone", "ai_coding", False,
     [("Neovim", "tool"), ("spellfile", "file"), ("CI", "infrastructure"), ("Markdown", "language")],
     [],
     "which editor config stopped typos from slipping through to the docs pipeline",
     "spell check medical dictionary project glossary markdown ci typo"),
    # --- 48 ---
    ("Set up a thinkpad-X1 specific ssh_config Host block that forces UseKeychain yes on macOS; other hosts keep the keychain-free setup for CI rotation.", "fact", "ai_coding", False,
     [("ssh_config", "file"), ("UseKeychain", "config"), ("macOS", "platform"), ("CI", "infrastructure")],
     [],
     "which ssh_config host-specific setting enables macOS keychain only on the laptop",
     "ssh config host block keychain macos specific ci rotation"),
    # --- 49 ---
    ("git-absorb changed our stacked-diff review loop; one command spreads WIP edits onto the right ancestor commits instead of interactive rebase ceremony.", "fact", "ai_coding", False,
     [("git-absorb", "tool")],
     [],
     "which git tool replaces the interactive-rebase dance for fixing up stacked commits",
     "git absorb stacked diff fixup auto ancestor commit rebase"),
    # --- 50 ---
    ("Kept Emacs on exactly one workstation for org-mode planning; it never became the team IDE but the author's weekly review notes flow best there.", "preference", "ai_coding", False,
     [("Emacs", "tool"), ("org-mode", "library")],
     [],
     "which editor stayed around strictly for org-mode planning rather than as the team IDE",
     "emacs org mode planning weekly review single user niche"),
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
