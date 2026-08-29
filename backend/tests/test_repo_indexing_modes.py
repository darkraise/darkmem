"""Per-repo indexing modes (spec 2026-08-29).

Every recurring indexing behaviour is a switch the operator sets. The bug
these replace: `code_reconcile` selected every indexed repo and never read
`auto_sync`, so there was no setting that stopped darkmem reindexing a
working tree another agent was editing.
"""
import pytest

from app.models.code import Repository


async def test_a_new_repository_opts_into_nothing(session):
    """Opt-in means opt-in: adding a row arms no recurring work."""
    repo = Repository(name="fresh", local_path=None, url=None)
    session.add(repo)
    await session.flush()

    assert repo.fetch_enabled is False
    assert repo.index_on_commit_enabled is False
    assert repo.index_uncommitted is False
    assert repo.fetch_interval_seconds == 300
    assert repo.commit_poll_seconds == 60


def test_auto_sync_is_gone():
    """Kept as a synonym it would recreate the confusion it caused: a name
    suggesting it governs all automatic behaviour while governing one loop
    of two."""
    assert not hasattr(Repository, "auto_sync")
