# fine-tuning/tests/test_eval_baseline_qwen.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.eval_baseline_qwen import run_entity, run_classification, format_entity_list


def test_format_entity_list_lines():
    entities = [
        {"name": "Alpha", "type": "project"},
        {"name": "Beta", "type": "library"},
    ]
    out = format_entity_list(entities)
    assert out == "- Alpha (project)\n- Beta (library)"


@patch("scripts.eval_baseline_qwen.call_ollama")
def test_run_entity_parses_json(mock_call):
    mock_call.return_value = json.dumps({"entities": [{"name": "X", "type": "project", "start": 0, "end": 1}]})
    out = run_entity("X is a project.", prompts={"system": "sys", "user_template": "Text: {text}\n\nOutput the JSON now."}, entity_types=["project"])
    assert out == [{"name": "X", "type": "project", "start": 0, "end": 1}]


@patch("scripts.eval_baseline_qwen.call_ollama")
def test_run_classification_returns_label(mock_call):
    mock_call.return_value = json.dumps({"memory_type": "fact"})
    out = run_classification("some text.", prompts={"system": "sys", "user_template": "Memory: {text}\n\nOutput the JSON now."})
    assert out == "fact"
