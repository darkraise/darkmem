"""Pure parsers for the progress board: registers, plans and the row rewrite.

They mirror dr-forge's shell parsers (`scripts/lib/plan.sh`, `lib/register.sh`)
so the board and the plugin agree on what a row, a task and a fence are. Text
in, records or text out: no database, no app imports, so `block_verbs` can
import the uri prefixes without reaching the board service.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

REGISTER_PREFIX = "superpowers/registers/"
PLAN_PREFIX = "superpowers/plans/"
BOARD_SOURCE_PREFIXES = (REGISTER_PREFIX, PLAN_PREFIX)

REGISTER_STATES = ("open", "planned", "doing", "verify", "done", "deferred", "n/a")
NOTE_REQUIRED_STATES = frozenset({"verify", "deferred", "n/a"})
TASK_STATES = ("todo", "wip", "review", "blocked", "done")
LEDGER_STATES = frozenset({"wip", "review", "blocked", "done"})

_OPENER = re.compile(r"^ {0,3}(`+|~+)")
_CLOSER_BODY = re.compile(r"`+|~+")
_TASK = re.compile(r"^#+[ \t]+(Task[ \t]+([0-9]+)[A-Za-z]*[ \t]*[:.\-]?[ \t]*(.*))$")
_STEP = re.compile(r"^[ \t]*[-*][ \t]+\[([ xX])\][ \t]+(.*)$")
_SEPARATOR = re.compile(r":?-+:?")
_DIGITS = re.compile(r"[0-9]+")
_ESCAPED_PIPE = "\x01"


def is_board_source(uri: str | None) -> bool:
    """A document the board reads: under a register or plan prefix, `.md`."""
    return bool(uri) and uri.startswith(BOARD_SOURCE_PREFIXES) and uri.endswith(".md")


def is_mirror_owned(uri: str | None) -> bool:
    """A document the dr-forge mirror owns through content puts."""
    return bool(uri) and uri.startswith(BOARD_SOURCE_PREFIXES)


def is_blank_note(note: str | None) -> bool:
    return note is None or note.strip(" \t") in ("", "-")


def cell_uri(cell: str | None) -> str | None:
    """A repository path in a cell, as the darkmem uri it was filed under."""
    if not cell:
        return None
    value = cell.strip(" \t")
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip(" \t")
    for prefix in ("docs/forge/", "docs/superpowers/"):
        if value.startswith(prefix):
            return "superpowers/" + value[len(prefix):]
    if value.startswith("superpowers/"):
        return value
    return None


def split_lines(text: str) -> list[str]:
    """Lines on `\\n` only, with every `\\r` removed, as `tr -d '\\r'` does.

    Never `str.splitlines`: it also splits on U+2028, U+000C and others, which
    would number lines differently from the plugin and break a cell apart.
    """
    return text.replace("\r", "").split("\n")


class _Fence:
    """`plan.sh`'s `in_fence`: True for fence markers and fenced lines."""

    def __init__(self) -> None:
        self.marker = ""

    def step(self, line: str) -> bool:
        if self.marker:
            body = re.sub(r"^ {0,3}", "", line, count=1).rstrip(" \t")
            if (
                _CLOSER_BODY.fullmatch(body)
                and body[0] == self.marker[0]
                and len(body) >= len(self.marker)
            ):
                self.marker = ""
            return True
        match = _OPENER.match(line)
        if match and len(match.group(1)) >= 3:
            self.marker = match.group(1)
            return True
        return False


def fence_flags(lines: list[str]) -> list[bool]:
    fence = _Fence()
    return [fence.step(line) for line in lines]


def _cells(line: str) -> list[str] | None:
    """`register.sh`'s `reg_cells`: the trimmed fields, or None off a table."""
    trimmed = line.strip(" \t")
    if not trimmed.startswith("|"):
        return None
    fields = trimmed.replace("\\|", _ESCAPED_PIPE).split("|")
    return [f.strip(" \t").replace(_ESCAPED_PIPE, "|") for f in fields]


@dataclass(frozen=True)
class RegisterRow:
    number: int
    item: str
    assigned: str
    acceptance: str
    state: str
    note: str
    line: int

    @property
    def state_recognised(self) -> bool:
        return self.state in REGISTER_STATES


@dataclass(frozen=True)
class MalformedRow:
    line: int
    text: str
    reason: str
    number: int | None


@dataclass(frozen=True)
class ParsedRegister:
    title: str | None
    covers: str | None
    rows: list[RegisterRow]
    malformed: list[MalformedRow]


def _first_title(lines: list[str], flags: list[bool]) -> str | None:
    for line, fenced in zip(lines, flags):
        if not fenced and line.startswith("# "):
            return line[2:].strip(" \t")
    return None


def parse_register(text: str) -> ParsedRegister:
    lines = split_lines(text)
    flags = fence_flags(lines)
    title = _first_title(lines, flags)
    covers = None
    candidates: list[tuple[int, list[str], str]] = []
    malformed: list[MalformedRow] = []
    for index, (line, fenced) in enumerate(zip(lines, flags)):
        if fenced:
            continue
        if covers is None and line.startswith("**Covers:**"):
            covers = line[len("**Covers:**"):].strip(" \t")
            continue
        fields = _cells(line)
        if fields is None:
            continue
        first = fields[1] if len(fields) > 1 else ""
        if first == "#" or _SEPARATOR.fullmatch(first):
            continue
        number = index + 1
        row_number = int(first) if _DIGITS.fullmatch(first) else None
        if len(fields) != 8:
            malformed.append(
                MalformedRow(number, line, f"{len(fields) - 2} cells, not 6", row_number)
            )
        elif row_number is None:
            malformed.append(MalformedRow(number, line, "the # cell is not a number", None))
        else:
            candidates.append((number, fields, line))

    counts: dict[int, int] = {}
    for _line, fields, _text in candidates:
        counts[int(fields[1])] = counts.get(int(fields[1]), 0) + 1
    rows: list[RegisterRow] = []
    for number, fields, line in candidates:
        row_number = int(fields[1])
        if counts[row_number] > 1:
            malformed.append(
                MalformedRow(number, line, f"duplicate number {row_number}", row_number)
            )
            continue
        rows.append(RegisterRow(
            number=row_number, item=fields[2], assigned=fields[3],
            acceptance=fields[4], state=fields[5], note=fields[6], line=number,
        ))
    malformed.sort(key=lambda m: m.line)
    return ParsedRegister(title=title, covers=covers, rows=rows, malformed=malformed)


@dataclass(frozen=True)
class TaskStep:
    checked: bool
    text: str


@dataclass(frozen=True)
class PlanTask:
    number: int
    label: str
    title: str
    line: int
    steps: list[TaskStep] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedPlan:
    title: str | None
    tasks: list[PlanTask]


def parse_plan(text: str) -> ParsedPlan:
    lines = split_lines(text)
    flags = fence_flags(lines)
    tasks: list[PlanTask] = []
    current: dict | None = None
    for index, (line, fenced) in enumerate(zip(lines, flags)):
        if fenced:
            continue
        match = _TASK.match(line)
        if match:
            if current is not None:
                tasks.append(PlanTask(**current))
            current = {
                "number": int(match.group(2)),
                "label": match.group(1).rstrip(" \t"),
                "title": match.group(3).strip(" \t"),
                "line": index + 1,
                "steps": [],
            }
            continue
        if current is not None:
            step = _STEP.match(line)
            if step:
                current["steps"].append(
                    TaskStep(checked=step.group(1) != " ", text=step.group(2).rstrip(" \t"))
                )
    if current is not None:
        tasks.append(PlanTask(**current))
    return ParsedPlan(title=_first_title(lines, flags), tasks=tasks)


# Cell index of each column inside a well-formed row's eight fields.
_CELL_INDEX = {"item": 2, "assigned": 3, "acceptance": 4, "state": 5, "note": 6}
EDITABLE_COLUMNS = frozenset({"state", "note", "assigned"})


class RowEditRefused(ValueError):
    """A register row edit the rewrite will not make; `reason` is the wire code."""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(message)


def _boundaries(line: str) -> list[int]:
    """Indexes of the `|` that split cells: a `|` after a backslash is text."""
    return [i for i, ch in enumerate(line) if ch == "|" and (i == 0 or line[i - 1] != "\\")]


def _splice_cell(segment: str, value: str) -> str:
    core = segment.strip(" \t")
    if not core:
        return f" {value} " if value else segment
    lead = segment[: len(segment) - len(segment.lstrip(" \t"))]
    trail = segment[len(segment.rstrip(" \t")):]
    return f"{lead}{value}{trail}"


def rewrite_register_row(text: str, number: int, changes: dict[str, str]) -> str:
    """Splice new cell values into row `number`, changing nothing else.

    Never re-serialises: only each changed cell's trimmed text is replaced,
    so padding, indentation, a trailing `\\r`, text after the last `|` and
    every other line keep their bytes.
    """
    unknown = set(changes) - EDITABLE_COLUMNS
    if unknown:
        raise ValueError(f"not an editable column: {sorted(unknown)}")
    values: dict[str, str] = {}
    for column, raw in changes.items():
        if "\n" in raw or "\r" in raw:
            raise RowEditRefused("invalid_cell", f"the {column} may not contain a line break")
        values[column] = raw.strip(" \t")
    if "state" in values and values["state"] not in REGISTER_STATES:
        raise RowEditRefused(
            "unknown_state",
            f"{values['state']!r} is not a register state; use one of {', '.join(REGISTER_STATES)}",
        )

    parsed = parse_register(text)
    matches = [row for row in parsed.rows if row.number == number]
    if not matches:
        named = [m for m in parsed.malformed if m.number == number]
        if any(m.reason.startswith("duplicate number") for m in named):
            raise RowEditRefused("duplicate_row", f"two rows carry the number {number}")
        if named:
            raise RowEditRefused(
                "malformed_row", f"row {number} is malformed; fix it in the register first",
            )
        raise RowEditRefused("not_found", f"no row {number} in this register")
    row = matches[0]
    state = values.get("state", row.state)
    note = values.get("note", row.note)
    if state in NOTE_REQUIRED_STATES and is_blank_note(note):
        raise RowEditRefused("note_required", f"a row in {state!r} needs a Note")

    raw_lines = text.split("\n")
    original = raw_lines[row.line - 1]
    pipes = _boundaries(original)
    updated = original
    for column in sorted(values, key=lambda c: _CELL_INDEX[c], reverse=True):
        cell = _CELL_INDEX[column]
        start, end = pipes[cell - 1] + 1, pipes[cell]
        escaped = values[column].replace("|", "\\|")
        updated = updated[:start] + _splice_cell(updated[start:end], escaped) + updated[end:]

    check = _cells(updated.replace("\r", ""))
    if (
        check is None
        or len(check) != 8
        or not check[1].isdigit()
        or int(check[1]) != number
        or any(check[_CELL_INDEX[c]] != v for c, v in values.items())
    ):
        raise RowEditRefused(
            "invalid_cell", "that value would change the row's shape; remove a trailing backslash",
        )
    raw_lines[row.line - 1] = updated
    return "\n".join(raw_lines)


class BoardRefusal(Exception):
    """A refusal the board's REST door answers as `error.code` = `reason`.

    `fields` ride `error.details[0]` (e.g. `current_hash` on a hash
    conflict), so the SPA can tell causes apart without parsing prose.
    """

    def __init__(self, status_code: int, reason: str, message: str, **fields):
        self.status_code = status_code
        self.reason = reason
        self.message = message
        self.fields = fields
        super().__init__(message)
