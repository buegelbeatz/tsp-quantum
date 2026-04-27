from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_seed_module():
    script_path = Path(__file__).resolve().parents[1] / "powerpoint_seed.py"
    spec = importlib.util.spec_from_file_location("powerpoint_seed", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


seed_mod = _load_seed_module()


def test_build_seed_is_deterministic() -> None:
    """TODO: add docstring for test_build_seed_is_deterministic."""
    assert seed_mod.build_seed(
        "digital-generic-team", "digital-generic-team"
    ) == seed_mod.build_seed("digital-generic-team", "digital-generic-team")


def test_source_slug_normalizes_name() -> None:
    """TODO: add docstring for test_source_slug_normalizes_name."""
    slug = seed_mod.source_slug(Path("My Great Spec.md"))
    assert slug == "my-great-spec"
