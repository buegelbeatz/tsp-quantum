from __future__ import annotations

from importlib import util
from pathlib import Path
import sys
from types import SimpleNamespace


def _load_module(name: str, file_path: Path):
    spec = util.spec_from_file_location(name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {name} from {file_path}")
    module = util.module_from_spec(spec)
    module_dir = str(file_path.parent)
    sys.path.insert(0, module_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        if sys.path and sys.path[0] == module_dir:
            sys.path.pop(0)
    return module


def test_quantum_topic_handoffs_disabled_by_default(monkeypatch):
    module = _load_module(
        "artifacts_flow_data_to_spec",
        Path(__file__).resolve().parents[1] / "artifacts_flow_data_to_spec.py",
    )
    monkeypatch.delenv("DIGITAL_ENABLE_TOPIC_HANDOFFS", raising=False)
    assert module._enable_topic_handoffs() is False


def test_quantum_topic_handoffs_can_be_enabled(monkeypatch):
    module = _load_module(
        "artifacts_flow_data_to_spec",
        Path(__file__).resolve().parents[1] / "artifacts_flow_data_to_spec.py",
    )
    monkeypatch.setenv("DIGITAL_ENABLE_TOPIC_HANDOFFS", "1")
    assert module._enable_topic_handoffs() is True


def test_story_title_is_not_generic_plan_delivery_phrase():
    module = _load_module(
        "artifacts_flow_planning",
        Path(__file__).resolve().parents[1] / "artifacts_flow_planning.py",
    )

    templates = {
        "epic": "{{epic_id}}\n{{title}}\n{{description}}",
        "story": "{{story_id}}\n{{title}}\n{{summary}}",
        "task": "{{task_id}}\n{{title}}\n{{description}}\n{{acceptance_criteria}}",
    }

    rendered = module._build_core_planning_artifacts(
        stage="project",
        bundle=SimpleNamespace(item_code="THM-01"),
        spec_path=Path("/tmp/spec.md"),
        templates=templates,
        title="Project Delivery Execution (THM-01)",
        problem="Compare classical and quantum-inspired TSP approaches with measurable output quality.",
        scope="Translate approved scope into implementation work packages.",
        acceptance=[
            "Notebook comparison table includes all selected algorithms.",
            "Each method reports runtime and route length on the same dataset.",
        ],
        hints=["Use deterministic dataset inputs."],
        milestone_id="MS-PROJECT-THM-01",
        sprint_hint="next",
    )

    assert "Plan delivery for" not in rendered["story"]
    assert "Define executable work packages for" in rendered["story"]


def test_acceptance_derivation_filters_heading_noise():
    module = _load_module(
        "artifacts_flow_planning",
        Path(__file__).resolve().parents[1] / "artifacts_flow_planning.py",
    )

    result = module._derive_acceptance_from_source_notes(
        [
            "🧭 Enterprise Project Specification",
            "Quantum vs Classical Approaches to the Traveling Salesman Problem (TSP)",
            "Notebook comparison table shows route length and runtime for all methods.",
        ],
        role="fullstack-engineer",
    )

    assert all("Enterprise Project Specification" not in line for line in result)
    assert any("Notebook comparison table" in line for line in result)
