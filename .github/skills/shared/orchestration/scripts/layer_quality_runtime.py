#!/usr/bin/env python3
"""Generate the canonical layer-quality runtime report from quality-expert output."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills").exists():
            return candidate
    raise RuntimeError("Could not resolve repository root")


def main() -> int:
    repo_root = _repo_root()
    reports_dir = repo_root / ".tests" / "python" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    source = reports_dir / "quality-expert-session.md"
    target = reports_dir / "layer-quality-current.md"

    if not source.exists():
        target.write_text(
            "# Layer Quality Runtime Report\n\n"
            "status: fail\n"
            "reason: missing quality-expert-session.md\n",
            encoding="utf-8",
        )
        print(f"layer-quality-runtime: missing source report: {source}")
        return 1

    source_content = source.read_text(encoding="utf-8")
    status = "fail" if "[FAIL]" in source_content else "pass"

    rendered = (
        "# Layer Quality Runtime Report\n\n"
        f"generated_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"status: {status}\n"
        f"source: {source.relative_to(repo_root)}\n\n"
        "## Embedded quality-expert report\n\n"
        f"{source_content}\n"
    )
    target.write_text(rendered, encoding="utf-8")
    print(f"layer-quality-runtime: wrote {target}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
