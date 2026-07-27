"""The extraction request has exactly one definition.

``ExtractionService.build_extraction_request`` is what the pipeline sends and
what the F1 bench measures. If the two ever assemble their own bytes again the
bench scores a configuration nobody runs, which is the failure T0.03 forbids.

The fingerprints below are the assembled *user* message, which carries the
schema string, the taxonomy width and the merge gate. They are deliberate-change
pins in the same sense as the system-prompt pin in ``test_taxonomy.py``: a diff
here means the request changed, which means every cached bench output is stale.
"""
import hashlib

import pytest

from app.services import prompt as prompt_constants
from app.services.extraction import ExtractionService
from app.services.extraction_clean import _content_seed

CONTENT = "Migrated darkmem from Qdrant to pgvector on 2026-04-22."

USER_MESSAGE_SHA16 = {
    False: "c7838e4f610cc990",
    True: "3e6ea7444c40af81",
}


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@pytest.mark.parametrize("with_classification", [False, True])
def test_assembled_user_message_is_pinned(with_classification):
    request = ExtractionService.build_extraction_request(
        CONTENT, with_classification=with_classification,
    )
    assert _sha16(request.messages[1]["content"]) == USER_MESSAGE_SHA16[with_classification]


def test_system_message_is_the_extraction_prompt():
    request = ExtractionService.build_extraction_request(CONTENT)
    assert request.messages[0] == {
        "role": "system", "content": prompt_constants.get("extraction"),
    }


def test_request_carries_seed_and_json_response_format():
    request = ExtractionService.build_extraction_request(CONTENT)
    assert request.seed == _content_seed(CONTENT)
    assert request.response_format == {"type": "json_object"}


def test_explicit_system_prompt_overrides_the_default():
    request = ExtractionService.build_extraction_request(CONTENT, system_prompt="custom")
    assert request.messages[0]["content"] == "custom"
