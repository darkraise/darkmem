"""Notion-export-shaped zips for the import tests.

Every shape here was measured against a real 2260-entry export on 2026-09-20
and is recorded in the design spec's section 3. `zipfile` cannot write an
encrypted member, so the hostile fixture sets the flag bit by hand -- readers
check the bit, which is all the importer's skip path needs.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

WRAPPER = "Export-68aaaecf-999e-41c4-aef1-6627846f2afb"

# A 1x1 PNG. Sniffed as image/png by the attachment store's magic-byte check.
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _id(n: int) -> str:
    return f"{n:032x}"


def _csv(header: list[str], rows: list[list[str]]) -> bytes:
    lines = [",".join(header)]
    lines += [",".join(row) for row in rows]
    return b"\xef\xbb\xbf" + ("\n".join(lines) + "\n").encode("utf-8")


class Entry:
    """One archive member, with the flags a hostile case needs."""

    def __init__(
        self, name: str, data: bytes, *, symlink: bool = False,
        encrypted: bool = False, raw: bool = False,
    ) -> None:
        self.name = name
        self.data = data
        self.symlink = symlink
        self.encrypted = encrypted
        # A traversal or absolute name must not be prefixed, or the wrapper
        # makes it an ordinary relative name and the defence goes untested.
        self.raw = raw

    def written_name(self, prefix: str) -> str:
        return self.name if self.raw else f"{prefix}{self.name}"


def _write(archive: zipfile.ZipFile, entry: Entry, prefix: str) -> None:
    info = zipfile.ZipInfo(entry.written_name(prefix))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o120777 if entry.symlink else 0o100644) << 16
    archive.writestr(info, entry.data)


def _mark_encrypted(dest: Path, name: bytes) -> None:
    """Set the encryption bit on `name`'s two headers, after the archive closed.

    `ZipFile.writestr` assigns `flag_bits` itself, so a bit set on the ZipInfo
    beforehand is discarded. The bit lives at +6 in a local file header and at
    +8 in a central-directory entry.
    """
    data = bytearray(dest.read_bytes())
    for magic, name_len_at, name_at, flag_at in (
        (b"PK\x03\x04", 26, 30, 6), (b"PK\x01\x02", 28, 46, 8),
    ):
        index = 0
        while (index := data.find(magic, index)) != -1:
            length = int.from_bytes(data[index + name_len_at:index + name_len_at + 2], "little")
            start = index + name_at
            if data[start:start + length] == name:
                data[index + flag_at] |= 0x01
            index += 4
    dest.write_bytes(bytes(data))


def build_fixture(
    entries: list[Entry], dest: Path, *, wrapper: str | None = WRAPPER,
) -> Path:
    """Write `entries` to `dest`, each under `wrapper` unless it is None."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"{wrapper}/" if wrapper else ""
    with zipfile.ZipFile(dest, "w") as archive:
        for entry in entries:
            _write(archive, entry, prefix)
    for entry in entries:
        if entry.encrypted:
            _mark_encrypted(dest, entry.written_name(prefix).encode("utf-8"))
    return dest


def _inner_zip(entries: list[Entry], wrapper: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for entry in entries:
            _write(archive, entry, f"{wrapper}/")
    return buffer.getvalue()


# A flat export: no folders, a root page linking to two children on their own
# lines, a database with a stub page and two row pages, and one image.
FLAT_EXPORT = [
    Entry(
        f"Home {_id(1)}.md",
        (
            f"# Home\n\n"
            f"[Notes](Notes%20{_id(2)}.md)\n\n"
            f"[Trip (2026) plan](Trip%20%282026%29%20plan%20{_id(3)}.md)\n\n"
            f"[People](People%20{_id(4)}_all.csv)\n"
        ).encode("utf-8"),
    ),
    Entry(
        f"Notes {_id(2)}.md",
        f"# Notes\n\n![shot](image.png)\n\n- [ ] open task\n- [x] done task\n".encode("utf-8"),
    ),
    Entry(
        f"Trip (2026) plan {_id(3)}.md",
        (
            "# Trip (2026) plan\n\n"
            "<aside>\nFirst paragraph.\n\nSecond paragraph.\n</aside>\n"
        ).encode("utf-8"),
    ),
    Entry(f"People {_id(4)}.md",
          f"# People\n\n[People](People%20{_id(4)}_all.csv)\n\nfilters: \nName\nsort: \nName: ascending\n".encode("utf-8")),
    Entry(f"People {_id(4)}_all.csv",
          _csv(["Name", "Role"], [["Ada", "Lead"], ["Ada", "Lead"]])),
    Entry(f"Ada {_id(5)}.md", "# Ada\n\nRole: Lead\n\nFirst hire.\n".encode("utf-8")),
    Entry(f"Ada {_id(6)}.md", "# Ada\n\nRole: Lead\n\nSecond hire, same name.\n".encode("utf-8")),
    Entry("image.png", PNG),
]

# "Create folders for subpages" on: a subpage sits in a sibling folder.
FOLDERED_EXPORT = [
    Entry(f"Parent {_id(11)}.md", "# Parent\n\nBody.\n".encode("utf-8")),
    Entry(f"Parent {_id(11)}/Child {_id(12)}.md", "# Child\n\nBody.\n".encode("utf-8")),
]

# A database whose id is not 32-hex, and a database with no stub page.
DATABASE_EXPORT = [
    Entry(f"Board {_id(21)}.md",
          "# Board\n\n[Tasks](Tasks%201507-2c1e_all.csv)\n".encode("utf-8")),
    Entry("Tasks 1507-2c1e_all.csv",
          _csv(["Name", "Status"], [["Ship", "Open"], ["Draft", "Done"]])),
    Entry(f"Orphans {_id(22)}_all.csv",
          _csv(["Name", "Note"], [["Stray", "No stub page"]])),
    Entry(f"Ship {_id(23)}.md", "# Ship\n\nStatus: Open\n\nBody.\n".encode("utf-8")),
]

HOSTILE_EXPORT = [
    Entry(f"Good {_id(31)}.md", "# Good\n\nBody.\n".encode("utf-8")),
    Entry("../escape.md", "# Escape\n".encode("utf-8"), raw=True),
    Entry("/absolute.md", "# Absolute\n".encode("utf-8"), raw=True),
    Entry("link.md", b"/etc/passwd", symlink=True),
    Entry("secret.md", b"opaque", encrypted=True),
]

# An outer archive whose members are the numbered inner zips of one export.
PART_EXPORT = [
    Entry(
        f"{WRAPPER}-Part-1.zip",
        _inner_zip([Entry(f"One {_id(41)}.md", "# One\n\nBody.\n".encode("utf-8"))], WRAPPER),
    ),
    Entry(
        f"{WRAPPER}-Part-2.zip",
        _inner_zip([Entry(f"Two {_id(42)}.md", "# Two\n\nBody.\n".encode("utf-8"))], WRAPPER),
    ),
]

HTML_EXPORT = [
    Entry(f"Home {_id(51)}.html", b"<h1>Home</h1>"),
    Entry("style.css", b"body{}"),
]
