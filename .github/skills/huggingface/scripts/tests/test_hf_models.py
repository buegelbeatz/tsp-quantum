from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("huggingface_hub")


def _load_module():
    """Load the hf_models module from the scripts directory."""
    script_path = Path(__file__).resolve().parents[1] / "hf_models.py"
    spec = importlib.util.spec_from_file_location("hf_models", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


hf_models = _load_module()


class _FakeApi:
    """Mock HuggingFace API for testing."""

    def __init__(self) -> None:
        self._models = [
            SimpleNamespace(id="org/model-a", downloads=20, tags=["text-generation"]),
            SimpleNamespace(id="org/model-b", downloads=5, tags=["summarization"]),
        ]

    def list_models(self, **_: object):
        """Return mock list of models."""
        return self._models

    def model_info(self, model_id: str):
        """Return mock model information."""
        return SimpleNamespace(
            id=model_id,
            pipeline_tag="text-generation",
            downloads=20,
            likes=3,
            tags=["text-generation", "en"],
        )


def test_list_models(monkeypatch) -> None:
    """Test listing models returns correct status and count."""
    monkeypatch.setattr(hf_models, "_api", lambda: _FakeApi())
    args = SimpleNamespace(search="", task="", author="", limit=5)
    payload = hf_models._list_models(args)
    assert payload["status"] == "ok"
    assert payload["count"] == 2


def test_inspect_model(monkeypatch) -> None:
    """Test inspecting a specific model returns metadata."""
    monkeypatch.setattr(hf_models, "_api", lambda: _FakeApi())
    payload = hf_models._inspect_model(SimpleNamespace(model_id="org/model-a"))
    assert payload["model"]["id"] == "org/model-a"
    assert payload["model"]["pipeline_tag"] == "text-generation"


def test_determine_models(monkeypatch) -> None:
    """Test determining models ranks them by task match and download count."""
    monkeypatch.setattr(hf_models, "_api", lambda: _FakeApi())
    args = SimpleNamespace(search="", task="text-generation", author="", limit=5)
    payload = hf_models._determine_models(args)
    assert payload["status"] == "ok"
    assert payload["candidates"][0]["id"] == "org/model-a"
