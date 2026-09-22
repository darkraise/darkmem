"""The fixture builder, and the spec claims the fixtures encode.

The claims in `test_real_export_matches_the_spec` were measured against a real
export on 2026-09-20 and written into the design spec's section 3. The test
re-measures them whenever that archive is present, so a spec claim cannot rot
into folklore.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.notion.builder import (
    DATABASE_EXPORT,
    FLAT_EXPORT,
    FOLDERED_EXPORT,
    HOSTILE_EXPORT,
    HTML_EXPORT,
    PART_EXPORT,
    WRAPPER,
    build_fixture,
)

REAL_EXPORT = Path("/root/notion-export/export.zip")


def test_flat_export_is_flat_under_one_wrapper(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    names = zipfile.ZipFile(path).namelist()
    assert names, "the fixture wrote no entries"
    assert all(n.startswith(WRAPPER + "/") for n in names)
    assert all(n[len(WRAPPER) + 1:].count("/") == 0 for n in names)


def test_flat_export_pages_carry_an_id_and_a_title(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive = zipfile.ZipFile(path)
    pages = [n for n in archive.namelist() if n.endswith(".md")]
    assert len(pages) >= 4
    for name in pages:
        stem = name.rsplit("/", 1)[-1][: -len(".md")]
        assert re.search(r" [0-9a-f]{32}$", stem), stem
        assert archive.read(name).decode("utf-8").startswith("# ")


def test_foldered_export_nests_subpages(tmp_path):
    path = build_fixture(FOLDERED_EXPORT, tmp_path / "foldered.zip")
    names = [n[len(WRAPPER) + 1:] for n in zipfile.ZipFile(path).namelist()]
    assert any(n.count("/") == 1 for n in names)


def test_database_export_has_a_stubless_database_and_a_short_id(tmp_path):
    path = build_fixture(DATABASE_EXPORT, tmp_path / "db.zip")
    names = [n[len(WRAPPER) + 1:] for n in zipfile.ZipFile(path).namelist()]
    csvs = [n for n in names if n.endswith("_all.csv")]
    assert any(not re.search(r" [0-9a-f]{32}_all\.csv$", n) for n in csvs), (
        "no short-id CSV: the real export carries 'Untitled 1507-2c1e_all.csv'"
    )
    stubless = [
        n for n in csvs
        if n[: -len("_all.csv")] + ".md" not in names
    ]
    assert stubless, "every database has a stub page; one must not"


def test_database_csvs_carry_a_utf8_bom(tmp_path):
    path = build_fixture(DATABASE_EXPORT, tmp_path / "db.zip")
    archive = zipfile.ZipFile(path)
    for name in archive.namelist():
        if name.endswith(".csv"):
            assert archive.read(name).startswith(b"\xef\xbb\xbf"), name


def test_hostile_export_carries_each_defence_case(tmp_path):
    path = build_fixture(HOSTILE_EXPORT, tmp_path / "hostile.zip")
    infos = {i.filename: i for i in zipfile.ZipFile(path).infolist()}
    assert any(".." in n for n in infos), "no traversal entry"
    assert any(n.startswith("/") for n in infos), "no absolute entry"
    assert any(i.external_attr >> 16 & 0o170000 == 0o120000 for i in infos.values()), (
        "no symlink entry"
    )
    assert any(i.flag_bits & 0x1 for i in infos.values()), "no encrypted entry"


def test_part_export_wraps_numbered_inner_zips(tmp_path):
    path = build_fixture(PART_EXPORT, tmp_path / "parts.zip")
    names = zipfile.ZipFile(path).namelist()
    assert len([n for n in names if re.search(r"Part-\d+\.zip$", n)]) == 2
    assert not [n for n in names if n.endswith(".md")], (
        "a Part export holds no markdown at the outer level"
    )


def test_html_export_holds_no_markdown(tmp_path):
    path = build_fixture(HTML_EXPORT, tmp_path / "html.zip")
    names = zipfile.ZipFile(path).namelist()
    assert any(n.endswith(".html") for n in names)
    assert not any(n.endswith(".md") for n in names)


def test_real_export_matches_the_spec():
    # This optional local archive may live under an inaccessible /root on CI.
    # Open it at test time: even is_file() can raise during collection.
    try:
        archive = zipfile.ZipFile(REAL_EXPORT)
    except (FileNotFoundError, PermissionError):
        pytest.skip("the real export is absent or inaccessible on this host")
    names = archive.namelist()
    tops = {n.split("/")[0] for n in names}
    assert len(tops) == 1, "spec section 3: one id-less wrapper folder"
    wrapper = tops.pop()
    assert not re.search(r" [0-9a-f]{32}$", wrapper)

    rel = [n[len(wrapper) + 1:] for n in names]
    assert all(r.count("/") == 0 for r in rel), "spec section 3: the export is flat"

    pages = [r for r in rel if r.endswith(".md")]
    assert all(re.search(r" [0-9a-f]{32}$", p[: -len(".md")]) for p in pages)

    csvs = [r for r in rel if r.endswith(".csv")]
    assert csvs and all(c.endswith("_all.csv") for c in csvs), (
        "spec section 3: only _all.csv exists"
    )
    assert any(not re.search(r" [0-9a-f]{32}_all\.csv$", c) for c in csvs), (
        "spec section 3: one CSV id is not 32-hex"
    )
