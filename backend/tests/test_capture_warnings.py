"""The memory-door warning (work-log spec §5) on all four capture doors."""
from __future__ import annotations

from app.services.events import EVENT_TYPES

LOG = "Task 5 complete: 7708 passed after merging e4363418."
FACT = "Postgres must listen on all addresses because the API connects across the stack network."


def test_the_vocabulary_carries_capture_flagged():
    from tests.test_event_taxonomy_map import _parse_frontend_map

    assert "capture_flagged" in EVENT_TYPES
    tabbed, _untabbed = _parse_frontend_map()
    assert "capture_flagged" in tabbed
