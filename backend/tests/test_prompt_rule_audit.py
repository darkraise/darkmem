"""The prompt-rule audit cannot rot into fiction.

`docs/eval/2026-07-28-T1.17-prompt-rule-audit.md` is the reviewable object behind
every rule stripped from the extraction system prompt: each strip cites the pass
or the schema that subsumes it. A later pass rename would silently turn those
citations into prose about passes that no longer exist, and the next agent to
read the audit would strip a rule against a twin that is gone.
"""
import re
from pathlib import Path

import pytest

from app.services.extraction_clean import PASS_REGISTRY

AUDIT = Path(__file__).resolve().parents[2] / "docs" / "eval" / "2026-07-28-T1.17-prompt-rule-audit.md"

# The passes the audit's coverage verdicts rest on.
CITED_PASSES = (
    "filter_noise",
    "filter_literals",
    "filter_event_edges",
    "remap_to_valid_entities",
    "rescue_relation_endpoints",
    "rescue_happened_on",
    "fan_out_coordinated",
    "suppress_temporal_edges",
    "validate_directions",
    "validate_hosting_direction",
)


@pytest.fixture(scope="module")
def audit_text():
    if not AUDIT.exists():
        pytest.fail(f"the prompt-rule audit is missing: {AUDIT}")
    return AUDIT.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", CITED_PASSES)
def test_every_cited_pass_still_exists_in_the_registry(name):
    assert name in {p.name for p in PASS_REGISTRY}


@pytest.mark.parametrize("name", CITED_PASSES)
def test_every_cited_pass_is_actually_cited_by_the_audit(name, audit_text):
    assert re.search(rf"`{re.escape(name)}`", audit_text)


def test_the_audit_records_the_prompt_fingerprints_it_moved_between(audit_text):
    assert "775ca7c45ed9a06a" in audit_text
    assert "f59a62d1be7273a8" in audit_text
