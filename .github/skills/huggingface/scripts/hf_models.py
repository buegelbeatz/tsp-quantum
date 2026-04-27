"""List, inspect, and determine Hugging Face models using optional token auth.

This module provides CLI functionality for:
- Listing models by task, search term, and author
- Inspecting detailed model metadata
- Determining and ranking suitable models based on task match and popularity
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from huggingface_hub import HfApi  # type: ignore[import-not-found]


def _api() -> HfApi:
    """Create and return an authenticated HuggingFace Hub API client.

    Returns:
        HfApi: API client with optional authentication from HUGGINGFACE_TOKEN.
    """
    return HfApi(token=os.getenv("HUGGINGFACE_TOKEN") or None)


def _list_models(args: argparse.Namespace) -> dict[str, object]:
    """List models from Hugging Face Hub with optional filtering.

    Args:
        args: Parsed arguments containing:
            - search: Search query string
            - task: Pipeline task filter (e.g., 'text-generation')
            - author: Author or organization filter
            - limit: Maximum number of results

    Returns:
        dict: Response with status, count, and list of model entries containing id and downloads.
    """
    try:
        models = _api().list_models(
            search=args.search, task=args.task, author=args.author, limit=args.limit
        )  # type: ignore[call-arg]
        entries = [
            {"id": model.id, "downloads": getattr(model, "downloads", None)}
            for model in models
        ]
        return {
            "status": "ok",
            "mode": "list",
            "count": len(entries),
            "models": entries,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "mode": "list", "error": str(exc)}


def _inspect_model(args: argparse.Namespace) -> dict[str, object]:
    """Inspect detailed metadata for a specific model.

    Args:
        args: Parsed arguments containing:
            - model_id: Full model identifier (e.g., 'org/model-name')

    Returns:
        dict: Response with status and model metadata including id, pipeline_tag,
              downloads, likes, and tags (limited to 20).
    """
    try:
        info = _api().model_info(args.model_id)
        tags = list(getattr(info, "tags", []) or [])
        return {
            "status": "ok",
            "mode": "inspect",
            "model": {
                "id": info.id,
                "pipeline_tag": getattr(info, "pipeline_tag", None),
                "downloads": getattr(info, "downloads", None),
                "likes": getattr(info, "likes", None),
                "tags": tags[:20],
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "mode": "inspect", "error": str(exc)}


def _rank_candidates(models: object, task: str | None) -> list[dict[str, object]]:
    """Score and rank model candidates by task match and download count."""
    candidates = []
    for model in models:  # type: ignore[attr-defined]
        tags = set(getattr(model, "tags", []) or [])
        score = (2 if task and task in tags else 0) + (
            1 if getattr(model, "downloads", 0) else 0
        )
        candidates.append(
            {
                "id": model.id,
                "score": score,
                "downloads": getattr(model, "downloads", 0),
            }
        )
    return sorted(
        candidates, key=lambda item: (item["score"], item["downloads"]), reverse=True
    )


def _determine_models(args: argparse.Namespace) -> dict[str, object]:
    """Determine and rank suitable models based on task match and popularity.

    Scoring: +2 for task tag match, +1 for download count > 0.
    Ranked by score then downloads, both descending.
    """
    try:
        models = _api().list_models(
            search=args.search, task=args.task, limit=args.limit
        )  # type: ignore[call-arg]
        ranked = _rank_candidates(models, args.task)
        return {
            "status": "ok",
            "mode": "determine",
            "count": len(ranked),
            "candidates": ranked,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "mode": "determine", "error": str(exc)}


def _parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for the CLI.

    Returns:
        argparse.ArgumentParser: Configured parser with subcommands for list, inspect, and determine.
    """
    parser = argparse.ArgumentParser(description="Hugging Face model helper")
    sub = parser.add_subparsers(dest="mode", required=True)
    for name in ("list", "determine"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--search", default="")
        cmd.add_argument("--task", default="")
        cmd.add_argument("--author", default="")
        cmd.add_argument("--limit", type=int, default=10)
    inspect_cmd = sub.add_parser("inspect")
    inspect_cmd.add_argument("--model-id", required=True)
    return parser


def main() -> int:
    """Entrypoint for the Hugging Face model CLI.

    Parses arguments and routes to list, inspect, or determine subcommands.
    Outputs JSON payload to stdout.

    Returns:
        int: Exit code (0 for success, non-zero for error).
    """
    try:
        args = _parser().parse_args()
        if args.mode == "list":
            payload = _list_models(args)
        elif args.mode == "inspect":
            payload = _inspect_model(args)
        else:
            payload = _determine_models(args)
        print(json.dumps(payload))
        return 0
    except Exception as exc:  # noqa: BLE001
        error_payload = {"status": "error", "error": str(exc)}
        print(json.dumps(error_payload), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
