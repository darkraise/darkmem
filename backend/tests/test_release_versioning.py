"""`scripts/next_version.py` decides what CI publishes and tags.

Every assertion here is about a decision that is expensive to get wrong in the
one direction the pipeline cannot undo: a version that ships, or a release cut
from commits that shipped nothing.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "next_version", ROOT / "scripts/next_version.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway git repo the planner reads instead of darkmem's own.

    Tests must never assert against real history: it moves under them, and a
    bump derived from this repo's own commits would change meaning every merge.
    """
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    def git(*args):
        subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, timeout=30,
        )

    git("init", "-q", "-b", "master")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")

    def commit(subject: str, body: str = ""):
        (tmp_path / "f.txt").write_text(subject)
        git("add", "-A")
        args = ["commit", "-q", "-m", subject]
        if body:
            args += ["-m", body]
        git(*args)

    def write_fields(version: str, changelog: str | None = None):
        (tmp_path / "backend").mkdir(exist_ok=True)
        (tmp_path / "backend/pyproject.toml").write_text(f'version = "{version}"\n')
        (tmp_path / "CHANGELOG.md").write_text(
            changelog if changelog is not None else f"## v{version}\n"
        )

    module.commit = commit
    module.git = git
    module.write_fields = write_fields
    write_fields("0.1.0")
    commit("chore: genesis")
    git("tag", "-a", "v0.1.0", "-m", "v0.1.0")
    return module


def test_a_feat_is_a_minor_bump(repo):
    repo.commit("feat(code): add a door")
    repo.write_fields("0.1.0")

    plan = repo.plan()

    assert plan["release"] is True
    assert plan["version"] == "0.2.0"
    assert plan["tag"] == "v0.2.0"
    assert plan["bump"] == "minor"


def test_a_fix_alone_is_a_patch_bump(repo):
    repo.commit("fix(api): stop dropping the header")

    plan = repo.plan()

    assert plan["version"] == "0.1.1"
    assert plan["bump"] == "patch"


def test_a_feat_outranks_a_fix_in_the_same_range(repo):
    repo.commit("fix(api): stop dropping the header")
    repo.commit("feat(api): add a route")

    assert repo.plan()["version"] == "0.2.0"


def test_a_bang_marks_a_breaking_change(repo):
    repo.commit("feat(api)!: rename every route")

    plan = repo.plan()

    assert plan["bump"] == "major"
    assert plan["version"] == "1.0.0"


def test_a_breaking_change_trailer_is_honoured_without_a_bang(repo):
    """The `!` is the common spelling but the trailer is the one the spec
    defines; a release that silently took a minor bump for a documented break
    is the failure that reaches users."""
    repo.commit("fix(api): tighten validation", "BREAKING CHANGE: rejects empty names")

    assert repo.plan()["bump"] == "major"


def test_docs_and_chore_alone_cut_no_release(repo):
    """A docs-only push must not publish an image or burn a version number."""
    repo.commit("docs(spec): correct a claim")
    repo.commit("chore(deps): bump a pin")
    repo.commit("refactor(code): rename a helper")
    repo.commit("test(api): add a case")

    plan = repo.plan()

    assert plan["release"] is False
    assert plan["version"] == ""
    assert "no feat, fix, perf or breaking commit" in plan["reason"]


def test_merge_commits_do_not_drive_the_bump(repo):
    """A merge subject describes the integration, not the change. Counting one
    would bump for work its own commits already accounted for -- and a merge of
    a docs-only branch would manufacture a release out of nothing."""
    repo.git("checkout", "-q", "-b", "side")
    repo.commit("docs(spec): a claim")
    repo.git("checkout", "-q", "master")
    repo.git("merge", "-q", "--no-ff", "side", "-m", "feat: merge the side branch")

    assert repo.plan()["release"] is False


def test_product_fields_newer_than_the_tag_win(repo):
    """`scripts/release.sh` syncs the fields and deploys before anyone pushes.
    CI must take that number rather than derive a second one on top of it, or a
    locally cut v0.2.0 would publish as v0.3.0."""
    repo.commit("feat(code): add a door")
    repo.write_fields("0.2.0")

    plan = repo.plan()

    assert plan["version"] == "0.2.0"
    assert plan["bump"] == "preset"


def test_the_changelog_check_reads_the_exact_version(repo):
    repo.write_fields("0.1.0", changelog="## v0.1.0\n\ntext\n")

    assert repo.changelog_has("0.1.0")
    # A section for the series must not satisfy the check for a point release:
    # v0.1.1 shipping under v0.1.0's notes is the silence the gate exists for.
    assert not repo.changelog_has("0.1.1")


def test_the_first_release_of_a_repo_with_no_tag(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=tmp_path, check=True)
    for key, value in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", key, value], cwd=tmp_path, check=True)
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend/pyproject.toml").write_text('version = "0.0.0"\n')
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "feat: the first thing"], cwd=tmp_path, check=True,
    )

    plan = module.plan()

    assert plan["release"] is True
    assert plan["version"] == "0.1.0"
    assert plan["previous_tag"] == ""


def test_notes_group_by_type_and_mark_breaking_changes(repo):
    repo.commit("feat(code): add a door")
    repo.commit("fix(api): stop dropping the header")
    repo.commit("docs(spec): correct a claim")
    repo.commit("perf(extraction)!: halve the tokens")

    body = repo.notes("0.2.0", "v0.1.0", "darkraise/darkmem")

    assert "### Breaking changes" in body
    assert "halve the tokens" in body.split("### Features")[0]
    assert "### Features" in body and "add a door" in body
    assert "### Fixes" in body and "stop dropping the header" in body
    assert "### Documentation" in body and "correct a claim" in body
    assert "compare/v0.1.0...v0.2.0" in body


def test_notes_mention_every_commit_in_the_range(repo):
    """Nothing in the range may go unreported: a commit with no conventional
    type still shipped, and the release body is the only account of it."""
    repo.commit("Revert the phase 2 changes")
    repo.commit("feat(code): add a door")

    body = repo.notes("0.2.0", "v0.1.0", "darkraise/darkmem")

    assert "### Other" in body
    assert "Revert the phase 2 changes" in body


def test_the_real_repository_plans_a_release(monkeypatch):
    """A smoke test against darkmem's own history: the planner must run here,
    not only against fixtures. Asserts the shape, never the number -- the
    number moves with every merge."""
    module = _load()

    plan = module.plan()

    assert set(plan) >= {"release", "version", "tag", "bump", "previous_tag"}
    if plan["release"]:
        assert plan["tag"] == "v" + plan["version"]
