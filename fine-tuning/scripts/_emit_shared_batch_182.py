"""One-off emitter for shared-base batch-182 — technical domain (Language Server Protocol 3.17+, DAP, editor tooling: tower-lsp, pygls, rust-analyzer, pyright, gopls, Neovim LSP, Zed, Helix).

Writes 50 rows to data/v2/shared/batch_182.tmp.jsonl with ids shared-09051..09100.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_182.tmp.jsonl"
ID_OFFSET = 9050

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Migrated the Rust server crate from lsp-server to tower-lsp so async handlers drop into tokio directly; the synchronous dispatch loop was blocking on completion requests during heavy workspace scans.", "decision", "technical", False,
     [("tower-lsp", "library"), ("lsp-server", "library"), ("tokio", "library"), ("completion", "concept")],
     [("tower-lsp", "lsp-server", "REPLACES"), ("tower-lsp", "tokio", "USES")],
     "which Rust LSP crate replaced lsp-server to unblock completion under heavy workspace scans",
     "tower lsp rust tokio async completion workspace scan replace"),
    # --- 2 ---
    ("Picked pygls over a hand-rolled JSON-RPC loop for the internal DSL server; pygls already wires textDocument/didChange and workspace/didChangeConfiguration with the 3.17 shape.", "decision", "technical", False,
     [("pygls", "library"), ("JSON-RPC", "protocol"), ("textDocument/didChange", "api"), ("workspace/didChangeConfiguration", "api")],
     [("pygls", "JSON-RPC", "USES")],
     "which Python LSP framework won over a hand-rolled JSON-RPC loop for the internal DSL server",
     "pygls python json rpc did change configuration dsl server"),
    # --- 3 ---
    ("rust-analyzer shipped as the primary Rust language server in the workspace; RLS got dropped because procedural macros and trait resolution needed the query-based architecture.", "milestone", "technical", False,
     [("rust-analyzer", "service"), ("RLS", "service"), ("procedural macros", "concept"), ("trait resolution", "concept")],
     [("rust-analyzer", "RLS", "REPLACES")],
     "which Rust language server replaced RLS for procedural macro and trait resolution support",
     "rust analyzer rls macro trait query architecture primary server"),
    # --- 4 ---
    ("pyright is the type checker behind the Python LSP; pylsp still handles linting and formatting via its plugin bus, so both servers attach to the same buffer through distinct client configs.", "architecture", "technical", False,
     [("pyright", "service"), ("pylsp", "service"), ("Python", "language"), ("plugin bus", "pattern")],
     [("pyright", "pylsp", "COMMUNICATES_WITH")],
     "how does the editor coordinate pyright for types and pylsp for linting on the same Python buffer",
     "pyright pylsp python type check lint plugin bus attach buffer"),
    # --- 5 ---
    ("Swapped the flake8+black+isort stack for ruff-lsp in the Python monorepo; a single binary replaced three subprocess round-trips per save and latency on textDocument/formatting halved.", "decision", "technical", False,
     [("ruff-lsp", "service"), ("flake8", "tool"), ("black", "tool"), ("isort", "tool"), ("textDocument/formatting", "api")],
     [("ruff-lsp", "flake8", "REPLACES"), ("ruff-lsp", "black", "REPLACES")],
     "which linter-formatter combo got replaced by ruff-lsp and what latency win did it unlock",
     "ruff lsp flake8 black isort python format latency subprocess save"),
    # --- 6 ---
    ("LSP 3.17 semantic tokens landed in the custom server using a delta encoding over prior frames; the full-range path survives only on the first didOpen notification per document.", "architecture", "technical", False,
     [("LSP 3.17", "protocol"), ("semantic tokens", "concept"), ("didOpen", "api"), ("delta encoding", "method")],
     [("semantic tokens", "delta encoding", "USES")],
     "how does the server stream LSP 3.17 semantic tokens without re-sending full ranges on every edit",
     "lsp 3 17 semantic token delta encode did open full range first"),
    # --- 7 ---
    ("Inlay hints for parameter names routed through textDocument/inlayHint with a resolve callback; the resolve path defers the hover tooltip text until the user actually moves the cursor over the hint.", "architecture", "technical", False,
     [("Inlay hints", "concept"), ("textDocument/inlayHint", "api"), ("resolve callback", "pattern"), ("hover", "concept")],
     [("Inlay hints", "textDocument/inlayHint", "USES")],
     "how does the server defer inlay hint tooltip text using the resolve callback in LSP 3.17",
     "inlay hint text document resolve callback hover tooltip defer"),
    # --- 8 ---
    ("Call hierarchy requests hit the symbol index through prepareCallHierarchy then incomingCalls; the old reference-walk fell apart on generics where monomorphised callers weren't reachable by name.", "problem", "technical", False,
     [("Call hierarchy", "concept"), ("prepareCallHierarchy", "api"), ("incomingCalls", "api"), ("generics", "concept")],
     [("prepareCallHierarchy", "incomingCalls", "COMMUNICATES_WITH")],
     "which call hierarchy flow fixed the monomorphised-caller miss on generic functions",
     "call hierarchy prepare incoming reference walk generics monomorphise"),
    # --- 9 ---
    ("Workspace symbol queries now fan out to a tantivy index; the design follows the LSP 3.17 Specification chapter on workspace/symbol and cites the Full-Text Search paper that informed tantivy's scoring model.", "reference", "technical", False,
     [("Workspace symbol", "concept"), ("tantivy", "library"), ("LSP 3.17 Specification", "publication"), ("Full-Text Search", "publication")],
     [("tantivy", "Full-Text Search", "BUILDS_ON"), ("Workspace symbol", "LSP 3.17 Specification", "PUBLISHED_IN")],
     "which two publications guide the tantivy-backed workspace symbol design referenced in our notes",
     "workspace symbol tantivy lsp 3 17 specification full text search cite"),
    # --- 10. noise ---
    ("The office kitchen swapped to a new bean supplier and the pour-over bar now has a laminated brew-ratio card taped next to the kettle.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Neovim built-in LSP plus nvim-lspconfig drives the team's default editor setup; coc.nvim got retired after the 0.8 release because built-in handlers covered every capability we actually used.", "decision", "technical", False,
     [("Neovim", "tool"), ("nvim-lspconfig", "library"), ("coc.nvim", "tool")],
     [("nvim-lspconfig", "coc.nvim", "REPLACES")],
     "which Neovim LSP stack replaced coc.nvim as the team default after the 0.8 release",
     "neovim lsp config coc nvim 0 8 built in handler default team"),
    # --- 12 ---
    ("Emacs users split between lsp-mode and eglot; eglot's lean handler surface won for the Go team since gopls only needed a small subset of client capabilities and startup latency mattered.", "preference", "technical", False,
     [("lsp-mode", "tool"), ("eglot", "tool"), ("Emacs", "tool"), ("gopls", "service")],
     [("eglot", "lsp-mode", "PREFERS")],
     "why did the Go team in Emacs pick eglot over lsp-mode for gopls integration",
     "emacs eglot lsp mode gopls go startup latency handler surface"),
    # --- 13 ---
    ("Sublime LSP is the team's preferred bridge for Sublime Text users; the native colour scheme hook for semantic tokens won out over a standalone plugin that would have duplicated JSON-RPC plumbing.", "preference", "technical", False,
     [("Sublime LSP", "tool"), ("Sublime Text", "tool"), ("JSON-RPC", "protocol"), ("semantic tokens", "concept")],
     [("Sublime LSP", "Sublime Text", "PREFERS")],
     "why do Sublime Text users on the team prefer Sublime LSP over a standalone plugin",
     "sublime lsp text prefer colour scheme semantic token json rpc bridge"),
    # --- 14 ---
    ("Zed's language server host runs out-of-process per language; the editor talks to rust-analyzer and gopls over stdio pipes and multiplexes completion resolve through its own actor runtime.", "architecture", "technical", False,
     [("Zed", "tool"), ("rust-analyzer", "service"), ("gopls", "service"), ("stdio", "protocol"), ("actor runtime", "pattern")],
     [("Zed", "rust-analyzer", "COMMUNICATES_WITH"), ("Zed", "gopls", "COMMUNICATES_WITH")],
     "how does Zed multiplex completion resolve across rust-analyzer and gopls over stdio",
     "zed language server rust analyzer gopls stdio actor completion"),
    # --- 15 ---
    ("Helix ships LSP support directly in the editor binary without a plugin layer; language servers are declared in languages.toml and the picker uses workspace/symbol for its fuzzy jump.", "fact", "technical", False,
     [("Helix", "tool"), ("languages.toml", "config"), ("workspace/symbol", "api")],
     [("Helix", "workspace/symbol", "USES")],
     "how does Helix declare LSP servers and power its fuzzy jump picker without a plugin layer",
     "helix languages toml workspace symbol picker fuzzy jump binary"),
    # --- 16 ---
    ("Cursor forked vscode-languageserver-node to add AI-inline suggestions as a sibling capability; the fork keeps protocol parity with upstream so third-party servers still attach unchanged.", "architecture", "technical", False,
     [("Cursor", "tool"), ("vscode-languageserver-node", "library")],
     [("Cursor", "vscode-languageserver-node", "EXTENDS")],
     "how does Cursor add AI-inline suggestions while keeping third-party LSP servers unchanged",
     "cursor vscode language server node fork inline suggestion parity"),
    # --- 17 ---
    ("JetBrains IntelliJ Platform gained an LSP API in 2023.2; the team wrapped rust-analyzer through it so the Rust plugin and CLion share one backend instead of maintaining two parsers.", "milestone", "technical", False,
     [("IntelliJ Platform", "platform"), ("rust-analyzer", "service"), ("CLion", "tool")],
     [("IntelliJ Platform", "rust-analyzer", "USES")],
     "how did the IntelliJ Platform LSP API unify Rust support across the Rust plugin and CLion",
     "intellij platform lsp api rust analyzer clion plugin backend share"),
    # --- 18 ---
    ("clangd is the C++ language server across the engine monorepo; cquery got dropped because its index was a giant sqlite blob and incremental updates failed on cross-compilation unit edits.", "decision", "technical", False,
     [("clangd", "service"), ("cquery", "service"), ("C++", "language"), ("sqlite", "database")],
     [("clangd", "cquery", "REPLACES")],
     "which C++ language server replaced cquery and what failure mode in the old index forced the switch",
     "clangd cquery cpp sqlite index cross compilation unit increment"),
    # --- 19 ---
    ("lua-language-server drives the Neovim config completions; the workspace library includes runtime/lua so vim.api stubs resolve without copying a types file into every plugin repo.", "fact", "technical", False,
     [("lua-language-server", "service"), ("Neovim", "tool"), ("vim.api", "api")],
     [("lua-language-server", "Neovim", "APPLIES_TO")],
     "which workspace-library trick makes vim api stubs available in Neovim config completions",
     "lua language server neovim vim api stub workspace library runtime"),
    # --- 20 ---
    ("The tsserver wrapper design for typescript-language-server follows the TypeScript Wire Protocol document and the LSP Specification 3.17 rename chapter; both links live in the integration guide for new contributors.", "reference", "technical", False,
     [("tsserver", "service"), ("typescript-language-server", "service"), ("TypeScript Wire Protocol", "publication"), ("LSP Specification 3.17", "publication")],
     [("typescript-language-server", "TypeScript Wire Protocol", "PUBLISHED_IN")],
     "which two specs does the typescript-language-server wrapper cite for rename and protocol translation",
     "tsserver typescript wire protocol lsp specification 3 17 rename cite"),
    # --- 21 ---
    ("Debug Adapter Protocol replaced the bespoke debugger bridge in the Zed port; DAP's stopped-event model maps cleanly onto our thread-state machine and CodeLLDB ships ready to attach.", "decision", "technical", False,
     [("Debug Adapter Protocol", "protocol"), ("Zed", "tool"), ("CodeLLDB", "tool"), ("bespoke debugger bridge", "pattern")],
     [("Debug Adapter Protocol", "bespoke debugger bridge", "REPLACES"), ("CodeLLDB", "Debug Adapter Protocol", "IMPLEMENTS")],
     "which debug protocol replaced the bespoke bridge in the Zed port and which adapter shipped ready",
     "dap debug adapter protocol zed codelldb bespoke bridge stopped"),
    # --- 22 ---
    ("Chose to group code actions by quickfix, refactor, and source with a codeActionKind prefix filter for the Rust server; the alternative of sending every kind to every client lost on round-trip bytes per save.", "decision", "technical", False,
     [("code actions", "concept"), ("codeActionKind", "api"), ("quickfix", "concept"), ("refactor", "concept")],
     [("code actions", "codeActionKind", "USES")],
     "which grouping choice for code actions won out over sending every kind to every client",
     "code action quickfix refactor source kind filter choose group bytes"),
    # --- 23 ---
    ("File watchers for the monorepo moved from per-server watchman calls to workspace/didChangeWatchedFiles sent by the client once; duplicate rebuilds that ran four times per save stopped.", "problem", "technical", False,
     [("File watchers", "concept"), ("watchman", "tool"), ("workspace/didChangeWatchedFiles", "api")],
     [("workspace/didChangeWatchedFiles", "watchman", "REPLACES")],
     "which file-watcher flow replaced per-server watchman and ended the duplicate-rebuild-per-save bug",
     "watchman did change watched files monorepo rebuild save duplicate"),
    # --- 24 ---
    ("The two-step rename flow with textDocument/prepareRename followed by textDocument/rename comes directly from the LSP 3.17 Specification; our guide's rename section links the spec's prepareRename prose for validation semantics.", "reference", "technical", False,
     [("textDocument/prepareRename", "api"), ("textDocument/rename", "api"), ("LSP 3.17 Specification", "publication"), ("rename", "concept")],
     [("textDocument/prepareRename", "LSP 3.17 Specification", "PUBLISHED_IN")],
     "which spec does the rename guide cite for the prepareRename validation semantics",
     "prepare rename text document lsp 3 17 specification cite guide section"),
    # --- 25 ---
    ("Incremental textDocument/didChange with range-based edits replaced full-buffer resync on every keystroke; server memory usage dropped by a third on long files during refactor sessions.", "problem", "technical", False,
     [("textDocument/didChange", "api"), ("range-based edits", "concept"), ("full-buffer resync", "pattern")],
     [("range-based edits", "full-buffer resync", "REPLACES")],
     "which didChange mode replaced full-buffer resync and by how much did it cut server memory",
     "did change range incremental full buffer resync memory long refactor"),
    # --- 26 ---
    ("Hover content negotiation between Markdown and plain text through MarkupContent is covered in the LSP 3.17 MarkupContent chapter; we also cite CommonMark Spec for the Markdown dialect clients should render.", "reference", "technical", False,
     [("Hover", "concept"), ("MarkupContent", "api"), ("LSP 3.17 MarkupContent chapter", "publication"), ("CommonMark Spec", "publication")],
     [("MarkupContent", "LSP 3.17 MarkupContent chapter", "PUBLISHED_IN"), ("Hover", "CommonMark Spec", "BUILDS_ON")],
     "which two publications does the hover content guide cite for MarkupContent and Markdown",
     "hover markup content lsp 3 17 commonmark spec cite markdown dialect"),
    # --- 27 ---
    ("Diagnostics shifted from textDocument/publishDiagnostics push to the pull-based textDocument/diagnostic in LSP 3.17; the pull model lets slow checkers skip stale documents without racing the client.", "decision", "technical", False,
     [("textDocument/publishDiagnostics", "api"), ("textDocument/diagnostic", "api"), ("LSP 3.17", "protocol")],
     [("textDocument/diagnostic", "textDocument/publishDiagnostics", "REPLACES")],
     "which diagnostics model replaced the push flavour in 3.17 and what race did it eliminate",
     "pull diagnostic push publish 3 17 stale skip race slow checker"),
    # --- 28 ---
    ("The Go monorepo cut a gopls-v0.14 pin milestone after the team burned two days on a workspace/symbol cache regression in 0.15; the pinned release is now baked into the bootstrap image for new hires.", "milestone", "technical", False,
     [("gopls", "service"), ("workspace/symbol", "api")],
     [],
     "which gopls pin milestone did the Go monorepo cut after the workspace/symbol regression",
     "gopls v0 14 pin milestone workspace symbol cache regression bootstrap"),
    # --- 29 ---
    ("WASM plus TreeSitter shipped as the editor's in-browser syntax layer in release 2.4; parsers compile to wasm32 and load lazily, which held the initial bundle under two megabytes at launch.", "milestone", "technical", False,
     [("WASM", "technology"), ("TreeSitter", "library"), ("wasm32", "platform")],
     [("TreeSitter", "WASM", "USES")],
     "which release shipped the WASM-plus-TreeSitter syntax layer and what bundle size did it hit",
     "wasm tree sitter browser parser wasm32 release 2 4 bundle megabyte"),
    # --- 30 ---
    ("rust-analyzer moves cargo check invocations onto a separate tokio task pool so save-watchers don't starve under IO-heavy didSave bursts; the parent server keeps the completion pool on its own runtime.", "fact", "technical", False,
     [("rust-analyzer", "service"), ("cargo", "tool"), ("tokio", "library"), ("didSave", "api")],
     [("rust-analyzer", "tokio", "USES")],
     "how does rust-analyzer keep save-watchers fed while cargo check runs under didSave bursts",
     "rust analyzer cargo tokio pool save watcher did save runtime completion"),
    # --- 31 ---
    ("pygls exposes a decorator-based handler registration; the team mirrored the same shape in a tower-lsp adapter so migrating a Python prototype server to Rust kept handler names verbatim.", "preference", "technical", False,
     [("pygls", "library"), ("tower-lsp", "library"), ("decorator", "pattern")],
     [("tower-lsp", "pygls", "RELATED_TO")],
     "which handler registration pattern did the team share between pygls and tower-lsp for ports",
     "pygls tower lsp decorator handler register prototype rust port shape"),
    # --- 32 ---
    ("Picked the SemanticTokensLegend-at-startup approach over a per-request legend for the custom server; declaring token types once lets clients cache the legend and skip it on later semantic tokens requests.", "decision", "technical", False,
     [("semantic tokens", "concept"), ("SemanticTokensLegend", "api"), ("token types", "concept")],
     [("SemanticTokensLegend", "semantic tokens", "CONFIGURES")],
     "which semantic tokens legend strategy did the custom server pick over a per-request legend",
     "semantic tokens legend modifier startup choose pick per request cache"),
    # --- 33 ---
    ("Inlay hints and diagnostics share a deferred-work queue so a long type-inference run doesn't starve the hint path; the queue prioritises the visible-range request from the client.", "architecture", "technical", False,
     [("Inlay hints", "concept"), ("diagnostics", "concept"), ("deferred-work queue", "pattern")],
     [],
     "how does the server keep inlay hints responsive when long type inference runs block diagnostics",
     "inlay hint diagnostic deferred queue visible range starve priority"),
    # --- 34 ---
    ("Workspace symbol results de-duplicate across clangd and pyright in polyglot projects by tagging each entry with the server id before merging; the picker surfaces the server on hover.", "architecture", "technical", False,
     [("Workspace symbol", "concept"), ("clangd", "service"), ("pyright", "service"), ("polyglot", "concept")],
     [],
     "how does the editor merge workspace symbol results from clangd and pyright without duplicates",
     "workspace symbol clangd pyright polyglot dedup server tag merge"),
    # --- 35 ---
    ("TypeScript monorepo maintainers prefer tsserver's workspace/willRenameFiles capability over post-hoc import fixups; updating imports before the disk move keeps the project-reference graph consistent at every step.", "preference", "technical", False,
     [("tsserver", "service"), ("workspace/willRenameFiles", "api"), ("project-reference", "concept")],
     [("tsserver", "workspace/willRenameFiles", "PREFERS")],
     "why do TypeScript monorepo maintainers prefer willRenameFiles over post-hoc import fixups",
     "tsserver will rename files project reference pre disk move prefer post"),
    # --- 36 ---
    ("Call hierarchy in clangd exposes virtual overrides through a dedicated edge type; the incomingCalls list shows override callers with a badge so refactor isn't accidentally narrowed to the base.", "fact", "technical", False,
     [("Call hierarchy", "concept"), ("clangd", "service"), ("incomingCalls", "api"), ("virtual overrides", "concept")],
     [],
     "how does clangd surface virtual overrides in call hierarchy so refactor includes subclass callers",
     "clangd call hierarchy virtual override incoming calls badge refactor"),
    # --- 37 ---
    ("Picked a pull-only diagnostics model for the custom DSL server; the DSL's parse is cheap enough that re-computing on request beats the bookkeeping of push invalidations across forty open files.", "decision", "technical", False,
     [("pull-only diagnostics", "pattern"), ("DSL", "language"), ("push invalidation", "pattern")],
     [("pull-only diagnostics", "push invalidation", "PREFERS")],
     "which diagnostics flavour did the cheap-parse DSL server prefer over push invalidations",
     "pull diagnostic dsl push invalidation forty open file cheap parse"),
    # --- 38 ---
    ("Release 1.8 shipped full LSP 3.17 support for the Rust server; the last capability added was notebookDocument/didChange for Jupyter-style cells edited in VS Code's notebook surface.", "milestone", "technical", False,
     [("LSP 3.17", "protocol"), ("notebookDocument/didChange", "api"), ("Jupyter", "platform"), ("VS Code", "tool")],
     [("notebookDocument/didChange", "LSP 3.17", "IMPLEMENTS")],
     "which LSP 3.17 capability landed last in the 1.8 Rust server release and why did it matter",
     "lsp 3 17 notebook did change jupyter vs code rust server 1 8"),
    # --- 39 ---
    ("Chose to pin vscode-languageserver-node as a devDependency in the custom server repo over vendoring protocol types locally; the pin keeps us in sync with VS Code's built-in client on every bump without a manual audit.", "decision", "technical", False,
     [("vscode-languageserver-node", "library"), ("devDependency", "pattern"), ("VS Code", "tool")],
     [("vscode-languageserver-node", "VS Code", "SUPPORTS")],
     "which pinning strategy for vscode-languageserver-node did the team pick over vendoring protocol types",
     "vscode language server node sdk dev dependency pin vendor choose audit"),
    # --- 40 ---
    ("The DSL server's TreeSitter query design for semantic tokens cites the Tree-sitter Query Syntax documentation and the LSP Semantic Tokens Guide; both publications live in the contributor onboarding folder.", "reference", "technical", False,
     [("TreeSitter", "library"), ("semantic tokens", "concept"), ("Tree-sitter Query Syntax", "publication"), ("LSP Semantic Tokens Guide", "publication")],
     [("TreeSitter", "Tree-sitter Query Syntax", "PUBLISHED_IN"), ("semantic tokens", "LSP Semantic Tokens Guide", "PUBLISHED_IN")],
     "which two onboarding publications cover the TreeSitter query and LSP semantic tokens design",
     "tree sitter query syntax lsp semantic tokens guide cite onboard highlight"),
    # --- 41 ---
    ("Rolled a reference implementation of the Memory DAP bridge against the Debug Adapter Protocol so debuggers can step through fine-tuning training loops; the adapter reuses CodeLLDB's stdio framing for transport.", "milestone", "technical", False,
     [("Memory DAP bridge", "service"), ("Debug Adapter Protocol", "protocol"), ("CodeLLDB", "tool"), ("stdio", "protocol")],
     [("Memory DAP bridge", "Debug Adapter Protocol", "IMPLEMENTS"), ("Memory DAP bridge", "CodeLLDB", "BUILDS_ON")],
     "which DAP adapter landed so debuggers can step through fine-tuning loops and what transport did it reuse",
     "memory dap adapter debug protocol codelldb stdio framing train loop"),
    # --- 42 ---
    ("The inlay-hint stability milestone for release 3.1 bundles client-side debouncing at 100 ms with resolve-deferred tooltips; cursor-move flicker on textDocument/inlayHint dropped to zero in the follow-up bench run.", "milestone", "technical", False,
     [("inlay-hint", "concept"), ("textDocument/inlayHint", "api"), ("debouncing", "pattern")],
     [("debouncing", "inlay-hint", "FIXES")],
     "which release bundled inlay-hint debouncing and resolve-deferred tooltips to kill cursor-move flicker",
     "inlay hint release 3 1 debounce 100 ms resolve defer tooltip bench"),
    # --- 43. noise ---
    ("A courier dropped off the wrong ergonomic keyboard and the desk next to mine now has two split models stacked like a layer cake.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("The Helix config references clangd, rust-analyzer, and gopls in one languages.toml; per-language roots use language-servers keys so the editor can fan a buffer to multiple servers for cross-language files.", "fact", "technical", False,
     [("Helix", "tool"), ("clangd", "service"), ("rust-analyzer", "service"), ("gopls", "service"), ("languages.toml", "config")],
     [("Helix", "languages.toml", "CONFIGURES")],
     "how does Helix's languages.toml wire multiple language servers for cross-language files in one buffer",
     "helix languages toml clangd rust analyzer gopls cross language buffer"),
    # --- 45 ---
    ("Switched the fine-tuning editor integration from raw stdio to an LSP-over-WebSocket transport for the hosted notebook; the same pygls server binary handles both paths behind a transport flag.", "decision", "technical", False,
     [("WebSocket", "protocol"), ("stdio", "protocol"), ("pygls", "library"), ("notebook", "platform")],
     [("WebSocket", "stdio", "REPLACES"), ("pygls", "WebSocket", "SUPPORTS")],
     "which LSP transport swap let the hosted notebook reuse the same pygls binary as the desktop flow",
     "web socket stdio pygls notebook transport flag hosted fine tuning"),
    # --- 46 ---
    ("Code actions of kind source.organizeImports run on save only when the editor has opted in via client capability; legacy clients that did not declare the capability no longer hit a silent no-op branch.", "fact", "technical", False,
     [("source.organizeImports", "concept"), ("client capability", "pattern")],
     [("client capability", "source.organizeImports", "CONFIGURES")],
     "how does the server gate source.organizeImports on save so legacy clients stop hitting a no-op branch",
     "source organize imports save client capability legacy no op branch"),
    # --- 47 ---
    ("rust-analyzer splits the proc-macro server into its own process so a macro panic cannot take down the language server; the parent restarts the child after three crashes and emits a diagnostic to the client.", "architecture", "technical", False,
     [("rust-analyzer", "service"), ("proc-macro server", "service"), ("diagnostic", "concept")],
     [("rust-analyzer", "proc-macro server", "HAS_PART")],
     "how does rust-analyzer isolate proc-macro panics from the main server and surface them to clients",
     "rust analyzer proc macro server separate process panic restart diagnostic"),
    # --- 48 ---
    ("Zed's collaboration layer re-uses Debug Adapter Protocol sessions across connected clients; a single adapter instance multiplexes stopped and continued events through the editor's peer-to-peer mesh.", "architecture", "technical", False,
     [("Zed", "tool"), ("Debug Adapter Protocol", "protocol"), ("peer-to-peer", "pattern")],
     [("Zed", "Debug Adapter Protocol", "USES")],
     "how does Zed share a single DAP session across collaboration peers in its p2p mesh",
     "zed dap debug session collaboration peer mesh stopped continued share"),
    # --- 49 ---
    ("LSP 3.17 type hierarchy shipped behind a client capability; the server fills prepareTypeHierarchy with supertypes and subtypes so class-heavy Java projects stop round-tripping through references.", "fact", "technical", False,
     [("LSP 3.17", "protocol"), ("type hierarchy", "concept"), ("prepareTypeHierarchy", "api"), ("Java", "language")],
     [("type hierarchy", "prepareTypeHierarchy", "USES")],
     "how does LSP 3.17 type hierarchy reduce reference round-trips in class-heavy Java projects",
     "type hierarchy prepare supertype subtype java class reference round"),
    # --- 50 ---
    ("Publishing strategy for the darkmem LSP reference followed the tower-lsp tutorial skeleton; the method section of the protocol guide cites RFC 8259 for JSON framing constraints.", "reference", "technical", False,
     [("darkmem", "project"), ("tower-lsp", "library"), ("RFC 8259", "publication"), ("JSON framing", "method")],
     [("darkmem", "tower-lsp", "BUILDS_ON"), ("JSON framing", "RFC 8259", "PUBLISHED_IN")],
     "which tutorial skeleton and JSON framing reference does the darkmem LSP guide cite",
     "darkmem tower lsp tutorial rfc 8259 json framing reference publish"),
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
