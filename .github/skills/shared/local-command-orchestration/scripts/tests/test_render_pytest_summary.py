"""Unit tests for render_pytest_summary.py."""

from __future__ import annotations

import importlib.util
import sys
import types
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


def _load_module(name: str) -> types.ModuleType:
    script_dir = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(name, script_dir / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


MODULE = _load_module("render_pytest_summary")


def _make_testcase(
    file: str | None = None, classname: str = "", name: str = "test_something"
) -> ET.Element:
    attrib: dict[str, str] = {"name": name, "classname": classname}
    if file is not None:
        attrib["file"] = file
    return ET.Element("testcase", attrib=attrib)


class TestShortenSource:
    def test_file_path_with_slashes(self) -> None:
        """TODO: add docstring for test_file_path_with_slashes."""
        tc = _make_testcase(file="skills/foo/tests/test_bar.py")
        assert MODULE.shorten_source(tc) == "bar"

    def test_file_path_strips_py_extension(self) -> None:
        """TODO: add docstring for test_file_path_strips_py_extension."""
        tc = _make_testcase(file="scripts/test_utils.py")
        assert MODULE.shorten_source(tc) == "utils"

    def test_file_path_strips_test_prefix(self) -> None:
        """TODO: add docstring for test_file_path_strips_test_prefix."""
        tc = _make_testcase(file="tests/test_something.py")
        assert MODULE.shorten_source(tc) == "something"

    def test_classname_dotted_falls_through(self) -> None:
        # dotted classname: last segment is extracted, then test_ prefix stripped
        """TODO: add docstring for test_classname_dotted_falls_through."""
        tc = _make_testcase(file=None, classname="tests.test_foo")
        assert MODULE.shorten_source(tc) == "foo"

    def test_windows_backslash_normalized(self) -> None:
        """TODO: add docstring for test_windows_backslash_normalized."""
        tc = _make_testcase(file="skills\\foo\\test_bar.py")
        assert MODULE.shorten_source(tc) == "bar"

    def test_empty_attributes_returns_default(self) -> None:
        """TODO: add docstring for test_empty_attributes_returns_default."""
        tc = ET.Element("testcase", {"name": "x"})
        assert MODULE.shorten_source(tc) == "test"

    def test_no_extension_no_prefix(self) -> None:
        """TODO: add docstring for test_no_extension_no_prefix."""
        tc = _make_testcase(file="tests/mymodule.py")
        assert MODULE.shorten_source(tc) == "mymodule"


class TestSummarizeReason:
    def test_none_returns_empty(self) -> None:
        """TODO: add docstring for test_none_returns_empty."""
        assert MODULE.summarize_reason(None) == ""

    def test_empty_string_returns_empty(self) -> None:
        """TODO: add docstring for test_empty_string_returns_empty."""
        assert MODULE.summarize_reason("") == ""

    def test_single_line(self) -> None:
        """TODO: add docstring for test_single_line."""
        assert (
            MODULE.summarize_reason("AssertionError: expected True")
            == "AssertionError: expected True"
        )

    def test_multiline_returns_first_non_empty(self) -> None:
        """TODO: add docstring for test_multiline_returns_first_non_empty."""
        assert MODULE.summarize_reason("\n\nfirst line\nsecond line") == "first line"

    def test_whitespace_only_returns_empty(self) -> None:
        """TODO: add docstring for test_whitespace_only_returns_empty."""
        assert MODULE.summarize_reason("   \n   \n") == ""


class TestColorize:
    def test_wraps_text_in_ansi_codes(self) -> None:
        """TODO: add docstring for test_wraps_text_in_ansi_codes."""
        result = MODULE.colorize("OK", MODULE.GREEN)
        assert result.startswith("\033[")
        assert "OK" in result
        assert result.endswith(MODULE.RESET)


class TestMainMissingJunit:
    def test_exits_1_when_junit_missing(self, tmp_path: Path) -> None:
        """TODO: add docstring for test_exits_1_when_junit_missing."""
        junit = str(tmp_path / "nonexistent.xml")
        raw_log = str(tmp_path / "pytest.log")
        sys.argv = ["render_pytest_summary.py", junit, raw_log, "0"]
        try:
            MODULE.main()
        except SystemExit as exc:
            assert exc.code == 1
        else:
            raise AssertionError("Expected SystemExit")

    def test_prints_raw_log_when_junit_missing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TODO: add docstring for test_prints_raw_log_when_junit_missing."""
        junit = str(tmp_path / "nonexistent.xml")
        raw_log = tmp_path / "pytest.log"
        raw_log.write_text("ERROR: import failed\n", encoding="utf-8")
        sys.argv = ["render_pytest_summary.py", str(junit), str(raw_log), "1"]
        try:
            MODULE.main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "ERROR: import failed" in captured.out


class TestMainWithJunit:
    def _write_junit(self, path: Path, testcases_xml: str) -> None:
        path.write_text(
            f'<?xml version="1.0"?><testsuite>{testcases_xml}</testsuite>',
            encoding="utf-8",
        )

    def test_all_passed_exits_0(self, tmp_path: Path) -> None:
        """TODO: add docstring for test_all_passed_exits_0."""
        junit = tmp_path / "junit.xml"
        self._write_junit(junit, '<testcase name="test_foo" file="tests/test_bar.py"/>')
        raw_log = tmp_path / "pytest.log"
        raw_log.write_text("", encoding="utf-8")
        sys.argv = ["render_pytest_summary.py", str(junit), str(raw_log), "0"]
        try:
            MODULE.main()
        except SystemExit as exc:
            assert exc.code == 0

    def test_failed_test_exits_1(self, tmp_path: Path) -> None:
        """TODO: add docstring for test_failed_test_exits_1."""
        junit = tmp_path / "junit.xml"
        self._write_junit(
            junit,
            '<testcase name="test_foo" file="tests/test_bar.py">'
            '<failure message="AssertionError"/>'
            "</testcase>",
        )
        raw_log = tmp_path / "pytest.log"
        raw_log.write_text("", encoding="utf-8")
        sys.argv = ["render_pytest_summary.py", str(junit), str(raw_log), "0"]
        try:
            MODULE.main()
        except SystemExit as exc:
            assert exc.code == 1

    def test_output_contains_counter(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TODO: add docstring for test_output_contains_counter."""
        junit = tmp_path / "junit.xml"
        self._write_junit(junit, '<testcase name="test_foo" file="tests/test_bar.py"/>')
        raw_log = tmp_path / "pytest.log"
        raw_log.write_text("", encoding="utf-8")
        sys.argv = ["render_pytest_summary.py", str(junit), str(raw_log), "0"]
        try:
            MODULE.main()
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "[001/001]" in out
        assert "total=1 passed=1 skipped=0 failed=0" in out

    def test_skipped_test_listed_with_reason(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """TODO: add docstring for test_skipped_test_listed_with_reason."""
        junit = tmp_path / "junit.xml"
        self._write_junit(
            junit,
            '<testcase name="test_skip_me" file="tests/test_bar.py">'
            '<skipped message="not yet implemented"/>'
            "</testcase>",
        )
        raw_log = tmp_path / "pytest.log"
        raw_log.write_text("", encoding="utf-8")
        sys.argv = ["render_pytest_summary.py", str(junit), str(raw_log), "0"]
        try:
            MODULE.main()
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "not yet implemented" in out
        assert "skip_me" in out

    def test_stage_failure_exits_1_even_with_all_passing(self, tmp_path: Path) -> None:
        """TODO: add docstring for test_stage_failure_exits_1_even_with_all_passing."""
        junit = tmp_path / "junit.xml"
        self._write_junit(junit, '<testcase name="test_foo" file="tests/test_bar.py"/>')
        raw_log = tmp_path / "pytest.log"
        raw_log.write_text("", encoding="utf-8")
        sys.argv = ["render_pytest_summary.py", str(junit), str(raw_log), "1"]
        try:
            MODULE.main()
        except SystemExit as exc:
            assert exc.code == 1
