"""CLI dispatch for artifacts workflow transitions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for artifacts stage transition commands."""
    parser = argparse.ArgumentParser(description="Artifacts workflow transitions")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "data-to-specification", help="Build specifications from 10-data"
    )
    stage_parser = subparsers.add_parser(
        "specification-to-stage", help="Build stage docs from 30-specification"
    )
    stage_parser.add_argument("--stage", required=True, help="Target stage key")
    planning_parser = subparsers.add_parser(
        "specification-to-planning", help="Build planning docs from stage docs"
    )
    planning_parser.add_argument("--stage", required=True, help="Target stage key")
    delivery_parser = subparsers.add_parser(
        "planning-to-delivery", help="Trigger delivery agents from planning items"
    )
    delivery_parser.add_argument("--stage", required=True, help="Target stage key")
    review_parser = subparsers.add_parser(
        "delivery-to-review", help="Aggregate delivery reviews and generate cumulated review"
    )
    review_parser.add_argument("--stage", required=True, help="Target stage key")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    run_data_to_specification_fn=None,
    run_specification_to_stage_fn=None,
    run_specification_to_planning_fn=None,
    run_planning_to_delivery_fn=None,
    run_delivery_to_review_fn=None,
) -> int:
    """CLI main for artifacts workflow transitions with dependency injection."""
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if args.command == "data-to-specification":
        result = run_data_to_specification_fn(repo_root)
    elif args.command == "specification-to-stage":
        result = run_specification_to_stage_fn(repo_root, args.stage)
    elif args.command == "specification-to-planning":
        result = run_specification_to_planning_fn(repo_root, args.stage)
    elif args.command == "planning-to-delivery":
        result = run_planning_to_delivery_fn(repo_root, args.stage) if run_planning_to_delivery_fn else {"status": "skipped", "reason": "planning-to-delivery not implemented"}
    elif args.command == "delivery-to-review":
        result = run_delivery_to_review_fn(repo_root, args.stage) if run_delivery_to_review_fn else {"status": "skipped", "reason": "delivery-to-review not implemented"}
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    print(
        json.dumps(
            {"status": "ok", "command": args.command, "result": result}, indent=2
        )
    )
    return 0
