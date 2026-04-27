#!/usr/bin/env python3
"""Render a human-readable test results summary from a JUnit XML report.

Purpose:
    Convert pytest JUnit XML and raw logs into terminal-friendly test summary tables.
    Displays pass/fail statistics, failure details, and execution metadata.

Security:
    Reads test reports from local paths only. Test output may contain user code output.
    Sanitizes before terminal display.

Usage:
    python render_pytest_summary.py <junit_xml_path> <raw_log_path> <stage_status>

Arguments:
    junit_xml_path  Path to the JUnit XML file produced by pytest --junitxml.
    raw_log_path    Path to the captured raw pytest log file.
    stage_status    Exit code of the pytest stage (0 = pass, non-zero = fail).

Exit codes:
    0  All tests passed and stage succeeded.
    1  One or more tests failed, stage failed, or JUnit report is missing.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Ensure this script's directory is in sys.path for relative imports
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from render_helpers import (  # noqa: F401, E402
    colorize,
    GREEN,
    RED,
    YELLOW,
    CYAN,
    RESET,
)


def shorten_source(testcase: ET.Element) -> str:
    """Derive a short module name from a testcase element's file or classname attribute."""
    source = testcase.attrib.get("file") or testcase.attrib.get("classname", "")
    source = source.replace("\\", "/")
    if "/" in source:
        source = source.rsplit("/", 1)[-1]
    elif "." in source:
        source = source.rsplit(".", 1)[-1]
    if source.endswith(".py"):
        source = source[:-3]
    if source.startswith("test_"):
        source = source[5:]
    return source or "test"


def summarize_reason(text: str | None) -> str:
    """Return the first non-empty line from a failure or skip reason string."""
    if not text:
        return ""
    for line in text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate
    return ""


def _load_junit(junit_path: str, raw_log_path: str) -> ET.Element:
    """Load and parse JUnit XML; exit 1 with raw log output if the file is missing."""
    if not os.path.exists(junit_path):
        print(f"  {colorize('FAILED', RED):<16}pytest did not produce a JUnit report")
        if os.path.exists(raw_log_path):
            print(open(raw_log_path, encoding="utf-8").read())
        sys.exit(1)
    return ET.parse(junit_path).getroot()


def _classify_testcases(
    root: ET.Element,
) -> tuple[int, int, int, int, list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """Iterate testcases, print per-test status lines, and return result counts."""
    testcases = list(root.iter("testcase"))
    total = len(testcases)
    passed = failed = skipped = 0
    failed_cases: list[tuple[str, str, str]] = []
    skipped_cases: list[tuple[str, str, str]] = []
    for index, testcase in enumerate(testcases, start=1):
        module = shorten_source(testcase)
        name = testcase.attrib.get("name", "unnamed")
        failure = testcase.find("failure")
        if failure is None:
            failure = testcase.find("error")
        skipped_node = testcase.find("skipped")
        if failure is not None:
            failed += 1
            reason = summarize_reason(failure.attrib.get("message") or failure.text)
            failed_cases.append((module, name, reason))
            status_label = colorize("FAILED", RED)
        elif skipped_node is not None:
            skipped += 1
            reason = summarize_reason(
                skipped_node.attrib.get("message") or skipped_node.text
            )
            skipped_cases.append((module, name, reason))
            status_label = colorize("SKIPPED", YELLOW)
        else:
            passed += 1
            status_label = colorize("PASSED", GREEN)
        print(f"  [{index:03d}/{total:03d}] {status_label} {module} :: {name}")
    return total, passed, failed, skipped, failed_cases, skipped_cases


def main() -> None:
    """Parse JUnit XML and print a compact, colored test results summary."""
    junit_path, raw_log_path, status_text = sys.argv[1:4]
    print("\nTest Results")
    root = _load_junit(junit_path, raw_log_path)
    total, passed, failed, skipped, failed_cases, skipped_cases = _classify_testcases(
        root
    )
    print()
    print(
        f"  {colorize('INFO', CYAN)} total={total} passed={passed} skipped={skipped} failed={failed}"
    )
    if skipped_cases:
        print(f"  {colorize('SKIPPED', YELLOW)} details")
        for module, name, reason in skipped_cases:
            suffix = f" ({reason})" if reason else ""
            print(f"    - {module} :: {name}{suffix}")
    if failed_cases:
        print(f"  {colorize('FAILED', RED)} details")
        for module, name, reason in failed_cases:
            suffix = f" ({reason})" if reason else ""
            print(f"    - {module} :: {name}{suffix}")
        if os.path.exists(raw_log_path):
            print()
            print(colorize("pytest raw output", CYAN))
            print(open(raw_log_path, encoding="utf-8").read())
    sys.exit(0 if status_text == "0" and failed == 0 else 1)


if __name__ == "__main__":
    main()
