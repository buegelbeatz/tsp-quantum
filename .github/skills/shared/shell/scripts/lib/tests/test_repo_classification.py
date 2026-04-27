"""Tests for repo-classification.sh shared library."""

from __future__ import annotations

import subprocess
from pathlib import Path


LIB_DIR = Path(__file__).resolve().parents[1]
REPO_CLASS = LIB_DIR / "repo-classification.sh"


def _run_bash(script: str) -> subprocess.CompletedProcess[str]:
    """Run bash script and return output + exit code."""
    return subprocess.run(
        ["bash", "-lc", script],
        check=False,
        text=True,
        capture_output=True,
    )


def _init_git_repo(path: Path) -> None:
    """Initialize a bare git repository."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        capture_output=True,
        check=True,
    )


def _add_and_commit(path: Path, file_list: list[str]) -> None:
    """Add files to git index and commit."""
    for file_path in file_list:
        full_path = path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text("")

    subprocess.run(
        ["git", "add"] + file_list,
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "test commit"],
        cwd=path,
        capture_output=True,
        check=True,
    )


class TestRepoClassificationLayer0:
    """Test Layer 0 classification (.digital-team/00-* tracked, .github untracked)."""

    def test_classify_layer_0(self, tmp_path: Path) -> None:
        """Layer 0 repo should be classified as layer-0."""
        _init_git_repo(tmp_path)

        # Create .github (not tracked)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "workflows").mkdir()
        (tmp_path / ".github" / "workflows" / "test.yml").write_text("test")

        # Create .digital-team/00-base (tracked)
        (tmp_path / ".digital-team").mkdir()
        (tmp_path / ".digital-team" / "00-base").mkdir()
        (tmp_path / ".digital-team" / "00-base" / "README.md").write_text("base layer")

        _add_and_commit(
            tmp_path,
            [".digital-team/00-base/README.md"],
        )

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode == 0
        assert result.stdout.strip() == "layer-0"


class TestRepoClassificationLayerN:
    """Test Layer N>0 classification (.digital-team/(01-99)-* tracked, .github untracked)."""

    def test_classify_layer_n(self, tmp_path: Path) -> None:
        """Layer N repo should be classified as layer-n."""
        _init_git_repo(tmp_path)

        # Create .github (not tracked)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "workflows").mkdir()
        (tmp_path / ".github" / "workflows" / "test.yml").write_text("test")

        # Create .digital-team/01-* (tracked)
        _add_and_commit(
            tmp_path,
            [".digital-team/01-digital-iot-team/README.md"],
        )

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode == 0
        assert result.stdout.strip() == "layer-n"


class TestRepoClassificationApp:
    """Test App classification (.digital-team untracked, .github tracked)."""

    def test_classify_app(self, tmp_path: Path) -> None:
        """App repo should be classified as app."""
        _init_git_repo(tmp_path)

        # Create .github (tracked)
        _add_and_commit(
            tmp_path,
            [".github/workflows/test.yml"],
        )

        # Create .digital-team/* (not tracked, already untracked in git)
        (tmp_path / ".digital-team").mkdir()
        (tmp_path / ".digital-team" / "00-app-layer").mkdir()
        (tmp_path / ".digital-team" / "00-app-layer" / "README.md").write_text("test")

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode == 0
        assert result.stdout.strip() == "app"


class TestRepoClassificationAmbiguous:
    """Test ambiguous state handling (hard-fail)."""

    def test_ambiguous_both_tracked(self, tmp_path: Path) -> None:
        """Repo with both .github and .digital-team tracked should hard-fail."""
        _init_git_repo(tmp_path)

        # Track both (ambiguous)
        _add_and_commit(
            tmp_path,
            [
                ".github/workflows/test.yml",
                ".digital-team/00-layer/README.md",
            ],
        )

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode != 0
        assert "Ambiguous" in result.stderr or "Ambiguous" in result.stdout

    def test_ambiguous_neither_github_tracked(self, tmp_path: Path) -> None:
        """Repo with neither .github tracked and multiple layer prefixes should hard-fail."""
        _init_git_repo(tmp_path)

        # Track both layer 0 and layer n (ambiguous)
        _add_and_commit(
            tmp_path,
            [
                ".digital-team/00-layer0/README.md",
                ".digital-team/01-layer1/README.md",
            ],
        )

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode != 0
        assert "Ambiguous" in result.stderr or "Ambiguous" in result.stdout

    def test_ambiguous_no_tracked_state(self, tmp_path: Path) -> None:
        """Repo with nothing tracked should hard-fail."""
        _init_git_repo(tmp_path)

        # Create initial commit (empty repo scenario)
        _add_and_commit(tmp_path, ["README.md"])

        # Remove all tracked files
        subprocess.run(
            ["git", "rm", "README.md"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "empty repo"],
            cwd=tmp_path,
            capture_output=True,
        )

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode != 0
        assert "Ambiguous" in result.stderr or "Ambiguous" in result.stdout


class TestRepoClassificationEdgeCases:
    """Test edge cases and robustness."""

    def test_classify_not_git_repo(self, tmp_path: Path) -> None:
        """Non-git directory should fail."""
        tmp_path.mkdir(exist_ok=True)

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode != 0
        assert "Not a git repository" in result.stderr

    def test_classify_repo_with_alias(self, tmp_path: Path) -> None:
        """get_repo_classification_mode alias should work."""
        _init_git_repo(tmp_path)

        # Layer 0
        (tmp_path / ".github").mkdir()
        _add_and_commit(
            tmp_path,
            [".digital-team/00-generic/README.md"],
        )

        result = _run_bash(
            f'source "{REPO_CLASS}" && get_repo_classification_mode "{tmp_path}"'
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "layer-0"


class TestRepoClassificationMultipleLayersN:
    """Test Layer N with multiple 01-99 prefixes."""

    def test_classify_layer_n_multiple_prefixes(self, tmp_path: Path) -> None:
        """Layer N with multiple 01-99 prefixes should still classify as layer-n."""
        _init_git_repo(tmp_path)

        # Create .github (not tracked)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "config.yml").write_text("config")

        # Create multiple .digital-team/0[1-9]* (tracked)
        _add_and_commit(
            tmp_path,
            [
                ".digital-team/01-iot/README.md",
                ".digital-team/02-platform/README.md",
            ],
        )

        result = _run_bash(f'source "{REPO_CLASS}" && classify_repo "{tmp_path}"')
        assert result.returncode == 0
        assert result.stdout.strip() == "layer-n"


class TestRuntimeRepoModeDetection:
    """Test filesystem-based runtime mode detection for app vs layer policy."""

    def test_detect_runtime_repo_mode_returns_app_for_source_repo(
        self, tmp_path: Path
    ) -> None:
        """Repos with source code outside .github should allow app-level runtime handling."""
        _init_git_repo(tmp_path)
        (tmp_path / ".github").mkdir()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

        result = _run_bash(
            f'source "{REPO_CLASS}" && detect_runtime_repo_mode "{tmp_path}"'
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "app"

    def test_detect_runtime_repo_mode_returns_layer_for_governance_repo(
        self, tmp_path: Path
    ) -> None:
        """Repos without app code should retain layer runtime handling."""
        _init_git_repo(tmp_path)
        (tmp_path / ".github" / "skills").mkdir(parents=True)
        (tmp_path / "README.md").write_text("layer repo\n", encoding="utf-8")

        result = _run_bash(
            f'source "{REPO_CLASS}" && detect_runtime_repo_mode "{tmp_path}"'
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "layer"
