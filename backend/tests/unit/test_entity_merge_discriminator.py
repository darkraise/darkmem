"""names_distinct: the lexical precision gate on Phase-4 ANN entity dedup.

The 0.85 cosine probe collapses surface variants (good) but also entities that
embed near-identically yet are distinct because they differ by a discriminating
token — a number/date/version or a month. names_distinct(a, b) returns True when
a and b must stay separate.
"""
from __future__ import annotations

import pytest

from app.services.relations import names_distinct


@pytest.mark.parametrize("a,b", [
    ("february outage", "march outage"),       # different month
    ("feb outage", "mar outage"),              # abbreviated months
    ("2026-05-20", "2026-05-12"),              # different ISO dates
    ("v2", "v3"),                              # different versions
    ("service-1", "service-2"),                # different instance numbers
    ("us-east-1", "us-west-2"),                # different region numbers
    ("gpt-4", "gpt-4o"),                        # different model variant token
])
def test_distinct_entities_are_not_merged(a, b):
    assert names_distinct(a, b) is True
    assert names_distinct(b, a) is True  # symmetric


@pytest.mark.parametrize("a,b", [
    ("gpt-4", "gpt4"),                          # pure formatting variant
    ("darkraise-ui", "darkraise ui"),          # hyphen vs space
    ("docker-compose", "docker compose"),
    ("API Gateway", "api gateway"),            # casing only
    ("postgres", "postgresql"),                # alias, no discriminator -> ANN may merge
    ("redis", "rediss"),                        # typo, no discriminator
    ("february outage", "february outage"),    # identical
])
def test_mergeable_names_are_allowed(a, b):
    assert names_distinct(a, b) is False
    assert names_distinct(b, a) is False
