# Pages, Increment B1 — backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give pages the backend a Notion-style editor needs — three page-only block types with validated properties and nesting rules, client-chosen block ids, a batch insert, sweep-only page embedding, a trash listing, `source` on the page read and a hash header on block delete — while every document surface stays byte-identical.

**Architecture:** The page/document differences ride the existing `BlockOwner` descriptor as four new fields (`normalize_type`, `validate`, `check_nesting`, `embed_inline`); the document instance carries today's behaviour, so no document code path branches. `_mutate` becomes list-valued internally so one pass can insert many blocks, while the document verbs' result object and journal payload keep their shape. The serialiser learns emit rules for `todo`, `toggle` and `callout`; `create_page` flattens heading nesting and stops embedding; two routes (`POST .../blocks/batch`, `GET /pages/trash`) land with their enumeration-guard entries in the same commit.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy Core with raw `text()` SQL, asyncpg, Postgres 16 with pgvector, pytest.

**Spec:** `docs/superpowers/specs/2026-09-17-pages-increment-b-workspace-editor-design.md` (B1 is §1, §3, §7 "B1", §8)

**Execution:** inline — `claude --model sonnet --effort high` — 3 of 12 tasks are heavy (not a majority); the 4 four-band tasks are a third of the plan, so they and the heavy tasks are delegated, and the highest self-implemented total is 3

**Plan review:** 2026-09-17 — dr-superpowers:judge-opus — executability 17 / coherence 18 / coverage 18 / assumptions 17 (round 2)

## Global Constraints

- **Greenfield until the freeze.** No backward compatibility, no migration, no compatibility shim. This increment is expected to change no schema (spec §8); Task 1 verifies that. If a task finds it must change `0001_baseline.py`, stop and report — the schema is ONE revision regenerated in place, never a `0002`.
- **`documents` must not change in behaviour.** Owner requirement. The document block verbs' normalisation, result object (`BlockWriteResult`, serialised by MCP through `vars()`), `blocks_edited` payload, embedding, routes and response headers stay exactly as they are. The shared request models in `app/api/routes/documents.py` are not edited.
- **Taxonomy is closed and taxonomy-first.** `PAGE_BLOCK_TYPES` lands before any writer or emitter uses the new types. Normalisers stay pure functions of one string.
- **Single worker (invariant 13).** Nothing may assume otherwise.
- **asyncpg needs explicit CAST** on any raw-SQL param whose type Postgres cannot infer: `CAST(:id AS uuid)`, `CAST(:ids AS uuid[])`, `CAST(:props AS jsonb)`.
- **Child embedding tables are named ONLY through `child_table(parent, fingerprint)`** (invariant 2). No literal slug in application code.
- **No new module reads block rows** in this plan. If one becomes necessary it joins `BLOCK_CHANNEL_MODULES` in `tests/test_block_retrieval.py` in the same change.
- **REST conventions** (`docs/api-rest-conventions.md`): 201 create, 204 delete.
- **Comments:** default to none; only where the WHY is non-obvious. Never reference the task, increment or a review finding.
- **English only** in code, comments, docs, commits, tests.
- **Commits:** `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no period. Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh
  ```
- **Backend tests** run from `backend/` on lane database 3, one named set of files per invocation, never the full suite in one process:
  `TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q <paths>`
  **Never use `darkmem_test`** — the controller keeps it.
- **The dev Postgres may be down.** If a run fails with "connection refused" on :5433, start only the database: `docker compose -f docker-compose.dev.yml up -d postgres` from the repo root. Never start the dev app service (it collides with production on :8000).
- **Host hazard:** an `earlyoom` daemon kills memory-heavy runs at ~80% swap. **Exit 143 is a SIGTERM, not a failure** — check `free -h` and re-run the leg alone before believing a red.
- **Deploy is not a task here.** After merge, the ordinary redeploy sequence in CLAUDE.md applies (spec §8).

## Contracts

**Taxonomy (`backend/app/taxonomy.py`, Task 1)**
- `PAGE_BLOCK_TYPES: list[str] = ["todo", "toggle", "callout"]`
- `normalize_page_block_type(raw_type: str | None) -> str` — a page-only type (stripped, lowercased) passes through; everything else returns `normalize_block_type(raw_type)`.

**Serialiser (`backend/app/services/block_serializer.py`, Task 2)**
- `todo`: `- [ ] text` / `- [x] text` (from `properties.checked`), continuation lines and children indented two spaces; counts as a bullet list kind in `_same_list_run` and `_separator`.
- `toggle`: `<details>` then `<summary>text</summary>`, blank line, children, blank line, `</details>`; its `char_span` covers the two opening lines only.
- `callout`: `> [!LABEL]` then `> ` text lines; `info→NOTE`, `warning→WARNING`, `error→CAUTION`, `success→TIP`.

**Block verbs (`backend/app/services/block_verbs.py`)**
- `class PageBlockInvalid(ValueError)` (Task 3), `class PageBlockIdTaken(ValueError)` (Task 4), message `block id <uuid> already exists`.
- `BlockOwner` new fields (Task 3): `normalize_type: Callable[[str | None], str]`, `validate: Callable[[TreeBlock, str | None], TreeBlock]` (second argument is the block's previous type, `None` on insert), `check_nesting: Callable[[TreeBlock | None, TreeBlock], None]`. Task 5 adds `embed_inline: bool`. `DOCUMENT_OWNER`: `normalize_block_type`, `_keep_block`, `_any_parent`, `True`. `PAGE_OWNER`: `normalize_page_block_type`, `_validate_page_block`, `_check_page_nesting`, `False`.
- Page nesting rule (Task 3): a parent is allowed when it is `None`, when its type is `list`, `todo` or `toggle`, or when it is a `table` and the child is a `table_row`.
- Page property rule (Task 3): `todo` requires `checked: bool`; `callout` requires `variant` in `{info, warning, error, success}`; on a type change, keys the new type does not define (`_PAGE_TYPE_PROPERTIES`) are dropped.
- `_insert_into(tree, owner, *, block_id: UUID, type, text, properties, parent_id: str | None, after_block_id: str | None) -> tuple[list[TreeBlock], TreeBlock]` (Task 3).
- `_mutate(..., block_ids: Sequence[str], expected_hash=None, claimed_ids: Sequence[str] = (), owner=DOCUMENT_OWNER)`; `apply` returns `(tree, inserted: list[TreeBlock], deleted_subtree: list[UUID])` (Task 4).
- `insert_block(session, llm, *, document_id, type, text, parent_id=None, after_block_id=None, properties=None, expected_hash=None, block_id: str | None = None, owner=DOCUMENT_OWNER) -> BlockWriteResult` (Task 4).
- `@dataclass(frozen=True) class NewBlock: block_id: str; type: str; text: str; properties: dict | None = None; parent_id: str | None = None; after_block_id: str | None = None` (Task 4).
- `@dataclass(frozen=True) class BlockBatchWriteResult: owner_kind: str; owner_id: str; block_ids: tuple[str, ...]; outcome: str; content_hash: str; blocks_total: int; blocks_embedded: int` (Task 4).
- `insert_blocks(session, llm, *, document_id: str, blocks: Sequence[NewBlock], owner: BlockOwner, expected_hash: str | None = None) -> BlockBatchWriteResult` (Task 4).
- `blocks_edited` payload: `{"verb", "block_id", "blocks_total", "content_hash"}` for one id; `{"verb", "block_ids", "blocks_total", "content_hash"}` for several (Task 4).
- `BlockWriteResult` fields are unchanged: `document_id, owner_kind, owner_id, block_id, outcome, content_hash, blocks_total, blocks_embedded`.

**Page door (`backend/app/services/page_door.py`)**
- `PageResult` loses `blocks_embedded`; `_flatten_headings(tree: list[TreeBlock]) -> list[TreeBlock]`; `create_page` embeds nothing (Task 6).
- `get_page(...).blocks` rows gain `source: str | None`; `list_trash(session, project: str) -> list[dict]` with keys `id, title, parent_id, deleted_at`, newest `deleted_at` first (Task 10).

**Schemas (`backend/app/schemas/page.py`)**
- `PageCreateResponse` loses `blocks_embedded` (Task 6).
- `PageBlockInsertRequest`, `PageBlockUpdateRequest`, `PageBlockMoveRequest`, `PageBlockBatchItem`, `PageBlockBatchInsertRequest` — all `extra="forbid"` (Task 8).
- `PageBlock.source: str | None = None`; `PageTrashItem(id: UUID, title: str | None, parent_id: UUID | None, deleted_at: datetime)` (Task 10).

**Routes (`backend/app/api/routes/pages.py`)**
- Page block refusals: `PageBlockInvalid` → 422, `PageBlockIdTaken` → 409 (Task 8).
- `DELETE /api/v1/pages/{page_id}/blocks/{block_id}` → 204 with header `X-Content-Hash: <new content_hash>` (Task 8).
- `POST /api/v1/pages/{page_id}/blocks/batch` → 201, body `PageBlockBatchWriteResponse {page_id, block_ids, outcome, content_hash, blocks_total, blocks_embedded}` (Task 9).
- `GET /api/v1/pages/trash?project=` → 200, `list[PageTrashItem]`, registered above `GET /{page_id}` (Task 11).

## Assumptions (evidence)

- **No schema change is needed.** `blocks.type` is `TEXT` with no CHECK and `search_vector` blanks only `code`/`html`: `backend/migrations/versions/0001_baseline.py:1374-1397`. The primary key constraint is named `blocks_pkey`: `0001_baseline.py:1390`. Task 1 re-verifies this as a step.
- **The violated constraint's name is reachable from `IntegrityError`.** SQLAlchemy's asyncpg adapter re-raises with `raise translated_error from error` (`backend/.venv/lib/python3.13/site-packages/sqlalchemy/dialects/postgresql/asyncpg.py:797`), so `exc.orig.__cause__` is the asyncpg exception, which carries `constraint_name` (`asyncpg/exceptions/_base.py:44`). Probe run 2026-09-17 against the dev Postgres (a temp table with a primary key and a CHECK, each violated inside `begin_nested()`): `exc.orig` is `IntegrityError` with `sqlstate` `23505` / `23514`, and `exc.orig.__cause__.constraint_name` is `t_pkey` / `t_v`. Task 4's race test exercises the real `blocks_pkey` path; it inserts **another page's** block id, because a same-page id enters the in-memory tree twice and `serialize_tree`'s reachability guard raises `ValueError` before any INSERT (`block_serializer.py:58-78`).
- **`BlockWriteResult` cannot gain a field.** MCP answers `json.dumps(vars(result))` for the document block tools (`backend/app/api/mcp/server.py:2230`, `:2277`), so a new field would change the document wire shape. The batch verb returns its own `BlockBatchWriteResult`.
- **Heading flattening is not lossless in one parser shape — spec §3.3's claim is contradicted.** Probe run 2026-09-17 (scratch script over `page_door._parse` + `serialize_tree`): byte-identical for root headings with paragraphs, bullet and ordered lists, code, quote and divider, and for a heading inside a blockquote; **different** for `"- item\n  # H\n- b\n"`, where the parser parents the sibling item `b` under the heading inside the list item (`document_parsers.py:153-156`) and, once flattened, `_separator`'s nested-item rule (`block_serializer.py:136`) makes it tight: `'- item\n\n  # H\n\n  - b'` becomes `'- item\n\n  # H\n  - b'`. The plan stores the flattened tree's serialisation (self-consistent with later edits) and pins byte-identity on the shapes it holds for; this exception is recorded in CLAUDE.md by Task 12.
- **Serialiser expected strings** in Task 2 were produced by a prototype of exactly Task 2's code, run 2026-09-17.
- **Spec §3.8 cites `routes/documents.py:427-429` for the `source` derivation; those lines are only the model field.** The derivation is the SQL `substring(...)` join in `backend/app/services/document_door.py:1101-1111`, which Task 10 mirrors for pages.
- **A fifth existing test changes with §3.6.** Spec §7 names four; `backend/tests/test_block_verbs.py:624-649` (`test_a_page_block_edit_embeds_into_the_page_family`) asserts inline page embedding too. Task 5 rewrites it.
- **`now()` is constant inside a test.** The `session` fixture joins one outer transaction (`backend/tests/conftest.py:68-105`), so every `deleted_at` stamped in one test is equal; the trash-order test sets stamps explicitly.
- **`create_page` keeps its unused `llm` parameter.** 62 call sites (`rg "create_page\(" backend`, 2026-09-17); removing it is churn outside B1's scope.
- **`PageBlockWriteResponse.blocks_embedded` stays** (always 0 on pages now). The spec removes only `PageCreateResponse.blocks_embedded`.
- **`normalize_page_block_type` delegates non-page values to `normalize_block_type`**, so legacy aliases (`h2 → heading`) keep mapping on pages. The spec says "accepts `BLOCK_TYPES ∪ PAGE_BLOCK_TYPES`, folding anything else to `paragraph`"; delegation satisfies that and keeps the three-step fallthrough.
- **Properties are dropped only on a type change** (spec §3.2 literally). A same-type update keeps unknown keys.
- **The batch request has `min_length=1`.** The spec states only the upper bound; an empty batch would journal an edit that changed nothing.
- **No test in this plan was run by the planner.** The dev Postgres on :5433 was started only for the two driver probes recorded here and stopped again; every test step is unverified until executed.
- **A str bound to `CAST(:x AS timestamptz)` is refused by asyncpg.** Probe run 2026-09-17: `"2026-09-01T00:00:00Z"` raised `DataError: invalid input for query argument`, a `datetime` bound cleanly; precedent binds datetimes (`tests/test_article_staleness.py:83`). Task 10's `_stamp` binds `datetime` values.
- **`app.schemas.page` importing `MAX_BLOCKS` from `app.services.page_door` creates no cycle.** `python -c "import sys, app.services.page_door; print([m for m in sys.modules if m.startswith(('app.schemas','app.api'))])"` printed `[]` on 2026-09-17: the page door's import closure reaches no schema or API module. Schemas importing a service constant has precedent (`app/schemas/facts.py:7`).
- **A type change from a container to a non-container leaves its children in place.** Changing a `toggle` with children to `paragraph` passes `_validate_page_block` and keeps the children under a parent the nesting rule would refuse for a new insert or move. Accepted: spec §3.3 restricts only new inserts and moves ("only new inserts or moves under a disallowed parent are refused"), existing parser shapes are kept the same way, and the serialiser emits any parent/child shape.
- **Route guards are bidirectional** (`test_content_surface_scoping.py:116-125` asserts both "registered but not classified" and "classified but not registered"), so each new route lands with its guard entries in the same task.

## Task index

1. Admit the page-only block types to the taxonomy
2. Serialise to-dos, toggles and callouts
3. Owner-specific type, property and nesting rules
4. Client block ids and a list-valued batch insert
5. Page edits drop vectors instead of embedding
6. Flatten headings and stop embedding on page create
7. Pin the document surfaces as unchanged
8. Page-only block request models and refusals
9. The batch insert route and its guard entries
10. Serve block source and list the trash
11. The trash route and its guard entries
12. Guards leg, read-only role and CLAUDE.md

---

### Task 1: Admit the page-only block types to the taxonomy

**Files:**
- Modify: `backend/app/taxonomy.py` (module docstring lines 1-8; after `normalize_block_type`, end of the block section ~line 462)
- Test: `backend/tests/test_taxonomy.py` (imports lines 26-45; parametrisations at lines 91, 96-103, 195-261)
- Test: `backend/tests/test_notes_schema.py:167-203`

**Interfaces:**
- Consumes: nothing.
- Produces: `PAGE_BLOCK_TYPES`, `normalize_page_block_type` (Contracts, Taxonomy). Tasks 3, 7 use them.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 0 = 3

- [ ] **Step 1: Verify the no-schema-change claim**

From the repo root:

```bash
sed -n 1374,1397p backend/migrations/versions/0001_baseline.py
```

Expected: `type        TEXT,` with no `CHECK` naming `type` anywhere in the `CREATE TABLE blocks` statement, and the `search_vector` expression `CASE WHEN type IN ('code', 'html') THEN '' ELSE coalesce(text, '') END`. If either differs, stop and report: the increment then needs a baseline change (spec §8).

- [ ] **Step 2: Write the failing taxonomy tests**

In `backend/tests/test_taxonomy.py`, add `PAGE_BLOCK_TYPES,` after `MEMORY_TYPES,` in the `from app.taxonomy import (...)` block and `normalize_page_block_type,` after `normalize_memory_type,`.

Change the duplicates parametrisation (line 91) to:

```python
    [ENTITY_TYPES, RELATIONSHIP_TYPES, MEMORY_TYPES, MEMORY_RELATION_TYPES, BLOCK_TYPES,
     PAGE_BLOCK_TYPES],
```

In `test_case_conventions_hold`, after `assert all(t == t.lower() for t in BLOCK_TYPES)` add:

```python
    assert all(t == t.lower() for t in PAGE_BLOCK_TYPES)
```

Append `(normalize_page_block_type, "quasar-block", "paragraph"),` to `test_unknown_values_fall_to_the_safe_default`'s list, `(normalize_page_block_type, "paragraph"),` to `test_empty_and_none_fall_to_the_safe_default`'s, `(normalize_page_block_type, "  Todo ", "todo"),` to `test_normalisers_strip_and_case_fold`'s, `normalize_page_block_type,` to `test_normalisers_take_exactly_one_argument`'s and `(normalize_page_block_type, "callout"),` to `test_normalisers_are_deterministic_across_calls`'s.

At the end of the file add:

```python
def test_page_block_types_are_separate_from_document_block_types():
    """Separate sets are why a document never stores a to-do: the document
    normaliser does not know these values and folds them to `paragraph`."""
    assert PAGE_BLOCK_TYPES == ["todo", "toggle", "callout"]
    assert not set(PAGE_BLOCK_TYPES) & set(BLOCK_TYPES)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("todo", "todo"),
        ("TOGGLE", "toggle"),
        (" callout ", "callout"),
        ("heading", "heading"),
        ("h2", "heading"),
        ("quasar-block", "paragraph"),
        (None, "paragraph"),
    ],
)
def test_the_page_normaliser_accepts_both_sets(raw, expected):
    assert normalize_page_block_type(raw) == expected


@pytest.mark.parametrize("raw", ["todo", "toggle", "callout"])
def test_the_document_normaliser_still_folds_page_types(raw):
    assert normalize_block_type(raw) == "paragraph"
```

- [ ] **Step 3: Classify the new types as prose**

In `backend/tests/test_notes_schema.py`, replace:

```python
PROSE_BLOCK_TYPES = frozenset({
    "paragraph", "heading", "list", "quote", "table", "table_row", "divider",
})
```

with:

```python
PROSE_BLOCK_TYPES = frozenset({
    "paragraph", "heading", "list", "quote", "table", "table_row", "divider",
    "todo", "toggle", "callout",
})
```

and in `test_the_block_type_vocabulary_is_partitioned_into_prose_and_source` replace:

```python
    from app.taxonomy import BLOCK_TYPES
```

with:

```python
    from app.taxonomy import BLOCK_TYPES, PAGE_BLOCK_TYPES
```

and:

```python
    assert SOURCE_BLOCK_TYPES | PROSE_BLOCK_TYPES == set(BLOCK_TYPES), (
```

with:

```python
    assert SOURCE_BLOCK_TYPES | PROSE_BLOCK_TYPES == set(BLOCK_TYPES) | set(PAGE_BLOCK_TYPES), (
```

- [ ] **Step 4: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_taxonomy.py tests/test_notes_schema.py
```

Expected: collection error `ImportError: cannot import name 'PAGE_BLOCK_TYPES'`.

- [ ] **Step 5: Implement**

In `backend/app/taxonomy.py`, replace the docstring's first paragraph:

```python
Six vocabularies govern the model. Five live here — ``ENTITY_TYPES``,
``RELATIONSHIP_TYPES``, ``MEMORY_TYPES``, ``MEMORY_RELATION_TYPES``,
``BLOCK_TYPES`` — and ``TECH_TYPES`` (the ``ENTITY_TYPES`` subset feeding the
``memories.technologies`` denorm) lives in ``app.services.relations`` beside the
graph code that reads it.
```

with:

```python
Seven vocabularies govern the model. Six live here — ``ENTITY_TYPES``,
``RELATIONSHIP_TYPES``, ``MEMORY_TYPES``, ``MEMORY_RELATION_TYPES``,
``BLOCK_TYPES``, ``PAGE_BLOCK_TYPES`` — and ``TECH_TYPES`` (the
``ENTITY_TYPES`` subset feeding the ``memories.technologies`` denorm) lives in
``app.services.relations`` beside the graph code that reads it.
```

Directly after the end of `normalize_block_type` append:

```python


# Block types only a page stores. Kept out of BLOCK_TYPES because the document
# parser never mints them: a filed document carrying `- [ ]`, `> [!NOTE]` or
# `<details>` must parse exactly as it did, and only the page editor sets these.
PAGE_BLOCK_TYPES: list[str] = [
    "todo",
    "toggle",
    "callout",
]

_PAGE_BLOCK_TYPE_SET: frozenset[str] = frozenset(PAGE_BLOCK_TYPES)


def normalize_page_block_type(raw_type: str | None) -> str:
    """Return one of ``BLOCK_TYPES`` or ``PAGE_BLOCK_TYPES``.

    A page-only type passes through; anything else takes
    ``normalize_block_type``'s fallthrough, so a legacy alias still maps and an
    unknown value still folds to ``paragraph``.
    """
    if raw_type and raw_type.strip().lower() in _PAGE_BLOCK_TYPE_SET:
        return raw_type.strip().lower()
    return normalize_block_type(raw_type)
```

- [ ] **Step 6: Run and watch them pass**

Same command as Step 4. Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/taxonomy.py backend/tests/test_taxonomy.py backend/tests/test_notes_schema.py
git commit -m "feat(taxonomy): admit page-only block types

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 2: Serialise to-dos, toggles and callouts

**Files:**
- Modify: `backend/app/services/block_serializer.py:30-32` (constants), `:81-97` (`_is_ordered`, `_same_list_run`), `:132-137` (`_separator`), `:211` (`emit`, before the `table` branch), `:236-247` (after the children loop)
- Test: `backend/tests/test_block_serializer.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the emit forms in Contracts, Serialiser.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 2 = 3

The ordinal loop needs no code change: it already resets the ordered count on any non-`list` sibling, which is what a `todo` must do. The test pins it.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_block_serializer.py`:

```python
def _page_block(type_, text="", properties=None, parent=None, order=0):
    return TreeBlock(uuid4(), parent, order, type_, text, properties)


def test_todos_emit_as_a_tight_task_list():
    first = _page_block("todo", "open", {"checked": False})
    second = _page_block("todo", "done", {"checked": True}, order=1)
    assert serialize_tree([first, second]).content == "- [ ] open\n- [x] done"


def test_a_todo_joins_a_bullet_run_and_resets_an_ordered_count():
    bullet = _page_block("list", "bullet", {"ordered": False, "marker": "-"})
    task = _page_block("todo", "task", {"checked": False}, order=1)
    one = _page_block("list", "one", {"ordered": True, "marker": "1."}, order=2)
    two = _page_block("list", "two", {"ordered": True, "marker": "1."}, order=3)
    assert serialize_tree([bullet, task, one, two]).content == (
        "- bullet\n- [ ] task\n\n1. one\n2. two"
    )

    zero = _page_block("list", "zero", {"ordered": True, "marker": "1."})
    mid = _page_block("todo", "mid", {"checked": True}, order=1)
    after = _page_block("list", "after", {"ordered": True, "marker": "1."}, order=2)
    assert serialize_tree([zero, mid, after]).content == (
        "1. zero\n\n- [x] mid\n\n1. after"
    )


def test_todos_nest_tightly_under_list_and_todo_parents():
    item = _page_block("list", "parent", {"ordered": False, "marker": "-"})
    child = _page_block("todo", "child", {"checked": False}, parent=item.id)
    task = _page_block("todo", "tparent", {"checked": True}, order=1)
    grandchild = _page_block(
        "list", "lchild", {"ordered": False, "marker": "-"}, parent=task.id,
    )
    assert serialize_tree([item, child, task, grandchild]).content == (
        "- parent\n  - [ ] child\n- [x] tparent\n  - lchild"
    )


def test_a_multi_line_todo_indents_its_continuation():
    task = _page_block("todo", "line one\nline two", {"checked": False})
    assert serialize_tree([task]).content == "- [ ] line one\n  line two"


def test_a_toggle_wraps_its_children_and_spans_only_its_opening_lines():
    toggle = _page_block("toggle", "Summary")
    inside = _page_block("paragraph", "inside", parent=toggle.id)
    nested = _page_block("todo", "nested", {"checked": False}, parent=toggle.id, order=1)
    after = _page_block("paragraph", "after", order=1)

    result = serialize_tree([toggle, inside, nested, after])

    assert result.content == (
        "<details>\n<summary>Summary</summary>\n\ninside\n\n- [ ] nested\n\n"
        "</details>\n\nafter"
    )
    start, end = next(p.char_span for p in result.placed if p.block_id == toggle.id)
    assert result.content[start:end] == "<details>\n<summary>Summary</summary>"


def test_an_empty_toggle_still_closes():
    assert serialize_tree([_page_block("toggle", "Empty")]).content == (
        "<details>\n<summary>Empty</summary>\n\n</details>"
    )


@pytest.mark.parametrize(
    "variant, label",
    [("info", "NOTE"), ("warning", "WARNING"), ("error", "CAUTION"), ("success", "TIP")],
)
def test_a_callout_emits_a_github_alert(variant, label):
    callout = _page_block("callout", "line1\nline2", {"variant": variant})
    assert serialize_tree([callout]).content == f"> [!{label}]\n> line1\n> line2"
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_serializer.py
```

Expected: the new tests FAIL (a `todo` currently emits as a paragraph, `open\n\ndone`); the existing tests pass.

- [ ] **Step 3: Add the constants**

In `block_serializer.py`, replace:

```python
DEFAULT_LIST_MARKER = "-"
```

with:

```python
DEFAULT_LIST_MARKER = "-"
# A to-do is a bullet item with a checkbox, so every list predicate treats it
# as one: without that a to-do beside a bullet item splits the list in two.
_LIST_KINDS = frozenset({"list", "todo"})
_CALLOUT_LABELS = {
    "info": "NOTE", "warning": "WARNING", "error": "CAUTION", "success": "TIP",
}
```

- [ ] **Step 4: Teach the list predicates about `todo`**

Replace:

```python
def _is_ordered(block: TreeBlock) -> bool:
    raw = (block.properties or {}).get("marker") or DEFAULT_LIST_MARKER
```

with:

```python
def _is_ordered(block: TreeBlock) -> bool:
    if block.type == "todo":
        return False
    raw = (block.properties or {}).get("marker") or DEFAULT_LIST_MARKER
```

In `_same_list_run`, replace:

```python
    if previous is None or previous.type != "list" or current.type != "list":
        return False
```

with:

```python
    if (
        previous is None
        or previous.type not in _LIST_KINDS
        or current.type not in _LIST_KINDS
    ):
        return False
```

In `_separator`, replace:

```python
    if current.type == "list" and index > 0 and _same_list_run(
        siblings[index - 1], current
    ):
        return "\n"                    # tight list, same run
    if current.type == "list" and parent is not None and parent.type == "list":
        return "\n"                    # nested item under its parent item
```

with:

```python
    if current.type in _LIST_KINDS and index > 0 and _same_list_run(
        siblings[index - 1], current
    ):
        return "\n"                    # tight list, same run
    if (
        current.type in _LIST_KINDS
        and parent is not None
        and parent.type in _LIST_KINDS
    ):
        return "\n"                    # nested item under its parent item
```

- [ ] **Step 5: Add the three emit branches**

In `emit`, replace:

```python
        elif block.type == "table":
            header = props.get("header") or [c.strip() for c in block.text.split("|")]
```

with:

```python
        elif block.type == "todo":
            box = "[x]" if props.get("checked") else "[ ]"
            lines = block.text.split("\n") if block.text else [""]
            indent = " " * (len(DEFAULT_LIST_MARKER) + 1)
            span = emit_lines(
                [f"{DEFAULT_LIST_MARKER} {box} {lines[0]}",
                 *(indent + line for line in lines[1:])],
                prefix,
            )
            child_prefix = prefix + indent
        elif block.type == "toggle":
            # The span covers the opening lines only; the closing line is
            # written after the children, so one contiguous range cannot
            # include it without swallowing theirs.
            span = emit_lines(
                ["<details>", *f"<summary>{block.text}</summary>".split("\n")],
                prefix,
            )
        elif block.type == "callout":
            label = _CALLOUT_LABELS.get(props.get("variant"), "NOTE")
            lines = block.text.split("\n") if block.text else []
            span = emit_lines(
                [f"> [!{label}]", *(f"> {line}" for line in lines)], prefix,
            )
        elif block.type == "table":
            header = props.get("header") or [c.strip() for c in block.text.split("|")]
```

- [ ] **Step 6: Add the toggle's closing hook**

In `emit`, replace:

```python
            write(_separator(block, kids, i, child_prefix))
            emit(kid, child_prefix, list_ordinal)
```

with:

```python
            write(_separator(block, kids, i, child_prefix))
            emit(kid, child_prefix, list_ordinal)

        if block.type == "toggle":
            write("\n" + prefix.rstrip() + "\n")
            write(prefix + "</details>")
```

- [ ] **Step 7: Run the serialiser and parser suites**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_serializer.py tests/test_document_parsers.py
```

Expected: PASS, including every pre-existing round-trip test (documents never carry the new types, so their output is unchanged).

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/block_serializer.py backend/tests/test_block_serializer.py
git commit -m "feat(blocks): serialise todo, toggle and callout

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 3: Owner-specific type, property and nesting rules

**Files:**
- Modify: `backend/app/services/block_verbs.py` (imports `:15-38`, `__all__` `:41-53`, exceptions `:58-65`, `BlockOwner` `:80-101`, `DOCUMENT_OWNER` `:168-178`, `PAGE_OWNER` `:209-219`, `update_block` `:410-438`, `insert_block` `:441-479`, `move_block` `:482-529`)
- Test: `backend/tests/test_block_verbs.py`

**Interfaces:**
- Consumes: `PAGE_BLOCK_TYPES`, `normalize_page_block_type` (Contracts, Taxonomy).
- Produces: `PageBlockInvalid`, the three `BlockOwner` hook fields, the page nesting and property rules, `_insert_into` (Contracts, Block verbs). Tasks 4, 5, 7, 8 consume them.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_block_verbs.py`, add to the imports at the top:

```python
from app.services.block_verbs import PAGE_OWNER, PageBlockInvalid
```

Append after the `_page` helper's existing page tests (end of file):

```python
async def _page_rows(session, page_id):
    return (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, CAST(parent_id AS text) AS parent_id, "
            "type, text, properties FROM blocks "
            "WHERE page_id = CAST(:id AS uuid) ORDER BY order_index"
        ),
        {"id": page_id},
    )).mappings().all()


def test_every_block_type_declares_its_page_properties():
    """A type missing here would have every property dropped on a type change."""
    from app.services.block_verbs import _PAGE_TYPE_PROPERTIES
    from app.taxonomy import BLOCK_TYPES, PAGE_BLOCK_TYPES

    assert set(_PAGE_TYPE_PROPERTIES) == set(BLOCK_TYPES) | set(PAGE_BLOCK_TYPES)


@pytest.mark.parametrize(
    "type_, properties",
    [("todo", {"checked": False}), ("toggle", None), ("callout", {"variant": "success"})],
)
@pytest.mark.asyncio
async def test_a_page_stores_each_page_only_type(session, type_, properties):
    page_id, _ = await _page(session, content="page prose\n")

    result = await insert_block(session, StubEmbedder(), document_id=page_id,
                                type=type_, text="x", properties=properties,
                                owner=PAGE_OWNER)

    row = next(r for r in await _page_rows(session, page_id) if r["id"] == result.block_id)
    assert row["type"] == type_
    assert row["properties"] == properties


@pytest.mark.parametrize(
    "type_, properties",
    [
        ("todo", None),
        ("todo", {"checked": "yes"}),
        ("callout", None),
        ("callout", {"variant": "loud"}),
        ("callout", {"variant": ["info"]}),
    ],
)
@pytest.mark.asyncio
async def test_a_page_refuses_a_page_only_type_without_its_property(
    session, type_, properties,
):
    page_id, _ = await _page(session, content="page prose\n")

    with pytest.raises(PageBlockInvalid):
        await insert_block(session, StubEmbedder(), document_id=page_id,
                           type=type_, text="x", properties=properties,
                           owner=PAGE_OWNER)

    assert len(await _page_rows(session, page_id)) == 1


@pytest.mark.asyncio
async def test_a_type_change_is_validated_on_the_merged_block(session):
    """The request names a type and no properties; the stored paragraph has
    none either, so the resulting to-do lacks `checked`."""
    page_id, block_id = await _page(session, content="page prose\n")

    with pytest.raises(PageBlockInvalid):
        await update_block(session, StubEmbedder(), block_id=block_id,
                           text="page prose", type="todo", owner=PAGE_OWNER)


@pytest.mark.asyncio
async def test_a_type_change_drops_properties_the_new_type_does_not_define(session):
    llm = StubEmbedder()
    page_id, _ = await _page(session, content="page prose\n")
    todo = await insert_block(session, llm, document_id=page_id, type="todo",
                              text="task", properties={"checked": True},
                              owner=PAGE_OWNER)

    await update_block(session, llm, block_id=todo.block_id, text="task",
                       type="paragraph", owner=PAGE_OWNER)

    row = next(r for r in await _page_rows(session, page_id) if r["id"] == todo.block_id)
    assert row["type"] == "paragraph"
    assert row["properties"] is None


@pytest.mark.asyncio
async def test_a_same_type_update_merges_properties(session):
    llm = StubEmbedder()
    page_id, _ = await _page(session, content="page prose\n")
    todo = await insert_block(session, llm, document_id=page_id, type="todo",
                              text="task", properties={"checked": False},
                              owner=PAGE_OWNER)

    await update_block(session, llm, block_id=todo.block_id, text="task",
                       properties={"checked": True}, owner=PAGE_OWNER)

    row = next(r for r in await _page_rows(session, page_id) if r["id"] == todo.block_id)
    assert row["properties"] == {"checked": True}


@pytest.mark.asyncio
async def test_a_page_refuses_nesting_under_a_block_that_holds_no_children(session):
    llm = StubEmbedder()
    page_id, paragraph_id = await _page(session, content="page prose\n")
    heading = await insert_block(session, llm, document_id=page_id, type="heading",
                                 text="H", properties={"level": 2}, owner=PAGE_OWNER)
    table = await insert_block(session, llm, document_id=page_id, type="table",
                               text="a", properties={"header": ["a"], "alignments": [None]},
                               owner=PAGE_OWNER)

    for parent in (paragraph_id, heading.block_id, table.block_id):
        with pytest.raises(PageBlockInvalid):
            await insert_block(session, llm, document_id=page_id, type="paragraph",
                               text="child", parent_id=parent, owner=PAGE_OWNER)

    loose = await insert_block(session, llm, document_id=page_id, type="paragraph",
                               text="loose", owner=PAGE_OWNER)
    with pytest.raises(PageBlockInvalid):
        await move_block(session, llm, block_id=loose.block_id,
                         new_parent_id=paragraph_id, owner=PAGE_OWNER)


@pytest.mark.parametrize(
    "parent_type, parent_properties, child_type, child_properties",
    [
        ("list", {"ordered": False, "marker": "-"}, "paragraph", None),
        ("todo", {"checked": False}, "todo", {"checked": True}),
        ("toggle", None, "code", {"language": "py"}),
        ("table", {"header": ["a"], "alignments": [None]}, "table_row", {"cells": ["1"]}),
    ],
)
@pytest.mark.asyncio
async def test_a_page_accepts_its_container_parents(
    session, parent_type, parent_properties, child_type, child_properties,
):
    llm = StubEmbedder()
    page_id, _ = await _page(session, content="page prose\n")
    parent = await insert_block(session, llm, document_id=page_id, type=parent_type,
                                text="parent", properties=parent_properties,
                                owner=PAGE_OWNER)

    child = await insert_block(session, llm, document_id=page_id, type=child_type,
                               text="child", properties=child_properties,
                               parent_id=parent.block_id, owner=PAGE_OWNER)
    moved = await insert_block(session, llm, document_id=page_id, type=child_type,
                               text="moved", properties=child_properties,
                               owner=PAGE_OWNER)
    await move_block(session, llm, block_id=moved.block_id,
                     new_parent_id=parent.block_id, owner=PAGE_OWNER)

    rows = {r["id"]: r for r in await _page_rows(session, page_id)}
    assert rows[child.block_id]["parent_id"] == parent.block_id
    assert rows[moved.block_id]["parent_id"] == parent.block_id


@pytest.mark.asyncio
async def test_a_document_block_still_nests_under_a_paragraph(session):
    """The page rule must not reach documents."""
    llm, doc_id = await _file(session, "# T\n\nalpha\n", "v/nest.md")
    alpha = next(r for r in await _blocks(session, doc_id) if r["text"] == "alpha")

    result = await insert_block(session, llm, document_id=doc_id, type="paragraph",
                                text="under", parent_id=alpha["id"])

    row = next(r for r in await _blocks(session, doc_id) if r["id"] == result.block_id)
    assert row["parent_id"] == alpha["id"]
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py
```

Expected: collection error `ImportError: cannot import name 'PageBlockInvalid'`.

- [ ] **Step 3: Imports, `__all__` and the exception**

In `block_verbs.py`, replace:

```python
from dataclasses import dataclass
from typing import Any
```

with:

```python
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any
```

Replace `from app.taxonomy import normalize_block_type` with:

```python
from app.taxonomy import normalize_block_type, normalize_page_block_type
```

In `__all__`, add `"PageBlockInvalid",` after `"BlockWriteResult",`.

After the `BlockCycleError` class add:

```python
class PageBlockInvalid(ValueError):
    """A page block the page rules refuse: a missing or malformed required
    property, or a parent that holds no children on a page."""
```

- [ ] **Step 4: Add the hook fields to `BlockOwner`**

At the end of the `BlockOwner` docstring (before its closing `"""`), add:

```
    `normalize_type`, `validate` and `check_nesting` are where the two owners'
    block rules differ. The document instance carries today's behaviour -- the
    document normaliser, no property rules, any parent -- so a document verb
    naming a page-only type still stores `paragraph`.
```

After `embed_parent: str` add:

```python
    normalize_type: Callable[[str | None], str]
    validate: Callable[[TreeBlock, str | None], TreeBlock]
    check_nesting: Callable[[TreeBlock | None, TreeBlock], None]
```

- [ ] **Step 5: Add the rule functions and wire both owners**

Directly above `DOCUMENT_OWNER = BlockOwner(` insert:

```python
def _keep_block(block: TreeBlock, previous_type: str | None) -> TreeBlock:
    return block


def _any_parent(parent: TreeBlock | None, child: TreeBlock) -> None:
    return None


```

In `DOCUMENT_OWNER`, after `embed_parent=PARENT_TABLE,` add:

```python
    normalize_type=normalize_block_type,
    validate=_keep_block,
    check_nesting=_any_parent,
```

Directly above `PAGE_OWNER = BlockOwner(` insert:

```python
# The keys each type defines. A page type change drops every other key, so
# `checked` never rides onto a paragraph and a list's `marker` never rides onto
# a to-do.
_PAGE_TYPE_PROPERTIES: dict[str, frozenset[str]] = {
    "paragraph": frozenset(),
    "heading": frozenset({"level"}),
    "list": frozenset({"ordered", "marker", "number"}),
    "code": frozenset({"language"}),
    "quote": frozenset(),
    "table": frozenset({"header", "alignments"}),
    "table_row": frozenset({"cells"}),
    "divider": frozenset(),
    "html": frozenset(),
    "todo": frozenset({"checked"}),
    "toggle": frozenset(),
    "callout": frozenset({"variant"}),
}
_CALLOUT_VARIANTS = frozenset({"info", "warning", "error", "success"})
# Headings are absent on purpose: an editor renders a heading's children as
# indentation, which is not what a heading means.
_PAGE_CONTAINERS = frozenset({"list", "todo", "toggle"})


def _validate_page_block(block: TreeBlock, previous_type: str | None) -> TreeBlock:
    if (
        previous_type is not None
        and previous_type != block.type
        and block.properties
    ):
        defined = _PAGE_TYPE_PROPERTIES.get(block.type, frozenset())
        kept = {k: v for k, v in block.properties.items() if k in defined}
        block = replace(block, properties=kept or None)
    properties = block.properties or {}
    if block.type == "todo" and not isinstance(properties.get("checked"), bool):
        raise PageBlockInvalid("a todo block needs a boolean `checked` property")
    variant = properties.get("variant")
    if block.type == "callout" and (
        not isinstance(variant, str) or variant not in _CALLOUT_VARIANTS
    ):
        raise PageBlockInvalid(
            "a callout block needs `variant` set to one of "
            f"{', '.join(sorted(_CALLOUT_VARIANTS))}"
        )
    return block


def _check_page_nesting(parent: TreeBlock | None, child: TreeBlock) -> None:
    if parent is None or parent.type in _PAGE_CONTAINERS:
        return
    if parent.type == "table" and child.type == "table_row":
        return
    raise PageBlockInvalid(
        f"a {parent.type} block cannot hold a {child.type} block on a page: "
        "only list, todo and toggle blocks hold children, and a table holds "
        "its table_row blocks"
    )


```

In `PAGE_OWNER`, after `embed_parent=PAGE_PARENT_TABLE,` add:

```python
    normalize_type=normalize_page_block_type,
    validate=_validate_page_block,
    check_nesting=_check_page_nesting,
```

- [ ] **Step 6: Route `update_block` through the hooks**

In `update_block`'s `apply`, replace:

```python
            merged = {**(block.properties or {}), **(properties or {})} or None
            out.append(TreeBlock(
                block.id, block.parent_id, block.order_index,
                normalize_block_type(type) if type else block.type,
                text, merged,
            ))
```

with:

```python
            merged = {**(block.properties or {}), **(properties or {})} or None
            out.append(owner.validate(
                TreeBlock(
                    block.id, block.parent_id, block.order_index,
                    owner.normalize_type(type) if type else block.type,
                    text, merged,
                ),
                block.type,
            ))
```

- [ ] **Step 7: Extract `_insert_into` and use it in `insert_block`**

Above `async def update_block(` insert:

```python
def _insert_into(
    tree: list[TreeBlock], owner: BlockOwner, *, block_id: UUID, type: str,
    text: str, properties: dict | None, parent_id: str | None,
    after_block_id: str | None,
) -> tuple[list[TreeBlock], TreeBlock]:
    """Place one new block in the in-memory tree; returns the tree and the
    placed block."""
    parent = None if parent_id is None else UUID(parent_id)
    after = None if after_block_id is None else UUID(after_block_id)
    parent_block = None
    if parent is not None:
        parent_block = next((b for b in tree if b.id == parent), None)
        if parent_block is None:
            raise BlockTargetUnresolved(
                f"no parent block {parent_id} in this {owner.noun}")
    siblings = [b for b in tree if b.parent_id == parent]
    if after is None:
        position = 0
    else:
        index = next((i for i, b in enumerate(siblings) if b.id == after), None)
        if index is None:
            raise BlockTargetUnresolved(
                f"after_block_id {after_block_id} is not a child of the "
                "target parent"
            )
        position = index + 1
    block = owner.validate(
        TreeBlock(block_id, parent, 0, owner.normalize_type(type), text,
                  properties or None),
        None,
    )
    owner.check_nesting(parent_block, block)
    reordered = siblings[:position] + [block] + siblings[position:]
    others = [b for b in tree if b.parent_id != parent]
    renumbered = [
        TreeBlock(b.id, b.parent_id, i, b.type, b.text, b.properties)
        for i, b in enumerate(reordered)
    ]
    return others + renumbered, next(b for b in renumbered if b.id == block_id)


```

Replace the whole body of `insert_block` (from `minted = new_id()` through its `return await _mutate(...)`) with:

```python
    minted = new_id()

    def apply(tree: list[TreeBlock]):
        tree, placed = _insert_into(
            tree, owner, block_id=minted, type=type, text=text,
            properties=properties, parent_id=parent_id,
            after_block_id=after_block_id,
        )
        return tree, placed, []

    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=str(minted), verb="inserted",
                         block_id=str(minted), expected_hash=expected_hash,
                         owner=owner)
```

- [ ] **Step 8: Check nesting in `move_block`**

In `move_block`'s `apply`, replace:

```python
        if parent is not None:
            if parent in _subtree(tree, target):
                raise BlockCycleError(
                    "a block cannot be moved inside its own subtree"
                )
            if not any(b.id == parent for b in tree):
                raise BlockTargetUnresolved(f"no parent block {new_parent_id}")
        moved = next(b for b in tree if b.id == target)
```

with:

```python
        parent_block = None
        if parent is not None:
            if parent in _subtree(tree, target):
                raise BlockCycleError(
                    "a block cannot be moved inside its own subtree"
                )
            parent_block = next((b for b in tree if b.id == parent), None)
            if parent_block is None:
                raise BlockTargetUnresolved(f"no parent block {new_parent_id}")
        moved = next(b for b in tree if b.id == target)
        owner.check_nesting(parent_block, moved)
```

- [ ] **Step 9: Run the verb, page and route suites**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py tests/test_page_routes.py tests/test_page_door.py
```

Expected: PASS. `test_block_verbs_round_trip_on_a_page` still passes: its insert and move target the root.

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/block_verbs.py backend/tests/test_block_verbs.py
git commit -m "feat(blocks): add page block rules

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 4: Client block ids and a list-valued batch insert

**Files:**
- Modify: `backend/app/services/block_verbs.py` (imports, `__all__`, exceptions, statements, `_mutate` `:236-380`, the four verbs' `apply` returns and `_mutate` calls)
- Test: `backend/tests/test_block_verbs.py`

**Interfaces:**
- Consumes: `_insert_into`, `PageBlockInvalid`, `PAGE_OWNER` hooks (Task 3).
- Produces: `PageBlockIdTaken`, `NewBlock`, `BlockBatchWriteResult`, `insert_blocks`, `insert_block(..., block_id=...)`, the list-valued `_mutate` and the journal payload rule (Contracts, Block verbs). Tasks 5, 8, 9 consume them.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_block_verbs.py`, extend the top-level import added in Task 3 to:

```python
from app.services.block_verbs import (
    PAGE_OWNER,
    NewBlock,
    PageBlockIdTaken,
    PageBlockInvalid,
    insert_blocks,
)
from app.utils.ids import new_id
```

Append:

```python
_WRITE_RESULT_FIELDS = [
    "document_id", "owner_kind", "owner_id", "block_id", "outcome",
    "content_hash", "blocks_total", "blocks_embedded",
]


@pytest.mark.asyncio
async def test_the_document_verbs_keep_their_result_and_journal_shape(session):
    """MCP answers `vars(result)` and the journal is read by id, so a
    list-valued pass must not leak into either on the document path."""
    llm, doc_id = await _file(session, "# T\n\nalpha\n", "v/shape.md")
    rows = await _blocks(session, doc_id)

    updated = await update_block(session, llm, block_id=rows[-1]["id"], text="beta")
    inserted = await insert_block(session, llm, document_id=doc_id,
                                  type="paragraph", text="gamma")

    for result in (updated, inserted):
        assert list(vars(result)) == _WRITE_RESULT_FIELDS
    assert updated.block_id == rows[-1]["id"]
    payloads = (await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'blocks_edited' "
            "AND object_id = CAST(:id AS uuid)"
        ),
        {"id": doc_id},
    )).scalars().all()
    assert len(payloads) == 2
    for payload in payloads:
        assert set(payload) == {"verb", "block_id", "blocks_total", "content_hash"}
    assert {p["block_id"] for p in payloads} == {updated.block_id, inserted.block_id}


@pytest.mark.asyncio
async def test_a_client_block_id_becomes_the_row_id(session):
    page_id, _ = await _page(session, content="page prose\n")
    chosen = str(new_id())

    result = await insert_block(session, StubEmbedder(), document_id=page_id,
                                type="paragraph", text="x", block_id=chosen,
                                owner=PAGE_OWNER)

    assert result.block_id == chosen
    assert chosen in {r["id"] for r in await _page_rows(session, page_id)}


@pytest.mark.asyncio
async def test_a_taken_block_id_is_refused(session):
    page_id, existing = await _page(session, content="page prose\n")

    with pytest.raises(PageBlockIdTaken) as caught:
        await insert_block(session, StubEmbedder(), document_id=page_id,
                           type="paragraph", text="x", block_id=existing,
                           owner=PAGE_OWNER)

    assert str(caught.value) == f"block id {existing} already exists"


@pytest.mark.asyncio
async def test_a_primary_key_race_past_the_check_is_the_same_refusal(
    session, monkeypatch,
):
    """Two different pages' inserts are not serialised by either page's row
    lock, so the primary key is the real guard; blinding the pre-check is how
    a single connection reaches it.

    The taken id must belong to ANOTHER page. A same-page id would enter the
    in-memory tree twice, and `serialize_tree`'s reachability guard raises
    ValueError before any INSERT runs, so the primary key would never fire.
    """
    from app.services import block_verbs

    monkeypatch.setattr(block_verbs, "_TAKEN_IDS", text(
        "SELECT CAST(id AS text) AS id FROM blocks "
        "WHERE false AND id = ANY(CAST(:ids AS uuid[]))"
    ))
    page_id, _ = await _page(session, content="page prose\n", title="A")
    _, existing = await _page(session, content="other prose\n", title="B")

    with pytest.raises(PageBlockIdTaken) as caught:
        await insert_block(session, StubEmbedder(), document_id=page_id,
                           type="paragraph", text="x", block_id=existing,
                           owner=PAGE_OWNER)

    assert existing in str(caught.value)


@pytest.mark.asyncio
async def test_a_non_primary_key_integrity_failure_is_not_mapped(session):
    import dataclasses

    from sqlalchemy.exc import IntegrityError

    orphaning = dataclasses.replace(PAGE_OWNER, insert_block=text(
        "INSERT INTO blocks (id, page_id, parent_id, order_index, type, text, properties) "
        "VALUES (CAST(:id AS uuid), CAST(:doc AS uuid), "
        "        COALESCE(CAST(:parent AS uuid), gen_random_uuid()), "
        "        :ord, CAST(:type AS text), CAST(:text AS text), CAST(:props AS jsonb))"
    ))
    page_id, _ = await _page(session, content="page prose\n")

    with pytest.raises(IntegrityError):
        await insert_block(session, StubEmbedder(), document_id=page_id,
                           type="paragraph", text="x", block_id=str(new_id()),
                           owner=orphaning)


@pytest.mark.asyncio
async def test_a_batch_applies_in_order_and_resolves_earlier_items(session):
    page_id, prose = await _page(session, content="page prose\n")
    toggle, inside, after = (str(new_id()) for _ in range(3))

    result = await insert_blocks(session, StubEmbedder(), document_id=page_id,
                                 owner=PAGE_OWNER, blocks=[
        NewBlock(block_id=toggle, type="toggle", text="T", after_block_id=prose),
        NewBlock(block_id=inside, type="paragraph", text="inside", parent_id=toggle),
        NewBlock(block_id=after, type="todo", text="task",
                 properties={"checked": False}, after_block_id=toggle),
    ])

    assert result.block_ids == (toggle, inside, after)
    assert result.outcome == "inserted"
    rows = await _page_rows(session, page_id)
    assert [r["id"] for r in rows] == [prose, toggle, inside, after]
    assert next(r for r in rows if r["id"] == inside)["parent_id"] == toggle


@pytest.mark.asyncio
async def test_a_multi_block_batch_journals_block_ids(session):
    page_id, _ = await _page(session, content="page prose\n")
    first, second = str(new_id()), str(new_id())

    await insert_blocks(session, StubEmbedder(), document_id=page_id,
                        owner=PAGE_OWNER, blocks=[
        NewBlock(block_id=first, type="paragraph", text="a"),
        NewBlock(block_id=second, type="paragraph", text="b", after_block_id=first),
    ])

    payload = (await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'blocks_edited' "
            "AND object_id = CAST(:id AS uuid)"
        ),
        {"id": page_id},
    )).scalar_one()
    assert payload["block_ids"] == [first, second]
    assert "block_id" not in payload


async def _page_hash(session, page_id):
    return (await session.execute(
        text("SELECT content_hash FROM pages WHERE id = CAST(:id AS uuid)"),
        {"id": page_id},
    )).scalar_one()


@pytest.mark.asyncio
async def test_a_batch_refuses_whole_on_its_first_invalid_item(session):
    page_id, existing = await _page(session, content="page prose\n")
    before = await _page_hash(session, page_id)

    with pytest.raises(PageBlockInvalid):
        await insert_blocks(session, StubEmbedder(), document_id=page_id,
                            owner=PAGE_OWNER, blocks=[
            NewBlock(block_id=str(new_id()), type="paragraph", text="fine"),
            NewBlock(block_id=str(new_id()), type="todo", text="no checked"),
        ])
    with pytest.raises(PageBlockIdTaken):
        await insert_blocks(session, StubEmbedder(), document_id=page_id,
                            owner=PAGE_OWNER, blocks=[
            NewBlock(block_id=str(new_id()), type="paragraph", text="fine"),
            NewBlock(block_id=existing, type="paragraph", text="taken"),
        ])

    assert len(await _page_rows(session, page_id)) == 1
    assert await _page_hash(session, page_id) == before


@pytest.mark.asyncio
async def test_a_batch_refuses_a_repeated_block_id(session):
    page_id, _ = await _page(session, content="page prose\n")
    repeated = str(new_id())

    with pytest.raises(PageBlockInvalid):
        await insert_blocks(session, StubEmbedder(), document_id=page_id,
                            owner=PAGE_OWNER, blocks=[
            NewBlock(block_id=repeated, type="paragraph", text="a"),
            NewBlock(block_id=repeated, type="paragraph", text="b"),
        ])
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py
```

Expected: collection error `ImportError: cannot import name 'NewBlock'`.

- [ ] **Step 3: Imports, `__all__`, exception, result types and statements**

In `block_verbs.py`, replace:

```python
from collections.abc import Callable
```

with:

```python
from collections import Counter
from collections.abc import Callable, Sequence
```

After `from sqlalchemy import text` add:

```python
from sqlalchemy.exc import IntegrityError
```

In `__all__` add `"BlockBatchWriteResult",` after `"BlockCycleError",`, `"NewBlock",` and `"PageBlockIdTaken",` after `"BlockWriteResult",`, and `"insert_blocks",` after `"insert_block",`.

After the `PageBlockInvalid` class add:

```python
class PageBlockIdTaken(ValueError):
    """A client-chosen block id already names a row."""
```

After the `BlockWriteResult` dataclass add:

```python
@dataclass(frozen=True)
class BlockBatchWriteResult:
    owner_kind: str
    owner_id: str
    block_ids: tuple[str, ...]
    outcome: str
    content_hash: str
    blocks_total: int
    blocks_embedded: int


@dataclass(frozen=True)
class NewBlock:
    block_id: str
    type: str
    text: str
    properties: dict | None = None
    parent_id: str | None = None
    after_block_id: str | None = None
```

After `_DELETE_BLOCK = text(...)` add:

```python
_TAKEN_IDS = text(
    "SELECT CAST(id AS text) AS id FROM blocks "
    "WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY id"
)
```

Above `async def _mutate(` add:

```python
async def _first_taken(session, ids: Sequence[str]) -> str | None:
    return (
        await session.execute(_TAKEN_IDS, {"ids": list(ids)})
    ).scalars().first()


def _violated_constraint(exc: IntegrityError) -> str | None:
    return getattr(getattr(exc.orig, "__cause__", None), "constraint_name", None)


```

- [ ] **Step 4: Replace `_mutate`**

Replace the whole `_mutate` function with:

```python
async def _mutate(session, llm, *, document_id, apply, touched_embed, verb,
                  block_ids, expected_hash=None, claimed_ids=(),
                  owner: BlockOwner = DOCUMENT_OWNER):
    """Lock, load, mutate in memory, serialise, write, journal, embed.

    Review M-3: the lock is the first statement, before anything is read off
    the row. The whole pass is a read-modify-write that crosses several
    awaits, and `put_document` takes the same lock, so the two serialise
    instead of interleaving into a tree whose blocks were stripped underneath
    it.
    """
    await session.execute(owner.lock, {"id": document_id})

    meta = (await session.execute(owner.meta, {"id": document_id})).mappings().first()
    if meta is None:
        raise BlockTargetUnresolved(f"no {owner.noun} with id {document_id}")
    # After the lock, which is what makes this a compare-and-set rather than a
    # check-then-act: no writer can move content_hash between this read and
    # the write below, because both are inside one held row lock.
    if expected_hash is not None and meta["content_hash"] != expected_hash:
        raise DocumentHashConflict(
            document_id=document_id,
            expected_hash=expected_hash,
            current_hash=meta["content_hash"],
        )
    if claimed_ids:
        taken = await _first_taken(session, claimed_ids)
        if taken is not None:
            raise PageBlockIdTaken(f"block id {taken} already exists")
    rows = (await session.execute(owner.load_tree, {"id": document_id})).mappings().all()
    tree = [
        TreeBlock(r["id"], r["parent_id"], r["order_index"], r["type"],
                  r["text"] or "", r["properties"])
        for r in rows
    ]
    spans = {
        r["id"]: (r["lo"], r["hi"])
        for r in rows
        if r["lo"] is not None and r["hi"] is not None
    }

    if meta["direction"] != BLOCK_FIRST and meta["content"]:
        # The conversion pass. Review M-2: refuse rather than convert when the
        # serialiser cannot reproduce the stored source -- regenerating content
        # without a construct the parser dropped is silent loss on exactly the
        # corpus this programme exists to hold.
        if not reproduces_source(
            tree, meta["content"], spans, frontmatter=meta["frontmatter"]
        ):
            raise DocumentNotConvertible(
                "this document contains source the block editor cannot "
                "represent (a raw HTML block, or a link-reference "
                "definition). Editing it as blocks would rewrite the file "
                "without it. Edit it with document_put instead."
            )
        tree = derive_markers(tree, meta["content"], spans)

    tree, inserted, deleted_subtree = apply(tree)

    # Frontmatter rides every serialisation, not only the conversion: an
    # ordinary edit of an already-block-first document would otherwise drop
    # the fence on the first save.
    result = serialize_tree(tree, frontmatter=meta["frontmatter"])
    if len(result.content) > MAX_CONTENT_CHARS:
        raise DocumentTooLarge(
            f"the edited document serialises to {len(result.content)} "
            f"characters; the bound is {MAX_CONTENT_CHARS}"
        )
    if len(tree) > MAX_BLOCKS:
        raise DocumentTooLarge(
            f"the edited document holds {len(tree)} blocks; the bound is "
            f"{MAX_BLOCKS}"
        )
    content_hash = compute_content_hash(result.content)
    by_id = {b.id: b for b in tree}

    try:
        async with session.begin_nested():
            if deleted_subtree:
                # The subtree's root only: parent_id ON DELETE CASCADE takes the
                # rest, and block_embeddings__<slug> cascades in every partition.
                await session.execute(
                    _DELETE_BLOCK, {"id": str(deleted_subtree[0])}
                )
            for block in inserted:
                await session.execute(owner.insert_block, {
                    "id": str(block.id),
                    "doc": document_id,
                    "parent": None if block.parent_id is None else str(block.parent_id),
                    "ord": block.order_index,
                    "type": block.type,
                    "text": block.text,
                    "props": _json(block.properties),
                })
            if verb == "updated":
                target = by_id[UUID(block_ids[0])]
                await session.execute(_UPDATE_BLOCK, {
                    "id": block_ids[0],
                    "type": target.type,
                    "text": target.text,
                    "parent": None if target.parent_id is None else str(target.parent_id),
                })

            placed = {p.block_id: p for p in result.placed}
            ids, ords, spans_out, props_out, parents = [], [], [], [], []
            for block in tree:
                p = placed[block.id]
                ids.append(str(block.id))
                ords.append(p.order_index)
                spans_out.append(f"[{p.char_span[0]},{p.char_span[1]})")
                props_out.append(_json(block.properties))
                parents.append(None if block.parent_id is None else str(block.parent_id))
            if ids:
                await session.execute(_PLACE, {
                    "ids": ids, "ords": ords, "spans": spans_out,
                    "props": props_out, "parents": parents,
                })

            await session.execute(owner.write_owner, {
                "id": document_id, "content": result.content, "hash": content_hash,
            })
            # No block text in the payload: write-time minimization, and a
            # journal row outlives the document it describes. One id keeps the
            # `block_id` key every existing reader of this stream expects.
            payload: dict[str, Any] = {"verb": verb}
            if len(block_ids) == 1:
                payload["block_id"] = block_ids[0]
            else:
                payload["block_ids"] = list(block_ids)
            payload["blocks_total"] = len(tree)
            payload["content_hash"] = content_hash
            await record_event(
                session,
                event_type=BLOCKS_EDITED_EVENT,
                object_type=owner.object_type,
                object_id=UUID(document_id),
                project=meta["project"],
                payload=payload,
            )
    except IntegrityError as exc:
        # The check above sees only committed rows under this owner's lock; an
        # insert of the same id into another owner is not serialised by it, so
        # the primary key is the guard of last resort.
        if not claimed_ids or _violated_constraint(exc) != "blocks_pkey":
            raise
        taken = await _first_taken(session, claimed_ids)
        raise PageBlockIdTaken(
            f"block id {taken or claimed_ids[0]} already exists"
        ) from exc
    await session.commit()

    written = 0
    if touched_embed is not None:
        embed = await embed_blocks(session, llm, block_ids=[touched_embed],
                                   parent=owner.embed_parent)
        written = embed.written if embed else 0
        await session.commit()

    return BlockWriteResult(
        document_id=document_id if owner.kind == "document" else None,
        owner_kind=owner.kind,
        owner_id=document_id,
        block_id=block_ids[0] if len(block_ids) == 1 else None,
        outcome=verb,
        content_hash=content_hash,
        blocks_total=len(tree),
        blocks_embedded=written,
    )
```

- [ ] **Step 5: Make the four verbs list-valued**

In `update_block`: replace `        return out, None, []` with `        return out, [], []`, and in its `_mutate` call replace `block_id=block_id, expected_hash=expected_hash,` with `block_ids=[block_id], expected_hash=expected_hash,`.

In `move_block`: replace `        return others + renumbered, None, []` with `        return others + renumbered, [], []`, and in its `_mutate` call replace `touched_embed=None, verb="moved", block_id=block_id,` with `touched_embed=None, verb="moved", block_ids=[block_id],`.

In `delete_block`: replace `        return remaining, None, doomed` with `        return remaining, [], doomed`, and in its `_mutate` call replace `touched_embed=None, verb="deleted", block_id=block_id,` with `touched_embed=None, verb="deleted", block_ids=[block_id],`.

Replace the whole `insert_block` function with:

```python
async def insert_block(
    session: AsyncSession, llm, *, document_id: str, type: str, text: str,
    parent_id: str | None = None, after_block_id: str | None = None,
    properties: dict | None = None, expected_hash: str | None = None,
    block_id: str | None = None, owner: BlockOwner = DOCUMENT_OWNER,
) -> BlockWriteResult:
    minted = new_id() if block_id is None else UUID(block_id)

    def apply(tree: list[TreeBlock]):
        tree, placed = _insert_into(
            tree, owner, block_id=minted, type=type, text=text,
            properties=properties, parent_id=parent_id,
            after_block_id=after_block_id,
        )
        return tree, [placed], []

    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=str(minted), verb="inserted",
                         block_ids=[str(minted)], expected_hash=expected_hash,
                         claimed_ids=() if block_id is None else (str(minted),),
                         owner=owner)


async def insert_blocks(
    session: AsyncSession, llm, *, document_id: str, blocks: Sequence[NewBlock],
    owner: BlockOwner, expected_hash: str | None = None,
) -> BlockBatchWriteResult:
    """Every block in one pass, in order: a later block may name an earlier
    one as its parent or `after_block_id`, and the first refusal writes
    nothing."""
    ids = [str(UUID(block.block_id)) for block in blocks]
    if not ids:
        raise PageBlockInvalid("a batch insert needs at least one block")
    repeated = sorted(i for i, n in Counter(ids).items() if n > 1)
    if repeated:
        raise PageBlockInvalid(
            f"block id {repeated[0]} appears more than once in this batch"
        )

    def apply(tree: list[TreeBlock]):
        inserted = []
        for block in blocks:
            tree, placed = _insert_into(
                tree, owner, block_id=UUID(block.block_id), type=block.type,
                text=block.text, properties=block.properties,
                parent_id=block.parent_id, after_block_id=block.after_block_id,
            )
            inserted.append(placed)
        return tree, inserted, []

    result = await _mutate(session, llm, document_id=document_id, apply=apply,
                           touched_embed=None, verb="inserted", block_ids=ids,
                           expected_hash=expected_hash, claimed_ids=tuple(ids),
                           owner=owner)
    return BlockBatchWriteResult(
        owner_kind=result.owner_kind,
        owner_id=result.owner_id,
        block_ids=tuple(ids),
        outcome=result.outcome,
        content_hash=result.content_hash,
        blocks_total=result.blocks_total,
        blocks_embedded=result.blocks_embedded,
    )
```

- [ ] **Step 6: Run and watch them pass**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py tests/test_page_routes.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_mcp.py -k block
```

Expected: PASS. A pass of `test_a_primary_key_race_past_the_check_is_the_same_refusal` is the evidence that the `blocks_pkey` mapping works. If it fails with a raw `IntegrityError`, print `type(exc.orig.__cause__)` and its attributes and report: the constraint-name assumption is then wrong. If it fails with `ValueError` mentioning a parent cycle, the test's setup is wrong (the taken id is on the same page) — fix the setup, never the code.

- [ ] **Step 7: Prove the shape pin discriminates**

In `_mutate`, temporarily replace `if len(block_ids) == 1:` with `if False:`. Run:

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py::test_the_document_verbs_keep_their_result_and_journal_shape
```

Expected: FAIL on the payload key set. Restore `if len(block_ids) == 1:` and re-run: PASS. Then temporarily change the result's `block_id=block_ids[0] if len(block_ids) == 1 else None,` to `block_id=None,`, re-run: FAIL on `updated.block_id`. Restore, re-run: PASS.

Then prove the primary-key mapping discriminates: temporarily make `_violated_constraint` return `None` (replace its body with `return None`). Run:

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py::test_a_primary_key_race_past_the_check_is_the_same_refusal
```

Expected: FAIL with a raw `IntegrityError` (the mapping no longer recognises `blocks_pkey`). Restore the original body and re-run: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/block_verbs.py backend/tests/test_block_verbs.py
git commit -m "feat(blocks): client block ids and batch insert

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 5: Page edits drop vectors instead of embedding

**Files:**
- Modify: `backend/app/services/block_verbs.py` (module docstring `:7-11`, imports, `BlockOwner`, both owner instances, statements, `_mutate`)
- Test: `backend/tests/test_block_verbs.py` (autouse fixture `:28-39`; rewrite `test_a_page_block_edit_embeds_into_the_page_family` `:624-649`)

**Interfaces:**
- Consumes: the list-valued `_mutate` (Task 4), `BlockOwner` hooks (Task 3).
- Produces: `BlockOwner.embed_inline` (Contracts, Block verbs). Task 6 relies on the sweep being the only page embedder.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_block_verbs.py`, replace:

```python
FINGERPRINT = "test-fp-verbs|3"
```

with:

```python
FINGERPRINT = "test-fp-verbs|3"
SECOND_FINGERPRINT = "test-fp-verbs-second|3"
```

In the autouse `_forget_probe_fingerprint` fixture, replace both `embedder_registry.forget(FINGERPRINT)` lines so each forgets both:

```python
    embedder_registry.forget(FINGERPRINT)
    embedder_registry.forget(SECOND_FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)
    embedder_registry.forget(SECOND_FINGERPRINT)
```

Add to the top-level imports:

```python
from app.services.block_embedding_refresh import refresh_block_embeddings
```

Replace the whole `test_a_page_block_edit_embeds_into_the_page_family` function with:

```python
@pytest.mark.asyncio
async def test_a_page_block_edit_embeds_nothing_inline(session):
    """Page vectors are the sweep's to write: an embed call behind every
    typing pause is the cost this avoids. The sweep still writes the page
    family, never the document one."""
    from app.services.block_embeddings import PAGE_PARENT_TABLE, PARENT_TABLE
    from app.services.embedder_registry import child_table

    llm = StubEmbedder()
    _, block_id = await _page(session, content="page prose\n")

    await update_block(session, llm, block_id=block_id, text="edited",
                       owner=PAGE_OWNER)
    assert llm.batches == []

    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)

    async def count(parent):
        exists = (await session.execute(
            text("SELECT to_regclass(:t)"), {"t": child_table(parent, FINGERPRINT)},
        )).scalar_one()
        if exists is None:
            return 0
        return (await session.execute(
            text(f"SELECT count(*) FROM {child_table(parent, FINGERPRINT)} "
                 "WHERE block_id = CAST(:id AS uuid)"),
            {"id": block_id},
        )).scalar_one()

    assert await count(PAGE_PARENT_TABLE) == 1
    assert await count(PARENT_TABLE) == 0
```

Append:

```python
async def _page_vectors(session, block_id, fingerprint):
    from app.services.block_embeddings import PAGE_PARENT_TABLE
    from app.services.embedder_registry import child_table

    table = child_table(PAGE_PARENT_TABLE, fingerprint)
    exists = (await session.execute(
        text("SELECT to_regclass(CAST(:t AS text)) IS NOT NULL"), {"t": table},
    )).scalar_one()
    if not exists:
        return 0
    return (await session.execute(
        text(f"SELECT count(*) FROM {table} WHERE block_id = CAST(:id AS uuid)"),
        {"id": block_id},
    )).scalar_one()


@pytest.mark.parametrize(
    "change", [{"text": "rewritten"}, {"text": "page prose", "type": "quote"}],
)
@pytest.mark.asyncio
async def test_a_page_text_or_type_edit_drops_its_vectors_in_every_live_fingerprint(
    session, change,
):
    """The sweep fills only blocks with no vector, so an edit that kept its
    old vector would stay stale forever."""
    llm, second = StubEmbedder(), StubEmbedder(SECOND_FINGERPRINT)
    _, block_id = await _page(session, content="page prose\n")
    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    await refresh_block_embeddings(session, second, batch=0, page_batch=100)
    assert await _page_vectors(session, block_id, FINGERPRINT) == 1
    assert await _page_vectors(session, block_id, SECOND_FINGERPRINT) == 1
    llm.batches.clear()

    await update_block(session, llm, block_id=block_id, owner=PAGE_OWNER, **change)

    assert llm.batches == []
    assert await _page_vectors(session, block_id, FINGERPRINT) == 0
    assert await _page_vectors(session, block_id, SECOND_FINGERPRINT) == 0
    outcome = await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    assert outcome.embedded == 1
    assert await _page_vectors(session, block_id, FINGERPRINT) == 1


@pytest.mark.asyncio
async def test_a_properties_only_page_edit_keeps_its_vector(session):
    """Ticking a to-do changes nothing the embedder reads."""
    llm = StubEmbedder()
    page_id, _ = await _page(session, content="page prose\n")
    todo = await insert_block(session, llm, document_id=page_id, type="todo",
                              text="task", properties={"checked": False},
                              owner=PAGE_OWNER)
    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    assert await _page_vectors(session, todo.block_id, FINGERPRINT) == 1

    await update_block(session, llm, block_id=todo.block_id, text="task",
                       properties={"checked": True}, owner=PAGE_OWNER)

    assert await _page_vectors(session, todo.block_id, FINGERPRINT) == 1


@pytest.mark.asyncio
async def test_a_missing_child_table_does_not_abort_the_edit(session):
    from app.services.block_embeddings import PAGE_PARENT_TABLE
    from app.services.embedder_registry import child_table

    llm, second = StubEmbedder(), StubEmbedder(SECOND_FINGERPRINT)
    _, block_id = await _page(session, content="page prose\n")
    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    await refresh_block_embeddings(session, second, batch=0, page_batch=100)
    await session.execute(
        text(f"DROP TABLE {child_table(PAGE_PARENT_TABLE, SECOND_FINGERPRINT)}")
    )

    result = await update_block(session, llm, block_id=block_id, text="rewritten",
                                owner=PAGE_OWNER)

    assert result.outcome == "updated"
    assert await _page_vectors(session, block_id, FINGERPRINT) == 0
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py
```

Expected: `test_a_page_block_edit_embeds_nothing_inline` fails on `llm.batches == []`, and the text/type-edit tests fail on the vectors still present.

- [ ] **Step 3: Add the descriptor field and the statements**

In the module docstring, replace:

```
SAVEPOINT, journal, commit, then embed only the block that changed. The
```

with:

```
SAVEPOINT, journal, commit, then embed only the block that changed -- for a
document. A page edit embeds nothing: it drops the changed block's vectors and
the hourly sweep refills them. The
```

After `from app.services.document_ingest import DocumentHashConflict, compute_content_hash` add:

```python
from app.services.embedder_registry import child_table
```

In `BlockOwner`, after `check_nesting: Callable[[TreeBlock | None, TreeBlock], None]` add:

```python
    # False means the sweep is this owner's only embedder, so an edit that
    # changes what the embedder reads must delete the stale vector: the sweep
    # fills only blocks that have none.
    embed_inline: bool
```

In `DOCUMENT_OWNER` after `check_nesting=_any_parent,` add `    embed_inline=True,`. In `PAGE_OWNER` after `check_nesting=_check_page_nesting,` add `    embed_inline=False,`.

After `_TAKEN_IDS = text(...)` add:

```python
_LIVE_FINGERPRINTS = text(
    "SELECT fingerprint FROM embedders WHERE retired_at IS NULL ORDER BY fingerprint"
)
_RELATION_EXISTS = text("SELECT to_regclass(CAST(:name AS text)) IS NOT NULL")
```

Above `async def _mutate(` add:

```python
async def _drop_vectors(session, owner: BlockOwner, block_id: str) -> None:
    fingerprints = (await session.execute(_LIVE_FINGERPRINTS)).scalars().all()
    for fingerprint in fingerprints:
        table = child_table(owner.embed_parent, fingerprint)
        # Boot reconciliation creates every live fingerprint's children, but a
        # hand-dropped one would otherwise abort the whole savepoint.
        exists = (
            await session.execute(_RELATION_EXISTS, {"name": table})
        ).scalar_one()
        if exists:
            await session.execute(
                text(f"DELETE FROM {table} WHERE block_id = CAST(:id AS uuid)"),
                {"id": block_id},
            )


```

- [ ] **Step 4: Drop on a text or type change, embed only inline owners**

In `_mutate`, replace:

```python
    tree, inserted, deleted_subtree = apply(tree)
```

with:

```python
    before = {block.id: block for block in tree}
    tree, inserted, deleted_subtree = apply(tree)
```

Replace:

```python
                    "parent": None if target.parent_id is None else str(target.parent_id),
                })

            placed = {p.block_id: p for p in result.placed}
```

with:

```python
                    "parent": None if target.parent_id is None else str(target.parent_id),
                })
                previous = before[target.id]
                if not owner.embed_inline and (
                    previous.text != target.text or previous.type != target.type
                ):
                    await _drop_vectors(session, owner, block_ids[0])

            placed = {p.block_id: p for p in result.placed}
```

Replace:

```python
    if touched_embed is not None:
```

with:

```python
    if owner.embed_inline and touched_embed is not None:
```

- [ ] **Step 5: Run and watch them pass**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py tests/test_block_embeddings.py tests/test_page_routes.py
```

Expected: PASS, including `test_update_embeds_only_the_touched_block` (documents still embed inline).

- [ ] **Step 6: Prove the vector drop discriminates**

Temporarily comment out the line `await _drop_vectors(session, owner, block_ids[0])` (replace it with `pass`). Run:

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q "tests/test_block_verbs.py::test_a_page_text_or_type_edit_drops_its_vectors_in_every_live_fingerprint"
```

Expected: both parametrisations FAIL on `_page_vectors(...) == 0`. Restore the call and re-run: PASS. Then temporarily replace `if exists:` with `if True:` and run `tests/test_block_verbs.py::test_a_missing_child_table_does_not_abort_the_edit`: expected FAIL (undefined table). Restore and re-run: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/block_verbs.py backend/tests/test_block_verbs.py
git commit -m "feat(blocks): drop page vectors on edit

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 6: Flatten headings and stop embedding on page create

**Files:**
- Modify: `backend/app/services/page_door.py` (docstring `:10-12`, imports `:16-28`, `PageResult` `:107-116`, after `_parse` `:342`, `create_page` `:411-495`)
- Modify: `backend/app/schemas/page.py:28-36`
- Test: `backend/tests/test_page_door.py` (`:187-216`, `:695-718`, new tests)
- Test: `backend/tests/test_page_document_isolation.py` (fixture `:134-157`, `:258-275`)

**Interfaces:**
- Consumes: the sweep being the only page embedder (Task 5).
- Produces: `PageResult` / `PageCreateResponse` without `blocks_embedded`; `_flatten_headings` (Contracts, Page door and Schemas).

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_page_door.py`, add to the imports:

```python
from app.services.block_embedding_refresh import refresh_block_embeddings
from app.services.block_serializer import serialize_tree
```

and add `_flatten_headings,` and `_parse,` to the `from app.services.page_door import (...)` list (after `PageTargetUnresolved,`).

Append:

```python
NESTED_HEADINGS = (
    "# A\n\npara\n\n## B\n\n- x\n- y\n\n1. o\n2. p\n\n"
    "### C\n\n```py\ncode\n```\n\n# D\n\n> q\n\n---\n"
)


def _heading_parented(tree):
    by_id = {block.id: block for block in tree}
    return [
        block for block in tree
        if block.parent_id is not None and by_id[block.parent_id].type == "heading"
    ]


@pytest.mark.asyncio
async def test_create_flattens_heading_nesting_losslessly(session, llm):
    """On a page only list, todo and toggle blocks hold children, so a
    heading-nested tree could not be extended by the editor. Flattening must
    not change a byte of the stored content."""
    unflattened = _parse(NESTED_HEADINGS)
    assert _heading_parented(unflattened), "fixture precondition: nested headings"

    page = await create_page(session, llm, project="p", title="n",
                             content=NESTED_HEADINGS)

    nested = (await session.execute(
        text(
            "SELECT count(*) FROM blocks b JOIN blocks parent ON parent.id = b.parent_id "
            "WHERE b.page_id = CAST(:id AS uuid) AND parent.type = 'heading'"
        ),
        {"id": str(page.id)},
    )).scalar_one()
    assert nested == 0
    row = await _page_row(session, page.id)
    assert row["content"] == serialize_tree(unflattened).content


def test_flattening_a_heading_inside_a_quote_keeps_the_quote_as_parent():
    tree = _parse("> # H\n\n- a\n- b\n")
    flat = _flatten_headings(tree)

    assert not _heading_parented(flat)
    quote = next(block for block in flat if block.type == "quote")
    assert {b.parent_id for b in flat if b.type == "list"} == {quote.id}
    assert serialize_tree(flat).content == serialize_tree(tree).content


@pytest.mark.asyncio
async def test_creating_a_page_embeds_nothing_inline(session, llm):
    await create_page(session, llm, project="p", title="n", content="# T\n\nbody\n")
    assert llm.batches == []
```

Replace the body of `test_a_page_embeds_into_the_page_partition` from `    page = await create_page(` through `    assert count == 2` with:

```python
    page = await create_page(session, llm, project="p", title="n",
                             content="# T\n\nbody\n")
    outcome = await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    assert outcome.embedded == 2
    table = child_table("page_embeddings", FINGERPRINT)
    count = (
        await session.execute(
            text(
                f"SELECT count(*) FROM {table} e JOIN blocks b ON b.id = e.block_id "
                "WHERE b.page_id = CAST(:id AS uuid)"
            ),
            {"id": str(page.id)},
        )
    ).scalar_one()
    assert count == 2
```

In `test_purge_removes_rows_blocks_and_vectors`, replace:

```python
    assert len(block_ids) == 3
    table = child_table("page_embeddings", FINGERPRINT)
```

with:

```python
    assert len(block_ids) == 3
    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    table = child_table("page_embeddings", FINGERPRINT)
```

In `backend/tests/test_page_document_isolation.py`, in the `isolation` fixture replace the docstring line `    blocks, both filed and embedded through the doors that ship."""` with:

```python
    blocks, filed through the doors that ship. The document embeds inline; the
    page's blocks are left for the sweep, as a page create leaves them."""
```

and delete the line:

```python
    assert page.blocks_embedded == len(page_blocks)
```

In `test_page_vectors_live_in_their_own_partition`, replace:

```python
    fingerprint = llm.llm_fingerprint()
    page_table = child_table(PAGE_PARENT_TABLE, fingerprint)
```

with:

```python
    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    fingerprint = llm.llm_fingerprint()
    page_table = child_table(PAGE_PARENT_TABLE, fingerprint)
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_door.py tests/test_page_document_isolation.py
```

Expected: collection error `ImportError: cannot import name '_flatten_headings'`.

- [ ] **Step 3: Implement flattening and remove inline embedding**

In `backend/app/services/page_door.py`, replace the docstring paragraph:

```
Embedding runs after the filing commits, as on the document door: first
contact with an unknown fingerprint runs child-table DDL through
`embedder_registry.register`, which commits on this session.
```

with:

```
Nothing here embeds. A new page block has no vector, and the hourly
`block_embedding_refresh` sweep's page arm fills it, so a create costs no
embedder call.
```

Replace:

```python
from dataclasses import dataclass
```

with:

```python
from dataclasses import dataclass, replace
```

Delete the line:

```python
from app.services.block_embeddings import PAGE_PARENT_TABLE, embed_blocks
```

In `PageResult`, delete the line `    blocks_embedded: int`.

Directly after the `_parse` function add:

```python
def _flatten_headings(tree: list[TreeBlock]) -> list[TreeBlock]:
    """Re-parent each heading's children onto its nearest non-heading
    ancestor, keeping reading order.

    The parser nests everything under the nearest open heading, but a page
    holds children only under list, todo and toggle blocks. A heading adds no
    child prefix, so the serialisation is unchanged for headings at the root
    or inside a quote -- except where a heading inside a list item adopts a
    later sibling item, which flattening turns into a tight nested item.
    """
    by_id = {block.id: block for block in tree}
    children: dict[UUID | None, list[TreeBlock]] = {}
    for block in tree:
        children.setdefault(block.parent_id, []).append(block)
    for siblings in children.values():
        siblings.sort(key=lambda b: (b.order_index, str(b.id)))

    reading_order: list[TreeBlock] = []
    stack = list(reversed(children.get(None, [])))
    while stack:
        block = stack.pop()
        reading_order.append(block)
        stack.extend(reversed(children.get(block.id, [])))

    flat: list[TreeBlock] = []
    for position, block in enumerate(reading_order):
        parent = block.parent_id
        while parent is not None and by_id[parent].type == "heading":
            parent = by_id[parent].parent_id
        flat.append(replace(block, parent_id=parent, order_index=position))
    return flat
```

In `create_page`, replace:

```python
    tree = _parse(content) if content else []
```

with:

```python
    tree = _flatten_headings(_parse(content)) if content else []
```

Replace:

```python
    await session.commit()

    written = 0
    if tree:
        result = await embed_blocks(
            session, llm,
            block_ids=[str(block.id) for block in tree],
            parent=PAGE_PARENT_TABLE,
        )
        written = result.written if result else 0
        await session.commit()

    return PageResult(
```

with:

```python
    await session.commit()

    return PageResult(
```

and delete the line `        blocks_embedded=written,` from the `PageResult(...)` call.

In `backend/app/schemas/page.py`, delete the line `    blocks_embedded: int` from `PageCreateResponse`.

- [ ] **Step 4: Run and watch them pass**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_door.py tests/test_page_document_isolation.py tests/test_page_routes.py
```

Expected: PASS.

- [ ] **Step 5: Prove the flattening test discriminates**

Temporarily change `tree = _flatten_headings(_parse(content)) if content else []` back to `tree = _parse(content) if content else []`. Run:

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_door.py::test_create_flattens_heading_nesting_losslessly
```

Expected: FAIL on `assert nested == 0`. Restore. Then, inside `_flatten_headings`, temporarily replace `stack.extend(reversed(children.get(block.id, [])))` with `stack.extend(children.get(block.id, []))` (children in reverse reading order) and re-run the same test: expected FAIL on the byte-identity assertion. Restore and re-run: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/page_door.py backend/app/schemas/page.py \
        backend/tests/test_page_door.py backend/tests/test_page_document_isolation.py
git commit -m "feat(pages): flatten headings, embed via sweep

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 7: Pin the document surfaces as unchanged

**Files:**
- Test: `backend/tests/test_page_document_isolation.py`

**Interfaces:**
- Consumes: `DOCUMENT_OWNER.normalize_type` (Task 3), `insert_block(..., block_id=...)` (Task 4).
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 0 - spec 0 - coupling 1 - risk 0 = 1

These pass on arrival — the document path is meant to be untouched. The discrimination proofs are what make them evidence.

- [ ] **Step 1: Write the tests**

In `backend/tests/test_page_document_isolation.py`, add to the imports:

```python
from app.services.block_verbs import insert_block, update_block
from app.services.document_parsers import parse_markdown
from app.taxonomy import BLOCK_TYPES, PAGE_BLOCK_TYPES
```

and replace the existing `from uuid import UUID` line with:

```python
from uuid import UUID, uuid4
```

Append:

```python
PAGE_ONLY_MARKDOWN = (
    "- [ ] open task\n- [x] done task\n\n"
    "> [!NOTE]\n> a callout\n\n"
    "<details>\n<summary>A toggle</summary>\n\nbody\n\n</details>\n"
)


def test_the_document_parser_mints_no_page_only_type():
    """The page-only types are the page editor's; a filed document carrying
    their markdown spellings parses exactly as it did before they existed."""
    drafts = parse_markdown(PAGE_ONLY_MARKDOWN)
    types = {draft.type for draft in drafts}

    assert types <= set(BLOCK_TYPES)
    assert not types & set(PAGE_BLOCK_TYPES)
    assert {"list", "quote", "html"} <= types
    assert any(draft.text.startswith("[ ] ") for draft in drafts)


@pytest.mark.asyncio
async def test_a_document_block_verb_folds_a_page_only_type_to_paragraph(
    session, llm, isolation,
):
    inserted = await insert_block(
        session, llm, document_id=isolation.document_id, type="todo",
        text="not a task here", properties={"checked": True},
    )
    blocks = await _owned_blocks(session, document_id=isolation.document_id)
    assert next(b for b in blocks if b["id"] == inserted.block_id)["type"] == "paragraph"

    await update_block(session, llm, block_id=inserted.block_id,
                       text="still prose", type="callout")
    blocks = await _owned_blocks(session, document_id=isolation.document_id)
    assert next(b for b in blocks if b["id"] == inserted.block_id)["type"] == "paragraph"


@pytest.mark.asyncio
async def test_the_document_insert_route_does_not_read_a_block_id(
    session, isolation, client, auth_headers,
):
    """Only the page request model carries `block_id`; the shared document
    model ignores the key, so the server still mints the id."""
    supplied = str(uuid4())

    response = await client.post(
        f"{V1}/documents/{isolation.document_id}/blocks",
        json={"type": "paragraph", "text": "routed", "block_id": supplied},
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["block_id"] != supplied
    stored = (await session.execute(
        text("SELECT count(*) FROM blocks WHERE id = CAST(:id AS uuid)"),
        {"id": supplied},
    )).scalar_one()
    assert stored == 0


@pytest.mark.asyncio
async def test_the_document_block_delete_carries_no_content_hash_header(
    isolation, client, auth_headers,
):
    response = await client.delete(
        f"{V1}/documents/{isolation.document_id}/blocks/{isolation.document_block_ids[-1]}",
        headers=auth_headers,
    )

    assert response.status_code == 204
    assert "x-content-hash" not in response.headers
```

- [ ] **Step 2: Run them**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_document_isolation.py
```

Expected: PASS.

- [ ] **Step 3: Prove the normalisation pin discriminates**

In `backend/app/services/block_verbs.py`'s `DOCUMENT_OWNER`, temporarily replace `normalize_type=normalize_block_type,` with `normalize_type=normalize_page_block_type,`. Run:

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_document_isolation.py::test_a_document_block_verb_folds_a_page_only_type_to_paragraph
```

Expected: FAIL (`'todo' == 'paragraph'`). Restore `normalize_type=normalize_block_type,` and re-run: PASS.

- [ ] **Step 4: Prove the block-id pin discriminates**

In `backend/app/api/routes/documents.py`, temporarily add `    block_id: str | None = None` as the last field of `BlockInsertRequest`, and add `block_id=body.block_id,` after `expected_hash=body.expected_hash,` in `insert_block_route`'s `insert_block(...)` call. Run:

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_document_isolation.py::test_the_document_insert_route_does_not_read_a_block_id
```

Expected: FAIL on `!= supplied`. Revert both edits (`git diff backend/app/api/routes/documents.py` must print nothing) and re-run: PASS.

- [ ] **Step 5: Prove the header pin discriminates**

In `backend/app/api/routes/documents.py`, temporarily add `from fastapi import Response` below the existing fastapi import, add a parameter `response: Response,` after `block_id: UUID,` in `delete_block_route`, and add `    response.headers["X-Content-Hash"] = "probe"` as its last line. Run:

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_document_isolation.py::test_the_document_block_delete_carries_no_content_hash_header
```

Expected: FAIL. Revert (`git diff backend/app/api/routes/documents.py` prints nothing) and re-run: PASS.

- [ ] **Step 6: Commit**

```bash
git status --short   # only the test file may be modified
git add backend/tests/test_page_document_isolation.py
git commit -m "test(pages): pin document surfaces as unchanged

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 8: Page-only block request models and refusals

**Files:**
- Modify: `backend/app/schemas/page.py` (imports `:1-6`, append models)
- Modify: `backend/app/api/routes/pages.py` (imports `:22-72`, `_block_write_error` / `_BLOCK_REFUSALS` `:236-251`, the four block routes `:267-357`)
- Test: `backend/tests/test_page_routes.py`

**Interfaces:**
- Consumes: `PageBlockInvalid` (Task 3), `PageBlockIdTaken`, `insert_block(..., block_id=...)` (Task 4).
- Produces: `PageBlockInsertRequest`, `PageBlockUpdateRequest`, `PageBlockMoveRequest`, `PageBlockBatchItem`, `PageBlockBatchInsertRequest`; the 422/409 mapping and the `X-Content-Hash` header (Contracts, Schemas and Routes). Task 9 consumes the batch models and the mapping.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_page_routes.py`:

```python
async def _insert(client, auth_headers, page, **body):
    return await client.post(
        f"{V1}/pages/{page}/blocks", json=body, headers=auth_headers,
    )


@pytest.mark.asyncio
async def test_a_page_block_insert_refuses_an_unknown_field(client, auth_headers, create):
    page = await create(content="para\n")
    response = await _insert(client, auth_headers, page,
                             type="paragraph", text="x", bogus=1)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "type_, properties",
    [("todo", {"checked": False}), ("toggle", None), ("callout", {"variant": "warning"})],
)
@pytest.mark.asyncio
async def test_each_page_only_type_is_accepted(
    client, auth_headers, create, type_, properties,
):
    page = await create(content="para\n")
    response = await _insert(client, auth_headers, page,
                             type=type_, text="x", properties=properties)
    assert response.status_code == 201, response.text
    block = next(b for b in await _blocks_of(client, auth_headers, page)
                 if b["id"] == response.json()["block_id"])
    assert block["type"] == type_


@pytest.mark.parametrize(
    "type_, properties",
    [("todo", None), ("todo", {"checked": "yes"}), ("callout", {"variant": "loud"})],
)
@pytest.mark.asyncio
async def test_a_page_only_type_with_invalid_properties_is_422(
    client, auth_headers, create, type_, properties,
):
    page = await create(content="para\n")
    response = await _insert(client, auth_headers, page,
                             type=type_, text="x", properties=properties)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_type_change_leaving_a_required_property_missing_is_422(
    client, auth_headers, create,
):
    page = await create(content="para\n")
    block = (await _blocks_of(client, auth_headers, page))[0]
    response = await client.patch(
        f"{V1}/pages/{page}/blocks/{block['id']}",
        json={"text": "para", "type": "todo"}, headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_nesting_under_a_paragraph_is_422_on_insert_and_move(
    client, auth_headers, create,
):
    page = await create(content="alpha\n\nbeta\n")
    alpha, beta = await _blocks_of(client, auth_headers, page)

    inserted = await _insert(client, auth_headers, page, type="paragraph",
                             text="child", parent_id=alpha["id"])
    moved = await client.post(
        f"{V1}/pages/{page}/blocks/{beta['id']}/move",
        json={"new_parent_id": alpha["id"]}, headers=auth_headers,
    )

    assert inserted.status_code == 422
    assert moved.status_code == 422


@pytest.mark.asyncio
async def test_a_client_block_id_becomes_the_block_id(client, auth_headers, create):
    page = await create(content="para\n")
    chosen = str(uuid4())
    response = await _insert(client, auth_headers, page,
                             type="paragraph", text="x", block_id=chosen)
    assert response.status_code == 201, response.text
    assert response.json()["block_id"] == chosen


@pytest.mark.asyncio
async def test_a_taken_block_id_is_409(client, auth_headers, create):
    page = await create(content="para\n")
    existing = (await _blocks_of(client, auth_headers, page))[0]["id"]
    response = await _insert(client, auth_headers, page,
                             type="paragraph", text="x", block_id=existing)
    assert response.status_code == 409
    assert response.json()["detail"] == f"block id {existing} already exists"


@pytest.mark.asyncio
async def test_a_page_block_delete_answers_the_new_hash_in_a_header(
    client, auth_headers, create,
):
    page = await create(content="alpha\n\nbeta\n")
    alpha = (await _blocks_of(client, auth_headers, page))[0]

    response = await client.delete(
        f"{V1}/pages/{page}/blocks/{alpha['id']}", headers=auth_headers,
    )

    assert response.status_code == 204
    current = (await client.get(f"{V1}/pages/{page}", headers=auth_headers)).json()
    assert response.headers["x-content-hash"] == current["content_hash"]
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_routes.py
```

Expected: the unknown-field, block-id, 409, invalid-properties and header tests FAIL. The invalid-properties and type-change tests fail either as a 500 response or as an unhandled `PageBlockInvalid` raised through the test client — both mean the refusal is unmapped.

- [ ] **Step 3: Add the page request models**

In `backend/app/schemas/page.py`, after `from pydantic import BaseModel, ConfigDict, Field` add the import below. It creates no cycle — `app.services.page_door`'s import closure reaches no `app.schemas` or `app.api` module (see Assumptions); if `import app.main` ever fails with a partially initialised module naming `app.schemas.page`, stop and report rather than moving the constant:

```python

from app.services.page_door import MAX_BLOCKS
```

Append:

```python
class PageBlockInsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    text: str
    parent_id: str | None = None
    after_block_id: str | None = None
    properties: dict | None = None
    expected_hash: str | None = None
    block_id: UUID | None = Field(
        None,
        description=(
            "The new block's id, chosen by the client so it can address the "
            "block before the response arrives. Absent mints one."
        ),
    )


class PageBlockUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    type: str | None = None
    properties: dict | None = None
    expected_hash: str | None = None


class PageBlockMoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_parent_id: str | None = None
    after_block_id: str | None = None
    expected_hash: str | None = None


class PageBlockBatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: UUID
    type: str = Field(min_length=1)
    text: str
    properties: dict | None = None
    parent_id: UUID | None = None
    after_block_id: UUID | None = None


class PageBlockBatchInsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocks: list[PageBlockBatchItem] = Field(min_length=1, max_length=MAX_BLOCKS)
    expected_hash: str | None = None
```

- [ ] **Step 4: Switch the routes to the page models and map the refusals**

In `backend/app/api/routes/pages.py`, replace:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
```

with:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
```

Delete:

```python
from app.api.routes.documents import (
    BlockInsertRequest,
    BlockMoveRequest,
    BlockUpdateRequest,
)
```

In the `from app.schemas.page import (...)` list add `PageBlockInsertRequest,`, `PageBlockMoveRequest,` and `PageBlockUpdateRequest,` before `PageCreateRequest,`. In the `from app.services.block_verbs import (...)` list add `PageBlockIdTaken,` and `PageBlockInvalid,` after `BlockTargetUnresolved,`.

Replace `_block_write_error` and `_BLOCK_REFUSALS` with:

```python
def _block_write_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BlockTargetUnresolved):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, (BlockCycleError, DocumentTooLarge, PageBlockInvalid)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    if isinstance(exc, PageBlockIdTaken):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    if isinstance(exc, DocumentHashConflict):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"expected_hash {exc.expected_hash} does not match the "
            f"page's current content_hash {exc.current_hash}",
        )
    raise exc


_BLOCK_REFUSALS = (BlockTargetUnresolved, BlockCycleError, DocumentTooLarge,
                   DocumentHashConflict, PageBlockInvalid, PageBlockIdTaken)
```

In `insert_page_block_route`, replace `    body: BlockInsertRequest,` with `    body: PageBlockInsertRequest,` and replace:

```python
            expected_hash=body.expected_hash, owner=PAGE_OWNER,
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    return _response(result)


@router.patch("/{page_id}/blocks/{block_id}", response_model=PageBlockWriteResponse)
```

with:

```python
            expected_hash=body.expected_hash, block_id=_str(body.block_id),
            owner=PAGE_OWNER,
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    return _response(result)


@router.patch("/{page_id}/blocks/{block_id}", response_model=PageBlockWriteResponse)
```

In `update_page_block_route` replace `    body: BlockUpdateRequest,` with `    body: PageBlockUpdateRequest,`. In `move_page_block_route` replace `    body: BlockMoveRequest,` with `    body: PageBlockMoveRequest,`.

Replace the whole `delete_page_block_route` with:

```python
@router.delete("/{page_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page_block_route(
    page_id: UUID,
    block_id: UUID,
    response: Response,
    expected_hash: str | None = Query(
        None, description="Refuse unless the page's content_hash matches."
    ),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> None:
    """The subtree goes with it. `expected_hash` rides the query string because
    a DELETE carries no body here, and the page's new hash rides the
    `X-Content-Hash` header because a 204 carries none either -- without it a
    client chaining preconditions would need a re-read after every delete."""
    await _assert_block_is_in(session, page_id, block_id)
    try:
        result = await delete_block(
            session, llm, block_id=str(block_id), expected_hash=expected_hash,
            owner=PAGE_OWNER,
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    response.headers["X-Content-Hash"] = result.content_hash
```

- [ ] **Step 5: Run and watch them pass**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_routes.py tests/test_page_document_isolation.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_api/test_rest_conformance.py tests/test_door_parity.py tests/test_content_surface_scoping.py
```

Expected: PASS. No route was added, so the guards stay green.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/page.py backend/app/api/routes/pages.py backend/tests/test_page_routes.py
git commit -m "feat(pages): page block models, ids and refusals

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 9: The batch insert route and its guard entries

**Files:**
- Modify: `backend/app/api/routes/pages.py` (module docstring `:3-14`, imports, after `insert_page_block_route`)
- Modify: `backend/app/services/content_surfaces.py:724`
- Modify: `backend/tests/test_api/test_rest_conformance.py:197-211`
- Modify: `backend/tests/test_door_parity.py:1545`
- Modify: `docs/two-door-parity.md` (regenerated between its markers)
- Test: `backend/tests/test_page_routes.py`

**Interfaces:**
- Consumes: `insert_blocks`, `NewBlock` (Task 4); `PageBlockBatchInsertRequest`, `_BLOCK_REFUSALS`, `_block_write_error` (Task 8).
- Produces: `POST /api/v1/pages/{page_id}/blocks/batch` (Contracts, Routes).

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

The route and its three guard entries land in one commit: every guard is bidirectional, so either half alone is red.

- [ ] **Step 1: Write the failing route tests**

Append to `backend/tests/test_page_routes.py`:

```python
@pytest.mark.asyncio
async def test_a_batch_inserts_in_order_with_intra_batch_references(
    client, auth_headers, create,
):
    page = await create(content="para\n")
    prose = (await _blocks_of(client, auth_headers, page))[0]["id"]
    toggle, inside, task = (str(uuid4()) for _ in range(3))

    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [
            {"block_id": toggle, "type": "toggle", "text": "T", "after_block_id": prose},
            {"block_id": inside, "type": "paragraph", "text": "inside", "parent_id": toggle},
            {"block_id": task, "type": "todo", "text": "task",
             "properties": {"checked": False}, "after_block_id": toggle},
        ]},
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["block_ids"] == [toggle, inside, task]
    assert body["outcome"] == "inserted"
    assert set(body) == {"page_id", "block_ids", "outcome", "content_hash",
                         "blocks_total", "blocks_embedded"}
    blocks = await _blocks_of(client, auth_headers, page)
    assert [b["id"] for b in blocks] == [prose, toggle, inside, task]
    assert next(b for b in blocks if b["id"] == inside)["parent_id"] == toggle


@pytest.mark.asyncio
async def test_a_batch_with_an_invalid_item_writes_nothing(client, auth_headers, create):
    page = await create(content="para\n")
    before = (await client.get(f"{V1}/pages/{page}", headers=auth_headers)).json()

    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [
            {"block_id": str(uuid4()), "type": "paragraph", "text": "fine"},
            {"block_id": str(uuid4()), "type": "todo", "text": "no checked"},
        ]},
        headers=auth_headers,
    )

    assert response.status_code == 422
    after = (await client.get(f"{V1}/pages/{page}", headers=auth_headers)).json()
    assert after["content_hash"] == before["content_hash"]
    assert len(after["blocks"]) == len(before["blocks"])


@pytest.mark.asyncio
async def test_a_batch_repeating_a_block_id_is_422(client, auth_headers, create):
    page = await create(content="para\n")
    repeated = str(uuid4())
    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [
            {"block_id": repeated, "type": "paragraph", "text": "a"},
            {"block_id": repeated, "type": "paragraph", "text": "b"},
        ]},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_batch_naming_a_taken_block_id_is_409(client, auth_headers, create):
    page = await create(content="para\n")
    existing = (await _blocks_of(client, auth_headers, page))[0]["id"]
    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch",
        json={"blocks": [{"block_id": existing, "type": "paragraph", "text": "a"}]},
        headers=auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_an_empty_batch_is_422(client, auth_headers, create):
    page = await create(content="para\n")
    response = await client.post(
        f"{V1}/pages/{page}/blocks/batch", json={"blocks": []}, headers=auth_headers,
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_routes.py
```

Expected: the five batch tests FAIL with 404/405 (no such route).

- [ ] **Step 3: Add the route**

In `backend/app/api/routes/pages.py`'s module docstring, after the line `  - POST   /api/v1/pages/{page_id}/blocks` add:

```
  - POST   /api/v1/pages/{page_id}/blocks/batch
```

In the `from app.schemas.page import (...)` list add `PageBlockBatchInsertRequest,` before `PageBlockInsertRequest,`. In the `from app.services.block_verbs import (...)` list add `NewBlock,` after `BlockTargetUnresolved,` and `insert_blocks,` after `insert_block,`.

Directly after `insert_page_block_route` add:

```python
class PageBlockBatchWriteResponse(BaseModel):
    page_id: str
    block_ids: list[str]
    outcome: str
    content_hash: str
    blocks_total: int
    blocks_embedded: int


@router.post(
    "/{page_id}/blocks/batch",
    response_model=PageBlockBatchWriteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def insert_page_blocks_route(
    page_id: UUID,
    body: PageBlockBatchInsertRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    llm=Depends(get_llm),
) -> PageBlockBatchWriteResponse:
    """Every item in one pass, applied in order: an item may name an earlier
    item's `block_id` as its parent or `after_block_id`, and the first refusal
    writes nothing. A paste of N blocks is one page rewrite, not N."""
    try:
        result = await insert_blocks(
            session, llm, document_id=str(page_id), owner=PAGE_OWNER,
            expected_hash=body.expected_hash,
            blocks=[
                NewBlock(
                    block_id=str(item.block_id), type=item.type, text=item.text,
                    properties=item.properties, parent_id=_str(item.parent_id),
                    after_block_id=_str(item.after_block_id),
                )
                for item in body.blocks
            ],
        )
    except _BLOCK_REFUSALS as exc:
        raise _block_write_error(exc) from exc
    return PageBlockBatchWriteResponse(
        page_id=result.owner_id, block_ids=list(result.block_ids),
        outcome=result.outcome, content_hash=result.content_hash,
        blocks_total=result.blocks_total, blocks_embedded=result.blocks_embedded,
    )
```

- [ ] **Step 4: Classify the route in the three guards**

In `backend/app/services/content_surfaces.py`, replace:

```python
    "POST /api/v1/pages/{page_id}/blocks",
    "PATCH /api/v1/pages/{page_id}/blocks/{block_id}",
```

with:

```python
    "POST /api/v1/pages/{page_id}/blocks",
    "POST /api/v1/pages/{page_id}/blocks/batch",
    "PATCH /api/v1/pages/{page_id}/blocks/{block_id}",
```

In `backend/tests/test_api/test_rest_conformance.py`, replace:

```python
    # write and block-verb doors above: both creates are 201 (a page, and a
    # block inserted into one), both deletes are 204, everything else is 200.
```

with:

```python
    # write and block-verb doors above: every create is 201 (a page, a block
    # inserted into one, and a batch of blocks), both deletes are 204,
    # everything else is 200.
```

and:

```python
    ("POST", "/api/v1/pages/{page_id}/blocks"): 201,
```

with:

```python
    ("POST", "/api/v1/pages/{page_id}/blocks"): 201,
    ("POST", "/api/v1/pages/{page_id}/blocks/batch"): 201,
```

In `backend/tests/test_door_parity.py`, in the `pages.write` surface, replace:

```python
            ("POST", f"{V1}/pages/{{page_id}}/blocks"),
            ("PATCH", f"{V1}/pages/{{page_id}}/blocks/{{block_id}}"),
```

with:

```python
            ("POST", f"{V1}/pages/{{page_id}}/blocks"),
            ("POST", f"{V1}/pages/{{page_id}}/blocks/batch"),
            ("PATCH", f"{V1}/pages/{{page_id}}/blocks/{{block_id}}"),
```

- [ ] **Step 5: Regenerate the parity table**

```bash
cd backend && timeout 120 .venv/bin/python - <<'EOF'
from tests.test_door_parity import PARITY_DOC, _DOC_BEGIN, _DOC_END, render_markdown

doc = PARITY_DOC.read_text(encoding="utf-8")
head, rest = doc.split(_DOC_BEGIN, 1)
_, tail = rest.split(_DOC_END, 1)
PARITY_DOC.write_text(
    f"{head}{_DOC_BEGIN}\n{render_markdown()}\n{_DOC_END}{tail}", encoding="utf-8",
)
EOF
cd .. && git diff --stat docs/two-door-parity.md
```

Expected: the diff touches only the `pages.write` row inside the generated block, and the headline `**80 surfaces: 25 two-door, 55 single-door with a stated reason (48 REST-only, 7 MCP-only), 0 divergent.**` is unchanged (no surface was added). The line count in `--stat` depends on git's diff rendering and is not the check; Step 6's `test_the_committed_table_is_the_enforced_table` and `test_the_committed_table_reports_its_own_counts` are.

- [ ] **Step 6: Run the route tests and the guards**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_routes.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/pages.py backend/app/services/content_surfaces.py \
        backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py \
        backend/tests/test_page_routes.py docs/two-door-parity.md
git commit -m "feat(pages): batch insert page blocks over REST

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 10: Serve block source and list the trash

**Files:**
- Modify: `backend/app/services/page_door.py` (`__all__` `:30-56`, `_GET_BLOCKS` `:239-245`, new `_TRASH_ROOTS` after `_LIST_PAGES`, new `list_trash` after `list_pages`)
- Modify: `backend/app/schemas/page.py` (`PageBlock` `:39-47`, new `PageTrashItem`)
- Test: `backend/tests/test_page_door.py`

**Interfaces:**
- Consumes: nothing from earlier tasks beyond the page door as it stands.
- Produces: `source` on `get_page` block rows and `PageBlock`; `list_trash`; `PageTrashItem` (Contracts, Page door and Schemas). Task 11 consumes them.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_page_door.py`, add `from datetime import datetime, timezone` below `import asyncio`, and add `list_trash,` to the `from app.services.page_door import (...)` list after `list_pages,`. Append:

```python
@pytest.mark.asyncio
async def test_the_keyed_read_serves_each_blocks_source(session, llm):
    """`text` is marker-stripped; an editor edits the block's own markdown."""
    page = await create_page(session, llm, project="p", title="n",
                             content="## Sub\n\n- item\n")

    view = await get_page(session, str(page.id))

    assert [block["source"] for block in view.blocks] == ["## Sub", "- item"]
    assert view.content is None


async def _stamp(session, page_id, at: datetime):
    # A datetime, not an ISO string: asyncpg refuses a str bound to
    # CAST(:at AS timestamptz) with "invalid input for query argument".
    await session.execute(
        text(
            "UPDATE pages SET deleted_at = CAST(:at AS timestamptz) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(page_id), "at": at},
    )


@pytest.mark.asyncio
async def test_the_trash_lists_only_the_roots_of_trashed_subtrees(session, llm):
    root = await create_page(session, llm, project="p", title="root")
    child = await create_page(session, llm, project="p", title="child",
                              parent_id=str(root.id))
    lone = await create_page(session, llm, project="p", title="lone")
    live = await create_page(session, llm, project="p", title="live")
    kid = await create_page(session, llm, project="p", title="kid",
                            parent_id=str(live.id))
    elsewhere = await create_page(session, llm, project="q", title="other")
    for page in (root, lone, kid, elsewhere):
        await delete_page(session, str(page.id))
    # One transaction means one `now()`; distinct stamps make the order real.
    await _stamp(session, root.id, datetime(2026, 9, 1, tzinfo=timezone.utc))
    await _stamp(session, child.id, datetime(2026, 9, 1, tzinfo=timezone.utc))
    await _stamp(session, lone.id, datetime(2026, 9, 2, tzinfo=timezone.utc))
    await _stamp(session, kid.id, datetime(2026, 9, 3, tzinfo=timezone.utc))

    rows = await list_trash(session, "p")

    assert [str(row["id"]) for row in rows] == [str(kid.id), str(lone.id), str(root.id)]
    assert set(rows[0]) == {"id", "title", "parent_id", "deleted_at"}
    assert str(rows[0]["parent_id"]) == str(live.id)
    assert rows[2]["title"] == "root"
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_door.py
```

Expected: collection error `ImportError: cannot import name 'list_trash'`.

- [ ] **Step 3: Implement**

In `backend/app/services/page_door.py`, add `"list_trash",` to `__all__` after `"list_pages",`.

Replace `_GET_BLOCKS` with:

```python
# `source` is sliced server-side the way `document_door._BLOCKS` slices it, so
# an editor reading one page does not also fetch and slice `content` itself.
_GET_BLOCKS = text(
    """
    SELECT b.id, b.parent_id, b.order_index, b.type, b.text, b.properties,
           lower(b.char_span) AS char_start, upper(b.char_span) AS char_end,
           substring(p.content
                     FROM lower(b.char_span) + 1
                     FOR upper(b.char_span) - lower(b.char_span)) AS source
    FROM blocks b
    JOIN pages p ON p.id = b.page_id
    WHERE b.page_id = CAST(:id AS uuid)
    ORDER BY b.order_index
    """
)
```

After `_LIST_PAGES` add:

```python
# A trashed page whose parent is also trashed is shown through that parent:
# restoring it alone is refused while the parent stays in the trash.
_TRASH_ROOTS = text(
    """
    SELECT p.id, p.title, p.parent_id, p.deleted_at
    FROM pages p
    LEFT JOIN pages parent ON parent.id = p.parent_id
    WHERE p.project = :project
      AND p.deleted_at IS NOT NULL
      AND (p.parent_id IS NULL OR parent.deleted_at IS NULL)
    ORDER BY p.deleted_at DESC, p.id
    """
)
```

After `list_pages` add:

```python
async def list_trash(session: AsyncSession, project: str) -> list[dict]:
    """The roots of `project`'s trashed subtrees, most recently trashed first.

    A read: it takes no lock, so the read-only worker can serve it.
    """
    rows = (
        await session.execute(_TRASH_ROOTS, {"project": project})
    ).mappings().all()
    return [dict(row) for row in rows]
```

In `backend/app/schemas/page.py`, in `PageBlock` after `    char_end: int | None` add:

```python
    # The block's own markdown, sliced from the page's content. `text` is
    # marker-stripped, so the two differ: "Sub" against "## Sub".
    source: str | None = None
```

After `PageListItem` add:

```python
class PageTrashItem(BaseModel):
    id: UUID
    title: str | None
    parent_id: UUID | None
    deleted_at: datetime
```

- [ ] **Step 4: Run and watch them pass**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_door.py tests/test_page_routes.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_read_only_role.py
```

Expected: PASS (the row-lock inventory is unchanged: `page_door.py` is already listed and `_TRASH_ROOTS` takes no lock).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_door.py backend/app/schemas/page.py backend/tests/test_page_door.py
git commit -m "feat(pages): serve block source and list trash

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---

### Task 11: The trash route and its guard entries

**Files:**
- Modify: `backend/app/api/routes/pages.py` (module docstring, imports, between `list_pages_route` and `empty_trash_route` `:132-133`)
- Modify: `backend/app/services/content_surfaces.py:720`
- Modify: `backend/tests/test_api/test_rest_conformance.py:207`
- Modify: `backend/tests/test_door_parity.py:1518-1521`
- Modify: `docs/two-door-parity.md` (regenerated between its markers)
- Test: `backend/tests/test_page_routes.py`

**Interfaces:**
- Consumes: `list_trash`, `PageTrashItem`, `PageBlock.source` (Task 10).
- Produces: `GET /api/v1/pages/trash` (Contracts, Routes).

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_page_routes.py`:

```python
@pytest.mark.asyncio
async def test_the_trash_route_resolves_before_the_page_id_route(
    client, auth_headers, create,
):
    """Registered below `/{page_id}`, `trash` would fail UUID parsing as 422."""
    root = await create(title="gone")
    await create(parent_id=root)
    await client.delete(f"{V1}/pages/{root}", headers=auth_headers)

    response = await client.get(
        f"{V1}/pages/trash", params={"project": "p"}, headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert [row["id"] for row in body] == [root]
    assert set(body[0]) == {"id", "title", "parent_id", "deleted_at"}


@pytest.mark.asyncio
async def test_the_page_read_serves_block_source(client, auth_headers, create):
    """Regression pin: passes on arrival once Task 10 lands `PageBlock.source`."""
    page = await create(content="## Sub\n\n- item\n")
    blocks = await _blocks_of(client, auth_headers, page)
    assert [b["source"] for b in blocks] == ["## Sub", "- item"]
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_routes.py
```

Expected: `test_the_trash_route_resolves_before_the_page_id_route` FAILS with 422. `test_the_page_read_serves_block_source` PASSES on arrival: it is a regression pin for the route half of Task 10's `source` field (Task 10 tests the service; this pins that `PageResponse` serialises it), kept here so Task 10 stays within its file budget.

- [ ] **Step 3: Add the route**

In `backend/app/api/routes/pages.py`'s module docstring, after the line `  - GET    /api/v1/pages` add:

```
  - GET    /api/v1/pages/trash
```

In the `from app.schemas.page import (...)` list add `PageTrashItem,` after `PageRestoreResponse,`. In the `from app.services.page_door import (...)` list add `list_trash,` after `list_pages,`.

Directly after `list_pages_route` (and above `empty_trash_route`) add:

```python
@router.get("/trash", response_model=list[PageTrashItem])
async def list_trash_route(
    project: str = Query(..., min_length=1),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> list[PageTrashItem]:
    """The roots of the project's trashed subtrees, newest first. Declared
    above `/{page_id}` so `trash` is never parsed as a page id."""
    return [PageTrashItem(**row) for row in await list_trash(session, project)]
```

- [ ] **Step 4: Classify the route in the three guards**

In `backend/app/services/content_surfaces.py`, replace:

```python
    "GET /api/v1/pages/{page_id}",
    "POST /api/v1/pages",
```

with:

```python
    "GET /api/v1/pages/{page_id}",
    "GET /api/v1/pages/trash",
    "POST /api/v1/pages",
```

In `backend/tests/test_api/test_rest_conformance.py`, replace:

```python
    ("GET", "/api/v1/pages/{page_id}"): 200,
```

with:

```python
    ("GET", "/api/v1/pages/{page_id}"): 200,
    ("GET", "/api/v1/pages/trash"): 200,
```

In `backend/tests/test_door_parity.py`, in the `pages.reads` surface, replace:

```python
            ("GET", f"{V1}/pages"),
            ("GET", f"{V1}/pages/{{page_id}}"),
        ),
```

with:

```python
            ("GET", f"{V1}/pages"),
            ("GET", f"{V1}/pages/trash"),
            ("GET", f"{V1}/pages/{{page_id}}"),
        ),
```

- [ ] **Step 5: Regenerate the parity table**

```bash
cd backend && timeout 120 .venv/bin/python - <<'EOF'
from tests.test_door_parity import PARITY_DOC, _DOC_BEGIN, _DOC_END, render_markdown

doc = PARITY_DOC.read_text(encoding="utf-8")
head, rest = doc.split(_DOC_BEGIN, 1)
_, tail = rest.split(_DOC_END, 1)
PARITY_DOC.write_text(
    f"{head}{_DOC_BEGIN}\n{render_markdown()}\n{_DOC_END}{tail}", encoding="utf-8",
)
EOF
cd .. && git diff --stat docs/two-door-parity.md
```

Expected: the diff touches only the `pages.reads` row inside the generated block, and the headline `**80 surfaces: 25 two-door, 55 single-door with a stated reason (48 REST-only, 7 MCP-only), 0 divergent.**` is unchanged. The line count in `--stat` is not the check; Step 6's `test_the_committed_table_is_the_enforced_table` and `test_the_committed_table_reports_its_own_counts` are.

- [ ] **Step 6: Run the route tests and the guards**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_routes.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes/pages.py backend/app/services/content_surfaces.py \
        backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py \
        backend/tests/test_page_routes.py docs/two-door-parity.md
git commit -m "feat(pages): list trashed page roots over REST

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```

---
### Task 12: Guards leg, read-only role and CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:1703-1710` (block verbs paragraph), `:1912`, `:1917-1918` (pages paragraph)

**Interfaces:**
- Consumes: every earlier task.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-haiku
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 0 = 0

- [ ] **Step 1: Run CLAUDE.md's guards leg**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py tests/test_event_taxonomy_map.py
```

Expected: PASS. A failure here is a real finding: report it with the failing test's message rather than editing a guard to pass.

- [ ] **Step 2: Run the read-only role guard (outside the leg)**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_read_only_role.py
```

Expected: PASS.

- [ ] **Step 3: Run the touched suites, one invocation each**

```bash
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_taxonomy.py tests/test_notes_schema.py tests/test_block_serializer.py tests/test_document_parsers.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_block_verbs.py tests/test_block_embeddings.py tests/test_block_embedding_refresh.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_page_door.py tests/test_page_routes.py tests/test_page_document_isolation.py tests/test_pages_schema.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_document_door.py tests/test_document_routes.py
cd backend && TEST_DATABASE_URL="postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_3" timeout 900 .venv/bin/python -m pytest -q tests/test_mcp.py -k block
```

Expected: PASS. Exit 143 is the host's OOM killer: check `free -h` and re-run that line alone.

- [ ] **Step 4: Update the block verbs paragraph in CLAUDE.md**

Replace:

```
write placement and document row in a SAVEPOINT, journal `blocks_edited`
(carrying no block text), commit, then embed **only** the touched block.
`char_span` is recomputed in that same pass — the serialiser is the only thing
that knows where each block landed — so spans never drift and are never NULL.
The cost model: one edit is one bulk placement UPDATE over the document's
blocks, one document write, and one single-block embed.
```

with:

```
write placement and document row in a SAVEPOINT, journal `blocks_edited`
(carrying no block text), commit, then embed **only** the touched block — on a
document. **A page block write embeds nothing** (`BlockOwner.embed_inline`): an
update that changes a block's text or type deletes that block's
`page_embeddings__<slug>` rows for every fingerprint with `retired_at IS NULL`
inside the same savepoint, because the hourly `block_embedding_refresh` page arm
fills only blocks with no vector and would otherwise leave the edit stale
forever. `char_span` is recomputed in that same pass — the serialiser is the
only thing that knows where each block landed — so spans never drift and are
never NULL. The cost model: one edit is one bulk placement UPDATE over the
owner's blocks, one owner-row write, and one single-block embed for a document
or none for a page. The pass is list-valued internally so a page's batch insert
is one pass too; a one-id pass still journals `block_id` and answers the same
eight-field result, which MCP serialises through `vars()`.
```

- [ ] **Step 5: Update the pages paragraph in CLAUDE.md**

Replace:

```
context path: eleven routes under `/api/v1/pages` (`api/routes/pages.py`), no
```

with:

```
context path: thirteen routes under `/api/v1/pages` (`api/routes/pages.py`), no
```

Replace:

```
rather than filed with it dropped. Delete is a **soft delete** of the whole
```

with:

```
rather than filed with it dropped. Create also **flattens heading nesting** —
a block the parser parented under a heading moves to that heading's nearest
non-heading ancestor — because on a page only `list`, `todo` and `toggle`
blocks hold children (a `table` holds its `table_row`s), and the block verbs
refuse any other parent with `PageBlockInvalid` → 422. Flattening is
byte-identical for headings at the root or in a quote, but not for a heading
inside a list item that adopted a later sibling item, which comes out as a
tight nested item. Pages carry **three block types documents never do** —
`todo`, `toggle`, `callout`, in `PAGE_BLOCK_TYPES` beside `BLOCK_TYPES` and
normalised by `normalize_page_block_type` — with their required properties
(`checked`, `variant`) checked inside the verb on the merged block, keys the
new type does not define dropped on a type change, and markdown emit forms
(`- [ ]`, `<details>`, `> [!NOTE]`) that nothing re-parses. A block insert may
name its own `block_id` (409 when taken), `POST .../blocks/batch` inserts many
in one pass, the block delete answers the new hash in `X-Content-Hash`, and
`GET /pages/trash` lists the roots of trashed subtrees. Nothing embeds a page
inline: create and every block write leave vectors to the sweep. Delete is a **soft delete** of the whole
```

- [ ] **Step 6: Re-read the prose counts by hand**

```bash
grep -n "thirteen routes\|surfaces:" CLAUDE.md docs/two-door-parity.md
```

Expected: `thirteen routes` in CLAUDE.md, and `**80 surfaces: 25 two-door, 55 single-door with a stated reason (48 REST-only, 7 MCP-only), 0 divergent.**` unchanged in the parity doc (both new routes joined existing surfaces).

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(pages): record page block types and routes

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UQgipD4phQcUg2AtRvaqEh"
```
