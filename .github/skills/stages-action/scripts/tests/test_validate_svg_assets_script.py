from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills" / "stages-action").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


def test_validate_svg_assets_normalizes_text_node_comparators(tmp_path: Path) -> None:
    repo = tmp_path
    script = _repo_root() / ".github" / "skills" / "stages-action" / "scripts" / "validate-svg-assets.sh"

    scribble_dir = repo / "docs" / "ux" / "scribbles"
    scribble_dir.mkdir(parents=True, exist_ok=True)
    svg_path = scribble_dir / "invalid-thresholds.svg"
    svg_path.write_text(
        """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\">\n"
        "  <text x=\"10\" y=\"20\">>= 90% task completion | <= 120s median | >= 4/5 clarity score</text>\n"
        "</svg>\n""",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(script), "project", sys.executable],
        cwd=repo,
        text=True,
        capture_output=True,
        env={"DIGITAL_REPO_ROOT": str(repo)},
        check=False,
    )

    assert result.returncode == 0
    assert "invalid=0" in result.stdout

    normalized = svg_path.read_text(encoding="utf-8")
    assert "&amp;gt;=" in normalized
    assert "&amp;lt;=" in normalized

    report_root = repo / ".digital-artifacts" / "60-review"
    report_files = list(report_root.glob("*/project/SVG_ASSET_STATUS.md"))
    assert report_files
    report_text = report_files[0].read_text(encoding="utf-8")
    assert "- invalid_svg_files: 0" in report_text
    assert "- docs/ux/scribbles/invalid-thresholds.svg" in report_text
