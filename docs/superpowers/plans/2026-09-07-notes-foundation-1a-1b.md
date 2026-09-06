# Personal Notes Foundation (increment 1, lanes 1a-1b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Goal:** Land the `html` block type and the baseline regeneration that the personal notes workspace is built on, so that imported notes convert faithfully and the schema carries links, tags, revisions, pins and a keyword arm.

**Architecture:** Two lanes with a forced order. Lane 1a widens the block model with an `html` type (code-only: taxonomy, parser, serialiser, conversion guard, renderer) so that raw HTML in an imported note stops being an unrepresentable construct. Lane 1b regenerates `0001_baseline.py` with six schema objects in one drop-and-recreate, seeds the personal project at boot, makes `projects.kind` visible to the derived catalogue, and re-imports the corpus. 1a must land before 1b's re-import, or every html-bearing document files with no `html` row and the conversion guard then refuses it.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, asyncpg, Alembic, markdown-it-py, Postgres 17 + pgvector; React 19 + TypeScript on the frontend.

**Spec:** `docs/superpowers/specs/2026-09-07-personal-notes-workspace-design.md` (lanes 1a-1b are §12; the schema objects are §1, §6, §7, §8, §10; the html decision is §12's closing paragraphs)

## Global Constraints

- **Greenfield.** No migration is ever required. A schema change **regenerates `backend/migrations/versions/0001_baseline.py` in place** and the database is dropped and recreated. Never append a `0002`; `./scripts/gate.sh` asserts exactly one revision.
- **Backend tests** run from `backend/` as `python -m pytest -q`. They need the dev Postgres on `127.0.0.1:5433` and a `darkmem_test` database; conftest pins `DATABASE_URL` to `TEST_DATABASE_URL` and runs `DROP SCHEMA public CASCADE` then `alembic upgrade head`. Never point it at a real database.
- **`pytest -q` does NOT collect `scripts/benchlib/tests`** (`testpaths = ["tests"]`). Name that path explicitly when it is in scope.
- **Taxonomy-first**: a new block type lands in `BLOCK_TYPES` before any parser emits it.
- **Frontend** from `frontend/`: `npm run typecheck` (= `tsc -b`), `npm test` (vitest), `npm run build`.
- **Conventional commits**: `<type>(<scope>): <subject>`, subject ≤50 chars, imperative, no period.
- **The serialiser's conversion guard is never relaxed** to make more documents convert. The way to convert more documents is to make the parser represent the shape as a block.

---

### Task 1: Add the `html` block type to the taxonomy

**Files:**
- Modify: `backend/app/taxonomy.py` (`BLOCK_TYPES`, `normalize_block_type` docstring)
- Test: `backend/tests/test_taxonomy.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `"html"` as a member of `app.taxonomy.BLOCK_TYPES`; `normalize_block_type("html") == "html"`. Tasks 2, 3 and 4 all depend on this literal.

**Implementer:** dcc-superpower-companions:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1
**Approach:** inline - skip 2: a ninth entry beside eight existing ones, which is the established taxonomy-first pattern

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_taxonomy.py`:

```python
def test_html_is_a_stored_block_type():
    """Raw HTML is a construct the parser used to skip, which made any
    document containing it permanently unconvertible to block-first. It is a
    block type now, so it round-trips instead."""
    from app.taxonomy import BLOCK_TYPES, normalize_block_type

    assert "html" in BLOCK_TYPES
    assert normalize_block_type("html") == "html"
    # markdown-it's own token name maps onto it rather than falling back.
    assert normalize_block_type("html_block") == "html"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_taxonomy.py::test_html_is_a_stored_block_type -q`
Expected: FAIL — `assert 'html' in BLOCK_TYPES`

- [ ] **Step 3: Write minimal implementation**

In `backend/app/taxonomy.py`, add `"html"` as the last entry of `BLOCK_TYPES`:

```python
BLOCK_TYPES: list[str] = [
    "paragraph",
    "heading",
    "list",
    "code",
    "quote",
    "table",
    "table_row",
    "divider",
    # Raw HTML: an opaque run the markdown parser hands back verbatim. It is a
    # stored type rather than a skipped token because skipping it made every
    # document containing `<img>` or `<details>` unconvertible to block-first,
    # and an imported Obsidian or Notion note routinely carries both.
    "html",
]
```

Add the token-name alias to `LEGACY_BLOCK_TYPE_MAP`, beside the other markdown-it names:

```python
    "html_block": "html",
```

Update `normalize_block_type`'s docstring first line:

```python
    """Return one of the nine stored ``BLOCK_TYPES``.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_taxonomy.py -q`
Expected: PASS, whole file green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/taxonomy.py backend/tests/test_taxonomy.py
git commit -m "feat(taxonomy): add the html block type"
```

---

### Task 2: Mint `html` blocks in the markdown parser

**Files:**
- Modify: `backend/app/services/document_parsers.py` (the top-level token loop, at the `html_block` comment)
- Test: `backend/tests/test_document_parsers.py`

**Interfaces:**
- Consumes: `"html"` from `BLOCK_TYPES` (Task 1).
- Produces: a `BlockDraft(type="html", text=<verbatim token content, trailing newlines stripped>, parent=<enclosing>, properties=None, char_span=<token map>)` for every `html_block` token. Task 3's serialiser round-trips exactly this `text`.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 2: the loop already has seven branches of this exact shape (code, quote, table, divider); this is an eighth

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_document_parsers.py`:

```python
def test_raw_html_becomes_an_html_block():
    """The parser skipped `html_block` entirely, so a document containing one
    had a construct in its content and no row for it -- which is exactly the
    state the conversion guard refuses."""
    from app.services.document_parsers import parse_markdown

    drafts = parse_markdown(
        "Before\n\n<details>\n<summary>More</summary>\n</details>\n\nAfter\n"
    )
    kinds = [d.type for d in drafts]
    assert kinds == ["paragraph", "html", "paragraph"]

    html = drafts[1]
    # Verbatim: the block is opaque to markdown, so nothing inside it is
    # re-interpreted and nothing about it is normalised.
    assert html.text == "<details>\n<summary>More</summary>\n</details>"
    assert html.properties is None


def test_an_html_block_containing_markdown_characters_stays_opaque():
    """`#` and `-` inside a raw HTML run are not a heading and not a list.
    If the parser ever re-tokenised the content, the serialiser would emit
    something that re-parses differently."""
    from app.services.document_parsers import parse_markdown

    drafts = parse_markdown("<div>\n# not a heading\n- not a list\n</div>\n")
    assert [d.type for d in drafts] == ["html"]
    assert drafts[0].text == "<div>\n# not a heading\n- not a list\n</div>"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_document_parsers.py -q -k html`
Expected: FAIL — `assert ['paragraph', 'paragraph'] == ['paragraph', 'html', 'paragraph']`

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/document_parsers.py`, replace the `html_block` skip comment and its bare `i += 1` with a real branch. The existing block reads:

```python
        # html_block — not in the committed block-type set (doc 16 §9);
        # skipped rather than minting a meaningless block. Tables were named
        # here until the 2026-08-31 spec §4.1 change, and `hr` until
        # 2026-09-02; both are parsed structurally above now.
        i += 1
```

Replace it with:

```python
        # html_block — a stored type since the notes workspace needed imported
        # documents to convert (2026-09-07 spec §12). The content is opaque:
        # markdown-it hands back the raw run, and re-emitting it between blank
        # lines re-tokenises to the same single token, so the round-trip holds
        # for every CommonMark HTML-block kind.
        if tok.type == "html_block":
            drafts.append({
                "text": tok.content.rstrip("\n"),
                "type": "html",
                "parent": parent(),
                "properties": None,
                "char_span": _span(tok.map, offsets, body),
            })
            i += 1
            continue

        i += 1
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_document_parsers.py -q`
Expected: PASS, whole file green — no existing parser test regresses.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/document_parsers.py backend/tests/test_document_parsers.py
git commit -m "feat(documents): parse raw HTML into html blocks"
```

---

### Task 3: Serialise `html` blocks and close the conversion guard

**Files:**
- Modify: `backend/app/services/block_serializer.py` (`emit`'s branch chain; `_UNREPRESENTABLE_TOKENS`; the count-check tuple in `reproduces_source`)
- Test: `backend/tests/test_block_serializer.py`

**Interfaces:**
- Consumes: `BlockDraft(type="html")` from Task 2.
- Produces: `serialize_tree` emits an `html` block's `text` verbatim; `reproduces_source` returns True for a document whose html blocks are all present in the tree and False when the tree is stale.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4
**Approach:** inline - skip 3: the spec fixes both halves (emit verbatim; add `("html_block", "html")` to the count check)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_block_serializer.py`:

```python
def test_html_round_trips_verbatim():
    """The block is opaque, so serialising it is writing its text back. A
    normalising branch here would change what re-parses."""
    from app.services.block_serializer import TreeBlock, serialize_tree

    blocks = [
        TreeBlock(id=uuid4(), parent_id=None, order_index=0,
                  type="paragraph", text="Before", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=1, type="html",
                  text="<details>\n<summary>More</summary>\n</details>",
                  properties=None),
    ]
    out = serialize_tree(blocks)
    assert out.content == (
        "Before\n\n<details>\n<summary>More</summary>\n</details>"
    )


def test_a_document_with_html_converts_when_the_tree_has_it():
    """Before the html type existed this document was permanently
    unconvertible, which meant permanently uneditable in the notes UI."""
    from app.services.block_serializer import TreeBlock, reproduces_source

    content = "Before\n\n<div>x</div>\n\nAfter\n"
    blocks = [
        TreeBlock(id=uuid4(), parent_id=None, order_index=0,
                  type="paragraph", text="Before", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=1,
                  type="html", text="<div>x</div>", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=2,
                  type="paragraph", text="After", properties=None),
    ]
    assert reproduces_source(blocks, content, {}) is True


def test_a_stale_tree_missing_its_html_block_still_refuses():
    """The count check is the half that keeps the guard honest. A document
    filed BEFORE the html type existed carries the construct in its content
    and no row for it, and `ingest_document` returns UNCHANGED on a
    byte-identical re-push without touching blocks -- so without this check
    the conversion would silently drop the HTML."""
    from app.services.block_serializer import TreeBlock, reproduces_source

    content = "Before\n\n<div>x</div>\n\nAfter\n"
    stale = [
        TreeBlock(id=uuid4(), parent_id=None, order_index=0,
                  type="paragraph", text="Before", properties=None),
        TreeBlock(id=uuid4(), parent_id=None, order_index=1,
                  type="paragraph", text="After", properties=None),
    ]
    assert reproduces_source(stale, content, {}) is False
```

If `uuid4` is not already imported at the top of that test file, add `from uuid import uuid4`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_block_serializer.py -q -k html`
Expected: FAIL — the round-trip test emits the html text through the paragraph branch (which is coincidentally correct) but `test_a_document_with_html_converts_when_the_tree_has_it` fails, because `_UNREPRESENTABLE_TOKENS` still refuses.

- [ ] **Step 3: Write the implementation**

Three edits in `backend/app/services/block_serializer.py`.

First, an explicit `emit` branch, placed immediately before the `else:` paragraph fallback, so that html never depends on the fallback happening to be right:

```python
        elif block.type == "html":
            # Verbatim. The run is opaque to markdown, so there is nothing to
            # normalise and any normalisation would change what re-parses.
            span = emit_lines(block.text.split("\n") if block.text else [""], prefix)
```

Second, empty the unrepresentable set — `html_block` is the only member, and the parser now mints a block for it:

```python
# Token kinds the block model has no shape for. The parser mints no block for
# these, so nothing in a tree records them and no serialiser can put them back.
#
# `hr` left this set on 2026-09-02 when it became the `divider` block type, and
# `html_block` on 2026-09-07 when it became `html`. The set is empty rather
# than deleted: the guard below is the shape that keeps a future construct from
# converting lossily, and an empty frozenset says "nothing is unrepresentable
# today", which is a different claim from "we stopped checking".
_UNREPRESENTABLE_TOKENS: frozenset[str] = frozenset()
```

Third — and this is the half that keeps the guard honest — extend the count check:

```python
    for token_type, block_type in (("hr", "divider"), ("html_block", "html")):
```

Leave the `env["references"]` check exactly as it is: link-reference definitions are still unrepresentable and must still refuse.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_block_serializer.py tests/test_document_parsers.py tests/test_taxonomy.py -q`
Expected: PASS across all three files.

- [ ] **Step 5: Run the block verb and door suites, which own the conversion path**

Run: `cd backend && python -m pytest tests/test_block_verbs.py tests/test_document_door.py tests/test_block_pipeline.py -q`
Expected: PASS. `tests/test_block_verbs.py` carries a test pinning that an unconvertible document raises `DocumentNotConvertible`; if it pinned html specifically it must now pin the reference-definition case instead — read it before changing it, and change the test only if its subject genuinely moved.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/block_serializer.py backend/tests/test_block_serializer.py
git commit -m "feat(documents): serialise html blocks and widen the guard"
```

---

### Task 4: Render `html` blocks as escaped source in the SPA

**Files:**
- Modify: `frontend/src/features/documents/components/block-view.tsx`
- Test: `frontend/src/features/documents/__tests__/block-view.test.tsx`

**Interfaces:**
- Consumes: blocks carrying `type: "html"` from the API.
- Produces: nothing other tasks consume.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3
**Approach:** inline - skip 3: the spec rules that html renders as escaped source through the code path, and that live rendering is a separate owner decision behind `rehype-sanitize`

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/features/documents/__tests__/block-view.test.tsx`:

```tsx
it("renders an html block as escaped source, never as live markup", () => {
  // The markdown pipeline carries no `rehype-raw`, so HTML is escaped today.
  // Making <img>/<details> "work" by adding it is the first place an imported
  // file or a capture-scoped key executes script under the operator's session
  // cookie. Live rendering is a separate owner decision behind
  // `rehype-sanitize`; until then this block is source, shown as source.
  const { container } = render(
    <BlockView
      block={{
        block_id: "b1",
        type: "html",
        text: "<img src=x onerror=alert(1)>",
        order_index: 0,
        char_span: null,
        parent_id: null,
        properties: null,
        source: null,
      }}
      rows={[]}
    />,
  )
  expect(container.querySelector("img")).toBeNull()
  expect(container.textContent).toContain("<img src=x onerror=alert(1)>")
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/block-view.test.tsx -t "escaped source"`
Expected: FAIL — the default branch renders the text through the inline markdown renderer.

- [ ] **Step 3: Write the implementation**

In `block-view.tsx`, add an `html` case immediately after the existing `case "code":`, reusing the same `CodeBlock` the code branch renders:

```tsx
    case "html":
      // Escaped source, never live markup. The markdown pipeline carries no
      // `rehype-raw`, so adding one to make <img>/<details> render is the
      // first place an imported file executes script under the operator's
      // session cookie. Live HTML is a separate owner decision behind
      // `rehype-sanitize` (2026-09-07 spec §12).
      return <CodeBlock code={block.text} language="html" />
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/features/documents/__tests__/block-view.test.tsx`
Expected: PASS, whole file green.

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npx tsc -b`
Expected: no output, exit 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/documents/components/block-view.tsx frontend/src/features/documents/__tests__/block-view.test.tsx
git commit -m "feat(documents): render html blocks as escaped source"
```

---

### Task 5: Regenerate the baseline with the notes schema objects

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py` (the `documents` and `projects` table statements; new statements after `blocks`; the downgrade drop list)
- Test: `backend/tests/test_notes_schema.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `projects.kind`; `ux_projects_one_personal`; tables `document_links`, `document_tags`, `document_revisions`; columns `documents.pinned_at`, `blocks.search_vector`; index `ix_documents_project_updated`. Tasks 6 and 7 and every later lane depend on these names.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6
**Approach:** inline - skip 3: every object's shape, nullability and FK action is fixed by the spec (§1, §6, §7, §8, §10)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_notes_schema.py`:

```python
"""The schema objects the personal notes workspace is built on.

Asserted against the live test database rather than against the baseline's
text, because what matters is what `alembic upgrade head` actually produced.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_projects_carries_an_enforced_personal_singleton(session):
    await session.execute(text(
        "INSERT INTO projects (name, kind) VALUES ('notes', 'personal')"
    ))
    # The database refuses a second personal space. This is the whole reason
    # `kind` is a column rather than a `properties` label.
    with pytest.raises(Exception):
        await session.execute(text(
            "INSERT INTO projects (name, kind) VALUES ('other', 'personal')"
        ))


@pytest.mark.asyncio
async def test_kind_defaults_to_project_and_is_constrained(session):
    await session.execute(text("INSERT INTO projects (name) VALUES ('p1')"))
    kind = await session.scalar(
        text("SELECT kind FROM projects WHERE name = 'p1'")
    )
    assert kind == "project"
    with pytest.raises(Exception):
        await session.execute(text(
            "INSERT INTO projects (name, kind) VALUES ('p2', 'nonsense')"
        ))


@pytest.mark.asyncio
async def test_a_link_survives_its_target_being_deleted(session):
    """An unresolved link is a first-class stub, so losing the target must
    null the pointer rather than delete the row -- otherwise deleting a note
    silently erases every backlink to it instead of showing them as stubs."""
    doc_a = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'a.md') RETURNING id"
    ))
    doc_b = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'b.md') RETURNING id"
    ))
    await session.execute(
        text(
            "INSERT INTO document_links "
            "(id, source_document_id, target_document_id, target_uri) "
            "VALUES (gen_random_uuid(), :a, :b, 'b.md')"
        ),
        {"a": doc_a, "b": doc_b},
    )
    await session.execute(
        text("DELETE FROM documents WHERE id = :b"), {"b": doc_b}
    )
    row = (await session.execute(text(
        "SELECT source_document_id, target_document_id, target_uri "
        "FROM document_links"
    ))).one()
    assert row.source_document_id == doc_a
    assert row.target_document_id is None
    assert row.target_uri == "b.md"


@pytest.mark.asyncio
async def test_deleting_a_document_takes_its_links_tags_and_revisions(session):
    doc = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'c.md') RETURNING id"
    ))
    tag = await session.scalar(text(
        "INSERT INTO tags (name) VALUES ('t1') RETURNING id"
    ))
    await session.execute(
        text("INSERT INTO document_tags (document_id, tag_id) "
             "VALUES (:d, :t)"),
        {"d": doc, "t": tag},
    )
    await session.execute(
        text("INSERT INTO document_revisions "
             "(id, document_id, content, content_hash) "
             "VALUES (gen_random_uuid(), :d, 'x', 'h')"),
        {"d": doc},
    )
    await session.execute(text("DELETE FROM documents WHERE id = :d"), {"d": doc})
    assert await session.scalar(text("SELECT count(*) FROM document_tags")) == 0
    assert await session.scalar(
        text("SELECT count(*) FROM document_revisions")
    ) == 0


@pytest.mark.asyncio
async def test_blocks_carry_a_search_vector_that_blanks_source_types(session):
    """The keyword arm indexes prose. Code and html text is source, and
    indexing it makes every note that mentions a function name a hit for it."""
    doc = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'd.md') RETURNING id"
    ))
    for block_type in ("paragraph", "code", "html"):
        await session.execute(
            text("INSERT INTO blocks (id, document_id, type, text) "
                 "VALUES (gen_random_uuid(), :d, :t, 'alpha beta')"),
            {"d": doc, "t": block_type},
        )
    hits = await session.scalar(text(
        "SELECT count(*) FROM blocks "
        "WHERE search_vector @@ plainto_tsquery('english', 'alpha')"
    ))
    assert hits == 1


@pytest.mark.asyncio
async def test_documents_can_be_pinned_and_ordered_by_recency(session):
    await session.execute(text(
        "INSERT INTO documents (id, project, uri, pinned_at) "
        "VALUES (gen_random_uuid(), 'notes', 'e.md', now())"
    ))
    pinned = await session.scalar(text(
        "SELECT count(*) FROM documents WHERE pinned_at IS NOT NULL"
    ))
    assert pinned == 1
    # The recents read is (project, updated_at); assert the index exists so a
    # later reader is not doing a seq scan over the corpus.
    assert await session.scalar(text(
        "SELECT count(*) FROM pg_indexes "
        "WHERE tablename = 'documents' AND indexname = 'ix_documents_project_updated'"
    )) == 1
```

Match the session fixture to the one the sibling suites use — read the top of `backend/tests/test_document_door.py` and copy its fixture import and `pytestmark` exactly rather than assuming.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_notes_schema.py -q`
Expected: FAIL — `column "kind" of relation "projects" does not exist`.

- [ ] **Step 3: Edit the baseline**

In `backend/migrations/versions/0001_baseline.py`:

Add `kind` to the `projects` CREATE TABLE and the singleton index after it:

```python
        CREATE TABLE projects (
            name         TEXT PRIMARY KEY,
            display_name TEXT,
            kind         TEXT NOT NULL DEFAULT 'project'
                         CHECK (kind IN ('project', 'personal')),
            properties   JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
```

```python
    # Exactly one personal space, enforced rather than conventional: this is
    # the whole reason `kind` is a column and not a `properties` label.
    op.execute(
        "CREATE UNIQUE INDEX ux_projects_one_personal ON projects (kind) "
        "WHERE kind = 'personal'"
    )
```

Add `pinned_at` to the `documents` CREATE TABLE, after `properties`:

```python
            pinned_at    TIMESTAMPTZ,
```

Add the recents index beside the existing `documents` index statements:

```python
    # The notes sidebar reads recents as (project, updated_at DESC); without
    # this it is a seq scan over the whole corpus.
    op.execute(
        "CREATE INDEX ix_documents_project_updated "
        "ON documents (project, updated_at DESC)"
    )
```

Add `search_vector` to the `blocks` CREATE TABLE, as the last column:

```python
            search_vector TSVECTOR GENERATED ALWAYS AS (
                to_tsvector(
                    'english',
                    CASE WHEN type IN ('code', 'html') THEN '' ELSE coalesce(text, '') END
                )
            ) STORED,
```

and its index beside the other block indexes:

```python
    op.execute("CREATE INDEX ix_blocks_search_vector ON blocks USING GIN (search_vector)")
```

Then the three new tables, immediately after the `blocks` statements:

```python
    # Wiki-links. `target_document_id` is nullable on purpose: `[[a-page]]`
    # pointing at a note that does not exist yet is a first-class stub, and
    # ON DELETE SET NULL turns a deleted target back into one rather than
    # erasing the backlink.
    op.execute(
        """
        CREATE TABLE document_links (
            id                 UUID NOT NULL,
            source_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            source_block_id    UUID REFERENCES blocks(id) ON DELETE CASCADE,
            target_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
            target_uri         TEXT NOT NULL,
            link_text          TEXT,
            CONSTRAINT document_links_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_links_target ON document_links (target_document_id)"
    )
    op.execute(
        "CREATE INDEX ix_document_links_target_uri ON document_links (target_uri)"
    )
    op.execute(
        "CREATE INDEX ix_document_links_source ON document_links (source_document_id)"
    )

    # Documents reuse the generic `tags` registry rather than minting a second
    # vocabulary, exactly as `memory_tags` does.
    op.execute(
        """
        CREATE TABLE document_tags (
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            CONSTRAINT document_tags_pkey PRIMARY KEY (document_id, tag_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_document_tags_tag ON document_tags (tag_id)")

    # Version history: a full post-image snapshot per commit, not a delta --
    # the serialiser already produces exactly this string on every mutation,
    # and a delta format would be a second representation to keep faithful.
    op.execute(
        """
        CREATE TABLE document_revisions (
            id           UUID NOT NULL,
            document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content      TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT document_revisions_pkey PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_revisions_document "
        "ON document_revisions (document_id, created_at DESC)"
    )
```

Finally add the three new tables to the `downgrade` drop list, before `documents` (they reference it):

```python
        "document_revisions",
        "document_tags",
        "document_links",
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_notes_schema.py -q`
Expected: PASS. conftest drops the schema and runs `alembic upgrade head`, so the regenerated baseline is what the assertions see.

- [ ] **Step 5: Confirm the tree still holds exactly one revision**

Run: `cd backend && ls migrations/versions/`
Expected: exactly `0001_baseline.py` (plus `__pycache__`). A second file here fails the gate.

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS. A red leg on this host is a kill before it is a regression — if anything reports exit 143, check `free -h` before believing it and re-run that file alone.

- [ ] **Step 7: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py backend/tests/test_notes_schema.py
git commit -m "feat(schema): add the notes workspace objects to the baseline"
```

---

### Task 6: Seed the personal project at boot

**Files:**
- Modify: `backend/app/services/project_registry.py` (add `seed_personal_project`)
- Modify: `backend/app/main.py` (call it in the boot block that already runs `backfill_projects`)
- Test: `backend/tests/test_project_registry.py`

**Interfaces:**
- Consumes: `projects.kind` (Task 5).
- Produces: `async def seed_personal_project(session: AsyncSession) -> None` in `app.services.project_registry`, and the guarantee that a `projects` row named `notes` with `kind='personal'` exists after boot.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4
**Approach:** inline - skip 3: the spec fixes the site (beside `backfill_projects`), the statement (`ON CONFLICT (name) DO UPDATE`) and why the wizard is the wrong place

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_project_registry.py` (create it if absent, matching the session fixture used by `tests/test_notes_schema.py`):

```python
@pytest.mark.asyncio
async def test_the_personal_project_is_seeded_idempotently(session):
    from app.services.project_registry import seed_personal_project

    await seed_personal_project(session)
    await seed_personal_project(session)
    rows = (await session.execute(text(
        "SELECT name, kind FROM projects WHERE kind = 'personal'"
    ))).all()
    assert [(r.name, r.kind) for r in rows] == [("notes", "personal")]


@pytest.mark.asyncio
async def test_the_seed_repairs_a_row_a_capture_created_first(session):
    """`project_registry.register` runs on every capture and inserts with
    `ON CONFLICT DO NOTHING`, so a memory captured into `notes` before the
    first boot mints the row with kind defaulting to 'project'. A
    DO-NOTHING seed would leave it wrong forever."""
    from app.services.project_registry import register, seed_personal_project

    await register(session, "notes")
    assert await session.scalar(
        text("SELECT kind FROM projects WHERE name = 'notes'")
    ) == "project"

    await seed_personal_project(session)
    assert await session.scalar(
        text("SELECT kind FROM projects WHERE name = 'notes'")
    ) == "personal"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_project_registry.py -q`
Expected: FAIL — `ImportError: cannot import name 'seed_personal_project'`

- [ ] **Step 3: Write the implementation**

In `backend/app/services/project_registry.py`, beside the existing statements:

```python
# The personal notes space. Seeded at boot rather than in the setup wizard:
# `register` runs on every capture with ON CONFLICT DO NOTHING, so a memory
# captured into `notes` before any seed mints the row with `kind` defaulting to
# 'project'. DO UPDATE is what makes the seed self-heal that race, and it
# survives a baseline regeneration without a runbook step.
PERSONAL_PROJECT = "notes"

_SEED_PERSONAL = text(
    "INSERT INTO projects (name, kind) VALUES (:name, 'personal') "
    "ON CONFLICT (name) DO UPDATE SET kind = 'personal'"
)


async def seed_personal_project(session: AsyncSession) -> None:
    """Ensure the one `kind='personal'` project row exists.

    Idempotent, and a repair as much as a seed.
    """
    await session.execute(_SEED_PERSONAL, {"name": PERSONAL_PROJECT})
```

In `backend/app/main.py`, inside the same `try` block that runs `backfill_projects`, seed before the backfill so a fresh database has the row before anything else reads it:

```python
                async with async_session_factory() as session:
                    await seed_personal_project(session)
                    inserted = await backfill_projects(session)
                    await session.commit()
```

and extend the existing import of `backfill_projects` to include `seed_personal_project`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_project_registry.py -q`
Expected: PASS.

- [ ] **Step 5: Confirm the boot writer is skipped read-only**

Read the boot block: it must sit under the same `DARKMEM_READ_ONLY` guard the other boot writers do. If `backfill_projects` is already inside that guard, the seed inherits it by placement and nothing more is needed; if it is not, do **not** add a guard in this task — note it for the reviewer instead, since changing the read-only posture is out of this task's scope.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/project_registry.py backend/app/main.py backend/tests/test_project_registry.py
git commit -m "feat(projects): seed the personal notes project at boot"
```

---

### Task 7: Make `kind` visible to the derived project catalogue

**Files:**
- Modify: `backend/app/api/routes/projects.py` (`ProjectSummary`, `_UNION_SQL`)
- Test: `backend/tests/test_projects_route.py` (create if absent)

**Interfaces:**
- Consumes: `projects.kind` (Task 5), the seeded row (Task 6).
- Produces: `ProjectSummary.kind: str` on `GET /api/v1/projects`, and a personal project that appears even when it holds nothing.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4
**Approach:** inline - skip 3: the spec fixes both halves (LEFT JOIN for `kind`; add the personal project to the `names` CTE)

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_an_empty_personal_project_still_appears_with_its_kind(session, client):
    """The catalogue is derived from a union over memories, documents and
    checkpoints -- a personal space holding nothing would be invisible to its
    own picker, which is exactly the bug that made `kind` inert."""
    from app.services.project_registry import seed_personal_project

    await seed_personal_project(session)
    await session.commit()

    body = (await client.get("/api/v1/projects")).json()
    rows = {p["name"]: p for p in body["items"]}
    assert "notes" in rows
    assert rows["notes"]["kind"] == "personal"
    assert rows["notes"]["document_count"] == 0
```

Match `client` and `session` to the fixtures the sibling route tests use — read the top of an existing `tests/test_*_route*.py` or `tests/test_api/` file and copy them exactly. If the response is a bare list rather than `{"items": [...]}`, assert against the shape the route actually returns.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/test_projects_route.py -q`
Expected: FAIL — `KeyError: 'notes'` (the union sees no rows for it), or `KeyError: 'kind'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/api/routes/projects.py`, add the field to `ProjectSummary`:

```python
    kind: str = "project"
```

and extend `_UNION_SQL` — a fourth arm in the `names` CTE so a personal project with no content still appears, and a LEFT JOIN so every row carries its kind:

```python
    WITH names AS (
        SELECT project FROM memories
        UNION
        SELECT project FROM documents
        UNION
        SELECT project FROM session_checkpoints
        UNION
        -- A registered personal space appears even holding nothing: it is the
        -- notes workspace's own scope, not a project that happens to exist.
        SELECT name FROM projects WHERE kind = 'personal'
    ),
```

Add `p` to the joins and select the column:

```python
    SELECT names.project AS name,
           COALESCE(p.kind, 'project') AS kind,
           COALESCE(m.n, 0) AS memory_count,
```

```python
    LEFT JOIN projects p ON p.name = names.project
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_projects_route.py -q`
Expected: PASS.

- [ ] **Step 5: Run the API conformance and door-parity suites**

Run: `cd backend && python -m pytest tests/test_api/test_rest_conformance.py tests/test_door_parity.py -q`
Expected: PASS. A new response field is additive and should trip neither, but both are full-list guards and this is exactly the kind of change that surprises them.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/projects.py backend/tests/test_projects_route.py
git commit -m "feat(projects): serve project kind on the catalogue"
```

---

### Task 8: Hide the personal project from the project-shaped surfaces

**Files:**
- Modify: `frontend/src/components/app-chrome/project-switcher.tsx`
- Modify: `frontend/src/features/documents/components/documents-view.tsx`
- Test: `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx` (create if absent)

**Interfaces:**
- Consumes: `ProjectSummary.kind` from Task 7.
- Produces: nothing other tasks consume.

**Implementer:** dcc-superpower-companions:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3
**Approach:** inline - skip 3: the spec names both surfaces and the rule (filter `kind === "personal"`)

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/components/app-chrome/__tests__/project-switcher.test.tsx`, inside the existing `describe("ProjectSwitcher", ...)` block. The file already mocks `@/hooks/api` with `mockUseProjects` and provides `renderSwitcher()`; use both rather than adding a second harness:

```tsx
  it("omits the personal notes space from the scope list", async () => {
    // The notes space has its own route and its own workspace. Offering it
    // here would open it in a surface built for project artifacts.
    mockUseProjects.mockReturnValue({
      data: [
        { name: "darkmem", kind: "project", memory_count: 3,
          document_count: 0, checkpoint_count: 0,
          last_checkpoint_at: null, last_event_day: null },
        { name: "notes", kind: "personal", memory_count: 0,
          document_count: 12, checkpoint_count: 0,
          last_checkpoint_at: null, last_event_day: null },
      ],
      isLoading: false,
    })
    renderSwitcher()
    await userEvent.click(screen.getByRole("button", { name: /project scope/i }))
    expect(screen.getByText("darkmem")).toBeInTheDocument()
    expect(screen.queryByText("notes")).toBeNull()
  })
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/components/app-chrome/__tests__/project-switcher.test.tsx`
Expected: FAIL — "notes" is listed.

- [ ] **Step 3: Write the implementation**

Two edits.

In `frontend/src/hooks/api/` where `ProjectSummary` is declared, add the field so both surfaces can read it:

```ts
  /** `personal` is the notes workspace's own scope. It has its own route, so
   *  project-shaped pickers filter it out rather than offering it. */
  kind: "project" | "personal"
```

In `project-switcher.tsx`, filter it out of the rows the list renders:

```tsx
  const rows = (projects ?? []).filter((p) => p.kind !== "personal")
```

Make the same filter in `documents-view.tsx` wherever it builds its project list.

- [ ] **Step 4: Run the tests and typecheck**

Run: `cd frontend && npx vitest run src/components/app-chrome && npx tsc -b`
Expected: PASS, then exit 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/app-chrome frontend/src/features/documents/components/documents-view.tsx
git commit -m "feat(projects): keep the notes space out of project pickers"
```

---

### Task 9: Recreate the database and re-import the corpus

**Files:**
- Modify: none (operational task)
- Test: verified by the running instance

**Interfaces:**
- Consumes: every object from Tasks 5-7.
- Produces: a live database on the regenerated baseline whose documents carry `html` rows.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 0 - spec 1 - coupling 2 - risk 3 = 6
**Approach:** inline - skip 3: the runbook and CLAUDE.md fix the procedure; the only new step is that the re-import must follow 1a

- [ ] **Step 1: Confirm the whole suite is green before touching any database**

Run: `cd backend && python -m pytest -q` and `cd frontend && npm test`
Expected: both green. Do not proceed on a red suite.

- [ ] **Step 2: Read the deployment runbook's regeneration procedure**

Read `docs/runbook-deployment.md`. It carries the drop-and-recreate procedure and the two rows a re-seed does **not** reproduce. Follow it rather than improvising: `schema_guard` stamps a hash of the baseline file and refuses to start when it disagrees, so a database that is not recreated will fail the container's boot, loudly and correctly.

- [ ] **Step 3: Recreate the development database**

The test database is recreated by conftest on every run, so this step is about the dev instance only. Drop and recreate it, then run `python -m alembic upgrade head` with `DATABASE_URL` pointed explicitly at port 5433 — `migrations/env.py` reads the app settings default of 5432 and will otherwise migrate the wrong database.

- [ ] **Step 4: Re-import the corpus**

Run the corpus import with `--force`, because `ingest_document` returns UNCHANGED on a byte-identical re-push without touching blocks — which is precisely how a document ends up carrying HTML in its content and no `html` row. Find the import entry point under `backend/scripts/` and read its `--help` before running it.

- [ ] **Step 5: Verify html blocks actually landed**

```sql
SELECT count(*) FROM blocks WHERE type = 'html';
```

Expected: greater than zero if any corpus document contains raw HTML. If it is zero, check whether the corpus genuinely has none (`grep -rl '<details>\|<img ' docs/`) before concluding the import worked.

- [ ] **Step 6: Confirm conversion now succeeds on a previously-refused document**

Pick a document containing raw HTML and drive one block verb against it. It must convert rather than raising `DocumentNotConvertible`.

- [ ] **Step 7: Commit nothing, report the counts**

This task writes no code. Report: rows imported, `html` block count, and whether any document still refuses conversion — and if one does, why, since a remaining refusal is either a link-reference definition (expected and correct) or a construct nobody anticipated (a finding).

---

## What this plan does NOT cover

Lanes 1c (`expected_hash` on all four verbs plus `content_hash` served, including MCP's `include_hash`), 1d (the tag sweep and histogram widened) and 1e (`document_update` in both shapes, `document_updated` in `EVENT_TYPES`, the rename refusals and the upsert-riding direction predicate) are a second plan, written after this one lands. They are separated deliberately: 1c and 1d are independent of the regeneration, and 1e's code depends on the schema this plan creates actually existing.

The spec's ordering constraint that **1d must precede 1e** carries into that plan: the first `document_tags` row the new verb writes is deleted within the hour by `prune_orphans` if the sweep has not been widened first.
