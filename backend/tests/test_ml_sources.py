"""Unit tests for MLModels source resolution (local vs HuggingFace Hub)."""

from pathlib import Path

import pytest

from app.services import ml_models as mm
from app.services.ml_models import HeadSource, _hf_kwargs, _resolve_source, _sentence_transformer_kwargs


def test_headsource_local_display():
    src = HeadSource(kind="local", location="/tmp/models/span/best")
    assert src.kind == "local"
    assert src.display.startswith("local:")
    assert src.identifier == "best"


def test_headsource_hub_display():
    src = HeadSource(kind="hub", location="darkraise/darkmem-span-v1", revision="abc1234")
    assert src.display == "hub:darkraise/darkmem-span-v1@abc1234"
    assert src.identifier == "darkraise/darkmem-span-v1@abc1234"


def test_headsource_hub_main_revision_omitted_from_identifier():
    src = HeadSource(kind="hub", location="darkraise/darkmem-span-v1", revision="main")
    assert src.identifier == "darkraise/darkmem-span-v1"


def test_resolve_source_prefers_hub_when_set(tmp_path, monkeypatch):
    monkeypatch.setattr(mm.ml_pipeline_settings, "models_dir", tmp_path)
    src = _resolve_source("darkmem-span-v1/best", "darkraise/darkmem-span-v1", "main")
    assert src.kind == "hub"
    assert src.location == "darkraise/darkmem-span-v1"
    assert src.revision == "main"


def test_resolve_source_falls_back_to_local(tmp_path, monkeypatch):
    monkeypatch.setattr(mm.ml_pipeline_settings, "models_dir", tmp_path)
    src = _resolve_source("darkmem-span-v1/best", None, "main")
    assert src.kind == "local"
    assert Path(src.location) == tmp_path / "darkmem-span-v1" / "best"
    assert src.revision is None


def test_resolve_source_treats_empty_string_as_unset(tmp_path, monkeypatch):
    monkeypatch.setattr(mm.ml_pipeline_settings, "models_dir", tmp_path)
    src = _resolve_source("darkmem-typer-v1/best", "", "main")
    assert src.kind == "local"


def test_hf_kwargs_local_returns_empty():
    src = HeadSource(kind="local", location="/tmp/models/span")
    assert _hf_kwargs(src) == {}


def test_hf_kwargs_local_merges_extra():
    src = HeadSource(kind="local", location="/tmp/models/span")
    kwargs = _hf_kwargs(src, extra={"trust_remote_code": True})
    assert kwargs == {"trust_remote_code": True}


def test_hf_kwargs_hub_includes_revision(monkeypatch):
    monkeypatch.setattr(mm.ml_pipeline_settings, "hub_cache_dir", None)
    monkeypatch.setattr(mm.ml_pipeline_settings, "hub_token", None)
    src = HeadSource(kind="hub", location="darkraise/darkmem-span-v1", revision="v1")
    kwargs = _hf_kwargs(src)
    assert kwargs == {"revision": "v1"}


def test_hf_kwargs_hub_includes_token_and_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(mm.ml_pipeline_settings, "hub_cache_dir", tmp_path / "hfcache")
    monkeypatch.setattr(mm.ml_pipeline_settings, "hub_token", "hf_test_token")
    src = HeadSource(kind="hub", location="darkraise/darkmem-span-v1", revision="main")
    kwargs = _hf_kwargs(src)
    assert kwargs["revision"] == "main"
    assert kwargs["cache_dir"] == str(tmp_path / "hfcache")
    assert kwargs["token"] == "hf_test_token"


def test_sentence_transformer_kwargs_uses_cache_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(mm.ml_pipeline_settings, "hub_cache_dir", tmp_path / "hfcache")
    monkeypatch.setattr(mm.ml_pipeline_settings, "hub_token", "hf_test_token")
    src = HeadSource(kind="hub", location="darkraise/darkmem-retriever-v1", revision="main")
    kwargs = _sentence_transformer_kwargs(src)
    assert "cache_folder" in kwargs
    assert "cache_dir" not in kwargs
    assert kwargs["cache_folder"] == str(tmp_path / "hfcache")
    assert kwargs["token"] == "hf_test_token"


def test_sentence_transformer_kwargs_local_empty():
    src = HeadSource(kind="local", location="/tmp/models/retriever")
    assert _sentence_transformer_kwargs(src) == {}
