"""The LLM resample runner, exercised without touching a vendor.

The point of these is that the first live run must not be the first run: a
sitting is 93 paid calls, and discovering a parse bug on call 93 wastes them
all. The transport is mocked; everything else is the shipping path, including
the scorer and the gold.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchlib import entailment_gold, resample_llm, resample_score  # noqa: E402


class _Reply:
    def __init__(self, content: str):
        self._content = content

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


@pytest.fixture
def gold_by_id():
    gold = json.loads(Path(entailment_gold.GOLD_PATH).read_text(encoding="utf-8"))
    return {p["id"]: p for p in gold["pairs"]}


def _pair_of(prompt: str) -> tuple[str, str]:
    """The (premise, hypothesis) the runner rendered into this prompt.

    Both halves, parsed off their markers. The hypothesis alone is not a key:
    the gold deliberately re-uses one hypothesis against several premises, and
    the verdict differs by premise -- which is the whole design of the set. A
    hypothesis-keyed mock answers the wrong pair and fails for a reason the
    runner does not have.
    """
    premise = prompt.rsplit("**Premise:** ", 1)[-1].split("**Hypothesis:**", 1)[0]
    hypothesis = prompt.rsplit("**Hypothesis:** ", 1)[-1]
    return premise.strip(), hypothesis.strip()


def _mock_post(reply_for):
    """Patch the transport, keying each reply off the hypothesis in the body.

    Keyed on content rather than call order because the runner completes
    requests out of order (asyncio.as_completed), and an order-keyed mock
    would pass while the real thing mismatched verdicts to pairs.
    """
    async def post(self, url, headers=None, json=None, **kw):  # noqa: A002
        text = json["messages"][-1]["content"]
        return _Reply(reply_for(text))
    return post


class TestClaudeFamilyRefusal:
    @pytest.mark.parametrize(
        "model",
        ["claude-opus-5", "anthropic/claude-sonnet-5", "some-haiku-4-5", "Fable-5", "OPUS"],
    )
    def test_refuses_every_claude_marker(self, model):
        with pytest.raises(SystemExit, match="Claude-family"):
            resample_llm.assert_not_claude_family(model)

    @pytest.mark.parametrize("model", ["gpt-5", "gemini-2.5-pro", "deepseek-v4-flash", "llama-4"])
    def test_allows_another_vendor(self, model):
        resample_llm.assert_not_claude_family(model)  # must not raise


class TestParseReply:
    def test_reads_a_clean_object(self):
        got = resample_llm.parse_reply('{"verdict": "entailed", "rule": "window rule"}')
        assert got["verdict"] == "entailed"
        assert got["rule"] == "window rule"

    def test_finds_the_object_inside_prose(self):
        got = resample_llm.parse_reply(
            'Thinking about it...\n{"verdict": "unsupported", "rule": "x"}\nDone.'
        )
        assert got["verdict"] == "unsupported"

    def test_normalises_case(self):
        assert resample_llm.parse_reply('{"verdict": "CONTRADICTED"}')["verdict"] == "contradicted"

    @pytest.mark.parametrize("text", ["", "no json here", "{broken", None])
    def test_a_refusal_stays_empty_rather_than_defaulting(self, text):
        # A parse that substituted a default would turn a model that declined
        # to answer into a confident labeller, and the scorer would never see it.
        assert resample_llm.parse_reply(text)["verdict"] == ""


class TestFullPass:
    def test_a_perfect_pass_scores_zero_and_names_the_model(self, monkeypatch, gold_by_id, capsys):
        import httpx

        by_pair = {
            (p["premise"].strip(), p["hypothesis"].strip()): p["verdict"]
            for p in gold_by_id.values()
        }

        def reply_for(prompt: str) -> str:
            hit = by_pair.get(_pair_of(prompt))
            return json.dumps({"verdict": hit or "", "rule": "mock"})

        monkeypatch.setattr(httpx.AsyncClient, "post", _mock_post(reply_for))
        before = Path(entailment_gold.GOLD_PATH).read_bytes()

        rc = resample_llm.main(
            ["--base-url", "https://mock/v1", "--model", "gpt-5",
             "--api-key-env", "MOCK_KEY", "--date", "2026-08-08"]
        )
        out = capsys.readouterr().out
        assert rc == 0
        assert "disagreements=0" in out
        # Measure-only by default: the gold is untouched without --write-gold.
        assert Path(entailment_gold.GOLD_PATH).read_bytes() == before
        assert "measure-only" in out

    def test_the_recorded_block_names_the_model_not_a_person(self, monkeypatch, gold_by_id):
        import httpx

        by_pair = {
            (p["premise"].strip(), p["hypothesis"].strip()): p["verdict"]
            for p in gold_by_id.values()
        }

        def reply_for(prompt: str) -> str:
            hit = by_pair.get(_pair_of(prompt))
            return json.dumps({"verdict": hit or "", "rule": "mock"})

        monkeypatch.setattr(httpx.AsyncClient, "post", _mock_post(reply_for))
        captured = {}
        real_score = resample_score.score

        def spy(*a, **kw):
            captured.update(kw)
            return real_score(*a, **kw)

        monkeypatch.setattr(resample_llm.resample_score, "score", spy)
        resample_llm.main(
            ["--base-url", "https://mock/v1", "--model", "gpt-5",
             "--api-key-env", "MOCK_KEY", "--date", "2026-08-08"]
        )
        # The gold must never claim a human sat when no human sat.
        assert "LLM pass" in captured["performed_by"]
        assert "gpt-5" in captured["performed_by"]

    def test_a_model_that_declines_fails_loudly_rather_than_scoring(self, monkeypatch):
        import httpx

        monkeypatch.setattr(
            httpx.AsyncClient, "post", _mock_post(lambda _: "I cannot help with that.")
        )
        with pytest.raises(ValueError, match="is not one of"):
            resample_llm.main(
                ["--base-url", "https://mock/v1", "--model", "gpt-5",
                 "--api-key-env", "MOCK_KEY", "--date", "2026-08-08"]
            )
