"""One-off emitter for shared-base batch-181 — technical domain (parsers and parser generators: tree-sitter, nom, ANTLR, PEG, Pratt, LR, Earley, tokenizers, AST, CST, incremental parsing).

Writes 50 rows to data/v2/shared/batch_181.tmp.jsonl with ids shared-09001..09050.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_181.tmp.jsonl"
ID_OFFSET = 9000

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the editor's syntax layer from a regex tokeniser to tree-sitter; incremental reparse under a keystroke stays under three ms on a 10k-line source file.", "decision", "technical", False,
     [("tree-sitter", "library"), ("regex tokeniser", "pattern"), ("incremental reparse", "pattern")],
     [("tree-sitter", "regex tokeniser", "REPLACES")],
     "which syntax backend replaced the regex tokeniser in the editor and what latency does reparse hold under",
     "tree sitter regex tokeniser incremental reparse editor keystroke"),
    # --- 2 ---
    ("The config-language parser is written in nom with a streaming input so a half-flushed TCP buffer can resume on the next chunk without restarting the whole parse pass.", "architecture", "technical", False,
     [("nom", "library"), ("streaming input", "pattern"), ("TCP", "protocol")],
     [("nom", "streaming input", "USES")],
     "which Rust combinator library drives the config parser and how does it cope with half-flushed TCP chunks",
     "nom streaming parser tcp chunk resume rust combinator config"),
    # --- 3 ---
    ("Dropped ANTLR 4 from the query-language stack in favour of a hand-written Pratt parser; generated code bulk and visitor boilerplate outweighed the grammar-file convenience.", "decision", "technical", False,
     [("ANTLR 4", "tool"), ("Pratt parser", "algorithm"), ("visitor", "pattern")],
     [("Pratt parser", "ANTLR 4", "REPLACES")],
     "which parser did we write by hand after dropping ANTLR 4 for the query language",
     "pratt parser antlr query language hand written visitor boilerplate"),
    # --- 4 ---
    ("Bison still generates the SQL expression grammar; the old Yacc port had shift-reduce conflicts silently resolved the wrong way on CASE expressions and produced wrong parse trees.", "problem", "technical", False,
     [("Bison", "tool"), ("Yacc", "tool"), ("shift-reduce", "concept"), ("CASE", "concept")],
     [("Bison", "Yacc", "REPLACES")],
     "which generator replaced Yacc for the SQL grammar after silent shift-reduce conflicts on CASE expressions",
     "bison yacc sql grammar shift reduce conflict case expression"),
    # --- 5 ---
    ("Flex drives the lexer for the DSL front-end; a hand-coded scanner we tried first lost on multiline string literals and trigraph-style escapes.", "decision", "technical", False,
     [("Flex", "tool"), ("hand-coded scanner", "pattern"), ("DSL", "concept")],
     [("Flex", "hand-coded scanner", "REPLACES")],
     "which lexer generator replaced the hand-coded scanner in the DSL front-end and which edge cases broke it",
     "flex lexer dsl hand coded scanner multiline string escape"),
    # --- 6 ---
    ("The browser-side expression parser uses PEG.js so grammars ship as JavaScript without a build step; generated output is tree-shake friendly and loads under 40 kB gzipped.", "architecture", "technical", False,
     [("PEG.js", "library"), ("JavaScript", "language"), ("tree-shake", "pattern")],
     [("PEG.js", "JavaScript", "PRODUCES")],
     "which PEG generator drives the browser-side parser and what bundle size does its output hold at",
     "peg js javascript browser parser grammar tree shake bundle size"),
    # --- 7 ---
    ("Parsing Expression Grammars replaced the ambiguous CFG for the template language; ordered choice killed the longest-match surprises that plagued the previous LL recogniser.", "reference", "technical", False,
     [("Parsing Expression Grammars", "concept"), ("CFG", "concept"), ("ordered choice", "concept"), ("LL recogniser", "algorithm")],
     [("Parsing Expression Grammars", "CFG", "REPLACES")],
     "why did the team abandon ambiguous context-free rules in the template engine and what ordered primitive solved longest-match",
     "peg cfg template language ordered choice ll longest match"),
    # --- 8 ---
    ("Pratt-style precedence climbing drives the expression sub-parser; the old recursive-descent cascade of a dozen binop levels was unreadable and hard to extend with new operators.", "architecture", "technical", False,
     [("Pratt-style", "method"), ("precedence climbing", "algorithm"), ("recursive-descent", "algorithm"), ("binop", "concept")],
     [("Pratt-style", "recursive-descent", "REPLACES")],
     "which expression-parsing technique replaced the binop cascade and how does it keep the grammar extensible",
     "pratt precedence climbing recursive descent binop cascade extend"),
    # --- 9 ---
    ("The hand-rolled recursive-descent parser for the config file is LL(1) by construction; a single-token lookahead suffices because the grammar was refactored to eliminate left factoring at every choice.", "fact", "technical", False,
     [("recursive-descent", "algorithm"), ("LL(1)", "concept"), ("left factoring", "concept")],
     [],
     "which lookahead class does the config recursive-descent parser hit after refactoring away left factoring",
     "recursive descent ll 1 config lookahead left factor refactor"),
    # --- 10 ---
    ("LL(k) with k=3 was necessary for the template preamble grammar; the directive-plus-colon-plus-identifier lookahead cannot be resolved inside a pure LL(1) parser without hacks.", "reference", "technical", False,
     [("LL(k)", "concept"), ("template preamble", "concept"), ("LL(1)", "concept")],
     [],
     "why did the template preamble grammar need LL(k) k=3 instead of LL(1) lookahead",
     "ll k lookahead template preamble directive colon identifier"),
    # --- 11. noise ---
    ("Found a 1983 parser textbook in the break-room bookshelf with a coffee ring covering the chapter on dragon-book exercises.", "fact", "noise", True, [], [], None, None),
    # --- 12 ---
    ("LR(1) tables for the full expression grammar ballooned past 180 KB of generated C; the LALR(1) collapse got it to 42 KB with no practical loss for the conflict set we actually hit.", "decision", "technical", False,
     [("LR(1)", "algorithm"), ("LALR(1)", "algorithm"), ("C", "language")],
     [("LALR(1)", "LR(1)", "REPLACES")],
     "which table algorithm replaced LR(1) for the expression grammar and what table-size win did it deliver",
     "lr 1 lalr table size collapse expression grammar c generator"),
    # --- 13 ---
    ("The natural-language command parser uses an Earley recogniser because the grammar is ambiguous by design; the chart survives to tie-break with a learned scorer downstream.", "architecture", "technical", False,
     [("Earley", "algorithm"), ("natural-language", "concept"), ("chart", "concept")],
     [("Earley", "chart", "USES")],
     "which recogniser drives the natural-language command parser and why is the chart preserved",
     "earley natural language command chart ambiguous learned scorer"),
    # --- 14 ---
    ("Packrat memoisation inside the PEG runtime cut quadratic worst-case traces on deeply-nested expressions to linear; memory cost is one memo per rule per position and we gladly pay it.", "reference", "technical", False,
     [("Packrat", "algorithm"), ("PEG", "concept"), ("memoisation", "method")],
     [("Packrat", "PEG", "APPLIES_TO")],
     "which memoisation strategy took PEG worst-case from quadratic to linear on nested expressions",
     "packrat peg memo quadratic linear nested expression rule position"),
    # --- 15 ---
    ("GLR drives the C++ header parser in the code-indexer; the template-vs-comparison ambiguity that killed a hand-rolled recursive descent resolves naturally across parallel GLR stacks.", "decision", "technical", False,
     [("GLR", "algorithm"), ("C++", "language"), ("recursive descent", "algorithm"), ("template", "concept")],
     [("GLR", "recursive descent", "REPLACES")],
     "which generalised parser replaced recursive descent for C++ headers and which ambiguity did it tame",
     "glr c++ header template comparison ambiguity recursive descent"),
    # --- 16 ---
    ("GLL-based parsing is under evaluation for the new grammar-workbench; functional stack merging handles ambiguity without GLR's cubic blow-up on the pathological test cases we care about.", "preference", "technical", False,
     [("GLL", "algorithm"), ("GLR", "algorithm"), ("grammar-workbench", "tool")],
     [],
     "which generalised parser is the workbench trialing instead of GLR and what pathological cost does it dodge",
     "gll glr grammar workbench stack merge cubic pathological eval"),
    # --- 17 ---
    ("Rewrote the URL matcher on top of combine; the old byte-level state machine was fast but unreadable and adding a scheme required three unrelated edits.", "decision", "technical", False,
     [("combine", "library"), ("URL matcher", "concept"), ("state machine", "pattern")],
     [("combine", "state machine", "REPLACES")],
     "which Rust combinator library replaced the URL state machine and which maintenance pain did it fix",
     "combine rust url matcher state machine scheme edit rewrite"),
    # --- 18 ---
    ("chumsky 0.10 ships with pratt helpers and a Stream trait that made porting the DSL parser painless; expression precedence now reads top-to-bottom instead of nested fold calls.", "milestone", "technical", False,
     [("chumsky", "library"), ("pratt", "method"), ("Stream", "api"), ("DSL", "concept")],
     [("chumsky", "pratt", "USES")],
     "which chumsky release shipped pratt helpers and a Stream trait and what DSL port did it enable",
     "chumsky pratt stream trait dsl parser precedence release port"),
    # --- 19 ---
    ("winnow replaced nom in the binary-format decoders; the new partial parse plus context error path is dramatically easier to thread through, and the migration took a Thursday afternoon.", "decision", "technical", False,
     [("winnow", "library"), ("nom", "library"), ("binary-format", "concept")],
     [("winnow", "nom", "REPLACES")],
     "which combinator library replaced nom in the binary decoders and which API improvement carried the decision",
     "winnow nom binary decode partial parse context error migrate"),
    # --- 20 ---
    ("pyparsing handles the config-file parser inside the admin CLI; a plain Python dependency beats adding a C-extension build for a tool that runs twice a day.", "decision", "technical", False,
     [("pyparsing", "library"), ("Python", "language"), ("admin CLI", "tool")],
     [("pyparsing", "Python", "USES")],
     "which parser library does the admin CLI ship because a pure Python dep beat a C extension",
     "pyparsing python admin cli config file dependency extension"),
    # --- 21 ---
    ("lark-parser drives the DSL front-end in the data pipeline; Earley mode handles the ambiguity that showed up once users started nesting macros inside default-value expressions.", "architecture", "technical", False,
     [("lark-parser", "library"), ("Earley", "algorithm"), ("DSL", "concept"), ("macro", "concept")],
     [("lark-parser", "Earley", "USES")],
     "which Python parser library drives the data-pipeline DSL and which mode catches nested-macro ambiguity",
     "lark parser earley python dsl data pipeline macro default value"),
    # --- 22 ---
    ("SentencePiece trains the tokenizer for the multilingual model; byte-fallback keeps out-of-vocab CJK punctuation from producing UNK tokens in tails of the training distribution.", "architecture", "technical", False,
     [("SentencePiece", "tool"), ("byte-fallback", "method"), ("CJK", "concept"), ("UNK", "concept")],
     [("SentencePiece", "byte-fallback", "USES")],
     "which tokenizer trainer powers the multilingual model and how does byte-fallback rescue CJK punctuation",
     "sentencepiece tokenizer multilingual byte fallback cjk unk model"),
    # --- 23 ---
    ("BPE from Hugging Face tokenizers replaced the whitespace splitter in the search indexer; vocabulary is 50k merges and the build step runs on a single worker in under eight minutes.", "milestone", "technical", False,
     [("BPE", "algorithm"), ("tokenizers", "library"), ("whitespace splitter", "pattern")],
     [("BPE", "whitespace splitter", "REPLACES")],
     "which subword algorithm replaced whitespace splitting in the search indexer and what vocab size did it settle on",
     "bpe tokenizers hugging face whitespace split vocab merges index"),
    # --- 24 ---
    ("WordPiece from BERT still beats BPE on our English-only classification set by a hair; we kept the 30k vocab for backwards compatibility with cached embeddings in production.", "reference", "technical", False,
     [("WordPiece", "algorithm"), ("BERT", "framework"), ("BPE", "algorithm")],
     [("WordPiece", "BPE", "IMPROVES_ON")],
     "which subword algorithm still beats BPE on the English classification set and why keep the vocab pinned",
     "wordpiece bert bpe english classification vocab compatibility cache"),
    # --- 25 ---
    ("tiktoken powers the token counting in the cost estimator; running the model's own tokenizer offline matches server-side billing byte-for-byte and removed a 2% drift we'd been eating.", "fact", "technical", False,
     [("tiktoken", "library"), ("cost estimator", "project")],
     [("tiktoken", "cost estimator", "USES")],
     "which tokenizer library drives the cost estimator and what billing drift did it close",
     "tiktoken cost estimator offline billing byte drift server match"),
    # --- 26 ---
    ("AST design separates node-kind enums from payload structs; a mix-in trait adds source spans so error reporting can unify across rewritten and original nodes without duplicating span logic.", "milestone", "technical", False,
     [("AST", "concept"), ("node-kind", "pattern"), ("source spans", "concept")],
     [],
     "how does the AST design keep spans unified across rewritten and original nodes without duplication",
     "ast node kind enum payload span mixin trait error report unify"),
    # --- 27 ---
    ("The concrete syntax tree is kept alongside the AST so formatters and linters never have to guess at whitespace or comment placement; pretty-print round-trips byte-for-byte.", "milestone", "technical", False,
     [("concrete syntax tree", "concept"), ("AST", "concept"), ("pretty-print", "method")],
     [],
     "why does the pipeline keep a CST alongside the AST and what round-trip guarantee does it unlock",
     "cst ast formatter linter whitespace comment pretty print round"),
    # --- 28 ---
    ("Incremental parsing in the IDE layer reuses subtrees keyed by byte range and kind; a keystroke in a 5 MB source file touches a handful of nodes instead of reparsing the whole document.", "milestone", "technical", False,
     [("Incremental parsing", "method"), ("subtree", "concept"), ("IDE", "tool")],
     [],
     "which reuse strategy lets the IDE avoid a full reparse on every keystroke in a large source file",
     "incremental parse subtree byte range reuse ide keystroke large"),
    # --- 29 ---
    ("Error recovery panics to the next synchronising token after a parse failure and keeps going; the old approach of failing the whole parse hid later syntax errors that the user wanted to see.", "decision", "technical", False,
     [("Error recovery", "method"), ("synchronising token", "concept"), ("parse failure", "error")],
     [("synchronising token", "parse failure", "FIXES")],
     "which error-recovery strategy replaced whole-parse failure and what user-visible benefit did it unlock",
     "error recovery sync token panic parse failure continue later"),
    # --- 30 ---
    ("tree-sitter queries power the semantic highlighter; S-expression patterns match against the parse tree so the highlighter never has to walk nodes imperatively again.", "architecture", "technical", False,
     [("tree-sitter", "library"), ("queries", "concept"), ("S-expression", "concept"), ("semantic highlighter", "tool")],
     [("tree-sitter", "queries", "HAS_PART")],
     "which tree-sitter feature drives the semantic highlighter so it avoids imperative tree walks",
     "tree sitter query s expression pattern highlight semantic walk"),
    # --- 31 ---
    ("Shipped WASM-compiled tree-sitter grammars to the web editor; each language loads lazily and the browser bundle stayed under 600 kB despite supporting nine languages on day one.", "milestone", "technical", False,
     [("WASM", "technology"), ("tree-sitter", "library"), ("web editor", "tool")],
     [("tree-sitter", "WASM", "USES")],
     "which compilation target lets the web editor load tree-sitter grammars lazily and keep the bundle small",
     "wasm tree sitter web editor grammar lazy load bundle size"),
    # --- 32 ---
    ("Recursive-descent with a split lexer is the house style for new DSLs; generator toolchains are reserved for grammars big enough to make hand maintenance a net loss.", "preference", "technical", False,
     [("Recursive-descent", "algorithm"), ("split lexer", "pattern"), ("DSL", "concept")],
     [],
     "which parser style is the default for new DSLs and when does the team reach for a generator instead",
     "recursive descent split lexer dsl house style generator maintain"),
    # --- 33 ---
    ("Context-sensitive keywords in the SQL dialect are handled in the lexer via a symbol table hook; the parser stays LALR(1) and nobody has to reason about a modal lexer.", "architecture", "technical", False,
     [("Context-sensitive keywords", "concept"), ("LALR(1)", "algorithm"), ("symbol table", "concept"), ("SQL", "language")],
     [],
     "how does the SQL dialect keep the parser LALR(1) while supporting context-sensitive keywords",
     "context sensitive keyword sql lalr symbol table lexer hook modal"),
    # --- 34 ---
    ("Grammar for the rule-language uses left recursion directly; ANTLR 4 rewrites left recursion internally so the surface grammar reads exactly like the spec document.", "reference", "technical", False,
     [("left recursion", "concept"), ("ANTLR 4", "tool"), ("rule-language", "concept")],
     [("ANTLR 4", "left recursion", "SUPPORTS")],
     "which generator lets the rule-language grammar keep left recursion verbatim from the spec document",
     "left recursion antlr rule language spec grammar surface rewrite"),
    # --- 35 ---
    ("Parser combinators live in an effect monad so errors, position, and user state thread through without tuple-returning boilerplate; custom combinators compose without touching internals.", "fact", "technical", False,
     [("Parser combinators", "method"), ("effect monad", "pattern")],
     [],
     "which plumbing pattern lets parser combinators thread errors, position, and state without tuples",
     "parser combinator effect monad error position state compose"),
    # --- 36 ---
    ("Skip-tree merging in the incremental reparse cache was dropping nodes after a multi-byte paste; the bug was a UTF-8 boundary check that compared bytes instead of code points.", "milestone", "technical", False,
     [("Skip-tree", "pattern"), ("incremental reparse", "method"), ("UTF-8", "concept")],
     [("UTF-8", "Skip-tree", "CAUSES")],
     "which UTF-8 boundary bug caused the incremental reparse cache to drop nodes after a multi-byte paste",
     "skip tree incremental reparse utf 8 boundary byte code point"),
    # --- 37 ---
    ("Grammar ambiguity in the expression language surfaced only on inputs with trailing dots; an Earley run confirmed the CFG admitted two trees and a disambiguation rule was added at the parser level.", "problem", "technical", False,
     [("Earley", "algorithm"), ("CFG", "concept"), ("disambiguation rule", "concept")],
     [("disambiguation rule", "Earley", "FIXES")],
     "which recogniser confirmed the trailing-dot ambiguity and how was the grammar disambiguated",
     "grammar ambiguous expression trailing dot earley cfg disambig"),
    # --- 38 ---
    ("Shifted the markdown dialect parser to tree-sitter with a scanner.c for indent-sensitive blocks; generic generators can't express indent context without a hand-written external scanner.", "decision", "technical", False,
     [("tree-sitter", "library"), ("scanner.c", "file"), ("markdown", "language")],
     [("tree-sitter", "scanner.c", "USES")],
     "how did tree-sitter handle indent-sensitive markdown blocks that generic generators couldn't express",
     "tree sitter scanner c markdown indent block external generator"),
    # --- 39 ---
    ("Action-production rules in the old Yacc grammar had side effects that broke on GLR forking; moving to pure AST construction made the same rules safe across parallel parse stacks.", "problem", "technical", False,
     [("Yacc", "tool"), ("GLR", "algorithm"), ("AST construction", "method")],
     [("AST construction", "Yacc", "REPLACES")],
     "why did Yacc action rules break under GLR and which rewrite made the grammar safe for parallel parse stacks",
     "yacc action rule side effect glr fork ast construction pure"),
    # --- 40 ---
    ("PEG negative lookahead made the comment rule trivial: one slash-star with a not-slash-slash guard killed the old C-style tokenizer's hand-written comment escape logic outright.", "reference", "technical", False,
     [("PEG", "concept"), ("negative lookahead", "concept"), ("comment rule", "concept")],
     [("negative lookahead", "comment rule", "APPLIES_TO")],
     "which PEG feature made the comment rule trivial and which hand-written escape logic did it retire",
     "peg negative lookahead comment rule slash star escape tokenizer"),
    # --- 41 ---
    ("The lexer-parser interface uses a token stream with a one-token pushback; full backtracking at the parser level turned out unnecessary once the grammar was factored for LL(1).", "preference", "technical", False,
     [("lexer-parser", "pattern"), ("token stream", "concept"), ("pushback", "method"), ("LL(1)", "concept")],
     [],
     "which minimal lookahead mechanism between lexer and parser suffices once the grammar is LL(1)",
     "lexer parser token stream pushback one token ll 1 backtrack"),
    # --- 42 ---
    ("Chose a hand-written Pratt parser over PEG.js for the formula bar; operator precedence and right-associativity read more naturally as a table than as nested PEG rules.", "decision", "technical", False,
     [("Pratt parser", "algorithm"), ("PEG.js", "library"), ("formula bar", "tool"), ("right-associativity", "concept")],
     [("Pratt parser", "PEG.js", "PREFERS")],
     "which parser won the formula-bar bake-off against PEG.js and what readability argument sealed it",
     "pratt peg js formula bar operator precedence right assoc table"),
    # --- 43 ---
    ("Lark's LALR backend reports shift-reduce conflicts at grammar-load time with the exact input pair; the Earley backend would just pick one silently and we missed a bug for a week.", "preference", "technical", False,
     [("Lark", "library"), ("LALR", "algorithm"), ("Earley", "algorithm"), ("shift-reduce", "concept")],
     [("LALR", "Earley", "IMPROVES_ON")],
     "which Lark backend surfaces shift-reduce conflicts loudly and what bug did the Earley backend hide",
     "lark lalr earley shift reduce conflict report silent miss week"),
    # --- 44. noise ---
    ("The compiler-nerd Slack channel ran a six-hour argument about tabs versus spaces in generated parser tables before anyone noticed it was a bot loop.", "fact", "noise", True, [], [], None, None),
    # --- 45 ---
    ("Grammar-level left factoring tool ships with the workbench; it normalises alternatives with common prefixes so the LL(1) checker passes without hand-reshuffling rules by eye.", "fact", "technical", False,
     [("left factoring", "concept"), ("workbench", "tool"), ("LL(1)", "concept")],
     [],
     "which tooling step normalises common-prefix alternatives so LL(1) passes without manual grammar edits",
     "left factoring workbench ll 1 normalise common prefix rule"),
    # --- 46 ---
    ("tree-sitter's incremental query evaluator caches per-node matches; a large file reopens to full syntax highlighting in under 30 ms because only dirty ranges re-evaluate.", "fact", "technical", False,
     [("tree-sitter", "library"), ("incremental query", "method"), ("syntax highlighting", "concept")],
     [],
     "which tree-sitter mechanism keeps large-file reopen highlighting under 30 ms",
     "tree sitter incremental query evaluate cache node dirty range"),
    # --- 47 ---
    ("Packrat parsing was rejected for the log-format front-end because the memo table footprint on 200 MB log files was unacceptable; a stateless PEG run with backtracking won instead.", "fact", "technical", False,
     [("Packrat parsing", "algorithm"), ("PEG", "concept"), ("log-format", "concept")],
     [("PEG", "Packrat parsing", "REPLACES")],
     "why did packrat lose to a stateless PEG run on the log-format front-end",
     "packrat peg log format memo table footprint stateless backtrack"),
    # --- 48 ---
    ("BPE training for the code model used a byte-level pretokenizer so whitespace and punctuation never split unexpectedly; GPT-2's regex rules were ported almost verbatim to keep tokens stable.", "architecture", "technical", False,
     [("BPE", "algorithm"), ("byte-level pretokenizer", "method"), ("GPT-2", "framework")],
     [("BPE", "byte-level pretokenizer", "USES")],
     "which pretokenizer flavour does the code-model BPE use and where did the regex rules come from",
     "bpe byte level pretokenizer gpt 2 regex code model stable"),
    # --- 49 ---
    ("CST-to-AST lowering is a separate pass so parser and semantic analysis stay decoupled; experiments with fused lowering made the parser harder to test and we walked it back.", "decision", "technical", False,
     [("CST", "concept"), ("AST", "concept"), ("lowering", "method"), ("semantic analysis", "concept")],
     [("lowering", "semantic analysis", "APPLIES_TO")],
     "why did the team keep CST-to-AST lowering as a separate pass instead of fusing it with the parser",
     "cst ast lower pass parser semantic decouple test fuse walk"),
    # --- 50 ---
    ("The Earley parser emits forest nodes with sharing so ambiguous inputs don't explode memory; an SPPF representation keeps common subtrees unique across parallel derivations.", "fact", "technical", False,
     [("Earley", "algorithm"), ("SPPF", "concept"), ("forest", "concept")],
     [("Earley", "SPPF", "USES")],
     "which shared-forest representation lets the Earley parser bound memory on ambiguous inputs",
     "earley sppf forest shared parse ambiguous memory derivation"),
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
