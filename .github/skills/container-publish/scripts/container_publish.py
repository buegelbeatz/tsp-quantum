from __future__ import annotations

import argparse
import glob
import io
import json
import os
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ImageConfig:
    image_id: str
    image: str
    docs_image: str
    context: str
    dockerfile: str
    description: str
    documentation_url: str
    readme: str
    platforms: list[str]
    docs_globs: list[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _norm_rel_path(repo_root: Path, value: str, *, field_name: str) -> str:
    path = (repo_root / value).resolve()
    try:
        relative = path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay inside repository: {value}") from exc
    return relative.as_posix()


def _default_docs_image(image: str) -> str:
    registry, owner, name = image.split("/", 2)
    return f"{registry}/{owner}/{name}-docs"


def _coerce_string_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{field_name} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _resolve_images(config_path: Path, repo_root: Path) -> list[ImageConfig]:
    config = _load_yaml(config_path)
    enabled = config.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    if not enabled:
        return []
    defaults = config.get("defaults") or {}
    if defaults and not isinstance(defaults, dict):
        raise ValueError("defaults must be a mapping")
    images = config.get("images") or []
    if not isinstance(images, list) or not images:
        raise ValueError("images must contain at least one entry")

    repo_env = os.getenv("GITHUB_REPOSITORY", "owner/repo")
    owner_env, repo_name = (
        repo_env.split("/", 1) if "/" in repo_env else ("owner", repo_env)
    )
    registry = str(defaults.get("registry", "ghcr.io")).strip()
    owner = str(defaults.get("owner", owner_env)).strip()
    base_platforms = _coerce_string_list(
        defaults.get("platforms", ["linux/amd64", "linux/arm64"]),
        field_name="defaults.platforms",
    )
    default_context = str(defaults.get("context", ".")).strip()
    default_dockerfile = str(defaults.get("dockerfile", "Dockerfile")).strip()
    default_docs_globs = _coerce_string_list(
        defaults.get("docs_globs", ["README.md", "docs/**"]),
        field_name="defaults.docs_globs",
    )
    default_readme = str(defaults.get("readme", "README.md")).strip()
    default_documentation_url = str(defaults.get("documentation_url", "")).strip()

    resolved: list[ImageConfig] = []
    for entry in images:
        if not isinstance(entry, dict):
            raise ValueError("Each image entry must be a mapping")
        image_id = str(entry.get("id", "")).strip()
        if not image_id:
            raise ValueError("Each image entry requires id")
        image_ref = str(entry.get("image", f"{registry}/{owner}/{repo_name}")).strip()
        if image_ref.count("/") < 2:
            raise ValueError(
                f"image must be a fully qualified GHCR reference: {image_ref}"
            )
        context = _norm_rel_path(
            repo_root,
            str(entry.get("context", default_context)).strip(),
            field_name=f"images[{image_id}].context",
        )
        dockerfile = _norm_rel_path(
            repo_root,
            str(entry.get("dockerfile", default_dockerfile)).strip(),
            field_name=f"images[{image_id}].dockerfile",
        )
        readme = _norm_rel_path(
            repo_root,
            str(entry.get("readme", default_readme)).strip(),
            field_name=f"images[{image_id}].readme",
        )
        docs_globs = _coerce_string_list(
            entry.get("docs_globs", default_docs_globs),
            field_name=f"images[{image_id}].docs_globs",
        )
        platforms = _coerce_string_list(
            entry.get("platforms", base_platforms),
            field_name=f"images[{image_id}].platforms",
        )
        description = str(
            entry.get(
                "description",
                defaults.get("description", f"Container image for {repo_name}"),
            )
        ).strip()
        if not description:
            raise ValueError(f"images[{image_id}].description must not be empty")
        documentation_url = str(
            entry.get("documentation_url", default_documentation_url)
        ).strip()
        docs_image = str(
            entry.get("docs_image", _default_docs_image(image_ref))
        ).strip()
        resolved.append(
            ImageConfig(
                image_id=image_id,
                image=image_ref,
                docs_image=docs_image,
                context=context,
                dockerfile=dockerfile,
                description=description,
                documentation_url=documentation_url,
                readme=readme,
                platforms=platforms,
                docs_globs=docs_globs,
            )
        )

    return resolved


def _resolve_docs_files(image: ImageConfig, repo_root: Path) -> list[Path]:
    matches: set[Path] = set()
    readme_path = (repo_root / image.readme).resolve()
    if readme_path.exists():
        matches.add(readme_path)
    for pattern in image.docs_globs:
        for matched in glob.glob(str(repo_root / pattern), recursive=True):
            candidate = Path(matched).resolve()
            if candidate.is_file():
                try:
                    candidate.relative_to(repo_root.resolve())
                except ValueError:
                    continue
                matches.add(candidate)
    if not matches:
        raise ValueError(f"No documentation files matched for image '{image.image_id}'")
    return sorted(matches)


def command_validate(args: argparse.Namespace) -> int:
    """Validate the container publish config and print the enabled image list as JSON."""
    images = _resolve_images(
        Path(args.config).resolve(), Path(args.repo_root).resolve()
    )
    payload = {
        "schema": "container_publish_config_v1",
        "image_count": len(images),
        "images": [image.image_id for image in images],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_matrix(args: argparse.Namespace) -> int:
    """Output a CI matrix JSON payload for all resolved container images."""
    images = _resolve_images(
        Path(args.config).resolve(), Path(args.repo_root).resolve()
    )
    payload = {
        "include": [
            {
                "id": image.image_id,
                "image": image.image,
                "docs_image": image.docs_image,
                "context": image.context,
                "dockerfile": image.dockerfile,
                "description": image.description,
                "documentation_url": image.documentation_url,
                "readme": image.readme,
                "platforms": ",".join(image.platforms),
            }
            for image in images
        ]
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


def command_package_docs(args: argparse.Namespace) -> int:
    """Package resolved documentation files for a container image into a gzipped tarball."""
    config_path = Path(args.config).resolve()
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output).resolve()
    images = {
        image.image_id: image for image in _resolve_images(config_path, repo_root)
    }
    if not images:
        raise ValueError("Container publishing is disabled in config")
    try:
        image = images[args.image_id]
    except KeyError as exc:
        raise ValueError(f"Unknown image id: {args.image_id}") from exc

    docs_files = _resolve_docs_files(image, repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        manifest = {
            "schema": "container_publish_docs_bundle_v1",
            "image": image.image,
            "docs_image": image.docs_image,
            "files": [path.relative_to(repo_root).as_posix() for path in docs_files],
        }
        manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_info.size = len(manifest_bytes)
        archive.addfile(manifest_info, fileobj=io.BytesIO(manifest_bytes))
        for path in docs_files:
            archive.add(path, arcname=path.relative_to(repo_root).as_posix())
    print(output.as_posix())
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the container-publishing CLI."""
    parser = argparse.ArgumentParser(
        description="Governed container publishing helpers"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("config")
    validate_parser.add_argument("repo_root")
    validate_parser.set_defaults(func=command_validate)

    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("config")
    matrix_parser.add_argument("repo_root")
    matrix_parser.set_defaults(func=command_matrix)

    docs_parser = subparsers.add_parser("package-docs")
    docs_parser.add_argument("config")
    docs_parser.add_argument("repo_root")
    docs_parser.add_argument("image_id")
    docs_parser.add_argument("output")
    docs_parser.set_defaults(func=command_package_docs)
    return parser


def main() -> int:
    """Entry point for the container-publishing CLI."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
