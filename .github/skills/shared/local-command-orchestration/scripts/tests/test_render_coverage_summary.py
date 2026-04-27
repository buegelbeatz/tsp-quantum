"""Unit tests for render_coverage_summary.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_module(name: str) -> types.ModuleType:
    script_dir = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(name, script_dir / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


MODULE = _load_module("render_coverage_summary")


class TestCoverColor:
    def test_green_at_or_above_90(self) -> None:
        """TODO: add docstring for test_green_at_or_above_90."""
        assert MODULE.cover_color(90.0) == MODULE.GREEN
        assert MODULE.cover_color(100.0) == MODULE.GREEN
        assert MODULE.cover_color(95.5) == MODULE.GREEN

    def test_yellow_between_80_and_90(self) -> None:
        """TODO: add docstring for test_yellow_between_80_and_90."""
        assert MODULE.cover_color(80.0) == MODULE.YELLOW
        assert MODULE.cover_color(89.9) == MODULE.YELLOW

    def test_red_below_80(self) -> None:
        """TODO: add docstring for test_red_below_80."""
        assert MODULE.cover_color(79.9) == MODULE.RED
        assert MODULE.cover_color(0.0) == MODULE.RED


class TestShorten:
    def test_strips_repo_root_prefix(self) -> None:
        """TODO: add docstring for test_strips_repo_root_prefix."""
        result = MODULE.shorten("/repo/root/mymodule.py", "/repo/root")
        assert result == "mymodule.py"

    def test_splits_on_skills_marker(self) -> None:
        """TODO: add docstring for test_splits_on_skills_marker."""
        result = MODULE.shorten(
            "/repo/root/.digital-team/skills/foo/bar.py", "/repo/root"
        )
        assert result == "foo/bar.py"

    def test_windows_backslash_normalized(self) -> None:
        """TODO: add docstring for test_windows_backslash_normalized."""
        result = MODULE.shorten("C:\\repo\\root\\src\\module.py", "C:\\repo\\root")
        assert result == "src/module.py"

    def test_unknown_root_returns_original(self) -> None:
        """TODO: add docstring for test_unknown_root_returns_original."""
        result = MODULE.shorten("/other/path/file.py", "/repo/root")
        assert result == "/other/path/file.py"


class TestColorize:
    def test_wraps_text_in_ansi_codes(self) -> None:
        """TODO: add docstring for test_wraps_text_in_ansi_codes."""
        result = MODULE.colorize("94%", MODULE.GREEN)
        assert "94%" in result
        assert result.startswith("\033[")
        assert result.endswith(MODULE.RESET)


class TestMainMissingJson:
    def test_exits_1_when_json_missing(self, tmp_path: Path) -> None:
        """TODO: add docstring for test_exits_1_when_json_missing."""
        json_path = str(tmp_path / "nonexistent.json")
        sys.argv = ["render_coverage_summary.py", json_path, "80", "/repo"]
        try:
            MODULE.main()
        except SystemExit as exc:
            assert exc.code == 1
        else:
            raise AssertionError("Expected SystemExit")


def _write_coverage_json(path: Path, files: dict, totals: dict) -> None:
    path.write_text(json.dumps({"files": files, "totals": totals}), encoding="utf-8")


class TestMainWithJson:
    def test_passes_threshold_exits_0(self, tmp_path: Path) -> None:
        """TODO: add docstring for test_passes_threshold_exits_0."""
        json_path = tmp_path / "coverage.json"
        _write_coverage_json(
            json_path,
            files={
                "/repo/src/module.py": {
                    "summary": {
                        "percent_covered": 95.0,
                        "num_statements": 20,
                        "missing_lines": 1,
                    },
                    "missing_lines": [42],
                }
            },
            totals={"percent_covered": 95.0, "num_statements": 20, "missing_lines": 1},
        )
        sys.argv = ["render_coverage_summary.py", str(json_path), "80", "/repo"]
        try:
            MODULE.main()
        except SystemExit as exc:
            assert exc.code == 0

    def test_fails_below_threshold_exits_1(self, tmp_path: Path) -> None:
        """TODO: add docstring for test_fails_below_threshold_exits_1."""
        json_path = tmp_path / "coverage.json"
        _write_coverage_json(
            json_path,
            files={},
            totals={"percent_covered": 70.0, "num_statements": 10, "missing_lines": 3},
        )
        sys.argv = ["render_coverage_summary.py", str(json_path), "80", "/repo"]
        try:
            MODULE.main()
        except SystemExit as exc:
            assert exc.code == 1

    def test_output_contains_total_row(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TODO: add docstring for test_output_contains_total_row."""
        json_path = tmp_path / "coverage.json"
        _write_coverage_json(
            json_path,
            files={},
            totals={"percent_covered": 85.0, "num_statements": 50, "missing_lines": 7},
        )
        sys.argv = ["render_coverage_summary.py", str(json_path), "80", "/repo"]
        try:
            MODULE.main()
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "TOTAL" in out
        assert "threshold=80%" in out

    def test_output_contains_info_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TODO: add docstring for test_output_contains_info_line."""
        json_path = tmp_path / "coverage.json"
        _write_coverage_json(
            json_path,
            files={},
            totals={"percent_covered": 85.0, "num_statements": 0, "missing_lines": 0},
        )
        sys.argv = ["render_coverage_summary.py", str(json_path), "80", "/repo"]
        try:
            MODULE.main()
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "excluding tests and test helpers" in out

    def test_file_rows_sorted_by_coverage(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TODO: add docstring for test_file_rows_sorted_by_coverage."""
        json_path = tmp_path / "coverage.json"
        _write_coverage_json(
            json_path,
            files={
                "/repo/high.py": {
                    "summary": {
                        "percent_covered": 95.0,
                        "num_statements": 10,
                        "missing_lines": 0,
                    },
                    "missing_lines": [],
                },
                "/repo/low.py": {
                    "summary": {
                        "percent_covered": 50.0,
                        "num_statements": 10,
                        "missing_lines": 5,
                    },
                    "missing_lines": [1, 2, 3, 4, 5],
                },
            },
            totals={"percent_covered": 72.5, "num_statements": 20, "missing_lines": 5},
        )
        sys.argv = ["render_coverage_summary.py", str(json_path), "80", "/repo"]
        try:
            MODULE.main()
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert out.index("low.py") < out.index("high.py")
