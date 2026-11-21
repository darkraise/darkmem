"""Every third-party module the app imports is a declared dependency.

A module that arrives only through another package's requirements is gone
the day that package is dropped or changes its own, and the image then fails
at boot rather than at build.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
from importlib.metadata import packages_distributions, requires
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"

# Modules the app imports from a distribution that a declared one requires
# and owns the version of, each named with that declared owner. The test
# checks the owner is declared and really requires the distribution.
PROVIDED_BY = {
    "starlette": ("fastapi", "starlette"),
    "pydantic_core": ("pydantic", "pydantic-core"),
    # The origin canonicaliser must encode exactly as httpx does, so it uses
    # httpx's own idna rather than a pin of its own.
    "idna": ("httpx", "idna"),
    # The declared python-igraph is the name under which igraph installs.
    "igraph": ("python-igraph", "igraph"),
}


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(spec: str) -> str:
    return _norm(re.split(r"[<>=!~\[; ]", spec, maxsplit=1)[0])


def _declared() -> set[str]:
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text())["project"]
    specs = list(project["dependencies"])
    for group in project.get("optional-dependencies", {}).values():
        specs.extend(group)
    return {_requirement_name(spec) for spec in specs}


def _third_party_imports() -> set[str]:
    modules: set[str] = set()
    for path in (BACKEND / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                modules |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return modules - set(sys.stdlib_module_names) - {"app", "__future__"}


def test_numpy_is_declared():
    declared = _declared()
    assert "numpy" in declared
    installed = packages_distributions()
    undeclared = []
    for module in sorted(_third_party_imports()):
        if module in PROVIDED_BY:
            owner, distribution = PROVIDED_BY[module]
            assert owner in declared, f"{module}: its owner {owner} is not declared"
            owned = {_requirement_name(spec) for spec in requires(owner) or []}
            assert distribution in owned, f"{module}: {owner} does not require {distribution}"
            continue
        # A module of an optional extra this venv lacks (torch) has no
        # installed distribution, and is declared under its own name.
        names = {_norm(d) for d in installed.get(module, [])} | {_norm(module)}
        if not names & declared:
            undeclared.append(module)
    assert undeclared == []


def test_lucide_react_is_declared():
    package = json.loads((FRONTEND / "package.json").read_text())
    assert "lucide-react" in package["dependencies"]


def _gate_arguments(tmp_path: Path, *arguments: str) -> str:
    """Runs release.sh in a scratch repository whose gate.sh records its
    arguments and stops the release there."""
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "release.sh").write_text((BACKEND.parent / "scripts" / "release.sh").read_text())
    (scripts / "gate.sh").write_text('#!/usr/bin/env bash\necho "$*" > "$(dirname "$0")/../gate-args"\nexit 3\n')
    (scripts / "gate.sh").chmod(0o755)
    (tmp_path / "CHANGELOG.md").write_text("## v9.9.9\n")
    (tmp_path / ".gitignore").write_text("gate-args\n")
    for command in (
        ["git", "init", "-q", "-b", "master"],
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"],
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "chore: base"],
    ):
        subprocess.run(command, cwd=tmp_path, check=True, timeout=30)
    run = subprocess.run(
        ["bash", "scripts/release.sh", "v9.9.9", *arguments],
        cwd=tmp_path, capture_output=True, text=True, timeout=60,
    )
    assert run.returncode == 3, run.stdout + run.stderr
    return (tmp_path / "gate-args").read_text().strip()


def test_release_script_runs_the_floor_gate_by_default(tmp_path):
    assert _gate_arguments(tmp_path / "floor") == ""
    assert _gate_arguments(tmp_path / "full", "--full-gate") == "--full"
    script = (BACKEND.parent / "scripts" / "release.sh").read_text()
    floor = script.split("./scripts/gate.sh\n", 1)[1].split("fi\n", 1)[0]
    for leg in ("tests/test_api/test_rest_conformance.py", "scripts/benchlib/tests", "make generate", "make test"):
        assert leg in floor, leg
