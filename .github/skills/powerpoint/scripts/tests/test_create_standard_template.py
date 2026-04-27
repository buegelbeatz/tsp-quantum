from __future__ import annotations

import json
import sys

import pytest

from test_helpers import load_module

pytest.importorskip("pptx")


def test_main_uses_default_template_path(tmp_path, monkeypatch, capsys) -> None:
    """TODO: add docstring for test_main_uses_default_template_path."""
    seed = load_module("powerpoint_seed")
    svg = load_module("powerpoint_svg")
    sys.modules["powerpoint_seed"] = seed
    sys.modules["powerpoint_svg"] = svg
    factory = load_module("template_factory")
    sys.modules["template_factory"] = factory
    script = load_module("create_standard_template")

    expected = tmp_path / ".github/skills/powerpoint/templates/layer-x_template.pptx"
    monkeypatch.setattr(script, "ensure_template", lambda *_args: (expected, False))
    monkeypatch.setattr(
        sys, "argv", ["prog", "--repo-root", str(tmp_path), "--layer", "layer-x"]
    )

    assert script.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["template"].endswith("layer-x_template.pptx")
    assert payload["created"] is False
