"""Unit tests for i2d_content_image_ocr delegations."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Ensure scripts directory is on PYTHONPATH so local imports resolve
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_SCRIPTS_DIR))

import i2d_content_image_ocr as image_ocr  # noqa: E402


def test_ocr_call_delegates_to_call_helper() -> None:
    """Low-level OCR call should delegate to the dedicated helper module."""
    pytesseract_module = object()
    image_obj = object()

    with patch(
        "i2d_content_image_ocr._ocr_call_helper.call_ocr",
        return_value="text",
    ) as helper_mock:
        result = image_ocr._ocr_call(
            pytesseract_module,
            image_obj,
            timeout=9,
            config="--psm 6",
            lang="eng",
        )

    assert result == "text"
    helper_mock.assert_called_once_with(
        pytesseract_module,
        image_obj,
        timeout=9,
        config="--psm 6",
        lang="eng",
    )


def test_build_ok_response_delegates_to_output_helper() -> None:
    """Successful OCR response formatting should delegate to the output helper."""
    with patch(
        "i2d_content_image_ocr._ocr_output.build_ok_response",
        return_value=("content", "ocr", "ok"),
    ) as helper_mock:
        result = image_ocr._build_ok_response("facts", "text")

    assert result == ("content", "ocr", "ok")
    helper_mock.assert_called_once_with("facts", "text")


def test_build_empty_response_delegates_to_output_helper() -> None:
    """Empty OCR response formatting should delegate to the output helper."""
    with patch(
        "i2d_content_image_ocr._ocr_output.build_empty_response",
        return_value=("content", "ocr", "empty"),
    ) as helper_mock:
        result = image_ocr._build_empty_response(file_facts="facts", timed_out=True)

    assert result == ("content", "ocr", "empty")
    helper_mock.assert_called_once_with("facts", timed_out=True)


def test_build_error_response_delegates_to_output_helper() -> None:
    """Error OCR response formatting should delegate to the output helper."""
    with patch(
        "i2d_content_image_ocr._ocr_output.build_error_response",
        return_value=("content", "ocr", "error"),
    ) as helper_mock:
        result = image_ocr._build_error_response("facts", "boom")

    assert result == ("content", "ocr", "error")
    helper_mock.assert_called_once_with("facts", "boom")


def test_extract_image_ocr_delegates_importerror_branch_to_cli_helper(
    tmp_path: Path,
) -> None:
    """ImportError branch should delegate CLI fallback to helper module."""
    image = tmp_path / "img.png"
    image.write_bytes(b"fake")

    builtin_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        """TODO: add docstring for fake_import."""
        if name in {"PIL", "pytesseract"}:
            raise ImportError("missing")
        return builtin_import(name, *args, **kwargs)  # type: ignore[arg-type]

    with patch("builtins.__import__", side_effect=fake_import):
        with patch(
            "i2d_content_image_ocr._ocr_cli.extract_image_ocr_cli",
            return_value=("body", "ocr-cli", "ok"),
        ) as cli_mock:
            result = image_ocr.extract_image_ocr(
                image,
                env_int_fn=lambda *_args, **_kwargs: 12,
                file_facts_fn=lambda _path: "facts",
                run_command_with_timeout_fn=lambda _cmd, _timeout: ("", ""),
            )

    assert result == ("body", "ocr-cli", "ok")
    args, kwargs = cli_mock.call_args
    assert args == (image,)
    assert kwargs["ocr_timeout_seconds"] == 12


def test_extract_image_ocr_delegates_pillow_branch_to_pil_helper(
    tmp_path: Path,
) -> None:
    """Pillow OCR branch should delegate execution to the dedicated PIL helper."""
    image = tmp_path / "img.png"
    image.write_bytes(b"fake")

    class _ImageModule:
        class Resampling:
            LANCZOS = 1

    builtin_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        """TODO: add docstring for fake_import."""
        if name == "PIL":

            class _PilPackage:
                Image = _ImageModule

            return _PilPackage
        if name == "pytesseract":
            return object()
        return builtin_import(name, *args, **kwargs)  # type: ignore[arg-type]

    with patch("builtins.__import__", side_effect=fake_import):
        with patch(
            "i2d_content_image_ocr._ocr_pil.extract_image_ocr_with_pil",
            return_value=("body", "ocr", "ok"),
        ) as pil_mock:
            result = image_ocr.extract_image_ocr(
                image,
                env_int_fn=lambda *_args, **_kwargs: 12,
                file_facts_fn=lambda _path: "facts",
                run_command_with_timeout_fn=lambda _cmd, _timeout: ("", ""),
            )

    assert result == ("body", "ocr", "ok")
    assert pil_mock.call_args.args == (image,)
    assert pil_mock.call_args.kwargs["image_module"] is _ImageModule


def test_extract_image_ocr_uses_scoring_helper_for_candidates(tmp_path: Path) -> None:
    """Enhanced OCR pass should call scoring helper when ranking candidates."""
    image = tmp_path / "img.png"
    image.write_bytes(b"fake")

    class _ImageCtx:
        width = 100
        height = 100

        def __enter__(self) -> "_ImageCtx":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def convert(self, _mode: str) -> "_ImageCtx":
            """TODO: add docstring for convert."""
            return self

        def filter(self, _flt: object) -> "_ImageCtx":
            """TODO: add docstring for filter."""
            return self

        def resize(
            self, _size: tuple[int, int], resample: object | None = None
        ) -> "_ImageCtx":
            """TODO: add docstring for resize."""
            return self

    class _ImageModule:
        class Resampling:
            LANCZOS = 1

        @staticmethod
        def open(_path: Path) -> _ImageCtx:
            """TODO: add docstring for open."""
            return _ImageCtx()

    class _ImageOpsModule:
        @staticmethod
        def grayscale(img: _ImageCtx) -> _ImageCtx:
            """TODO: add docstring for grayscale."""
            return img

        @staticmethod
        def autocontrast(img: _ImageCtx) -> _ImageCtx:
            """TODO: add docstring for autocontrast."""
            return img

    class _ImageFilterModule:
        class MedianFilter:
            def __init__(self, size: int) -> None:
                self.size = size

    class _PytesseractModule:
        calls = 0

        @staticmethod
        def image_to_string(_img: object, **_kwargs: object) -> str:
            """TODO: add docstring for image_to_string."""
            _PytesseractModule.calls += 1
            if _PytesseractModule.calls == 1:
                return ""
            if _PytesseractModule.calls == 2:
                return "a b"
            if _PytesseractModule.calls == 3:
                return "alpha beta"
            return "x"

    builtin_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        """TODO: add docstring for fake_import."""
        if name == "PIL":

            class _PilPackage:
                Image = _ImageModule
                ImageOps = _ImageOpsModule
                ImageFilter = _ImageFilterModule

            return _PilPackage
        if name == "pytesseract":
            return _PytesseractModule
        if name == "pillow_heif":
            raise ImportError("missing")
        return builtin_import(name, *args, **kwargs)  # type: ignore[arg-type]

    with patch("builtins.__import__", side_effect=fake_import):
        with patch(
            "i2d_content_image_ocr._ocr_scoring.score_ocr_candidate",
            side_effect=lambda text: (len(text), len(text)),
        ) as score_mock:
            _content, engine, status = image_ocr.extract_image_ocr(
                image,
                env_int_fn=lambda *_args, **_kwargs: 12,
                file_facts_fn=lambda _path: "facts",
                run_command_with_timeout_fn=lambda _cmd, _timeout: ("", ""),
            )

    assert score_mock.call_count >= 2
    assert engine == "ocr"
    assert status == "ok"


def test_extract_image_ocr_delegates_enhanced_pass_to_helper(tmp_path: Path) -> None:
    """When first OCR pass is empty, enhanced OCR helper should be called."""
    image = tmp_path / "img.png"
    image.write_bytes(b"fake")

    class _ImageCtx:
        width = 100
        height = 100

        def __enter__(self) -> "_ImageCtx":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def convert(self, _mode: str) -> "_ImageCtx":
            """TODO: add docstring for convert."""
            return self

    class _ImageModule:
        class Resampling:
            LANCZOS = 1

        @staticmethod
        def open(_path: Path) -> _ImageCtx:
            """TODO: add docstring for open."""
            return _ImageCtx()

    class _ImageOpsModule:
        @staticmethod
        def grayscale(img: _ImageCtx) -> _ImageCtx:
            """TODO: add docstring for grayscale."""
            return img

        @staticmethod
        def autocontrast(img: _ImageCtx) -> _ImageCtx:
            """TODO: add docstring for autocontrast."""
            return img

    class _ImageFilterModule:
        class MedianFilter:
            def __init__(self, size: int) -> None:
                self.size = size

    class _PytesseractModule:
        @staticmethod
        def image_to_string(_img: object, **_kwargs: object) -> str:
            """TODO: add docstring for image_to_string."""
            return ""

    builtin_import = __import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        """TODO: add docstring for fake_import."""
        if name == "PIL":

            class _PilPackage:
                Image = _ImageModule
                ImageOps = _ImageOpsModule
                ImageFilter = _ImageFilterModule

            return _PilPackage
        if name == "pytesseract":
            return _PytesseractModule
        if name == "pillow_heif":
            raise ImportError("missing")
        return builtin_import(name, *args, **kwargs)  # type: ignore[arg-type]

    with patch("builtins.__import__", side_effect=fake_import):
        with patch(
            "i2d_content_image_ocr_pil._ocr_enhance.run_enhanced_ocr_passes",
            return_value="enhanced text",
        ) as enhance_mock:
            content, engine, status = image_ocr.extract_image_ocr(
                image,
                env_int_fn=lambda *_args, **_kwargs: 12,
                file_facts_fn=lambda _path: "facts",
                run_command_with_timeout_fn=lambda _cmd, _timeout: ("", ""),
            )

    enhance_mock.assert_called_once()
    assert engine == "ocr"
    assert status == "ok"
    assert "enhanced text" in content
