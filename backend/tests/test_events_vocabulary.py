from app.services.events import EVENT_TYPES


def test_repo_reindex_requested_is_in_the_vocabulary():
    """The file-scoped reindex doors journal under their own event type.

    `repo_indexed` belongs to the run itself and `repo_webhook_received` names
    a different door, so neither can carry this one's outcome.
    """
    assert "repo_reindex_requested" in EVENT_TYPES
