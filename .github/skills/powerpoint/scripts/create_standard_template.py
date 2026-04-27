"""Create a deterministic standard layer template if it does not exist."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from template_factory import ensure_template


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for template creation.

    Returns:
        argparse.Namespace: Parsed arguments with repo_root, layer, and optional template.
    """
    parser = argparse.ArgumentParser(description="Create layer PowerPoint template")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--layer", required=True)
    parser.add_argument(
        "--template",
        help="Optional target template path. Default: .github/skills/powerpoint/templates/<layer>_template.pptx",
    )
    return parser.parse_args()


def main() -> int:
    """Create a template PPTX file for the given layer.

    Generates a template with title slide, content slide, and team member slide
    with deterministic backgrounds and team portrait grid.

    Returns:
        int: Exit code (0 for success).
    """
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    default_template = (
        repo_root
        / ".github/skills/powerpoint/templates"
        / f"{args.layer}_template.pptx"
    )
    template_path = Path(args.template).resolve() if args.template else default_template
    created_path, created = ensure_template(repo_root, args.layer, template_path)
    payload = {
        "status": "ok",
        "template": str(created_path),
        "created": created,
        "layer": args.layer,
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
