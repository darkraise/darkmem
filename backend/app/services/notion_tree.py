"""Deriving the page hierarchy from a Notion export.

A foldered export states its hierarchy and this module reads it. A flat export
-- which is what "Create folders for subpages" off produces, and what the
measured export is -- states nothing, so the hierarchy is derived from two
signals the export carries anyway: a row page's property block names its
database's columns, and a subpage is linked from its parent on a line of its
own. On the measured export those two parent 2171 of 2193 pages with none
ambiguous. Inference is reported, never silent: every page carries which
signal placed it, and the caller turns that into one warning.
"""
from __future__ import annotations

import csv
import io
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from urllib.parse import unquote
from uuid import UUID, uuid4

from app.services.notion_archive import ArchiveEntry, NotionArchive
from app.services.notion_content import resolve_target, scan_links

Warn = Callable[[str, str, str], None]

_ID_SUFFIX = re.compile(r" ([0-9a-f]{32})$")
_PROPERTY = re.compile(r"^([^:\n]{1,60}): ?(.*)$")
_ALL_CSV = "_all.csv"


class NotionExportInvalid(ValueError):
    """The export cannot be imported as it stands."""


@dataclass(frozen=True)
class DatabaseInfo:
    csv_name: str
    page_uuid: UUID | None
    header: list[str]
    rows: list[list[str]]


@dataclass(frozen=True)
class PageNode:
    uuid: UUID
    entry: ArchiveEntry | None
    title: str
    notion_id: str | None
    parent_uuid: UUID | None
    order: int
    database_csv: str | None
    row_of: UUID | None


@dataclass(frozen=True)
class NotionTree:
    pages: list[PageNode]
    by_target: dict[str, UUID]
    assets: dict[str, ArchiveEntry]
    databases: dict[str, DatabaseInfo]
    signal_counts: dict[str, int]


def _stem(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0] if "." in base else base
    # A database is `Title <id>_all.csv`; without dropping `_all` the id never
    # matches and the title keeps a suffix no human wrote.
    return stem[: -len("_all")] if stem.endswith("_all") else stem


def _notion_id(name: str) -> str | None:
    match = _ID_SUFFIX.search(_stem(name))
    return match.group(1) if match else None


def _title_from_name(name: str) -> str:
    stem = _stem(name)
    return unquote(_ID_SUFFIX.sub("", stem)).strip() or stem


def _title_and_properties(source: str, name: str) -> tuple[str, list[str]]:
    """The page's title and its property-block keys.

    The property block is the run of contiguous `Key: value` lines directly
    after the title. It is read here because it is the database-membership
    signal; the content module rewrites it into a bullet list later.
    """
    lines = source.split("\n")
    title = _title_from_name(name)
    index = 0
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip() or title
        index = 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    keys: list[str] = []
    while index < len(lines):
        match = _PROPERTY.match(lines[index])
        if match is None:
            break
        keys.append(match.group(1))
        index += 1
    return title, keys


def _read_csv(text: str) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _standalone_targets(source: str) -> list[str]:
    """Targets of links that occupy a whole line, in order.

    Every one of the measured export's 289 page-to-page links is written this
    way and none is inline, which is what makes the signal a subpage reference
    rather than a mention.
    """
    out: list[str] = []
    for span in scan_links(source):
        if span.is_image:
            continue
        line_start = source.rfind("\n", 0, span.start) + 1
        line_end = source.find("\n", span.end)
        line_end = len(source) if line_end == -1 else line_end
        if source[line_start:line_end].strip() == source[span.start:span.end]:
            out.append(unquote(span.destination.split("#")[0]))
    return out


def _creates_cycle(parents: dict[UUID, UUID], child: UUID, parent: UUID) -> bool:
    walk: UUID | None = parent
    seen: set[UUID] = set()
    while walk is not None:
        if walk == child:
            return True
        if walk in seen:
            return True
        seen.add(walk)
        walk = parents.get(walk)
    return False


def build_tree(archive: NotionArchive, *, max_pages: int, warn: Warn) -> NotionTree:
    pages_entries = [e for e in archive.entries if e.name.endswith(".md")]
    csv_entries = [e for e in archive.entries if e.name.endswith(_ALL_CSV)]
    asset_entries = [
        e for e in archive.entries
        if not e.name.endswith(".md") and not e.name.endswith(_ALL_CSV)
    ]
    if len(pages_entries) > max_pages:
        raise NotionExportInvalid(
            f"the export holds {len(pages_entries)} pages; the bound is {max_pages}"
        )

    sources = {e.name: archive.read_text(e) for e in pages_entries}
    uuids = {e.name: uuid4() for e in pages_entries}
    titles: dict[str, str] = {}
    keys: dict[str, list[str]] = {}
    for entry in pages_entries:
        titles[entry.name], keys[entry.name] = _title_and_properties(
            sources[entry.name], entry.name
        )

    by_id = {
        _notion_id(e.name): e.name for e in pages_entries if _notion_id(e.name)
    }

    # Standalone links, resolved once: they are both the subpage signal and,
    # for a CSV target, how a database with a differently-named view stub is
    # found. The measured export has one -- `Untitled 1507-2c1e_all.csv`, whose
    # stub page is titled "Sprint 47".
    standalone: dict[str, list[str]] = {}
    for entry in pages_entries:
        for target in _standalone_targets(sources[entry.name]):
            resolved = resolve_target(target, entry.name)
            if resolved != entry.name:
                standalone.setdefault(resolved, []).append(entry.name)

    databases: dict[str, DatabaseInfo] = {}
    minted: dict[str, tuple[UUID, str]] = {}
    stub_csv: dict[str, str] = {}
    for entry in csv_entries:
        header, rows = _read_csv(archive.read_text(entry))
        stub = entry.name[: -len(_ALL_CSV)] + ".md"
        if stub not in uuids:
            # No stem-matching page: the view stub may carry another name, in
            # which case it is the one page linking to this CSV.
            linkers = [n for n in standalone.get(entry.name, []) if n not in stub_csv]
            stub = linkers[0] if len(linkers) == 1 else stub
        page_uuid = uuids.get(stub)
        if page_uuid is None:
            page_uuid = uuid4()
            minted[entry.name] = (page_uuid, _title_from_name(entry.name))
        else:
            stub_csv[stub] = entry.name
        databases[entry.name] = DatabaseInfo(
            csv_name=entry.name, page_uuid=page_uuid, header=header, rows=rows,
        )

    parents: dict[UUID, UUID] = {}
    row_of: dict[str, UUID] = {}
    signal: dict[UUID, str] = {}

    # Signal 1: folder nesting. An export made with "Create folders for
    # subpages" states its hierarchy, so nothing below is consulted for it.
    for entry in pages_entries:
        if "/" not in entry.name:
            continue
        folder = entry.name.rsplit("/", 1)[0].rsplit("/", 1)[-1]
        match = _ID_SUFFIX.search(folder)
        if match is None:
            continue
        parent_name = by_id.get(match.group(1))
        if parent_name and parent_name != entry.name:
            parents[uuids[entry.name]] = uuids[parent_name]
            signal[uuids[entry.name]] = "folder"

    # Signal 2: database membership, via the property block.
    for entry in pages_entries:
        node_uuid = uuids[entry.name]
        if node_uuid in parents or entry.name in stub_csv:
            continue
        page_keys = keys[entry.name]
        if not page_keys:
            continue
        hits = [
            info for info in databases.values()
            if set(page_keys) <= set(info.header[1:])
        ]
        if len(hits) != 1:
            continue
        info = hits[0]
        if info.page_uuid is None or info.page_uuid == node_uuid:
            continue
        parents[node_uuid] = info.page_uuid
        row_of[entry.name] = info.page_uuid
        signal[node_uuid] = "database"

    # Signal 3: a link on a line of its own, and only where exactly one page
    # points at the target. Ambiguous parentage is left unplaced, not guessed.
    # A link to a database's CSV parents that database's PAGE -- a parent links
    # to the CSV, never to the view stub, so without this every database in the
    # measured export strands at the root.
    linkable: dict[str, UUID] = dict(uuids)
    for info in databases.values():
        if info.page_uuid is not None:
            linkable[info.csv_name] = info.page_uuid
    for target, all_linkers in standalone.items():
        node_uuid = linkable.get(target)
        if node_uuid is None or node_uuid in parents:
            continue
        # A view stub links to its own CSV, which would otherwise read as a
        # second linker and make every database look ambiguously parented.
        linkers = [name for name in all_linkers if uuids[name] != node_uuid]
        if len(linkers) != 1:
            continue
        parent_uuid = uuids[linkers[0]]
        if _creates_cycle(parents, node_uuid, parent_uuid):
            warn("", "hierarchy_cycle",
                 f"{target} and {linkers[0]} link to each other on their own "
                 f"lines; {target} stays at the root")
            continue
        parents[node_uuid] = parent_uuid
        signal[node_uuid] = "link"

    nodes: dict[UUID, PageNode] = {}
    for entry in pages_entries:
        node_uuid = uuids[entry.name]
        nodes[node_uuid] = PageNode(
            uuid=node_uuid,
            entry=entry,
            title=titles[entry.name],
            notion_id=_notion_id(entry.name),
            parent_uuid=parents.get(node_uuid),
            order=0,
            database_csv=stub_csv.get(entry.name),
            row_of=row_of.get(entry.name),
        )
    for csv_name, (node_uuid, title) in minted.items():
        nodes[node_uuid] = PageNode(
            uuid=node_uuid, entry=None, title=title, notion_id=None,
            parent_uuid=None, order=0, database_csv=csv_name, row_of=None,
        )
        signal[node_uuid] = "root"
    for node_uuid in nodes:
        signal.setdefault(node_uuid, "root")

    # Order: siblings alphabetically, except a database's rows, which follow
    # the CSV. The export carries no sidebar order, so this is a choice.
    row_rank: dict[UUID, int] = {}
    for info in databases.values():
        titles_in_order = [r[0] for r in info.rows if r]
        taken: set[UUID] = set()
        for rank, row_title in enumerate(titles_in_order):
            for node in nodes.values():
                if (node.row_of == info.page_uuid and node.title == row_title
                        and node.uuid not in taken):
                    row_rank[node.uuid] = rank
                    taken.add(node.uuid)
                    break

    children: dict[UUID | None, list[PageNode]] = {}
    for node in nodes.values():
        children.setdefault(node.parent_uuid, []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda n: (
            row_rank.get(n.uuid, len(row_rank) + 1), n.title, str(n.uuid),
        ))
        for index, node in enumerate(siblings):
            nodes[node.uuid] = replace(node, order=index)

    ordered: list[PageNode] = []
    stack = list(reversed(children.get(None, [])))
    while stack:
        node = nodes[stack.pop().uuid]
        ordered.append(node)
        stack.extend(reversed(children.get(node.uuid, [])))

    counts: dict[str, int] = {}
    for node in ordered:
        counts[signal[node.uuid]] = counts.get(signal[node.uuid], 0) + 1

    return NotionTree(
        pages=ordered,
        by_target={e.name: uuids[e.name] for e in pages_entries} | {
            info.csv_name: info.page_uuid
            for info in databases.values() if info.page_uuid is not None
        },
        assets={e.name: e for e in asset_entries},
        databases=databases,
        signal_counts=counts,
    )
