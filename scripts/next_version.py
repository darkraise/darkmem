"""Derive the next release version, and the release body, from git history.

Lives here rather than inside the workflow YAML so it can be run and tested
without pushing anything: `.github/workflows/release.yml` shells out to it.

Version resolution is deliberately two-stage. The product version fields win
when they already name something newer than the last tag, because that means a
human cut the version on purpose (`scripts/release.sh`); only when they do not
is the bump derived from the commit types. Without that order the two paths
fight -- a local cut would be silently re-bumped by the next push.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `feat(scope)!: subject` and `feat!: subject` both mark a break. The `!` binds
# to the type, so it is matched before the colon rather than anywhere in the
# subject -- a subject that merely ends in "!" is not an API break.
SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<text>.+)$")
BREAKING_BODY = re.compile(r"^BREAKING[ -]CHANGE:", re.M)
PRODUCT_VERSION = re.compile(r'version\s*=\s*"(\d+\.\d+\.\d+)"')

# What each type does to the version. Types absent from this map describe work
# that changed no shipped behaviour, so they appear in the notes but never on
# their own cause a release -- a docs-only push must not cut a version.
BUMP_BY_TYPE = {"feat": "minor", "fix": "patch", "perf": "patch"}

# Notes headings, in the order they are rendered. `_other` collects every type
# with no heading of its own so nothing in the range goes unmentioned.
SECTIONS = [
    ("feat", "Features"),
    ("fix", "Fixes"),
    ("perf", "Performance"),
    ("refactor", "Refactoring"),
    ("docs", "Documentation"),
    ("_other", "Other"),
]


def _git(*args: str) -> str:
    """Raw stdout, deliberately unstripped.

    Python counts the ASCII separators \x1c-\x1f as whitespace, so a `.strip()`
    here would silently eat the trailing field of the record format below --
    which is the commit body, empty on most commits. Callers strip what they
    know is safe to strip.
    """
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    ).stdout


def last_tag() -> str | None:
    """The newest `v*` tag reachable from HEAD, or None on a repo with none."""
    try:
        return _git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*").strip() or None
    except subprocess.CalledProcessError:
        return None


def _parse_version(tag: str) -> tuple[int, int, int] | None:
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def commits_since(tag: str | None) -> list[dict]:
    """Every commit in the release range, parsed into its conventional parts.

    Merge commits are excluded: a merge subject describes the integration, not
    the change, so counting one would bump the version for work its own
    commits already accounted for.
    """
    span = f"{tag}..HEAD" if tag else "HEAD"
    # \x1e separates records and \x1f fields -- neither can appear in a commit
    # message, so a subject or body containing newlines cannot split a record.
    raw = _git("log", span, "--no-merges", "--format=%H\x1f%s\x1f%b\x1e")
    out = []
    for record in raw.split("\x1e"):
        # Only newlines: the separators themselves are load-bearing here.
        record = record.strip("\n")
        if not record:
            continue
        sha, subject, body = record.split("\x1f", 2)
        m = SUBJECT.match(subject)
        out.append({
            "sha": sha,
            "short": sha[:7],
            "subject": subject,
            "type": m["type"] if m else None,
            "scope": m["scope"] if m else None,
            "text": m["text"] if m else subject,
            "breaking": bool(m and m["bang"]) or bool(BREAKING_BODY.search(body)),
        })
    return out


def derive_bump(commits: list[dict]) -> str | None:
    """major | minor | patch, or None when nothing in the range ships."""
    if any(c["breaking"] for c in commits):
        return "major"
    bumps = {BUMP_BY_TYPE.get(c["type"] or "") for c in commits}
    if "minor" in bumps:
        return "minor"
    if "patch" in bumps:
        return "patch"
    return None


def apply_bump(version: tuple[int, int, int], bump: str) -> str:
    major, minor, patch = version
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def product_version() -> str:
    return PRODUCT_VERSION.search(
        (ROOT / "backend/pyproject.toml").read_text(encoding="utf-8")
    ).group(1)


def changelog_has(version: str) -> bool:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return bool(re.search(rf"^## v{re.escape(version)}\b", changelog, re.M))


def plan() -> dict:
    """Decide whether this commit releases, and as what version."""
    tag = last_tag()
    tagged = _parse_version(tag) if tag else None
    commits = commits_since(tag)
    fields = product_version()

    # A human already cut this version locally; take it rather than deriving a
    # second one on top of it.
    if tagged and _parse_version(fields) > tagged:
        return {
            "release": True, "version": fields, "tag": f"v{fields}",
            "bump": "preset", "previous_tag": tag, "commits": len(commits),
            "reason": f"product fields already name {fields}, newer than {tag}",
        }

    bump = derive_bump(commits)
    if bump is None:
        return {
            "release": False, "version": "", "tag": "", "bump": "",
            "previous_tag": tag or "", "commits": len(commits),
            "reason": "no feat, fix, perf or breaking commit since "
                      + (tag or "the start of history"),
        }

    version = apply_bump(tagged or (0, 0, 0), bump)
    return {
        "release": True, "version": version, "tag": f"v{version}", "bump": bump,
        "previous_tag": tag or "", "commits": len(commits),
        "reason": f"{bump} bump from {tag or 'v0.0.0'} across {len(commits)} commits",
    }


def notes(version: str, previous_tag: str, repository: str) -> str:
    """The GitHub release body: what changed, grouped by commit type.

    CHANGELOG.md is the hand-written account of a release and stays that way;
    this is the mechanical companion to it, so it links there rather than
    trying to reproduce its prose.
    """
    commits = commits_since(previous_tag or None)
    grouped: dict[str, list[dict]] = {}
    for c in commits:
        key = c["type"] if any(c["type"] == k for k, _ in SECTIONS) else "_other"
        grouped.setdefault(key, []).append(c)

    lines: list[str] = []
    breaking = [c for c in commits if c["breaking"]]
    if breaking:
        lines.append("### Breaking changes\n")
        for c in breaking:
            lines.append(f"- {c['text']} ({c['short']})")
        lines.append("")

    for key, heading in SECTIONS:
        entries = grouped.get(key)
        if not entries:
            continue
        lines.append(f"### {heading}\n")
        for c in entries:
            scope = f"**{c['scope']}** — " if c["scope"] else ""
            lines.append(f"- {scope}{c['text']} ({c['short']})")
        lines.append("")

    if not lines:
        lines.append("_No conventional commits in this range._\n")

    lines.append(
        f"The hand-written account of this release is in "
        f"[CHANGELOG.md](https://github.com/{repository}/blob/v{version}/CHANGELOG.md)."
    )
    if previous_tag:
        lines.append("")
        lines.append(
            f"**Full diff:** https://github.com/{repository}/compare/{previous_tag}...v{version}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="emit the release decision as JSON")
    notes_cmd = sub.add_parser("notes", help="emit the release body as markdown")
    notes_cmd.add_argument("--version", required=True)
    notes_cmd.add_argument("--previous-tag", default="")
    notes_cmd.add_argument("--repository", required=True)

    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps(plan()))
    else:
        print(notes(args.version, args.previous_tag, args.repository), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
