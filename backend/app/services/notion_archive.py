"""Reading a Notion export archive safely.

No entry name is ever joined into a filesystem path: entries are read by name
through `zipfile`, and an extraction writes to a destination the caller minted.
The central directory's declared sizes buy a cheap early refusal, but a crafted
archive can lie in them, so the enforced bound is a running counter over
chunked reads -- `read()` of a whole entry is never called.
"""
from __future__ import annotations

import hashlib
import logging
import re
import zipfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO
from zipfile import ZipInfo

from app.services.page_attachments import sniff_content_type

logger = logging.getLogger(__name__)

CHUNK = 1 << 16
# A ceiling on what `read_text` will hold in memory for one member. A page's
# stored text is bounded by MAX_CONTENT_CHARS (1M) and the later stages
# truncate to it, so no source a page can use comes near this -- the largest
# page in the measured export is 182 KB. A literal rather than an import
# because this module knows nothing about pages.
MAX_TEXT_BYTES = 16 << 20
_SNIFF_BYTES = 16
_ID_SUFFIX = re.compile(r" [0-9a-f]{32}$")
_PART_SUFFIX = re.compile(r"[-_ ]?Part[-_ ]?(\d+)\.zip$", re.IGNORECASE)
_DRIVE = re.compile(r"^[A-Za-z]:")

Warn = Callable[[str, str, str], None]


class NotionArchiveInvalid(ValueError):
    """The archive is not a Markdown & CSV Notion export."""


class NotionArchiveTooLarge(ValueError):
    """The archive passed an entry-count or uncompressed-bytes ceiling."""


_ZIP_FAILURES = (zipfile.BadZipFile, OSError, EOFError)


@contextmanager
def _folding(what: str) -> Iterator[None]:
    """The module's one definition of "a zipfile failure is our 422".

    It belongs around the SOURCE side only -- opening or reading a member, or
    opening a staged part. A failure writing to a destination is the disk, not
    the export, and must reach the caller as itself.
    """
    try:
        yield
    except _ZIP_FAILURES as exc:
        raise NotionArchiveInvalid(f"{what}: {exc}") from exc


def _read_chunks(handle: IO[bytes], what: str) -> Iterator[bytes]:
    while True:
        with _folding(what):
            chunk = handle.read(CHUNK)
        if not chunk:
            return
        yield chunk


@dataclass(frozen=True)
class ArchiveEntry:
    name: str
    info: ZipInfo
    size: int
    part: int


def _decode_name(info: zipfile.ZipInfo) -> str:
    """Recover a UTF-8 name from an entry that did not set the UTF-8 flag.

    `zipfile` decodes such a name as cp437. Most producers actually wrote
    UTF-8, so re-encoding to cp437 and decoding as UTF-8 recovers it; a name
    that really was cp437 fails that decode and keeps what zipfile gave us.
    """
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def _normalise(name: str) -> str | None:
    """A `/`-separated relative name, or None when the entry must be skipped."""
    candidate = name.replace("\\", "/")
    if candidate.startswith("/") or _DRIVE.match(candidate):
        return None
    parts = [p for p in candidate.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return "/".join(parts) or None


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return (info.external_attr >> 16) & 0o170000 == 0o120000


def _is_encrypted(info: zipfile.ZipInfo) -> bool:
    return bool(info.flag_bits & 0x1)


def _strip_wrapper(names: list[str]) -> int:
    """How many leading path components every entry shares and none identifies.

    Notion wraps a workspace export in one `Export-<uuid>/` folder, and a
    teamspace export adds more. The signal is a single shared component that
    carries no 32-hex id -- not how many children it has, since the measured
    export's wrapper holds 2260.
    """
    depth = 0
    while True:
        heads = {n.split("/")[0] for n in names if n.count("/") > depth - 1}
        if len(heads) != 1:
            return depth
        head = heads.pop()
        if _ID_SUFFIX.search(head):
            return depth
        if not all(n.startswith(head + "/") for n in names):
            return depth
        names = [n[len(head) + 1:] for n in names]
        depth += 1


class _Source:
    """One physical zip and the entries taken from it."""

    def __init__(self, path: Path, part: int) -> None:
        self.zip = zipfile.ZipFile(path)
        self.part = part


class NotionArchive:
    def __init__(self, sources: list[_Source], max_uncompressed_bytes: int) -> None:
        self._sources = {s.part: s for s in sources}
        self._max = max_uncompressed_bytes
        self._read = 0
        self.entries: list[ArchiveEntry] = []

    def open(self, entry: ArchiveEntry) -> IO[bytes]:
        # By ZipInfo, never by name: zipfile's NameToInfo keeps the LAST entry
        # of a duplicated name, so opening by name would hand back the entry
        # `_collect` deliberately skipped.
        with _folding(f"{entry.name} could not be read"):
            return self._sources[entry.part].zip.open(entry.info)

    def _consume(self, n: int) -> None:
        self._read += n
        if self._read > self._max:
            raise NotionArchiveTooLarge(
                f"the archive expands past {self._max} bytes"
            )

    def read_text(self, entry: ArchiveEntry) -> str:
        buffer = bytearray()
        with self.open(entry) as handle:
            for chunk in _read_chunks(handle, f"{entry.name} could not be read"):
                self._consume(len(chunk))
                if len(buffer) + len(chunk) > MAX_TEXT_BYTES:
                    raise NotionArchiveTooLarge(
                        f"{entry.name} expands past {MAX_TEXT_BYTES} bytes of text"
                    )
                buffer += chunk
        return buffer.decode("utf-8-sig", errors="replace")

    def extract(self, entry: ArchiveEntry, dest: Path) -> tuple[int, str, str]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        head = b""
        try:
            with self.open(entry) as handle, open(dest, "wb") as out:
                for chunk in _read_chunks(handle, f"{entry.name} could not be read"):
                    self._consume(len(chunk))
                    size += len(chunk)
                    if len(head) < _SNIFF_BYTES:
                        head += chunk[: _SNIFF_BYTES - len(head)]
                    digest.update(chunk)
                    out.write(chunk)
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        return size, digest.hexdigest(), sniff_content_type(head)

    def close(self) -> None:
        for source in self._sources.values():
            source.zip.close()


def _collect(zf: zipfile.ZipFile, part: int, warn: Warn) -> list[ArchiveEntry]:
    seen: set[str] = set()
    out: list[ArchiveEntry] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        decoded = _decode_name(info)
        if _is_symlink(info):
            warn(decoded, "skipped_entry", "symlink entries are not read")
            continue
        if _is_encrypted(info):
            warn(decoded, "skipped_entry", "encrypted entries cannot be read")
            continue
        name = _normalise(decoded)
        if name is None:
            warn(decoded, "skipped_entry", "the name escapes the archive root")
            continue
        if name in seen:
            warn(name, "skipped_entry", "a duplicate name; the first entry wins")
            continue
        seen.add(name)
        out.append(ArchiveEntry(name=name, info=info,
                                size=info.file_size, part=part))
    return out


def open_archive(
    zip_path: Path,
    staging: Path,
    *,
    max_entries: int,
    max_uncompressed_bytes: int,
    warn: Warn,
) -> NotionArchive:
    try:
        outer = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        raise NotionArchiveInvalid(f"this is not a readable zip: {exc}") from exc
    members = [i for i in outer.infolist() if not i.is_dir()]
    if len(members) > max_entries:
        outer.close()
        raise NotionArchiveTooLarge(
            f"the archive holds {len(members)} entries; the bound is {max_entries}"
        )
    # A cheap early refusal off the central directory. It can understate, which
    # is why the running counter below is the real enforcement -- but an honest
    # bomb is refused here without reading a byte.
    declared = sum(i.file_size for i in members)
    if declared > max_uncompressed_bytes:
        outer.close()
        raise NotionArchiveTooLarge(
            f"the archive declares {declared} uncompressed bytes; the bound is "
            f"{max_uncompressed_bytes}"
        )

    parts = [i for i in members if _PART_SUFFIX.search(_decode_name(i))]
    sources: list[_Source] = []
    if parts and not any(_decode_name(i).endswith(".md") for i in members):
        # A Part-N export. Each inner zip is EXTRACTED first and opened from
        # disk: zipfile seeks backwards per entry, and a compressed stream read
        # through the outer archive re-decompresses from the start every time.
        staging.mkdir(parents=True, exist_ok=True)
        numbers: set[int] = set()
        try:
            for info in sorted(parts, key=lambda i: _decode_name(i)):
                decoded = _decode_name(info)
                number = int(_PART_SUFFIX.search(decoded).group(1))
                if number in numbers:
                    # The staged name and the source registry are both keyed on
                    # the number: a repeat would overwrite one part's bytes and
                    # strand the other's open handle.
                    raise NotionArchiveInvalid(
                        f"{decoded}: part {number} appears twice"
                    )
                numbers.add(number)
                target = staging / f"part-{number}.zip"
                what = f"{decoded} could not be read as a Part archive"
                with _folding(what):
                    src = outer.open(info)
                with src, open(target, "wb") as out:
                    for chunk in _read_chunks(src, what):
                        out.write(chunk)
                with _folding(what):
                    sources.append(_Source(target, number))
        except BaseException:
            outer.close()
            for source in sources:
                source.zip.close()
            raise
        outer.close()
    else:
        sources.append(_Source(zip_path, 0))

    archive = NotionArchive(sources, max_uncompressed_bytes)
    collected: list[ArchiveEntry] = []
    total = 0
    for source in sources:
        found = _collect(source.zip, source.part, warn)
        total += len(found)
        collected += found
    if total > max_entries:
        archive.close()
        raise NotionArchiveTooLarge(
            f"the archive holds {total} entries; the bound is {max_entries}"
        )

    depth = _strip_wrapper([e.name for e in collected])
    if depth:
        collected = [
            ArchiveEntry(
                name="/".join(e.name.split("/")[depth:]),
                info=e.info, size=e.size, part=e.part,
            )
            for e in collected
        ]
        collected = [e for e in collected if e.name]

    if not any(e.name.endswith(".md") for e in collected):
        archive.close()
        if any(e.name.lower().endswith((".html", ".htm")) for e in collected):
            raise NotionArchiveInvalid(
                "this is Notion's HTML export; re-export from Notion as "
                "Markdown & CSV"
            )
        raise NotionArchiveInvalid("the archive holds no markdown pages")

    archive.entries = collected
    return archive
