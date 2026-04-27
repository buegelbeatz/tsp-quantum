"""Unit tests for image vision provider routing."""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_vision  # noqa: E402
from i2d_vision import classify_image  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._bytes = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        """TODO: add docstring for read."""
        return self._bytes

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None


def test_classify_image_uses_copilot_first(tmp_path: Path) -> None:
    """TODO: add docstring for test_classify_image_uses_copilot_first."""
    image = tmp_path / "img.png"
    image.write_bytes(b"png-bytes")

    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_ORDER": "copilot,digital,claude",
            "GH_TOKEN": "gh-test",
            "GITHUB_MODELS_VISION_API_URL": "https://models.inference.ai.azure.com/chat/completions",
            "GITHUB_MODELS_VISION_MODEL": "gpt-4o-mini",
            "DIGITAL_TEAM_VISION_API_URL": "https://fallback.example/chat/completions",
            "DIGITAL_TEAM_VISION_API_KEY": "fallback-key",
            "CLAUDE_TOKEN": "claude-key",
        },
        clear=False,
    ):
        with patch(
            "urllib.request.urlopen",
            return_value=_FakeResponse(
                {"choices": [{"message": {"content": "ok-copilot"}}]}
            ),
        ) as mock_urlopen:
            content, engine, status = classify_image(image)

    assert status == "ok"
    assert engine == "vision-copilot"
    assert "ok-copilot" in content
    assert mock_urlopen.call_count == 1


def test_classify_image_falls_back_to_digital(tmp_path: Path) -> None:
    """TODO: add docstring for test_classify_image_falls_back_to_digital."""
    image = tmp_path / "img.png"
    image.write_bytes(b"png-bytes")

    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_ORDER": "copilot,digital",
            "GH_TOKEN": "gh-test",
            "GITHUB_MODELS_VISION_API_URL": "https://models.inference.ai.azure.com/chat/completions",
            "GITHUB_MODELS_VISION_MODEL": "gpt-4o-mini",
            "DIGITAL_TEAM_VISION_API_URL": "https://fallback.example/chat/completions",
            "DIGITAL_TEAM_VISION_API_KEY": "fallback-key",
            "DIGITAL_TEAM_VISION_MODEL": "gpt-4o-mini",
        },
        clear=False,
    ):
        responses = [
            urllib.error.URLError("copilot failure"),
            _FakeResponse({"choices": [{"message": {"content": "ok-digital"}}]}),
        ]

        def _side_effect(*_args, **_kwargs):
            result = responses.pop(0)
            if isinstance(result, urllib.error.URLError):
                raise result
            return result

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            content, engine, status = classify_image(image)

    assert status == "ok"
    assert engine == "vision-digital"
    assert "ok-digital" in content


def test_classify_image_falls_back_to_claude(tmp_path: Path) -> None:
    """TODO: add docstring for test_classify_image_falls_back_to_claude."""
    image = tmp_path / "img.png"
    image.write_bytes(b"png-bytes")

    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_ORDER": "copilot,digital,claude",
            "GH_TOKEN": "gh-test",
            "GITHUB_MODELS_VISION_API_URL": "https://models.inference.ai.azure.com/chat/completions",
            "DIGITAL_TEAM_VISION_API_URL": "https://fallback.example/chat/completions",
            "DIGITAL_TEAM_VISION_API_KEY": "fallback-key",
            "CLAUDE_TOKEN": "claude-key",
            "CLAUDE_VISION_API_URL": "https://api.anthropic.com/v1/messages",
            "CLAUDE_VISION_MODEL": "claude-3-5-sonnet-latest",
        },
        clear=False,
    ):
        responses = [
            urllib.error.URLError("copilot failure"),
            urllib.error.URLError("digital failure"),
            _FakeResponse({"content": [{"type": "text", "text": "ok-claude"}]}),
        ]

        def _side_effect(*_args, **_kwargs):
            result = responses.pop(0)
            if isinstance(result, urllib.error.URLError):
                raise result
            return result

        with patch("urllib.request.urlopen", side_effect=_side_effect):
            content, engine, status = classify_image(image)

    assert status == "ok"
    assert engine == "vision-claude"
    assert "ok-claude" in content


def test_classify_image_returns_unavailable_without_credentials(tmp_path: Path) -> None:
    """TODO: add docstring for test_classify_image_returns_unavailable_without_credentials."""
    image = tmp_path / "img.png"
    image.write_bytes(b"png-bytes")

    with patch.dict(
        "os.environ", {"VISION_PROVIDER_ORDER": "copilot,digital,claude"}, clear=True
    ):
        content, engine, status = classify_image(image)

    assert engine == "vision"
    assert status == "unavailable"
    assert "unavailable" in content.lower()


def test_classify_image_converts_heic_to_png_payload(tmp_path: Path) -> None:
    """HEIC inputs should be converted to PNG payload for OpenAI-compatible providers."""
    image = tmp_path / "img.heic"
    image.write_bytes(b"fake-heic")

    with patch.dict(
        "os.environ",
        {
            "VISION_PROVIDER_ORDER": "copilot",
            "GH_TOKEN": "gh-test",
            "GITHUB_MODELS_VISION_API_URL": "https://models.inference.ai.azure.com/chat/completions",
            "GITHUB_MODELS_VISION_MODEL": "gpt-4o-mini",
        },
        clear=False,
    ):
        with patch(
            "i2d_vision._prepare_image_payload", return_value=("ZmFrZQ==", "image/png")
        ):
            with patch(
                "urllib.request.urlopen",
                return_value=_FakeResponse(
                    {"choices": [{"message": {"content": "ok-copilot"}}]}
                ),
            ) as mock_urlopen:
                content, engine, status = classify_image(image)

    assert status == "ok"
    assert engine == "vision-copilot"
    assert "ok-copilot" in content

    request = mock_urlopen.call_args.args[0]
    body = json.loads(request.data.decode("utf-8"))
    assert body["messages"][0]["content"][1]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )


def test_classify_image_delegates_to_flow_helper(tmp_path: Path) -> None:
    """TODO: add docstring for test_classify_image_delegates_to_flow_helper."""
    image = tmp_path / "img.png"
    image.write_bytes(b"png-bytes")
    expected = SimpleNamespace(result=True)

    with patch(
        "i2d_vision._vision_flow.classify_image",
        return_value=expected,
    ) as flow_mock:
        result = i2d_vision.classify_image(image)

    assert result is expected
    assert flow_mock.call_count == 1
    args, kwargs = flow_mock.call_args
    assert args == (image,)
    assert kwargs["prepare_image_payload_fn"] is i2d_vision._prepare_image_payload
    assert kwargs["vision_provider_order_fn"] is i2d_vision._vision_provider_order
    assert kwargs["call_openai_compatible_fn"] is i2d_vision._call_openai_compatible
    assert kwargs["call_claude_fn"] is i2d_vision._call_claude
    assert kwargs["default_github_models_url"] == i2d_vision._DEFAULT_GITHUB_MODELS_URL
    assert (
        kwargs["default_github_models_model"] == i2d_vision._DEFAULT_GITHUB_MODELS_MODEL
    )
    assert kwargs["default_claude_api_url"] == i2d_vision._DEFAULT_CLAUDE_API_URL
    assert kwargs["default_claude_model"] == i2d_vision._DEFAULT_CLAUDE_MODEL


def test_call_openai_compatible_delegates_to_api_helper() -> None:
    """Ensure wrapper delegates OpenAI-compatible call to vision API helper."""
    with patch(
        "i2d_vision._vision_api.call_openai_compatible",
        return_value="ok",
    ) as api_mock:
        result = i2d_vision._call_openai_compatible(
            endpoint="https://example.com/chat",
            api_key="k",
            model="m",
            image_b64="abc",
            media_type="image/png",
        )

    assert result == "ok"
    args, kwargs = api_mock.call_args
    assert args == ("https://example.com/chat", "k", "m", "abc", "image/png")
    assert kwargs["image_prompt_fn"] is i2d_vision._image_prompt
