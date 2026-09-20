from __future__ import annotations

import pytest

from app.services.notion_archive import open_archive
from app.services.notion_tree import NotionExportInvalid, build_tree
from tests.fixtures.notion.builder import (
    DATABASE_EXPORT,
    FLAT_EXPORT,
    FOLDERED_EXPORT,
    Entry,
    build_fixture,
)


def _tree(entries, tmp_path, name="x.zip", max_pages=10_000):
    path = build_fixture(entries, tmp_path / name)
    warnings: list[tuple] = []
    archive = open_archive(
        path, tmp_path / "staging", max_entries=50_000,
        max_uncompressed_bytes=5_368_709_120,
        warn=lambda p, k, d: warnings.append((p, k, d)),
    )
    tree = build_tree(
        archive, max_pages=max_pages,
        warn=lambda p, k, d: warnings.append((p, k, d)),
    )
    return tree, warnings


def _by_title(tree):
    return {node.title: node for node in tree.pages}


def test_titles_come_from_the_leading_heading(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    assert "Home" in _by_title(tree)
    assert "Trip (2026) plan" in _by_title(tree)


def test_a_title_falls_back_to_the_stem_without_its_id(tmp_path):
    entries = [Entry("Bare 00000000000000000000000000000001.md", b"No heading here\n")]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["Bare"].notion_id == "0" * 31 + "1"


def test_folder_nesting_parents_a_subpage(tmp_path):
    tree, _ = _tree(FOLDERED_EXPORT, tmp_path)
    nodes = _by_title(tree)
    assert nodes["Child"].parent_uuid == nodes["Parent"].uuid
    assert tree.signal_counts["folder"] == 1


def test_a_standalone_link_parents_its_target(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    nodes = _by_title(tree)
    assert nodes["Notes"].parent_uuid == nodes["Home"].uuid
    assert nodes["Trip (2026) plan"].parent_uuid == nodes["Home"].uuid


def test_an_inline_link_does_not_parent(tmp_path):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\nsee [B](B%2000000000000000000000000000000002.md) inline\n"),
        Entry("B 00000000000000000000000000000002.md", b"# B\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["B"].parent_uuid is None


def test_two_inbound_standalone_links_leave_the_page_at_the_root(tmp_path):
    target = "T 00000000000000000000000000000003.md"
    link = f"[T]({target.replace(' ', '%20')})".encode()
    entries = [
        Entry("A 00000000000000000000000000000001.md", b"# A\n\n" + link + b"\n"),
        Entry("B 00000000000000000000000000000002.md", b"# B\n\n" + link + b"\n"),
        Entry(target, b"# T\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["T"].parent_uuid is None


def test_database_membership_beats_a_standalone_link(tmp_path):
    # A real disagreement: Home links to the row page on its own line, which
    # signal 3 would parent under Home. Signal 2 must win, or 1847 rows scatter
    # out of their database on the measured export.
    row = "Ada 00000000000000000000000000000005.md"
    entries = [
        Entry("Home 00000000000000000000000000000001.md",
              f"# Home\n\n[Ada]({row.replace(' ', '%20')})\n".encode()),
        Entry("People 00000000000000000000000000000004.md",
              b"# People\n\n[People](People%2000000000000000000000000000000004_all.csv)\n"),
        Entry("People 00000000000000000000000000000004_all.csv",
              "﻿Name,Role\nAda,Lead\n".encode("utf-8")),
        Entry(row, b"# Ada\n\nRole: Lead\n\nBody.\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    nodes = _by_title(tree)
    ada = nodes["Ada"]
    assert ada.parent_uuid == nodes["People"].uuid
    assert ada.parent_uuid != nodes["Home"].uuid
    assert ada.row_of == nodes["People"].uuid


def test_row_pages_land_under_their_database(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    people = _by_title(tree)["People"]
    rows = [n for n in tree.pages if n.title == "Ada"]
    assert len(rows) == 2
    assert all(row.parent_uuid == people.uuid for row in rows)


def test_a_database_page_linked_from_its_parent_is_parented(tmp_path):
    # A parent links to the CSV, never to the view stub, and the stub links to
    # its own CSV -- so without excluding that self-link every database would
    # read as ambiguously parented and strand at the root.
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    nodes = _by_title(tree)
    assert nodes["People"].parent_uuid == nodes["Home"].uuid


def test_a_page_whose_keys_match_no_database_is_not_a_row(tmp_path):
    entries = [
        Entry("Note 00000000000000000000000000000001.md",
              b"# Note\n\nAuthor: me\n\nBody.\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    assert _by_title(tree)["Note"].row_of is None


def test_a_database_without_a_stub_page_gets_a_grouping_page(tmp_path):
    tree, _ = _tree(DATABASE_EXPORT, tmp_path)
    assert "Orphans" in _by_title(tree)


def test_a_database_id_need_not_be_32_hex(tmp_path):
    tree, _ = _tree(DATABASE_EXPORT, tmp_path)
    info = tree.databases["Tasks 1507-2c1e_all.csv"]
    assert info.header == ["Name", "Status"]
    assert len(info.rows) == 2
    assert info.page_uuid == _by_title(tree)["Board"].uuid


def test_a_link_cycle_is_broken_with_a_warning(tmp_path):
    a = "A 00000000000000000000000000000001.md"
    b = "B 00000000000000000000000000000002.md"
    entries = [
        Entry(a, f"# A\n\n[B]({b.replace(' ', '%20')})\n".encode()),
        Entry(b, f"# B\n\n[A]({a.replace(' ', '%20')})\n".encode()),
    ]
    tree, warnings = _tree(entries, tmp_path)
    parents = {n.title: n.parent_uuid for n in tree.pages}
    assert list(parents.values()).count(None) >= 1
    assert any(w[1] == "hierarchy_cycle" for w in warnings)
    cycle = [w for w in warnings if w[1] == "hierarchy_cycle"][0]
    assert cycle[0] == ""
    assert a in cycle[2] and b in cycle[2]


def test_a_parent_always_precedes_its_children(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    seen: set = set()
    for node in tree.pages:
        assert node.parent_uuid is None or node.parent_uuid in seen
        seen.add(node.uuid)


def test_siblings_are_ordered_alphabetically(tmp_path):
    entries = [
        Entry("Zeta 00000000000000000000000000000001.md", b"# Zeta\n"),
        Entry("Alpha 00000000000000000000000000000002.md", b"# Alpha\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    roots = sorted((n for n in tree.pages if n.parent_uuid is None),
                   key=lambda n: n.order)
    assert [n.title for n in roots] == ["Alpha", "Zeta"]


def test_row_pages_take_csv_row_order(tmp_path):
    tree, _ = _tree(DATABASE_EXPORT, tmp_path)
    board = _by_title(tree)["Board"]
    rows = sorted((n for n in tree.pages if n.row_of == board.uuid),
                  key=lambda n: n.order)
    assert [n.title for n in rows] == ["Ship"]


def test_rows_sharing_a_title_take_the_csv_rows_in_entry_order(tmp_path):
    # Two "Ada" pages against two "Ada" rows: which page takes which rank is
    # entry order, and nothing else in the export distinguishes them.
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    people = _by_title(tree)["People"]
    rows = sorted((n for n in tree.pages if n.row_of == people.uuid),
                  key=lambda n: n.order)
    assert [n.entry.name for n in rows] == [
        "Ada 00000000000000000000000000000005.md",
        "Ada 00000000000000000000000000000006.md",
    ]


def test_a_csv_row_with_no_page_of_that_title_ranks_nothing(tmp_path):
    entries = [
        Entry("Board 00000000000000000000000000000021.md",
              b"# Board\n\n[Tasks](Tasks%201507-2c1e_all.csv)\n"),
        Entry("Tasks 1507-2c1e_all.csv",
              "﻿Name,Status\nGhost,Open\nShip,Open\n".encode("utf-8")),
        Entry("Ship 00000000000000000000000000000023.md",
              b"# Ship\n\nStatus: Open\n\nBody.\n"),
    ]
    tree, _ = _tree(entries, tmp_path)
    board = _by_title(tree)["Board"]
    rows = [n for n in tree.pages if n.row_of == board.uuid]
    assert [(n.title, n.order) for n in rows] == [("Ship", 0)]


def test_assets_are_indexed_and_not_pages(tmp_path):
    tree, _ = _tree(FLAT_EXPORT, tmp_path)
    assert "image.png" in tree.assets
    assert not any(n.title == "image.png" for n in tree.pages)


def test_the_page_cap_refuses(tmp_path):
    with pytest.raises(NotionExportInvalid):
        _tree(FLAT_EXPORT, tmp_path, max_pages=2)


def test_a_folder_cycle_is_broken_with_a_warning(tmp_path):
    a = f"A {'0' * 31}1"
    b = f"B {'0' * 31}2"
    entries = [Entry(f"{b}/{a}.md", b"# A\n"), Entry(f"{a}/{b}.md", b"# B\n")]
    tree, warnings = _tree(entries, tmp_path)
    assert {n.title for n in tree.pages} == {"A", "B"}
    assert any(w[1] == "hierarchy_cycle" for w in warnings)


def test_a_database_membership_cycle_is_broken_with_a_warning(tmp_path):
    r = f"R {'0' * 31}1"
    p = f"P {'0' * 31}2"
    entries = [
        Entry(f"{r}.md", b"# R\n\nStatus: Open\n\nBody.\n"),
        Entry(f"{r}/{p}.md", b"# P\n"),
        Entry(f"{r}/{p}_all.csv", "﻿Name,Status\nShip,Open\n".encode("utf-8")),
    ]
    tree, warnings = _tree(entries, tmp_path)
    assert {n.title for n in tree.pages} == {"R", "P"}
    assert any(w[1] == "hierarchy_cycle" for w in warnings)


def test_no_page_is_lost_between_the_entries_and_the_tree(tmp_path):
    a = f"A {'0' * 31}1"
    b = f"B {'0' * 31}2"
    cyclic = [Entry(f"{b}/{a}.md", b"# A\n"), Entry(f"{a}/{b}.md", b"# B\n")]
    for index, entries in enumerate((FLAT_EXPORT, DATABASE_EXPORT, cyclic)):
        tree, _ = _tree(entries, tmp_path, name=f"count{index}.zip")
        filed = [n for n in tree.pages if n.entry is not None]
        assert len(filed) == len([e for e in entries if e.name.endswith(".md")])
        assert sum(tree.signal_counts.values()) == len(tree.pages)
