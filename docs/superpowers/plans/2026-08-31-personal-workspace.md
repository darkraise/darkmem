# Personal Workspace Implementation Plan (Increment 8)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** The Notion-style personal workspace (spec §8, as redesigned; both §8.3 decisions taken): four block verbs on both doors (`block_update`, `block_insert`, `block_move`, `block_delete`), block-first ingest whose serialiser regenerates `documents.content`, recomputes `content_hash` and **recomputes `char_span` in the same pass**, a per-block markdown-source editor with no framework, and nesting derived from the uri path.

**No baseline regeneration is required by any part of this plan — verified, not assumed.** Every storage touch is enumerated: `blocks.id` is already a stable uuid PK, `parent_id`/`order_index`/`type`/`text`/`properties`/`char_span` all exist (`backend/migrations/versions/0001_baseline.py:1307-1329`); the ingest-direction flag and the marker records ride existing `JSONB` columns (`documents.properties`, `blocks.properties`); `documents.content`/`content_hash` are increment 3's columns, consumed here, not created; the `blocks_edited` event type is a code-side vocabulary edit (`EVENT_TYPES` is a Python list, not a CHECK). No task in this plan runs DDL, edits `0001_baseline.py`, or moves the schema-guard hash. The review's B2 blocker was precisely that the earlier §8 priced a regen it could not name; the redesign removed the claim and this plan confirms it against the shipped DDL.

**Architecture:** One pure serialiser (`block_serializer.py`: tree → content + per-block spans + reading order), one verbs service (`block_verbs.py`: load tree → apply one mutation in memory → serialise → write blocks placement + document row in a SAVEPOINT → journal → commit → embed the touched block), thin REST and MCP doors over it (invariant 17), and a frontend editor that wraps increment 4's `BlockView` in a focus-to-textarea shell. A document is content-first or block-first, recorded at `documents.properties.ingest_direction`; `document_put` against a block-first document is a **409 refusal**, never a silent overwrite. The first block verb against a content-first document converts it: markers the parser discarded are derived from the stored `content` through each block's exact `char_span` — which is what makes the conversion faithful instead of defaulting every list to `-`.

**Editor decision is taken and closed (spec §8.3):** markdown-source blocks, no framework — one editable per block holding that block's markdown source, `react-markdown` (already a dependency) for the unfocused render, darkraise-ui `textarea`. **No TipTap, no Lexical, no ProseMirror** — storage format and edit format being identical is what removes the conversion step where round-trip fidelity dies; do not reopen this. Accepted ceiling, restated so nobody discovers it: no drag handles, no table editing, no slash menu.

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §8 (as redesigned), §5.2-5.3 (the content column and CAS it builds on), §8.5 (dependencies).
**Review:** B2 (upheld against the old §8; the redesign this plan implements is the answer), M5 (the editor ADR — taken in §8.3, recorded above).

**Amendments (2026-09-02, cross-plan adversarial review of all eight plans).** This plan carried the most defects of the eight, and three of them are design changes rather than corrections — read this list before executing any of Tasks 2, 4, 5, 6 or 8.

- **M-2 (the conversion was lossy and silent).** Block-first conversion regenerates `documents.content` from the tree, but the tree does not contain frontmatter, thematic breaks, HTML blocks or link-reference definitions. Any `capture`-scoped caller could have converted a corpus document and silently dropped them, contradicting spec §4.5 and §8.2's "never regenerated". Fixed two ways: the serialiser re-emits frontmatter from `documents.properties.frontmatter` (increment 2 stores it, so nothing is lost there), and conversion is now **guarded by a fidelity check** that refuses rather than converting when the round trip would not reproduce the stored source. Tasks 1, 2 and 4.
- **M-3 (the direction refusal was check-then-act).** Both the put's refusal and `_mutate` read the direction, then write across `await` boundaries with no row lock — the same M1 race increment 3 spent its Task 3 closing, re-opened on the predicate that protects an editing session. Both writers now take `FOR UPDATE` on the document row as the first statement inside their savepoint. Task 4, and increment 3's put.
- **M-8 (a move never persisted).** `_PLACE` wrote `order_index`/`char_span`/`properties` and `_UPDATE_BLOCK` — the only statement writing `parent_id` — ran only for `updated`, so `move_block` reordered without reparenting. `_PLACE` now carries `parent_id`. Task 4.
- **M-4** — `DocumentIsBlockFirst` had a 409 on REST and no shape at all on MCP, where the agent (the likelier caller) would get an unstructured tool error. Task 6 adds a `direction_conflict` envelope beside increment 3's `hash_conflict`.
- **M-7** — the editor's "storage format and edit format are identical, so there is no conversion step" claim was false at block granularity: `text` is marker-stripped and `properties` is on neither read surface, so Task 8 hand-rolled a promotion regex that *is* a conversion step. New Task 5a serves `properties` and the block's own `source` on both doors; the editor now edits real source. This also closes the deviation increment 4 recorded for the library `table` component.
- **B-2 arithmetic** — Task 6 stated literal parity headline totals (72→73, 23→24) computed before increments 6 and 7 existed; both add a surface. It now recomputes from the derived assertion. Also `m-14`: the headline is at `docs/two-door-parity.md:13`, not `:14`.
- **m-2, m-9, m-10** — the second "all 34 tools" occurrence at `scopes.py:10`, `document-tree.tsx` listed as *Modify* against a "nothing is rewritten" promise, and `derive_markers`' two different signatures.

Tasks 1, 3, 5, 7, 9, 10 and 11 were otherwise found sound, and the components this plan consumes from increment 4 (`BlockView`, `DocumentTree`, `buildUriTree`, the documents query keys) were verified to match increment 4's emitted signatures exactly.

## Prerequisites

1. **Increment 3 landed and deployed** — hard dependency. This plan consumes: `documents.content TEXT NULL` written by `put_document`; `compute_content_hash` unchanged (`backend/app/services/document_ingest.py`, sha256 over UTF-8); the `include_content` read flag. If increment 3's plan (written in parallel with this one) spells any of these differently, reconcile **at execution against its landed code**, not by guessing here.
2. **Increment 4 landed** (`docs/superpowers/plans/2026-08-31-workspace-ui.md`) — the editor extends its `BlockView`, `DocumentTree` (via the `nodeActions` slot it declared for exactly this), `buildUriTree`, and the documents hooks. Nothing is rewritten.
3. **Increment 2 landed** — the serialiser handles `table`/`table_row` blocks in the shape its plan fixed (`table.properties = {header, alignments}`, `table_row.properties = {cells}`, texts `"a | b"`).

## Where this plan deviates from the spec, flagged

- **`block_update` takes an optional `type`** (spec §8.1's table says text and properties only). Without it, turning a paragraph into a heading is a delete-plus-insert that discards the block's id and vector for a label change. The type is normalised through `normalize_block_type` like every stored type (taxonomy rule: the writer normalises).
- **The spec's "a move renumbers its sibling run — O(siblings), not O(document)" does not survive contact with the shipped semantics, and the code wins.** `order_index` is a *global* reading-order sequence (`tests/test_block_pipeline.py:256` pins "reading order is strictly increasing across the whole tree"; `document_blocks` and `_OUTLINE` sort by it flat, `backend/app/services/document_door.py:609-651`), and the serialiser rewrites every subsequent block's `char_span` per edit regardless. The honest cost model: **one edit = one bulk placement UPDATE over the document's blocks (order_index + char_span) plus one document-row write, with re-embedding confined to the touched block.** O(document) rows, one statement, zero extra embeds — cheaper where it matters (the embed), not where it reads nicely.
- **§5.3's `expected_hash` compare-and-set is not consumed by the block verbs.** §8.4 fixes block-first concurrency as single-user last-write-wins per block; what protects an editing session from a concurrent `document_put` is the direction refusal. **Amended 2026-09-02 (review M-3):** this originally added "which is unconditional rather than hash-gated", implying unconditional was the stronger property. It is not — an unconditional predicate evaluated in a *separate read* before the write is check-then-act, and a compare-and-set at least fails loudly. The refusal is now taken under a `FOR UPDATE` row lock held by both writers, with the direction predicate also riding the put's own UPDATE and zero-rows treated as a refusal. Unconditional-and-locked is the stronger property; unconditional-and-unlocked was the weaker one.

## Global Constraints

- **Backend tests** (from `backend/`): `.venv/bin/python -m pytest -q` against `darkmem_test` (dev-compose Postgres, 127.0.0.1:5433). **Plain `pytest -q` does not collect `scripts/benchlib/tests`** — run the gate before calling anything done.
- **Frontend** (from `frontend/`): `npm run typecheck`, `npm test`, `npm run build`. `routeTree.gen.ts` is generated.
- **Merge gate:** `./scripts/gate.sh`. `--full` is unreliable on this host (earlyoom kills Chromium); Playwright only via `backend/scripts/e2e/run_playwright_e2e.py`.
- **The block-channel firewall is structural and this plan feeds it, never fights it.** Every new backend module here joins `BLOCK_CHANNEL_MODULES` (`backend/tests/test_block_retrieval.py:345`) and the filing-closure seeds (`backend/tests/test_block_pipeline.py:792`) in the same task that creates it — an unclassified module is a scan hole, which is this codebase's named characteristic defect.
- **Taxonomy-first:** the `blocks_edited` event value lands in `EVENT_TYPES` (`backend/app/services/events.py:124`) before its emitter ships (same task, vocabulary step first). Write-time minimization: the payload carries **no block text**.
- **Two doors, one service layer (invariant 17):** both doors call `app/services/block_verbs.py`; the parity table (`backend/tests/test_door_parity.py`'s `PARITY_TABLE`) gains the classified row in the same increment — its enumeration is driven off the router and tool registry, so an unclassified route/tool fails the build by design.
- **Demo mode makes no API calls**: every new hook rides `enabled: !DEMO`.
- **Commits:** conventional, atomic. A `feat` push cuts a release; the final task writes the CHANGELOG section.

## File Structure

```
backend/app/services/block_serializer.py       # Task 1 (create): pure serialiser
backend/tests/test_block_serializer.py         # Task 1 (create)
backend/app/services/events.py                 # Task 2: EVENT_TYPES += blocks_edited
backend/app/services/document_door.py          # Task 2: direction refusal; Task 3: expiry helper extraction
backend/tests/test_document_door.py            # Tasks 2-3: extend
backend/app/services/block_fact_sources.py     # Task 3: withdraw_blocks
backend/tests/test_block_fact_sources.py       # Task 3: extend
backend/app/services/block_verbs.py            # Task 4 (create): the four verbs
backend/tests/test_block_verbs.py              # Task 4 (create)
backend/tests/test_block_retrieval.py          # Task 4: module set += 2
backend/tests/test_block_pipeline.py           # Task 4: closure seed += 1
backend/app/services/document_door.py          # Task 5a: BlockRow += properties, source
backend/app/api/routes/documents.py            # Task 5a: BlockRowModel; Task 5: four routes
backend/tests/test_api/test_rest_conformance.py # Task 5: status table += 4
backend/tests/test_document_routes.py          # Task 5: extend
backend/app/api/mcp/server.py                  # Task 6: four tools
backend/app/api/mcp/scopes.py                  # Task 6: CAPTURE_TOOLS += 4
backend/tests/test_door_parity.py              # Task 6: PARITY_TABLE row
docs/two-door-parity.md                        # Task 6: regenerate
backend/tests/test_mcp_auth.py                 # Task 6: stale-count docstring
frontend/src/hooks/api/use-blocks-api.ts       # Task 7 (create)
frontend/src/features/documents/components/block-editor.tsx  # Task 8 (create)
frontend/src/features/documents/components/documents-view.tsx # Task 9: edit mode, new page, nodeActions consumer
CLAUDE.md                                      # Task 10: Documents + MCP count updates
docs/agent-conventions.md                      # Task 10: block-first note
CHANGELOG.md                                   # Task 11
```

---

### Task 1: The serialiser — tree in, source plus spans out

**Files:**
- Create: `backend/app/services/block_serializer.py`
- Create: `backend/tests/test_block_serializer.py`

**Interfaces:**
- Consumes: nothing at runtime (pure); tests consume `parse_markdown` for round-trip assertions.
- Produces: `serialize_tree` and `derive_markers` — the core Task 4 builds on.

**Signatures, fixed here rather than deferred** (review m-10): this plan spelled `derive_markers` two ways — `derive_markers(tree, content)` in this task and `derive_markers(tree, meta["content"], spans)` in Task 4. **The three-argument form is correct** and is what both tasks use: the spans are what let it read each block's own marker out of the source, and without them it would have to re-parse. The signature is:

```python
def derive_markers(
    tree: list[TreeBlock],
    content: str,
    spans: dict[UUID, tuple[int, int]],
) -> list[TreeBlock]
```

A block with no span in `spans` keeps its properties unchanged — it was minted by a verb, not parsed, so there is no source to read a marker from.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5
**Approach:** inline - skip 3: the spec (§8.2-8.3) fixed the approach — serialisation of markdown-source blocks with spans recorded in the same pass; the per-type rules below are the decision written down.

- [ ] **Step 1: Write the round-trip tests first**

`test_block_serializer.py` — the properties that make this module trustworthy, before any emit rule exists:

```python
"""The serialiser is trusted only as far as the parser agrees with it.

The load-bearing property is the ROUND TRIP: parse(serialize(tree)) must
reproduce the tree's types, texts and structure, and serialize must be a
fixed point (serialize(parse(serialize(t))) == serialize(t)). Per-shape
emit tests localise a failure; the round-trip test is the contract.
"""
from app.services.block_serializer import TreeBlock, derive_markers, serialize_tree
from app.services.document_parsers import parse_markdown
from app.services.document_ingest import BlockDraft


def _tree_from_drafts(drafts: list[BlockDraft]) -> list[TreeBlock]:
    """Adapt parser output to serialiser input, minting ids and resolving
    the backward parent indexes — the same resolution _resolve_tree does."""
    ...


def _skeleton(blocks) -> list[tuple]:
    """(type, text, parent-position) triples — the structure that must survive."""
    ...


def _spans_of(source: str) -> dict:
    """{block id: char_span} for a freshly parsed tree — what derive_markers
    and reproduces_source read each block's own marker out of."""
    ...


ROUND_TRIP_SOURCES = [
    "# Title\n\nA paragraph with **bold** and `code`.",
    "# H1\n\n## H2\n\ndeeper prose\n\n## H2 again",
    "- one\n- two\n  - nested\n- three",
    "1. first\n2. second\n3. third",
    "> quoted line\n> more of it",
    "```python\nprint('hi')\n```",
    "| Name | Age |\n|---|---:|\n| Ann | 3 |\n| Bo | 4 |",
    "# Doc\n\npara\n\n- item\n  - sub\n\n> quote\n\n```\ncode\n```",
    # Review M-2: frontmatter round-trips because increment 2 files it into
    # documents.properties.frontmatter, so the serialiser can re-emit it.
    "---\ntitle: The Plan\nstatus: draft\n---\n\n# Title\n\nprose",
]

# Shapes the parser drops on the floor: `hr` and `html_block` mint no block
# (document_parsers.py:211-213) and markdown-it consumes link-reference
# definitions into `env`. NOTHING can serialise them back, so a document
# containing one must REFUSE conversion rather than silently lose it
# (review M-2). These are the guard's fixtures, not the round trip's.
NON_CONVERTIBLE_SOURCES = [
    "para one\n\n---\n\npara two",                    # thematic break
    "before\n\n<div class='x'>raw</div>\n\nafter",    # html_block
    "see [the doc][ref]\n\n[ref]: https://example.test",  # link reference
]


@pytest.mark.parametrize("source", ROUND_TRIP_SOURCES)
def test_parse_serialize_parse_is_stable(source):
    tree = _tree_from_drafts(parse_markdown(source))
    first = serialize_tree(tree)
    reparsed = _tree_from_drafts(parse_markdown(first.content))
    assert _skeleton(reparsed) == _skeleton(tree)
    second = serialize_tree(reparsed)
    assert second.content == first.content        # fixed point


@pytest.mark.parametrize("source", ROUND_TRIP_SOURCES)
def test_every_span_slices_its_own_block_back_out(source):
    tree = _tree_from_drafts(parse_markdown(source))
    result = serialize_tree(tree)
    by_id = {b.id: b for b in tree}
    for placed in result.placed:
        lo, hi = placed.char_span
        sliced = result.content[lo:hi]
        block = by_id[placed.block_id]
        # The span covers the block's own source including its marker
        # (the parser's own convention, document_parsers.py module doc);
        # its text must appear inside the slice.
        first_text_line = (block.text or "").split("\n", 1)[0]
        assert first_text_line in sliced or block.text == ""


def test_placed_order_is_the_strictly_increasing_reading_order():
    tree = _tree_from_drafts(parse_markdown("# a\n\npara\n\n- x\n  - y"))
    result = serialize_tree(tree)
    assert [p.order_index for p in result.placed] == list(range(len(tree)))


def test_ordered_lists_renumber_by_position():
    tree = _tree_from_drafts(parse_markdown("1. a\n2. b\n3. c"))
    tree = [b for b in tree if b.text != "b"]      # delete the middle item
    result = serialize_tree(tree)
    assert "1. a" in result.content and "2. c" in result.content


def test_a_code_block_containing_backticks_gets_a_longer_fence():
    tree = [TreeBlock(id=uuid4(), parent_id=None, order_index=0, type="code",
                      text="```\nnested\n```", properties=None)]
    content = serialize_tree(tree).content
    assert content.startswith("````")
    assert _skeleton(_tree_from_drafts(parse_markdown(content))) == _skeleton(tree)


def test_derive_markers_reads_the_marker_out_of_the_source():
    source = "* star item\n\n1) paren ordered"
    tree = _tree_from_drafts(parse_markdown(source))
    derived = derive_markers(tree, source, _spans_of(source))
    markers = [b.properties.get("marker") for b in derived if b.type == "list"]
    assert markers == ["*", "1)"]


@pytest.mark.parametrize("source", ROUND_TRIP_SOURCES)
def test_reproduces_source_reports_true_for_every_round_trip_fixture(source):
    tree = _tree_from_drafts(parse_markdown(source))
    assert reproduces_source(tree, source, _spans_of(source)) is True


@pytest.mark.parametrize("source", NON_CONVERTIBLE_SOURCES)
def test_reproduces_source_refuses_what_the_parser_dropped(source):
    """Review M-2: the serialiser cannot emit these, so the guard that
    gates conversion must say so. A False here is the whole protection
    against a block verb silently rewriting a corpus document without its
    frontmatter fence, its rules or its link definitions."""
    tree = _tree_from_drafts(parse_markdown(source))
    assert reproduces_source(tree, source, _spans_of(source)) is False


def test_frontmatter_is_re_emitted_from_document_properties():
    source = "---\ntitle: T\n---\n\n# H\n\nbody"
    tree = _tree_from_drafts(parse_markdown(source))
    out = serialize_tree(tree, frontmatter="title: T")
    assert out.content.startswith("---\ntitle: T\n---\n")
    assert "# H" in out.content


def test_a_parent_cycle_raises_instead_of_hanging():
    a, b = uuid4(), uuid4()
    tree = [
        TreeBlock(id=a, parent_id=b, order_index=0, type="paragraph", text="a", properties=None),
        TreeBlock(id=b, parent_id=a, order_index=1, type="paragraph", text="b", properties=None),
    ]
    with pytest.raises(ValueError):
        serialize_tree(tree)
```

Run: FAIL (module absent).

**Two additions the review forced into this module** (M-2), both pure and both covered by the tests above:

1. **`serialize_tree(tree, *, frontmatter: str | None = None)`** re-emits a leading `---` fence when `frontmatter` is given. Increment 2 files the frontmatter text into `documents.properties.frontmatter`, so this is a stored value being restored, not a reconstruction — and without it every conversion of a corpus document would drop its front fence. The emitted fence is counted in the spans exactly as the parser counts it (`document_parsers.py`'s "spans point at the source" contract, kept by increment 2's offset shift).

2. **`reproduces_source(tree, content, spans) -> bool`** — the conversion guard. It serialises the tree (with the frontmatter it was given) and reports whether the result reproduces `content` modulo trailing whitespace. This is the honest boundary: the parser drops `hr`, `html_block` and link-reference definitions, nothing in the tree records them, and no serialiser can invent them back. Rather than converting lossily and telling nobody, Task 4 refuses conversion when this returns `False`.

   **Do not "fix" this by widening the comparison until it passes.** A tolerant comparison is exactly the silent loss the guard exists to prevent. The way to make more documents convertible is to make the *parser* preserve those shapes as blocks — a parser change, in increment 2's lane, not in this plan.

- [ ] **Step 2: Write the module**

```python
"""Serialise a block tree back into markdown source (spec §8.2, increment 8).

Block-first ingest's source-of-record producer: the block verbs are
authoritative and ``documents.content`` is a serialisation of the tree in
reading order. Because this pass writes the content, it knows the offset at
which every block landed — so ``char_span`` is recomputed here, in the same
pass, never dropped to NULL (the concession §8.2 explicitly retired). The
span convention matches the parser's: a block's span covers its own source
lines including its marker, and children claim their own lines.

Pure: no session, no I/O, no imports from the writer stack. `block_verbs`
owns every database write.
"""
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

__all__ = ["DEFAULT_LIST_MARKER", "PlacedBlock", "SerializedDocument",
           "TreeBlock", "derive_markers", "serialize_tree"]

DEFAULT_LIST_MARKER = "-"
_ORDERED_RE = re.compile(r"^\d+([.)])$")
_MARKER_RE = re.compile(r"^[ \t]*([-*+]|\d+[.)])[ \t]+")
_QUOTE_RE = re.compile(r"^[ \t]*(>)[ \t]?")


@dataclass(frozen=True)
class TreeBlock:
    id: UUID
    parent_id: UUID | None
    order_index: int
    type: str
    text: str
    properties: dict | None


@dataclass(frozen=True)
class PlacedBlock:
    block_id: UUID
    order_index: int
    char_span: tuple[int, int]


@dataclass(frozen=True)
class SerializedDocument:
    content: str
    placed: list[PlacedBlock]


def _children_map(blocks: Sequence[TreeBlock]):
    by_id = {b.id: b for b in blocks}
    children: dict[UUID | None, list[TreeBlock]] = defaultdict(list)
    for b in blocks:
        parent = b.parent_id if b.parent_id in by_id else None
        children[parent].append(b)
    for seq in children.values():
        seq.sort(key=lambda b: (b.order_index, str(b.id)))
    # Cycle guard: every block must be reachable from the roots exactly once.
    reachable: set[UUID] = set()
    stack = [b.id for b in children[None]]
    while stack:
        node = stack.pop()
        if node in reachable:
            raise ValueError(f"blocks.parent_id cycle at {node}")
        reachable.add(node)
        stack.extend(child.id for child in children.get(node, []))
    if len(reachable) != len(blocks):
        raise ValueError("blocks unreachable from any root: parent cycle")
    return children


def _marker_for(block: TreeBlock, ordinal: int) -> str:
    raw = (block.properties or {}).get("marker") or DEFAULT_LIST_MARKER
    m = _ORDERED_RE.match(raw)
    if m:
        return f"{ordinal}{m.group(1)}"
    return raw


def _fence_for(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def serialize_tree(blocks: Sequence[TreeBlock]) -> SerializedDocument:
    children = _children_map(blocks)
    out: list[str] = []
    placed: list[PlacedBlock] = []
    offset = 0
    walk = 0

    def write(piece: str) -> None:
        nonlocal offset
        out.append(piece)
        offset += len(piece)

    def emit_lines(lines: list[str], prefix: str) -> tuple[int, int]:
        start = offset
        for i, line in enumerate(lines):
            if i:
                write("\n")
            write(prefix + line if line else prefix.rstrip())
        return (start, offset)

    def emit(block: TreeBlock, prefix: str, ordinal: int) -> None:
        nonlocal walk
        props = block.properties or {}
        child_prefix = prefix
        if block.type == "heading":
            level = int(props.get("level") or 1)
            span = emit_lines([f"{'#' * level} {block.text}"], prefix)
        elif block.type == "code":
            fence = _fence_for(block.text)
            info = props.get("language") or ""
            span = emit_lines(
                [fence + info, *block.text.split("\n"), fence], prefix,
            )
        elif block.type == "quote":
            lines = block.text.split("\n") if block.text else []
            span = emit_lines([f"> {line}" for line in lines] or ["“"[:0] + ">"], prefix)
            child_prefix = prefix + "> "
        elif block.type == "list":
            marker = _marker_for(block, ordinal)
            lines = block.text.split("\n") if block.text else [""]
            indent = " " * (len(marker) + 1)
            span = emit_lines(
                [f"{marker} {lines[0]}", *(indent + l for l in lines[1:])], prefix,
            )
            child_prefix = prefix + indent
        elif block.type == "table":
            header = props.get("header") or [c.strip() for c in block.text.split("|")]
            aligns = props.get("alignments") or [None] * len(header)
            delim = {"left": ":---", "right": "---:", "center": ":---:"}
            span = emit_lines([
                "| " + " | ".join(header) + " |",
                "| " + " | ".join(delim.get(a or "", "---") for a in aligns) + " |",
            ], prefix)
        elif block.type == "table_row":
            cells = props.get("cells") or [c.strip() for c in block.text.split("|")]
            span = emit_lines(["| " + " | ".join(cells) + " |"], prefix)
        else:  # paragraph and anything normalised to it
            span = emit_lines(block.text.split("\n") if block.text else [""], prefix)

        placed.append(PlacedBlock(block.id, walk, span))
        walk += 1

        kids = children.get(block.id, [])
        list_ordinal = 0
        for i, kid in enumerate(kids):
            list_ordinal = list_ordinal + 1 if kid.type == "list" else 0
            write(_separator(block, kids, i))
            emit(kid, child_prefix, list_ordinal)

    def _separator(parent: TreeBlock | None, siblings: list[TreeBlock], index: int) -> str:
        current = siblings[index]
        if current.type == "table_row":
            return "\n"                    # rows are lines of their table
        if current.type == "list" and index > 0 and siblings[index - 1].type == "list":
            return "\n"                    # tight list
        if current.type == "list" and parent is not None and parent.type == "list":
            return "\n"                    # nested item under its parent item
        return "\n\n"

    roots = children[None]
    list_ordinal = 0
    for i, root in enumerate(roots):
        list_ordinal = list_ordinal + 1 if root.type == "list" else 0
        if i:
            write(_separator(None, roots, i))
        emit(root, "", list_ordinal)

    return SerializedDocument(content="".join(out), placed=placed)


def derive_markers(blocks: Sequence[TreeBlock], content: str | None) -> list[TreeBlock]:
    """Backfill the markers the parser discarded, from the stored source.

    The block-first conversion pass (spec §8.2's requirement): a `list` block
    does not record whether it was `-` or `1.`, so on the first block verb
    against a content-first document each list block's marker is read out of
    `content[char_span]`. `derive_markers` runs on the tree the caller loaded
    (which carries `char_span` slices into exactly that content); a block
    with no span, or a document with no stored content, falls back to the
    serialiser's defaults — deterministic, merely less faithful.
    Quote and heading markers need no record: `>` and ATX `#` are the only
    spellings the serialiser emits and the parser accepts round-trip.
    """
    ...
```

Notes for the implementer (the gaps to close, each pinned by a Step-1 test):
- `derive_markers` takes the tree as loaded by Task 4 (a parallel sequence of `(TreeBlock, char_span)` — choose the signature that fits Task 4's loader; the test adapts). Slice `content[lo:hi]`, match `_MARKER_RE`, and `replace(block, properties={**props, "marker": m.group(1)})` for list blocks.
- The `emit_lines` empty-line handling (`prefix.rstrip()`) keeps quote continuation honest (`>` alone on a blank quoted line).
- Where a Step-1 round-trip case disagrees with this sketch, **the test is the contract**: adjust the emit rule until `parse_markdown` agrees, and add the case to `ROUND_TRIP_SOURCES` if it is a new shape. Do not weaken `_skeleton` to make a case pass.

- [ ] **Step 3: Run**

`cd backend && .venv/bin/python -m pytest tests/test_block_serializer.py -q` — all green.

---

### Task 2: The direction flag — vocabulary first, then the put refusal

**Files:**
- Modify: `backend/app/services/events.py` (`EVENT_TYPES`, `backend/app/services/events.py:124-198`)
- Modify: `backend/app/services/document_door.py` (`put_document`, `backend/app/services/document_door.py:409`)
- Extend: `backend/tests/test_document_door.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `DIRECTION_KEY` / `BLOCK_FIRST` constants, `DocumentIsBlockFirst`, and the `blocks_edited` vocabulary entry Task 4 emits.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4
**Approach:** inline - skip 3: the spec (§8.2) fixes both halves — direction recorded on the row, put against block-first is a refusal.

- [ ] **Step 1: Vocabulary (taxonomy-first — this lands before any emitter)**

In `EVENT_TYPES`, after `"document_filed"`:

```python
    # Increment 8's block verbs (spec §8.2). One row per verb call; the
    # payload names the verb, the block id and the resulting content_hash and
    # carries NO block text — write-time minimization, stated here at the
    # vocabulary because the writer is in block_verbs.py.
    "blocks_edited",
```

- [ ] **Step 2: The refusal in the door**

In `document_door.py`, add beside the other exceptions and constants:

```python
# documents.properties key recording which ingest direction owns the row
# (spec §8.2). Absent or any other value = content-first (every document
# ever filed through put); "blocks" = the block verbs are authoritative and
# content is a serialisation. Server-owned: neither door accepts caller
# properties on put, and the block verbs merge it with jsonb `||` rather
# than writing properties wholesale.
DIRECTION_KEY = "ingest_direction"
BLOCK_FIRST = "blocks"


class DocumentIsBlockFirst(ValueError):
    """put refused: this document is owned by the block verbs (spec §8.2 —
    a content push over an editing session is a silent overwrite)."""


class DocumentNotConvertible(ValueError):
    """block verb refused: this content-first document contains source the
    parser does not represent as blocks (a thematic break, a raw HTML block
    or a link-reference definition), so converting it to block-first would
    regenerate `content` without them (review M-2, 2026-09-02).

    Spec section 4.5 promises generated-region markers survive in the stored
    raw content and section 8.2 promises a content-first document's content
    is never regenerated. Converting lossily would break both silently, on a
    corpus this programme exists to hold. Refusing is the honest outcome
    until the parser represents those shapes.
    """
```

In `put_document`, **inside** the `begin_nested` filing and after the document row has been resolved — not before it (review M-3, 2026-09-02). A `SELECT` before the savepoint is check-then-act: the block verbs can convert the document between this read and the put's own `_UPDATE_DOCUMENT`, which writes `properties` wholesale and would erase `ingest_direction` while `strip_blocks` deletes the rows an editing session just placed. That is the exact M1 race increment 3 spent its Task 3 closing, re-opened on the predicate that protects an editing session — and "unconditional rather than hash-gated" (this plan's own deviation note) is *weaker* here, not stronger, because a compare-and-set at least fails loudly.

So: take the row lock first, then read the direction under it.

```python
    # Review M-3: the lock is what makes the refusal a decision rather than
    # a guess. Both writers of this row take it as their first statement
    # inside the savepoint, so a conversion and a put serialise instead of
    # interleaving.
    await session.execute(
        text("SELECT id FROM documents WHERE id = CAST(:id AS uuid) FOR UPDATE"),
        {"id": str(document_id)},
    )
    direction = (
        await session.execute(_DIRECTION_SQL, {"project": project, "uri": uri})
    ).scalar_one_or_none()
    if direction == BLOCK_FIRST:
        raise DocumentIsBlockFirst(
            f"the document at uri {uri!r} in project {project!r} is "
            "block-first: its content is owned by the block verbs, and a "
            "content push would silently overwrite an editing session. "
            "Edit it through the block verbs, or delete and re-file it."
        )
```

with `_DIRECTION_SQL = text("SELECT properties->>'ingest_direction' FROM documents WHERE project = CAST(:project AS text) AND uri = CAST(:uri AS text)")`. The guard is the **door's**, deliberately — the same layer that owns `MAX_CONTENT_CHARS`/`MAX_BLOCKS`; `file_document` stays unguarded for in-process callers exactly as it is for the bounds.

A brand-new document has no row to lock, and that is correct rather than a hole: there is nothing to convert and nothing to overwrite, so the insert path skips both statements. Carry increment 3's discipline for the predicate that *is* on the write: where `_UPDATE_DOCUMENT` writes a content-first document, its `WHERE` also carries `AND COALESCE(properties->>'ingest_direction', '') <> 'blocks'`, and **zero rows updated is a refusal, not a success** — the same rowcount check increment 3's Task 3 established for `expected_hash`. Belt and braces on purpose: the lock orders the writers, the predicate means a missed lock still cannot overwrite.

**Note for the read-only worker (increment 7).** `FOR UPDATE` needs row-lock privilege beyond `SELECT`, so this statement fails under the `darkmem_viewer` role with SQLSTATE 42501 — which increment 7's global handler already maps to a 403. That is the correct behaviour (a put is a write and must refuse there), but it means `document_door` is a **writer** module for the purposes of increment 7's Task 5 `FOR UPDATE` scan and must not be listed among the pure-read modules that assert no row locks. Increment 7's plan has been corrected accordingly; if that correction is missing when this lands, fix it there rather than dropping the lock here.

- [ ] **Step 3: Tests**

In `test_document_door.py`: a document whose properties carry `{"ingest_direction": "blocks"}` (write it with raw SQL in the fixture — Task 4's verbs do it for real) refuses `put_document` with `DocumentIsBlockFirst` and leaves content, hash and blocks untouched; a content-first document (flag absent) still puts normally; `"blocks_edited" in EVENT_TYPES`. Run the file green, then full `pytest -q`.

---

### Task 3: Block-scoped provenance withdrawal

**Files:**
- Modify: `backend/app/services/block_fact_sources.py`
- Modify: `backend/app/services/document_door.py` (extract the expiry tail of `delete_document`, `backend/app/services/document_door.py:548-586`)
- Extend: `backend/tests/test_block_fact_sources.py`, `backend/tests/test_document_door.py`

**Interfaces:**
- Consumes: the shipped `fact_sources` shapes (`BLOCK_SOURCE_KIND`, `_DELETE_SOURCES_SQL`).
- Produces: `withdraw_blocks(session, *, block_ids)` and `expire_facts_left_bare(session, withdrawal, *, document_id)` — Task 4's delete path.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5
**Approach:** inline - skip 3: doc 16 §5's one-origin-per-document rule and `delete_document`'s existing tail fix the behaviour; this task only re-scopes and factors it.

- [ ] **Step 1: Generalise the withdrawal**

`blocks.id` is `fact_sources.source_ref` for block-kind sources and carries **no FK**, so deleting a block row (Task 4's `block_delete`, cascading its subtree) would leave a fact corroborated by evidence that no longer exists — the exact window `delete_document` already closes at document scope. In `block_fact_sources.py`:

```python
async def withdraw_blocks(
    session: AsyncSession, *, block_ids: Sequence[str]
) -> BlockWithdrawal:
    """Withdraw the block-kind sources for exactly these blocks.

    The subtree half of `withdraw_document`: a `block_delete` removes one
    subtree, not the document, and only that subtree's provenance goes.
    """
```

— the `_DELETE_SOURCES_SQL` call with the given ids, returning the same `BlockWithdrawal` shape. Re-implement `withdraw_document` as: resolve the document's block ids (`_DOCUMENT_BLOCKS_SQL`), delegate to `withdraw_blocks`. Behaviour identical; every existing test must stay green unmodified.

- [ ] **Step 2: Extract the expiry tail**

The body of `delete_document` between the withdrawal and the `_DELETE_DOCUMENT` execute (`document_door.py:550-586` — the `_STILL_SOURCED` probe, the `expire` of facts left bare and not already expired, and the per-fact `sources_changed` journal) becomes a module-level function:

```python
async def expire_facts_left_bare(
    session: AsyncSession, withdrawal: BlockWithdrawal, *, document_id: str
) -> None:
```

`delete_document` calls it; Task 4's `block_delete` calls it with the same document id (origin for a block source is the document — `block_fact_sources.py`'s own rule — so the payload spelling is already right). Neither writes `verification_status`; the rung stays the ladder's (the repository-method allowlist scan, `test_block_retrieval.py:477`, enforces this for every block-channel module including the new ones).

- [ ] **Step 3: Tests**

`test_block_fact_sources.py`: `withdraw_blocks` removes only the named blocks' sources and leaves a sibling block's source standing; `withdraw_document` still withdraws all. `test_document_door.py`: `delete_document`'s behaviour byte-identical through the extraction (existing tests are the proof; run them unmodified). Full `pytest -q` green.

---

### Task 4: The four verbs — one service, one placement pass

**Files:**
- Create: `backend/app/services/block_verbs.py`
- Create: `backend/tests/test_block_verbs.py`
- Modify: `backend/tests/test_block_retrieval.py` (`BLOCK_CHANNEL_MODULES` += `app.services.block_verbs`, `app.services.block_serializer` — `backend/tests/test_block_retrieval.py:345`)
- Modify: `backend/tests/test_block_pipeline.py` (`FILING_CLOSURE` seeds += `"app.services.block_verbs"` — `backend/tests/test_block_pipeline.py:792`)

**Interfaces:**
- Consumes: Task 1's `serialize_tree`/`derive_markers`, Task 2's flag constants, Task 3's `withdraw_blocks`/`expire_facts_left_bare`, `embed_blocks` (`backend/app/services/block_embeddings.py:81`), `compute_content_hash`, `normalize_block_type`, `record_event`.
- Produces: `update_block`, `insert_block`, `move_block`, `delete_block`, `BlockWriteResult`, `BlockTargetUnresolved`, `BlockCycleError` — both doors' one service layer.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5
**Approach:** inline - skip 3: the spec (§8.1-8.2) fixes the verb set, the id-addressed no-diffing model and the regenerate-on-every-mutation rule; the shared `_mutate` pass below is that decision written down.

- [ ] **Step 1: Write the failing tests**

`test_block_verbs.py`, driving everything through a document filed with `put_document` first (real parse, real spans), then the verbs. Name at least:

```python
async def test_update_regenerates_content_hash_and_every_span(session, llm)
    # file "# T\n\npara one\n\npara two"; update the middle block's text to be
    # longer; assert: documents.content re-serialised, content_hash ==
    # compute_content_hash(content), the LAST block's char_span shifted by
    # exactly the length delta, and content[span] slices each block's own
    # source back out.

async def test_update_preserves_every_other_blocks_id(session, llm)
    # the anti-strip-and-rewrite property: ids before == ids after, minus none.

async def test_first_verb_converts_and_derives_markers(session, llm)
    # file "* star\n\n1) one\n2) two" content-first; update one block;
    # assert properties.ingest_direction == "blocks" on the document,
    # frontmatter keys (if any) survived (jsonb merge, not wholesale), and
    # the regenerated content still spells "*" and "1)".

async def test_put_refuses_after_conversion(session, llm)          # 409 seam
async def test_insert_after_and_first_child_positions(session, llm)
async def test_insert_normalises_an_unknown_type(session, llm)     # "h2" -> heading
async def test_move_reparents_and_reorders(session, llm)
async def test_move_into_own_subtree_refuses(session, llm)         # BlockCycleError
async def test_delete_takes_the_subtree_and_its_provenance(session, llm)
    # seed a fact_sources row (BLOCK_SOURCE_KIND, source_ref=a child block id);
    # delete the parent; assert the source row is gone, the bare fact expired,
    # one sources_changed event journalled — Task 3's tail through this door.

async def test_each_verb_journals_blocks_edited_without_text(session, llm)
async def test_update_embeds_only_the_touched_block(session, llm)  # spy embed_blocks
async def test_a_verb_on_a_missing_block_refuses(session, llm)     # BlockTargetUnresolved
async def test_serialised_content_over_the_bound_refuses_and_rolls_back(session, llm)
```

- [ ] **Step 2: Write the module**

```python
"""The block verbs — block-first ingest's write half (spec §8, increment 8).

Four verbs, both doors, one service layer (invariant 17). The client holds
block ids (it fetched the blocks), so every verb addresses a real id and
there is no diffing and no matching heuristic.

Every mutation runs the same pass: load the tree, apply one change in
memory, serialise (Task 1's `serialize_tree`), and write the result — the
per-block placement (order_index + char_span) in ONE bulk statement, the
document row's content/content_hash/direction flag in another. Blocks that
did not change keep their ids and their vectors; only an updated or inserted
block re-embeds, after commit, the door's own embed posture.

Cost model, stated: one edit is O(document) placement rows in one UPDATE
plus one document-row write and at most one single-block embed. The spec's
"O(siblings)" line described a sibling-scoped order_index this schema does
not have — order_index is the global reading order the readers sort by.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import embed_blocks
from app.services.block_fact_sources import withdraw_blocks
from app.services.block_serializer import (
    SerializedDocument, TreeBlock, derive_markers, serialize_tree,
)
from app.services.document_door import (
    BLOCK_FIRST, DIRECTION_KEY, MAX_BLOCKS, MAX_CONTENT_CHARS,
    DocumentTooLarge, expire_facts_left_bare,
)
from app.services.document_ingest import compute_content_hash
from app.services.events import record_event
from app.taxonomy import normalize_block_type
from app.utils.ids import new_id

__all__ = [
    "BlockCycleError", "BlockTargetUnresolved", "BlockWriteResult",
    "delete_block", "insert_block", "move_block", "update_block",
]

BLOCKS_EDITED_EVENT = "blocks_edited"


class BlockTargetUnresolved(ValueError):
    """Nothing the caller named resolves to a block that exists."""


class BlockCycleError(ValueError):
    """A move that would make a block its own ancestor."""


@dataclass(frozen=True)
class BlockWriteResult:
    document_id: str
    block_id: str | None
    outcome: str            # updated | inserted | moved | deleted
    content_hash: str
    blocks_total: int
    blocks_embedded: int


_RESOLVE_BLOCK = text(
    "SELECT CAST(document_id AS text) AS document_id FROM blocks "
    "WHERE id = CAST(:id AS uuid)"
)
_DOC_META = text(
    "SELECT project, content, properties->>'ingest_direction' AS direction, "
    "       properties->>'frontmatter' AS frontmatter "
    "FROM documents WHERE id = CAST(:id AS uuid)"
)
_LOAD_TREE = text(
    "SELECT id, parent_id, order_index, type, text, properties, "
    "       lower(char_span) AS lo, upper(char_span) AS hi "
    "FROM blocks WHERE document_id = CAST(:id AS uuid) ORDER BY order_index"
)
_PLACE = text(
    """
    UPDATE blocks b
    SET order_index = u.ord,
        char_span = CAST(CAST(u.span AS text) AS int4range),
        properties = CAST(u.props AS jsonb),
        parent_id = CAST(u.parent AS uuid)
    FROM (SELECT unnest(CAST(:ids AS uuid[])) AS id,
                 unnest(CAST(:ords AS integer[])) AS ord,
                 unnest(CAST(:spans AS text[])) AS span,
                 unnest(CAST(:props AS text[])) AS props,
                 unnest(CAST(:parents AS text[])) AS parent) u
    WHERE b.id = u.id
    """
)
# Review M-8, 2026-09-02: `parent_id` is the fourth unnest and it is not
# optional. Without it the only statement writing parent_id is _UPDATE_BLOCK,
# which runs only for verb == "updated", so move_block reordered its target
# without ever reparenting it -- the verb silently did half its job. The
# placement pass already rewrites the whole document's order and spans, so
# carrying parentage in the same statement is both correct and free. NULL
# parents ride as NULL through the text[] cast (root-level blocks).
_INSERT_BLOCK = text(
    "INSERT INTO blocks (id, document_id, parent_id, order_index, type, text, properties) "
    "VALUES (CAST(:id AS uuid), CAST(:doc AS uuid), CAST(:parent AS uuid), "
    "        :ord, CAST(:type AS text), CAST(:text AS text), CAST(:props AS jsonb))"
)
_UPDATE_BLOCK = text(
    "UPDATE blocks SET type = CAST(:type AS text), text = CAST(:text AS text), "
    "parent_id = CAST(:parent AS uuid) WHERE id = CAST(:id AS uuid)"
)
_DELETE_BLOCK = text("DELETE FROM blocks WHERE id = CAST(:id AS uuid)")
_WRITE_DOC = text(
    """
    UPDATE documents
    SET content = CAST(:content AS text),
        content_hash = CAST(:hash AS text),
        properties = COALESCE(properties, '{}'::jsonb)
                     || jsonb_build_object('ingest_direction', 'blocks')
    WHERE id = CAST(:id AS uuid)
    """
)
```

The shared pass (private; each verb builds a mutation closure over the loaded tree):

```python
async def _mutate(session, llm, *, document_id, apply, touched_embed, verb, block_id):
    # Review M-3: lock the document row before reading anything off it. The
    # whole pass -- load tree, serialise in Python across awaits, place rows
    # -- is a read-modify-write, and put_document takes the same lock, so the
    # two serialise instead of interleaving into a tree whose blocks were
    # stripped underneath it.
    async with session.begin_nested():
        await session.execute(
            text("SELECT id FROM documents WHERE id = CAST(:id AS uuid) FOR UPDATE"),
            {"id": document_id},
        )
        return await _mutate_locked(
            session, llm, document_id=document_id, apply=apply,
            touched_embed=touched_embed, verb=verb, block_id=block_id,
        )


async def _mutate_locked(session, llm, *, document_id, apply, touched_embed, verb, block_id):
    meta = (await session.execute(_DOC_META, {"id": document_id})).mappings().first()
    if meta is None:
        raise BlockTargetUnresolved("document not found")
    rows = (await session.execute(_LOAD_TREE, {"id": document_id})).mappings().all()
    tree = [TreeBlock(r["id"], r["parent_id"], r["order_index"], r["type"],
                      r["text"] or "", r["properties"]) for r in rows]
    spans = {r["id"]: (r["lo"], r["hi"]) for r in rows
             if r["lo"] is not None and r["hi"] is not None}

    if meta["direction"] != BLOCK_FIRST and meta["content"]:
        # Conversion pass. Review M-2: refuse rather than convert when the
        # serialiser cannot reproduce the stored source -- the parser drops
        # hr, html_block and link-reference definitions, and regenerating
        # content without them is silent loss on exactly the corpus this
        # programme exists to hold.
        tree = derive_markers(tree, meta["content"], spans)
        if not reproduces_source(tree, meta["content"], spans,
                                 frontmatter=meta["frontmatter"]):
            raise DocumentNotConvertible(
                "this document contains source the block editor cannot "
                "represent (a thematic break, a raw HTML block or a link "
                "reference definition). Editing it as blocks would rewrite "
                "the file without them. Edit it with document_put instead."
            )

    tree, inserted, deleted_subtree = apply(tree)             # in-memory mutation

    # Frontmatter rides every serialisation, not only the conversion: an
    # ordinary edit of an already-block-first document would otherwise drop
    # the fence on the first save (review M-2).
    result = serialize_tree(tree, frontmatter=meta["frontmatter"])
    if len(result.content) > MAX_CONTENT_CHARS:
        raise DocumentTooLarge(...)
    if len(tree) > MAX_BLOCKS:
        raise DocumentTooLarge(...)
    content_hash = compute_content_hash(result.content)

    async with session.begin_nested():
        if deleted_subtree:
            withdrawal = await withdraw_blocks(
                session, block_ids=[str(b) for b in deleted_subtree])
            await expire_facts_left_bare(session, withdrawal, document_id=document_id)
            await session.execute(_DELETE_BLOCK, {"id": str(deleted_subtree[0])})
            # the root of the subtree; parent_id ON DELETE CASCADE takes the
            # rest, and block_embeddings__<slug> cascades in every partition
            # (invariant 2)
        if inserted is not None:
            await session.execute(_INSERT_BLOCK, {...})
        if verb == "updated":
            await session.execute(_UPDATE_BLOCK, {...})
        await session.execute(_PLACE, {...from result.placed and tree properties...})
        await session.execute(_WRITE_DOC, {
            "id": document_id, "content": result.content, "hash": content_hash,
        })
        await record_event(
            session, event_type=BLOCKS_EDITED_EVENT, object_type="document",
            object_id=UUID(document_id), project=meta["project"],
            payload={"verb": verb, "block_id": block_id,
                     "blocks_total": len(tree), "content_hash": content_hash},
        )
    await session.commit()

    written = 0
    if touched_embed is not None:
        embed = await embed_blocks(session, llm, block_ids=[touched_embed])
        written = embed.written if embed else 0
        await session.commit()

    return BlockWriteResult(document_id, block_id, verb, content_hash,
                            len(tree), written)
```

The four public verbs:

```python
async def update_block(session, llm, *, block_id, text, type=None, properties=None) -> BlockWriteResult
async def insert_block(session, llm, *, document_id, type, text,
                       parent_id=None, after_block_id=None, properties=None) -> BlockWriteResult
async def move_block(session, *, block_id, new_parent_id=None, after_block_id=None) -> BlockWriteResult
async def delete_block(session, *, block_id) -> BlockWriteResult
```

Semantics each closure implements against the in-memory tree:
- **update**: replace text (and type via `normalize_block_type` when given; merge `properties`). Refuse a missing id (`BlockTargetUnresolved`). Embed the block.
- **insert**: mint `new_id()`, type normalised; position = after `after_block_id` among the target parent's children, or first child when `None`; `parent_id=None` = root level. `after_block_id` not a child of the target parent → `BlockTargetUnresolved`. Embed the new block.
- **move**: reparent + reposition; `new_parent_id` inside the moved block's own subtree → `BlockCycleError`. No embed (text unchanged). **Its test must re-read the row from the database and assert `parent_id` actually changed**, not merely that the verb returned a result — the defect this fixes (M-8) would have passed any assertion made against the returned object or the in-memory tree.
- **delete**: remove the subtree (computed from the loaded tree, root-first list handed to the withdrawal). No embed; the FK cascades take rows and vectors.
- **resolution**: `update`/`move`/`delete` resolve `document_id` through `_RESOLVE_BLOCK`; a miss is `BlockTargetUnresolved`.

`_PLACE`'s `props` array carries each block's (possibly marker-backfilled) properties as JSON text — the conversion writes markers in the same bulk statement; blocks with unchanged properties round-trip their own value. Its `parents` array carries every block's parentage from the mutated in-memory tree, which is what makes `move_block` actually persist (review M-8); `_UPDATE_BLOCK` keeps writing `parent_id` too, harmlessly, since both derive from the same tree.

- [ ] **Step 3: Classify the new modules in the firewall scans — same task, not a follow-up**

- `test_block_retrieval.py:345`: `BLOCK_CHANNEL_MODULES` += `"app.services.block_verbs"`, `"app.services.block_serializer"`. The vault-method allowlist scan now covers both automatically; `block_verbs` names only `expire` through Task 3's helper, which the allowlist already carries.
- `test_block_pipeline.py:792`: `FILING_CLOSURE = import_closure(BACKEND, "app.services.block_pipeline", DOCUMENT_DOOR, "app.services.block_verbs")` — the verbs' closure must not reach `process_batch` either.

- [ ] **Step 4: Run**

`cd backend && .venv/bin/python -m pytest tests/test_block_verbs.py tests/test_block_retrieval.py tests/test_block_pipeline.py -q`, then full `pytest -q`.

---

### Task 5a: Serve `properties` and each block's own source on the block read

**Files:**
- Modify: `backend/app/services/document_door.py` (`BlockRow`, `_BLOCKS`, `document_blocks`)
- Modify: `backend/app/api/routes/documents.py` (`BlockRowModel`)
- Modify: `backend/tests/test_document_door.py`, `backend/tests/test_document_routes.py`, `backend/tests/test_mcp.py`

**Interfaces:**
- Produces: `BlockRow.properties` and `BlockRow.source`, on both doors through the one service read — consumed by Task 8's editor and by increment 4's table render.

**Implementer:** dcc-superpower-companions:impl-sonnet-medium

**Why this task exists** (cross-plan review M-7, 2026-09-02). This plan's header claims "storage format and edit format being identical is what removes the conversion step where round-trip fidelity dies". That claim is false at block granularity as the plan stood, and Task 8 proved it by hand-rolling a promotion regex — which *is* a conversion step:

- `blocks.text` is stored **marker-stripped** (`document_parsers.py:25-31`): a level-2 heading's text is `Foo`, not `## Foo`.
- `properties` — which carries `level` for headings, `marker` for list items, and increment 2's `{header, alignments}` / `{cells}` for tables — is on **neither** read surface (`BlockRow`, `document_door.py:601-606`; `BlockRowModel`, `routes/documents.py:246-251`).

So the editor could not show a heading's level or a list's marker, had no way to demote a heading back to a paragraph, and increment 4 could not render tables through the library `table` component the spec §2 requires. One additive read closes all three.

- [ ] **Step 1: Failing tests.** `properties` round-trips on the blocks read for a heading (`{"level": 2}`) and a list item with a marker; `source` for each block equals `content[char_span]` exactly, including its marker; `source` is `None` when the document has no `content` (a bytes-filed row) or the block has no span; the MCP `document_blocks` payload carries both fields.

- [ ] **Step 2: Implement.** Add `properties: dict | None` and `source: str | None` to `BlockRow` and `BlockRowModel`. `_BLOCKS` gains `properties` and joins the document's `content` so `source` is sliced server-side from `char_span` — the caller must never have to fetch the whole document and slice it itself, which would make every editor keystroke depend on a second read. One service function, both doors (invariant 17); no new route and no new tool, so `PARITY_TABLE` does not move and `sdks/generate.py` stays a zero-diff check.

- [ ] **Step 3:** `pytest tests/test_document_door.py tests/test_document_routes.py tests/test_mcp.py -q`, then full `pytest -q`.

**This also closes increment 4's recorded deviation** (its Task 5 Step 1 note): with `properties` served, `table` can render through the library component as spec §2 says. Landing this before increment 4's UI work is not required, but whoever lands it should strike that deviation note.

---

### Task 5: The REST door

**Files:**
- Modify: `backend/app/api/routes/documents.py`
- Modify: `backend/tests/test_api/test_rest_conformance.py` (`EXPECTED_STATUS`, `backend/tests/test_api/test_rest_conformance.py:42`)
- Extend: `backend/tests/test_document_routes.py`

**Interfaces:**
- Consumes: Task 4's verbs, Task 2's `DocumentIsBlockFirst`.
- Produces: the four routes and `BlockWriteResponse`.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Routes** (per `docs/api-rest-conventions.md`: 201 create, 204 delete, `PATCH` partial update, verb-shaped POST for move — the `/runs/{id}/rerun` precedent):

```python
class BlockInsertRequest(BaseModel):
    type: str = Field(min_length=1)
    text: str
    parent_id: str | None = None
    after_block_id: str | None = None
    properties: dict | None = None

class BlockUpdateRequest(BaseModel):
    text: str
    type: str | None = None
    properties: dict | None = None

class BlockMoveRequest(BaseModel):
    new_parent_id: str | None = None
    after_block_id: str | None = None

class BlockWriteResponse(BaseModel):
    document_id: str
    block_id: str | None
    outcome: str
    content_hash: str
    blocks_total: int
    blocks_embedded: int
    horizon: bool = True
```

```
POST   /api/v1/documents/{document_id}/blocks                  → 201, insert_block
PATCH  /api/v1/documents/{document_id}/blocks/{block_id}       → 200, update_block
POST   /api/v1/documents/{document_id}/blocks/{block_id}/move  → 200, move_block
DELETE /api/v1/documents/{document_id}/blocks/{block_id}       → 204, delete_block
```

Each keyed handler first confirms the block belongs to the path's document (the service resolves the block's own document; a mismatch is the same 404 as a missing block — a block in another document does not exist *at this path*). Exception mapping: `BlockTargetUnresolved` → 404, `BlockCycleError` → 422, `DocumentTooLarge` → 422. And on the existing put route: `DocumentIsBlockFirst` → **409** (the conventions' conflict shape, the same status §5.3's CAS uses).

- [ ] **Step 2: Conformance table**

`EXPECTED_STATUS` += the four rows above (201/200/200/204). The enumeration-driven test fails without them — that failure is the reminder, not an obstacle.

- [ ] **Step 3: Route tests**

`test_document_routes.py`: one happy path per verb through the HTTP client (insert returns the minted id; update returns the new hash; delete 204 then the block 404s on read), the 409 on put-against-block-first, the 404 on cross-document block addressing. Run the file, then `pytest -q`.

---

### Task 6: The MCP door, scopes and the parity row

**Files:**
- Modify: `backend/app/api/mcp/server.py` (after the document tools, `backend/app/api/mcp/server.py:607-800`)
- Modify: `backend/app/api/mcp/scopes.py` (`CAPTURE_TOOLS`, `backend/app/api/mcp/scopes.py:46-55`; the "names all 34" docstring at `scopes.py:21`)
- Modify: `backend/tests/test_door_parity.py` (`PARITY_TABLE`) and regenerate `docs/two-door-parity.md`
- Modify: `backend/tests/test_mcp_auth.py` (the "all 34" docstring at `backend/tests/test_mcp_auth.py:395`; the scope-total assertion at `:421` derives and needs no edit)

**Interfaces:**
- Consumes: Task 4's verbs.
- Produces: `block_update` / `block_insert` / `block_move` / `block_delete` tools, capture-scoped.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Four tools**, each the thin twin of its REST route, session posture identical to `document_put` (`server.py:614-650` — own session, rollback on raise, `json.dumps(vars(result))`). Signatures mirror the service: `block_update(block_id, text, type=None, properties=None)`, `block_insert(document_id, type, text, parent_id=None, after_block_id=None, properties=None)`, `block_move(block_id, new_parent_id=None, after_block_id=None)`, `block_delete(block_id)`. No `ctx`/`source` resolution — the verbs journal `blocks_edited` themselves and the editor's identity question is the session's, not a capture header's. Tool descriptions state the direction rule ("only for block-first documents; a document filed with document_put converts on the first block verb, after which document_put refuses it").

- [ ] **Step 1b: The two refusals need MCP wire shapes, not just REST status codes** (cross-plan review M-4, 2026-09-02)

`DocumentIsBlockFirst` gets a 409 on REST (Task 5) and, as this plan stood, **nothing on MCP**: increment 3's `document_put` tool catches `DocumentHashConflict` into a `hash_conflict` envelope and re-raises everything else (`server.py:641-649` as amended by increment 3), so the agent — the caller most likely to hit this, since these tools are capture-scoped — would get an unstructured tool error where the SPA gets a structured 409. Increment 3's own argument for the envelope applies verbatim: the caller made no mistake, it lost a race, and it should be able to machine-read the outcome and recover.

Add to increment 3's `document_put` try/except, beside `hash_conflict`:

```python
        except DocumentIsBlockFirst as exc:
            await session.rollback()
            return json.dumps({
                "status": "direction_conflict",
                "document_uri": uri,
                "project": project,
                "reason": str(exc),
            })
```

and give the four block tools the same treatment for `DocumentNotConvertible`, whose REST twin is a 409 too:

```python
        except DocumentNotConvertible as exc:
            await session.rollback()
            return json.dumps({
                "status": "not_convertible", "block_id": block_id,
                "reason": str(exc),
            })
```

Both refusals are outcomes a caller should handle, not crashes. Task 5 carries the REST halves (`DocumentIsBlockFirst` → 409, `DocumentNotConvertible` → 409 with a detail naming what the document contains), and the parity row in Step 3 states **both** wire shapes rather than only the route's.

- [ ] **Step 2: Scopes.** `CAPTURE_TOOLS` += the four (capture is the writer scope; these are writers). Update `scopes.py:21`'s docstring count (34 → 38), **and the second occurrence in the same file at `scopes.py:10`** — "one such call as the first statement of all 34 tools - is 34 chances to omit one" — which this plan missed (review m-2, 2026-09-02); both numbers move together. Then `test_mcp_auth.py:395`'s docstring likewise. All three are invariant-23 "full list" sentences whose referent moves here. The derived assertion at `:421` passes untouched, which is the point of deriving it.

- [ ] **Step 3: Parity.** Add one `PARITY_TABLE` row — surface `documents.block_write`, REST = the four routes, MCP = the four tools, status two-door, note stating: one service (`block_verbs`), the direction refusal on put, and the wire asymmetry (REST delete answers 204 with no body; `block_delete` answers the full result object — the same delete asymmetry the `documents.write` row already records). Regenerate the markdown:

```bash
cd backend && .venv/bin/python -c \
  "from tests.test_door_parity import render_markdown; print(render_markdown())"
```

and update the hand-maintained headline above the generated region — which is at **`docs/two-door-parity.md:13`**, not `:14` (review m-14).

**Do not write the literal numbers this plan originally gave** (72 → 73, 23 → 24). They were computed against the tree as it stood before increments 6 and 7 were planned, and **both of those add a REST-only surface** (`config.backup_destinations` and `backups.inventory`). Whichever of the three lands last would have written a headline that disagrees with the table above it, and `test_the_committed_table_reports_its_own_counts` (`test_door_parity.py:1851-1875`) fails on exactly that. It derives the expected string from `PARITY_TABLE` and prints it, so: run the test, read the headline out of the failure message, paste it in. That is the only correct source for the number regardless of landing order.

- [ ] **Step 4:** `pytest tests/test_door_parity.py tests/test_mcp_auth.py -q`, then full `pytest -q`.

---

### Task 7: Frontend block mutations

**Files:**
- Create: `frontend/src/hooks/api/use-blocks-api.ts` (export from `frontend/src/hooks/api/index.ts`)

**Interfaces:**
- Consumes: Task 5's routes.
- Produces: the four mutation hooks Task 8 consumes.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1

- [ ] **Step 1:**

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface BlockWriteResponse {
  document_id: string
  block_id: string | null
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

/** All four invalidate the document's blocks and outline — the serialiser
 *  moved every span, so a partial cache is a wrong cache. */
function useBlockMutation<V>(fn: (v: V) => Promise<BlockWriteResponse | void>, documentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["documentBlocks", documentId] })
      void qc.invalidateQueries({ queryKey: ["documentOutline", documentId] })
      void qc.invalidateQueries({ queryKey: ["documentsAll"] })
    },
  })
}

export function useBlockUpdate(documentId: string) {
  return useBlockMutation(
    (v: { block_id: string; text: string; type?: string }) =>
      apiFetch<BlockWriteResponse>(`/documents/${documentId}/blocks/${v.block_id}`, {
        method: "PATCH", body: JSON.stringify({ text: v.text, type: v.type }),
      }),
    documentId,
  )
}

export function useBlockInsert(documentId: string) { /* POST .../blocks */ }
export function useBlockMove(documentId: string)   { /* POST .../blocks/{id}/move */ }
export function useBlockDelete(documentId: string) { /* DELETE .../blocks/{id} */ }
```

(The three siblings follow the same shape; delete's `apiFetch` returns void on 204.) Mutations need no `enabled: !DEMO` — they only fire from user action on a surface demo mode never arms — but Task 9 must not render the editor affordances in demo mode.

- [ ] **Step 2:** `npm run typecheck`; a hooks test asserting the invalidation keys fire on success.

---

### Task 8: The block editor

**Files:**
- Create: `frontend/src/features/documents/components/block-editor.tsx`
- Extend: `frontend/src/features/documents/__tests__/`

**Interfaces:**
- Consumes: increment 4's `BlockView` (pure `{type, text}` render), Task 5a's `source`/`properties` fields, Task 7's mutations, darkraise-ui `textarea`.
- Produces: `BlockEditor` — Task 9 mounts it.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: §8.3 took the editor decision (markdown-source blocks, no framework) and this plan's header restates the accepted ceiling; only interaction details are left.

- [ ] **Step 1:** `BlockEditor({ documentId, blocks })` renders the ordered block list. Per block:

- **Unfocused:** `BlockView` inside a click-target that sets focus. The storage format *is* the edit format — no conversion anywhere (§8.3's whole argument).
- **Focused:** darkraise-ui `textarea` (read `textarea.d.ts`; auto-grow if the props offer it, else rows from line count) holding **`block.source`** — the block's actual markdown source, marker included, served by Task 5a. Fall back to `block.text` only when `source` is `null` (a bytes-filed document, or a block with no span).

  **This is the correction that makes §8.3's central claim true** (review M-7, 2026-09-02). `blocks.text` is stored marker-*stripped* — a level-2 heading's text is `Foo`, not `## Foo` — so a textarea holding `block.text` is not the storage format, and the plan's "storage format and edit format being identical means there is no conversion step" was false at block granularity. Editing the real source removes the conversion instead of relocating it into the client.

- **Commit** (blur, `Escape`, or `Ctrl/Cmd+Enter`): if the source changed, run the type-promotion pass then `useBlockUpdate`. The promotion regexes mirror the serialiser's emit rules exactly, nothing more: leading `#{1,6} ` → `heading` with `properties: {level: n}`; leading `- ` / `* ` / `+ ` / `\d+[.)] ` → `list` with `properties.marker`; leading `> ` → `quote`; a ``` fence → `code`; **no marker → `paragraph`**, which is what makes a heading demotable — deleting the `## ` now demotes the block, where under the old design the marker was never shown and so could never be deleted. Send `text` as the marker-stripped remainder, matching how the parser stores it, so the server-side round trip is unchanged.

  This client-side promotion mirrors Python emit rules and is a real duplication; say so in a comment naming `block_serializer.py` as the authority, and pin it with a test over the same fixture strings the serialiser's own tests use, so a change on one side fails loudly on the other.
- **`Ctrl/Cmd+Enter` additionally** inserts a new empty `paragraph` block after the current one (`useBlockInsert` with `after_block_id`) and focuses it.
- **`Backspace` on an empty focused block**: `useBlockDelete`, focus the previous block.
- **`ArrowUp`/`ArrowDown`** at the textarea's first/last line: move focus between blocks.
- **While a mutation is in flight**, keep the textarea enabled with the local value (optimistic locally; the invalidation refreshes spans and order underneath). Surface a failed mutation inline under the block ("the edit was not saved — {message}") — never silently drop keystrokes.

- [ ] **Step 2: Tests.** Mock the mutation hooks: focusing a heading block puts `## Foo` in the textarea (from `source`, not `Foo` from `text`); commit-on-blur fires update with the promotion applied (`# Foo` → `{type:"heading", text:"Foo", properties:{level:1}}`); **deleting the marker demotes** (`Foo` alone → `{type:"paragraph", text:"Foo"}`); Ctrl+Enter fires insert-after; Backspace-on-empty fires delete; an unchanged blur fires nothing. `npm test -- block-editor && npm run typecheck`.

---

### Task 9: The personal workspace — edit mode, new pages, uri nesting

**Files:**
- Modify: `frontend/src/features/documents/components/documents-view.tsx`
- ~~Modify: `frontend/src/features/documents/components/document-tree.tsx`~~ — **not modified** (review m-9, 2026-09-02). Increment 4 already renders `nodeActions?.(node)`; the *consumer* that passes the slot is `documents-view.tsx`, which is the file this task edits. Listing the tree as Modify contradicted this plan's own "nothing is rewritten" promise (Prerequisites 2) and would have invited an implementer to edit a component increment 4 owns.
- Extend: `frontend/src/features/documents/__tests__/documents.real.test.tsx`

**Interfaces:**
- Consumes: Tasks 7-8, increment 4's tree/reader, `useGroundedQa`'s existing put-shaped sibling — plus one new tiny mutation for `document_put` (add `useDocumentPut()` to `use-documents-api.ts`: `POST /documents`, body `{project, uri, content, title?}`).
- Produces: the editable personal surface.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: §8.3 fixed nesting as uri-derived and the tree as increment 4's grouping; what remains is wiring.

- [ ] **Step 1: Edit mode.** On the personal surface (`project="default"` only — the project workspace stays read-only; state that in a code comment where the mode is gated), a selected document shows a Read / Edit toggle (darkraise-ui `segment-group` or `toggle-group`): Read mounts `DocumentReader`, Edit mounts `BlockEditor`. Hidden entirely in demo mode.

- [ ] **Step 2: New page and subpage — nesting is the uri path, nothing else (§8.3).**

- Tree `nodeActions`: on a folder node, a "new subpage" action; above the tree, a "new page" action.
- Both prompt for a title, slugify it (`lower, spaces→-, strip non [a-z0-9-]`), and `document_put` at `` `${prefix}${slug}.md` `` — the parent's `node.path` plus `/` for a subpage, `notes/` for a root page — with content `` `# ${title}` ``. Then select the new document and enter Edit mode; the first committed edit converts it block-first server-side. No parent column, no page-ref block, no schema: creating a subpage **is** assigning a uri under the parent's prefix.
- A put refused with 409 (uri already taken by a block-first document) surfaces its message inline; do not retry, do not overwrite.

- [ ] **Step 3: Tests + full check.** Extend `documents.real.test.tsx`: toggle mounts the editor; the new-subpage action puts at the prefixed uri. `cd frontend && npm test && npm run typecheck && npm run build`.

---

### Task 10: The stale-count and contract docs move with their referents

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/agent-conventions.md` (created by increment 5's plan; skip the file gracefully if that increment has not landed, and say so in the report)

**Interfaces:**
- Consumes: the landed surface (Tasks 4-6).
- Produces: contract prose that matches the tree (invariant 23).

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 1 - spec 1 - coupling 0 - risk 0 = 2

- [ ] **Step 1: CLAUDE.md, MCP endpoint section.** "capture covers the 8 writers (…)" → 12, appending the four block verbs to the parenthetical list; "the full 34-tool catalogue" → 38. `read` stays 25, `admin` stays 1. These are exactly the "here is the full list" sentences invariant 23 exists for; they change in the same increment as their referent, per the convention the jobs-roster paragraph records.

- [ ] **Step 2: CLAUDE.md, Documents section.** "Five verbs, both doors" gains the block-verb half: the four verbs, the direction rule (a row is content-first or block-first; `document_put` against block-first is a 409 refusal; the first block verb converts and derives markers from the stored content), the serialiser's span guarantee (recomputed in the same pass, never NULL), and the cost model (one edit = one bulk placement UPDATE + one document write + one single-block embed).

- [ ] **Step 3: agent-conventions.md.** Its round-trip-honesty item says "do not get-edit-put a document and expect the source back". Amend: for **content-first** documents that stands; **block-first** documents (the editor's) are the inverse — do not `document_put` them at all (the door refuses), and an agent that must change one uses the block verbs with ids from `document_get`.

---

### Task 11: Gate, changelog, deploy

**Files:**
- Modify: `CHANGELOG.md`

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 2 = 2

- [ ] **Step 1:** `./scripts/gate.sh` — green. This includes the alembic single-revision assertion, which doubles as this plan's no-regen proof: the revision file is untouched.
- [ ] **Step 2:** SDK zero-diff: `cd sdks && make generate && git diff --exit-code sdks/` (no document or block verb is bound; a diff means drift elsewhere — stop and investigate).
- [ ] **Step 3:** CHANGELOG section for the next derived version; coordinate with any sibling increment landing in the same push.
- [ ] **Step 4:** Commits, atomic by concern: `feat(blocks): serialiser and block-first ingest direction` (Tasks 1-3), `feat(blocks): four block verbs on both doors` (Tasks 4-6), `feat(frontend): per-block editor on the personal surface` (Tasks 7-9), `docs: block-verb contract updates` (Task 10).
- [ ] **Step 5:** Redeploy (owner ruling 2026-08-21):

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh
docker compose up -d
# healthy, then confirm the running image, not the tree:
curl -s http://127.0.0.1:8000/openapi.json | grep -c "blocks/{block_id}"   # non-zero
```

- [ ] **Step 6:** Watch it work: create a page on `/documents`, edit a block, confirm in SQL that `documents.content` re-serialised and `blocks.char_span` values slice it (`SELECT text, content FROM blocks b JOIN documents d ON d.id=b.document_id ...` — spot-check one span), and confirm `document_put` at that uri answers 409.

## Rollback

All code, no schema. `git revert` the commits and redeploy. Data left behind by an aborted rollout: documents whose `properties.ingest_direction = "blocks"` — after a revert they are ordinary documents again (the flag is dead weight the old code never reads, and `document_put` works on them again because the refusal reverted with the code). `blocks_edited` events remain in the journal — append-only by design, the accepted T2.59 posture.

## Notes on scope

- **No baseline regeneration — restated as the increment's verified property.** Verified against `0001_baseline.py:1276-1329`: every column this plan writes exists today or is increment 3's; every new key is JSONB content; every vocabulary is a Python list. The review's B2 ("the regen has no referent") is answered by there being, demonstrably, no regen.
- **Not built, per spec §7/§8.4:** no CRDT, no multiplayer, no revisions table, no drag handles, no table editing, no slash menu, no block-level diffing on the agent path (`document_put` stays whole-document for content-first), no `page_ref` block type. Adopting an editor framework is a decision to retake with evidence, not a drift.
- **The workspace surface (increment 4's `/projects/$project`) stays read-only.** The editor is the personal surface's; widening it to project artifacts is a deliberate later decision, since project artifacts are agent-filed content-first documents the door would refuse to convert silently... precisely: they *would* convert on the first verb, which is why the UI does not offer it.
- **Adjacent hazard, found while planning, NOT fixed here:** a content-first **re-put** (outcome `updated`) strips and re-mints every block id (`document_ingest.py` strip-before-rewrite) with **no provenance withdrawal**, so any `fact_sources` row keyed to an old block id dangles. Latent today — the lift is on-demand and nothing in production has lifted a block — but Task 3's `withdraw_blocks` is the exact tool a future fix would call from the strip path. Owner's call which increment takes it.
- **Parallel-plan seam:** increment 3's plan is being written concurrently. The interfaces this plan assumes from it are listed in Prerequisites; reconcile against its landed code at execution.
