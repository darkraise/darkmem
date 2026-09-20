from __future__ import annotations

import builtins
import hashlib
import zipfile
from pathlib import Path

import pytest

from app.services.notion_archive import (
    MAX_TEXT_BYTES,
    NotionArchiveInvalid,
    NotionArchiveTooLarge,
    _decode_name,
    open_archive,
)
from tests.fixtures.notion.builder import (
    FLAT_EXPORT,
    HOSTILE_EXPORT,
    PART_EXPORT,
    WRAPPER,
    Entry,
    build_fixture,
)

LIMITS = {"max_entries": 50_000, "max_uncompressed_bytes": 5_368_709_120}


def _open(path, staging, **over):
    warnings: list[tuple[str, str, str]] = []
    limits = {**LIMITS, **over}
    archive = open_archive(
        path, staging, warn=lambda p, k, d: warnings.append((p, k, d)), **limits
    )
    return archive, warnings


def test_the_wrapper_folder_is_stripped(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive, _ = _open(path, tmp_path / "staging")
    assert archive.entries
    assert all("/" not in e.name for e in archive.entries)
    assert any(e.name.startswith("Home ") for e in archive.entries)


def test_a_wrapper_with_many_children_is_still_stripped(tmp_path):
    # The real export's wrapper holds 2260 children, so a "single child" rule
    # would not fire on it. The signal is one shared id-less component.
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive, _ = _open(path, tmp_path / "staging")
    assert len(archive.entries) >= 8


def test_traversal_absolute_symlink_and_encrypted_entries_are_skipped(tmp_path):
    path = build_fixture(HOSTILE_EXPORT, tmp_path / "hostile.zip")
    archive, warnings = _open(path, tmp_path / "staging")
    names = {e.name for e in archive.entries}
    assert not [n for n in names if ".." in n or n.startswith("/")]
    assert "link.md" not in names
    assert "secret.md" not in names
    assert any(n.startswith("Good ") for n in names)
    assert {w[1] for w in warnings} == {"skipped_entry"}


def test_a_flagless_utf8_name_is_recovered():
    # zipfile cannot WRITE a flagless non-ASCII name -- it sets the UTF-8 flag
    # whenever the name needs one -- so the decoder is tested directly. A
    # flagless entry holding the UTF-8 bytes of "café.md" reaches us as
    # its cp437 reading, "caf├⌐.md", and must decode back.
    info = zipfile.ZipInfo("caf├⌐.md")
    info.flag_bits = 0
    assert _decode_name(info) == "café.md"


def test_a_genuine_cp437_name_is_kept():
    info = zipfile.ZipInfo("café.md")
    info.flag_bits = 0
    assert _decode_name(info) == "café.md"


def test_a_flagged_name_is_taken_as_is():
    info = zipfile.ZipInfo("café.md")
    info.flag_bits = 0x800
    assert _decode_name(info) == "café.md"


def test_a_duplicate_name_keeps_the_first_entry(tmp_path):
    entries = [
        Entry("Dup 00000000000000000000000000000001.md", b"# First\n"),
        Entry("Dup 00000000000000000000000000000001.md", b"# Second\n"),
    ]
    path = build_fixture(entries, tmp_path / "dup.zip")
    archive, warnings = _open(path, tmp_path / "staging")
    assert len(archive.entries) == 1
    assert archive.read_text(archive.entries[0]) == "# First\n"
    assert any(w[1] == "skipped_entry" for w in warnings)


def test_the_entry_count_cap_refuses(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    with pytest.raises(NotionArchiveTooLarge):
        _open(path, tmp_path / "staging", max_entries=2)


def test_the_declared_sizes_give_an_early_refusal(tmp_path):
    entries = [Entry("Big 00000000000000000000000000000001.md", b"x" * 5000)]
    path = build_fixture(entries, tmp_path / "big.zip")
    with pytest.raises(NotionArchiveTooLarge):
        _open(path, tmp_path / "staging", max_uncompressed_bytes=100)


def test_the_running_counter_bounds_the_total_across_reads(tmp_path):
    # The declared total (1800) clears the bound, so only the counter can stop
    # this. Each entry is read twice, which is what the import itself does --
    # once for the title and property block, once to translate the body.
    entries = [
        Entry(f"P{i} {i:032x}.md", b"x" * 600) for i in range(3)
    ]
    path = build_fixture(entries, tmp_path / "many.zip")
    archive, _ = _open(path, tmp_path / "staging", max_uncompressed_bytes=2000)
    with pytest.raises(NotionArchiveTooLarge):
        for _ in range(2):
            for entry in archive.entries:
                archive.read_text(entry)


def test_read_text_refuses_a_member_past_the_text_ceiling(tmp_path):
    # Clears both caller-supplied bounds: the ceiling read_text keeps for its
    # own in-memory buffer is the only thing that can stop this.
    entries = [
        Entry("Big 00000000000000000000000000000001.md",
              b"x" * (MAX_TEXT_BYTES + 1)),
    ]
    path = build_fixture(entries, tmp_path / "huge.zip")
    archive, _ = _open(path, tmp_path / "staging")
    with pytest.raises(NotionArchiveTooLarge):
        archive.read_text(archive.entries[0])


def test_a_tampered_size_is_refused_rather_than_raising_BadZipFile(tmp_path):
    # Understating the central directory's uncompressed size does not let more
    # bytes through -- zipfile stops at the declared length and the CRC check
    # fails. What matters is that the caller sees this module's own refusal, so
    # the route answers 422 instead of a 500 from a zipfile internal.
    entries = [Entry("Big 00000000000000000000000000000001.md", b"x" * 5000)]
    path = build_fixture(entries, tmp_path / "liar.zip")
    raw = bytearray(path.read_bytes())
    index = raw.find(b"PK\x01\x02")
    assert index != -1
    raw[index + 24:index + 28] = (10).to_bytes(4, "little")  # uncompressed size
    path.write_bytes(bytes(raw))

    archive, _ = _open(path, tmp_path / "staging")
    with pytest.raises(NotionArchiveInvalid):
        archive.read_text(archive.entries[0])


def test_a_truncated_archive_is_refused(tmp_path):
    path = build_fixture(
        [Entry("A 00000000000000000000000000000001.md", b"# A\n")],
        tmp_path / "cut.zip",
    )
    path.write_bytes(path.read_bytes()[: -40])
    with pytest.raises(NotionArchiveInvalid):
        _open(path, tmp_path / "staging")


def test_extract_returns_size_hash_and_sniffed_type(tmp_path):
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive, _ = _open(path, tmp_path / "staging")
    png = next(e for e in archive.entries if e.name == "image.png")
    dest = tmp_path / "out.bin"

    size, digest, content_type = archive.extract(png, dest)

    raw = dest.read_bytes()
    assert size == len(raw)
    assert digest == hashlib.sha256(raw).hexdigest()
    assert content_type == "image/png"


def test_a_failing_destination_is_not_blamed_on_the_export(tmp_path, monkeypatch):
    # A full or unwritable disk is not a malformed export, so it must not reach
    # the caller as this module's 422.
    path = build_fixture(FLAT_EXPORT, tmp_path / "flat.zip")
    archive, _ = _open(path, tmp_path / "staging")
    png = next(e for e in archive.entries if e.name == "image.png")
    dest = tmp_path / "out" / "image.png"
    real_open = builtins.open

    def refuse(file, *args, **kwargs):
        if Path(file) == dest:
            raise OSError(28, "No space left on device")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", refuse)
    with pytest.raises(OSError):
        archive.extract(png, dest)
    monkeypatch.undo()
    assert not dest.exists()


def test_a_part_export_reads_as_one_tree(tmp_path):
    path = build_fixture(PART_EXPORT, tmp_path / "parts.zip")
    archive, _ = _open(path, tmp_path / "staging")
    names = sorted(e.name for e in archive.entries)
    assert [n.split(" ")[0] for n in names] == ["One", "Two"]
    assert sorted(e.part for e in archive.entries) == [1, 2]


def test_an_unreadable_part_member_is_refused(tmp_path):
    path = build_fixture(
        [Entry(f"{WRAPPER}-Part-1.zip", b"not a zip")], tmp_path / "parts.zip"
    )
    with pytest.raises(NotionArchiveInvalid):
        _open(path, tmp_path / "staging")


def test_a_zip_attachment_is_not_opened_as_a_part(tmp_path):
    entries = [
        Entry("Page 00000000000000000000000000000001.md", b"# Page\n\n[z](ODT.zip)\n"),
        Entry("ODT.zip", b"PK\x05\x06" + b"\x00" * 18),
    ]
    path = build_fixture(entries, tmp_path / "attach.zip")
    archive, _ = _open(path, tmp_path / "staging")
    assert {e.name for e in archive.entries} == {
        "Page 00000000000000000000000000000001.md", "ODT.zip",
    }


def test_an_archive_with_no_markdown_is_invalid(tmp_path):
    path = build_fixture([Entry("only.txt", b"hi")], tmp_path / "none.zip")
    with pytest.raises(NotionArchiveInvalid):
        _open(path, tmp_path / "staging")
