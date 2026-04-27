"""CLI dispatch for artifacts tool commands."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for artifacts CLI commands."""
    parser = argparse.ArgumentParser(description="Artifacts skill utility commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bundle_parser = subparsers.add_parser(
        "bundle", help="Allocate a new numbered data bundle"
    )
    bundle_parser.add_argument(
        "--data-root", required=True, help="Path to the 10-data root"
    )
    bundle_parser.add_argument(
        "--date", required=True, help="Date key in YYYY-MM-DD format"
    )

    inventory_parser = subparsers.add_parser(
        "inventory", help="Upsert an inventory entry"
    )
    inventory_parser.add_argument("--inventory-path", required=True)
    inventory_parser.add_argument("--template-path")
    inventory_parser.add_argument("--item-id", required=True)
    inventory_parser.add_argument("--created-at", required=True)
    inventory_parser.add_argument(
        "--fields-json",
        required=True,
        help="JSON object where values are strings or arrays of strings",
    )

    latest_parser = subparsers.add_parser(
        "latest", help="Update a managed LATEST.md snapshot"
    )
    latest_parser.add_argument("--latest-path", required=True)
    latest_parser.add_argument("--source-path", required=True)

    return parser


def main(
    argv: list[str] | None = None,
    *,
    handle_bundle_fn=None,
    handle_inventory_fn=None,
    handle_latest_fn=None,
) -> int:
    """Execute artifacts CLI by dispatching to command handlers."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bundle":
        return handle_bundle_fn(args)
    if args.command == "inventory":
        return handle_inventory_fn(args)
    if args.command == "latest":
        return handle_latest_fn(args)

    parser.error("unknown command")
    return 2
