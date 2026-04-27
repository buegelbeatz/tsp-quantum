from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_svg_module():
    script_path = Path(__file__).resolve().parents[1] / "powerpoint_svg.py"
    spec = importlib.util.spec_from_file_location("powerpoint_svg", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


svg_mod = _load_svg_module()


def test_svg_generation_is_deterministic() -> None:
    """TODO: add docstring for test_svg_generation_is_deterministic."""
    a = svg_mod.make_background_svg(1280, 720, 1234, "title")
    b = svg_mod.make_background_svg(1280, 720, 1234, "title")
    assert a == b
    assert "<svg" in a
    assert "<circle" in a
