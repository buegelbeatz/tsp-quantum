from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "container_publish.py"


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )


def test_validate_accepts_basic_config(tmp_path: Path) -> None:
    """TODO: add docstring for test_validate_accepts_basic_config."""
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    config = tmp_path / "container-publish.yaml"
    config.write_text(
        "\n".join(
            [
                "enabled: true",
                "defaults:",
                "  description: Demo image",
                "images:",
                "  - id: app",
                "    image: ghcr.io/example/demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run("validate", str(config), str(tmp_path), cwd=tmp_path)

    payload = json.loads(result.stdout)
    assert payload["schema"] == "container_publish_config_v1"
    assert payload["images"] == ["app"]


def test_matrix_resolves_defaults_and_docs_image(tmp_path: Path) -> None:
    """TODO: add docstring for test_matrix_resolves_defaults_and_docs_image."""
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    config = tmp_path / "container-publish.yaml"
    config.write_text(
        "\n".join(
            [
                "enabled: true",
                "defaults:",
                "  description: Demo image",
                "  platforms:",
                "    - linux/amd64",
                "images:",
                "  - id: app",
                "    image: ghcr.io/example/demo",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run("matrix", str(config), str(tmp_path), cwd=tmp_path)

    payload = json.loads(result.stdout)
    entry = payload["include"][0]
    assert entry["docs_image"] == "ghcr.io/example/demo-docs"
    assert entry["platforms"] == "linux/amd64"
    assert entry["dockerfile"] == "Dockerfile"


def test_package_docs_creates_bundle_with_manifest(tmp_path: Path) -> None:
    """TODO: add docstring for test_package_docs_creates_bundle_with_manifest."""
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "usage.md").write_text("Usage\n", encoding="utf-8")
    config = tmp_path / "container-publish.yaml"
    config.write_text(
        "\n".join(
            [
                "enabled: true",
                "defaults:",
                "  description: Demo image",
                "images:",
                "  - id: app",
                "    image: ghcr.io/example/demo",
                "    docs_globs:",
                "      - README.md",
                "      - docs/**",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "bundle.tar.gz"

    _run("package-docs", str(config), str(tmp_path), "app", str(output), cwd=tmp_path)

    with tarfile.open(output, "r:gz") as archive:
        names = sorted(archive.getnames())
        assert names == ["README.md", "docs/usage.md", "manifest.json"]
        manifest = json.loads(
            archive.extractfile("manifest.json").read().decode("utf-8")
        )
    assert manifest["schema"] == "container_publish_docs_bundle_v1"
    assert manifest["docs_image"] == "ghcr.io/example/demo-docs"


def test_validate_returns_empty_when_disabled(tmp_path: Path) -> None:
    """TODO: add docstring for test_validate_returns_empty_when_disabled."""
    (tmp_path / "container-publish.yaml").write_text(
        "enabled: false\n", encoding="utf-8"
    )

    result = _run(
        "validate",
        str(tmp_path / "container-publish.yaml"),
        str(tmp_path),
        cwd=tmp_path,
    )

    payload = json.loads(result.stdout)
    assert payload["image_count"] == 0
    assert payload["images"] == []
