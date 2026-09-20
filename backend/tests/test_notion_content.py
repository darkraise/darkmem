from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID, uuid4

from app.services.block_serializer import serialize_tree
from app.services.notion_archive import open_archive
from app.services.notion_content import StagedAsset, scan_links, translate_page
from app.services.notion_tree import build_tree
from tests.fixtures.notion.builder import DATABASE_EXPORT, FLAT_EXPORT, Entry, build_fixture

BOUNDS = {"max_blocks": 5_000, "max_content_chars": 1_000_000}


def _prepared(entries, tmp_path):
    path = build_fixture(entries, tmp_path / "x.zip")
    warnings: list[tuple] = []
    sink = lambda p, k, d: warnings.append((p, k, d))  # noqa: E731
    archive = open_archive(
        path, tmp_path / "staging", max_entries=50_000,
        max_uncompressed_bytes=5_368_709_120, warn=sink,
    )
    tree = build_tree(archive, max_pages=10_000, warn=sink)
    assets = {
        name: StagedAsset(
            attachment_id=uuid4(), staged_path=Path(tempfile.mkstemp()[1]),
            filename=name.rsplit("/", 1)[-1], content_type="image/png",
            size_bytes=10, sha256="ab" * 32,
        )
        for name in tree.assets
    }
    return archive, tree, assets, warnings, sink


def _render(title, entries, tmp_path):
    archive, tree, assets, warnings, sink = _prepared(entries, tmp_path)
    node = next(n for n in tree.pages if n.title == title)
    blocks = translate_page(
        node, tree, archive, assets=assets, warn=sink, **BOUNDS
    )
    return blocks, serialize_tree(blocks).content, warnings, tree, assets


def test_the_title_line_is_not_a_block(tmp_path):
    _, content, _, _, _ = _render("Notes", FLAT_EXPORT, tmp_path)
    assert not content.startswith("# Notes")


def test_an_internal_page_link_becomes_a_notes_url(tmp_path):
    _, content, _, tree, _ = _render("Home", FLAT_EXPORT, tmp_path)
    notes = next(n for n in tree.pages if n.title == "Notes")
    assert f"/notes?page={notes.uuid}" in content


def test_a_database_csv_link_becomes_its_page_not_an_attachment(tmp_path):
    _, content, _, tree, _ = _render("Home", FLAT_EXPORT, tmp_path)
    people = next(n for n in tree.pages if n.title == "People")
    assert f"/notes?page={people.uuid}" in content
    assert "/api/v1/pages/attachments/" not in content


def test_an_image_becomes_an_attachment_url(tmp_path):
    _, content, _, _, assets = _render("Notes", FLAT_EXPORT, tmp_path)
    staged = assets["image.png"]
    assert f"![shot](/api/v1/pages/attachments/{staged.attachment_id})" in content


def test_a_missing_target_becomes_a_missing_file_note(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n![gone](nowhere.png)\n"),
    ]
    _, content, warnings, _, _ = _render("A", entries, tmp_path)
    assert "[missing file: nowhere.png]" in content
    assert any(w[1] == "missing_file" for w in warnings)


def test_a_missing_page_link_keeps_its_text_and_loses_its_target(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\nsee [Gone](Gone%2000000000000000000000000000000009.md) x\n"),
    ]
    _, content, warnings, _, _ = _render("A", entries, tmp_path)
    assert "Gone" in content and "00000000000000000000000000000009.md" not in content
    assert any(w[1] == "unresolved_link" for w in warnings)


def test_an_external_link_is_unchanged(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n[site](https://example.test/x) tail\n"),
    ]
    _, content, _, _, _ = _render("A", entries, tmp_path)
    assert "https://example.test/x" in content


def test_an_aside_becomes_a_callout(tmp_path):
    blocks, _, _, _, _ = _render("Trip (2026) plan", FLAT_EXPORT, tmp_path)
    callouts = [b for b in blocks if b.type == "callout"]
    assert len(callouts) == 1
    assert (callouts[0].properties or {}).get("variant") == "info"
    assert "[!NOTE]" not in callouts[0].text


def test_a_checkbox_item_becomes_a_todo(tmp_path):
    blocks, _, _, _, _ = _render("Notes", FLAT_EXPORT, tmp_path)
    todos = [b for b in blocks if b.type == "todo"]
    assert [b.text for b in todos] == ["open task", "done task"]
    assert [(b.properties or {}).get("checked") for b in todos] == [False, True]
    assert all("marker" not in (b.properties or {}) for b in todos)


def test_a_database_page_renders_its_csv_as_a_table(tmp_path):
    blocks, content, _, _, _ = _render("Board", DATABASE_EXPORT, tmp_path)
    assert any(b.type == "table" for b in blocks)
    assert len([b for b in blocks if b.type == "table_row"]) == 2
    assert "| Name | Status |" in content


def test_a_database_page_drops_its_filters_and_sort_tail(tmp_path):
    _, content, warnings, _, _ = _render("People", FLAT_EXPORT, tmp_path)
    assert "filters:" not in content and "sort:" not in content
    assert any(w[1] == "stripped_source" for w in warnings)


def test_a_cell_holding_a_pipe_is_escaped(tmp_path):
    entries = [
        Entry("Board 00000000000000000000000000000021.md",
              b"# Board\n\n[T](T%201507-2c1e_all.csv)\n"),
        Entry("T 1507-2c1e_all.csv",
              "﻿Name,Note\na|b,two\n".encode("utf-8")),
    ]
    _, content, _, _, _ = _render("Board", entries, tmp_path)
    assert r"a\|b" in content


def test_a_row_page_property_block_becomes_a_bullet_list(tmp_path):
    blocks, content, _, _, _ = _render("Ship", DATABASE_EXPORT, tmp_path)
    assert content.startswith("- Status: Open")
    assert blocks[0].type == "list"


def test_a_page_over_the_block_bound_is_truncated(tmp_path):
    body = "\n\n".join(f"para {i}" for i in range(50))
    entries = [
        Entry("Big 00000000000000000000000000000001.md",
              f"# Big\n\n{body}\n".encode("utf-8")),
    ]
    archive, tree, assets, warnings, sink = _prepared(entries, tmp_path)
    node = next(n for n in tree.pages if n.title == "Big")
    blocks = translate_page(
        node, tree, archive, assets=assets, warn=sink,
        max_blocks=10, max_content_chars=1_000_000,
    )
    assert len(blocks) == 10
    assert any(w[1] == "truncated" for w in warnings)


def test_a_page_over_the_character_bound_is_truncated(tmp_path):
    body = "\n\n".join("x" * 200 for _ in range(20))
    entries = [
        Entry("Big 00000000000000000000000000000001.md",
              f"# Big\n\n{body}\n".encode("utf-8")),
    ]
    archive, tree, assets, warnings, sink = _prepared(entries, tmp_path)
    node = next(n for n in tree.pages if n.title == "Big")
    blocks = translate_page(
        node, tree, archive, assets=assets, warn=sink,
        max_blocks=5_000, max_content_chars=500,
    )
    assert len(serialize_tree(blocks).content) <= 500
    assert any(w[1] == "truncated" for w in warnings)


def test_every_block_respects_the_page_parent_rule(tmp_path):
    from app.services.block_verbs import _check_page_nesting

    blocks, _, _, _, _ = _render("Notes", FLAT_EXPORT, tmp_path)
    by_id = {b.id: b for b in blocks}
    for block in blocks:
        parent = by_id.get(block.parent_id) if block.parent_id else None
        _check_page_nesting(parent, block)


def test_a_notion_so_link_in_the_export_becomes_a_page_link(tmp_path):
    target = "T 00000000000000000000000000000009.md"
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n[T](https://www.notion.so/workspace/T-"
              b"00000000000000000000000000000009) x\n"),
        Entry(target, b"# T\n"),
    ]
    _, content, _, tree, _ = _render("A", entries, tmp_path)
    t = next(n for n in tree.pages if n.title == "T")
    assert f"/notes?page={t.uuid}" in content
    assert "notion.so" not in content


def test_a_notion_so_link_outside_the_export_is_unchanged(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n[Gone](https://www.notion.so/workspace/Gone-"
              b"000000000000000000000000000000ff) x\n"),
    ]
    _, content, _, _, _ = _render("A", entries, tmp_path)
    assert "notion.so" in content
    assert "/notes?page=" not in content


def test_a_frontmatter_fence_is_stripped(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"---\ntags: x\n---\n\n# A\n\nBody.\n"),
    ]
    blocks, content, warnings, _, _ = _render("A", entries, tmp_path)
    assert "tags: x" not in content
    assert any(w[1] == "stripped_source" for w in warnings)
    assert not any(b.type == "heading" for b in blocks)


def test_a_fenced_link_definition_is_left_alone(tmp_path):
    sample = "[a]: https://x.test\nsee [t][a]\n"
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              ("# A\n\n```\n" + sample + "```\n\nBody.\n").encode("utf-8")),
    ]
    blocks, _, warnings, _, _ = _render("A", entries, tmp_path)
    code = [b for b in blocks if b.type == "code"]
    assert len(code) == 1
    assert code[0].text == sample.rstrip("\n")
    assert not any(w[1] == "stripped_source" for w in warnings)


def test_a_fenced_aside_is_left_alone(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n```\n<aside>x</aside>\n```\n\nBody.\n"),
    ]
    blocks, _, _, _, _ = _render("A", entries, tmp_path)
    code = [b for b in blocks if b.type == "code"]
    assert len(code) == 1
    assert code[0].text == "<aside>x</aside>"


def test_a_fenced_sort_line_does_not_truncate_a_database_page(tmp_path):
    entries = [
        Entry("Board 00000000000000000000000000000021.md",
              b"# Board\n\n[Tasks](Tasks%201507-2c1e_all.csv)\n\n"
              b"```\nsort:\nname\n```\n\nTail text.\n"),
        Entry("Tasks 1507-2c1e_all.csv",
              "﻿Name,Status\nShip,Open\n".encode("utf-8")),
    ]
    blocks, content, _, _, _ = _render("Board", entries, tmp_path)
    code = [b for b in blocks if b.type == "code"]
    assert len(code) == 1
    assert code[0].text == "sort:\nname"
    assert "Tail text." in content
