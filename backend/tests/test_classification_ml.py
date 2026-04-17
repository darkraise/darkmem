import pytest

from app.services.classification_ml import ClassificationMLService


async def test_classify_empty_content():
    svc = ClassificationMLService()
    result = await svc.classify("", ["general"], "system-prompt")
    assert result == {"hall": "fact", "summary": None, "emotions": [], "flags": []}


async def test_classify_whitespace_only():
    svc = ClassificationMLService()
    result = await svc.classify("   ", ["general"], "")
    assert result["hall"] == "fact"
    assert result["summary"] is None


async def test_classify_returns_hall_key_not_type(monkeypatch):
    """Must expose 'hall' (matches the LLM service contract), not 'type'."""

    def fake_classify_sync(content: str) -> str:
        return "decision"

    monkeypatch.setattr("app.services.classification_ml._classify_sync", fake_classify_sync)

    svc = ClassificationMLService()
    result = await svc.classify("let's use pgvector", ["general"], "", mode="simple")
    assert "hall" in result
    assert "type" not in result
    assert result["hall"] == "decision"
    assert result["summary"] is None
    assert result["emotions"] == []
    assert result["flags"] == []


async def test_classify_unknown_label_falls_back_to_fact(monkeypatch):
    def fake_classify_sync(content: str) -> str:
        return "bogus_label_not_in_taxonomy"

    monkeypatch.setattr("app.services.classification_ml._classify_sync", fake_classify_sync)

    svc = ClassificationMLService()
    result = await svc.classify("something", ["general"], "")
    assert result["hall"] == "fact"


async def test_classify_exception_falls_back(monkeypatch):
    def fake_classify_sync(content: str) -> str:
        raise RuntimeError("typer loading failed")

    monkeypatch.setattr("app.services.classification_ml._classify_sync", fake_classify_sync)

    svc = ClassificationMLService()
    result = await svc.classify("something", ["general"], "")
    assert result == {"hall": "fact", "summary": None, "emotions": [], "flags": []}


async def test_classify_signature_accepts_all_positional_args():
    """Signature parity with ClassificationService — four positional args."""
    svc = ClassificationMLService()
    result = await svc.classify("content", ["general", "technical"], "system_prompt_here", "simple")
    assert isinstance(result, dict)
    assert "hall" in result
