"""Render PowerPoint slides to per-slide PNG screenshots.

Uses LibreOffice/soffice in headless mode and normalizes output names to
slide-001.png, slide-002.png, ... for deterministic downstream checks.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


CONTAINER_IMAGE = "docker.io/linuxserver/libreoffice:latest"


def _find_office_binary() -> str | None:
    """Return the first available headless office converter binary."""
    for candidate in ("soffice", "libreoffice"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _render_with_local_office(office_bin: str, input_pptx: Path, temp_dir: Path) -> None:
    """Render slides using a locally installed office binary."""
    cmd = [
        office_bin,
        "--headless",
        "--convert-to",
        "png",
        "--outdir",
        str(temp_dir),
        str(input_pptx),
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        output = (completed.stdout or "") + (completed.stderr or "")
        raise RuntimeError(f"slide screenshot export failed: {output.strip()}")


def _render_with_podman(input_pptx: Path, temp_dir: Path) -> None:
    """Render slides using a containerized LibreOffice fallback."""
    podman = shutil.which("podman")
    if podman is None:
        raise RuntimeError("LibreOffice not found and podman fallback is unavailable")

    work_input = temp_dir / "input.pptx"
    shutil.copy2(input_pptx, work_input)

    cmd = [
        podman,
        "run",
        "--rm",
        "-v",
        f"{temp_dir}:/work",
        CONTAINER_IMAGE,
        "/usr/bin/soffice",
        "--headless",
        "--convert-to",
        "png",
        "--outdir",
        "/work",
        "/work/input.pptx",
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        output = (completed.stdout or "") + (completed.stderr or "")
        raise RuntimeError(f"slide screenshot export failed (podman): {output.strip()}")


def _convert_pdf_with_local_office(office_bin: str, input_pptx: Path, temp_dir: Path) -> None:
    """Convert presentation to PDF using local office binary."""
    cmd = [
        office_bin,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(temp_dir),
        str(input_pptx),
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        output = (completed.stdout or "") + (completed.stderr or "")
        raise RuntimeError(f"pdf export failed: {output.strip()}")


def _convert_pdf_with_podman(input_pptx: Path, temp_dir: Path) -> None:
    """Convert presentation to PDF using containerized LibreOffice."""
    podman = shutil.which("podman")
    if podman is None:
        raise RuntimeError("PDF fallback failed: podman is unavailable")

    work_input = temp_dir / "input.pptx"
    shutil.copy2(input_pptx, work_input)
    cmd = [
        podman,
        "run",
        "--rm",
        "-v",
        f"{temp_dir}:/work",
        CONTAINER_IMAGE,
        "/usr/bin/soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        "/work",
        "/work/input.pptx",
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        output = (completed.stdout or "") + (completed.stderr or "")
        raise RuntimeError(f"pdf export failed (podman): {output.strip()}")


def _rasterize_pdf_with_ghostscript(pdf_path: Path, temp_dir: Path) -> list[Path]:
    """Render all PDF pages to PNG files using Ghostscript."""
    gs_bin = shutil.which("gs")
    if gs_bin is None:
        raise RuntimeError("Ghostscript not found for multipage screenshot fallback")

    pattern = temp_dir / "gs-slide-%03d.png"
    cmd = [
        gs_bin,
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=pngalpha",
        "-r160",
        f"-sOutputFile={pattern}",
        str(pdf_path),
    ]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        output = (completed.stdout or "") + (completed.stderr or "")
        raise RuntimeError(f"pdf rasterization failed: {output.strip()}")

    return sorted(temp_dir.glob("gs-slide-*.png"))


def render_slide_screenshots(input_pptx: Path, output_dir: Path) -> list[Path]:
    """Render all slides from input_pptx to numbered PNG files in output_dir."""
    if not input_pptx.exists():
        raise FileNotFoundError(f"Input presentation not found: {input_pptx}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("slide-*.png"):
        stale.unlink(missing_ok=True)

    with tempfile.TemporaryDirectory(prefix="ppt-screens-") as temp_raw:
        temp_dir = Path(temp_raw)
        office_bin = _find_office_binary()
        if office_bin is not None:
            _render_with_local_office(office_bin, input_pptx, temp_dir)
        else:
            _render_with_podman(input_pptx, temp_dir)

        generated = sorted(temp_dir.glob("*.png"))
        if len(generated) <= 1:
            for stale in temp_dir.glob("gs-slide-*.png"):
                stale.unlink(missing_ok=True)

            if office_bin is not None:
                _convert_pdf_with_local_office(office_bin, input_pptx, temp_dir)
            else:
                _convert_pdf_with_podman(input_pptx, temp_dir)

            pdf_candidates = sorted(temp_dir.glob("*.pdf"))
            if pdf_candidates:
                generated = _rasterize_pdf_with_ghostscript(pdf_candidates[0], temp_dir)

        if not generated:
            raise RuntimeError("No PNG screenshots were produced")

        exported: list[Path] = []
        for index, image in enumerate(generated, start=1):
            target = output_dir / f"slide-{index:03}.png"
            shutil.copy2(image, target)
            exported.append(target)

    return exported


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PPTX slides to PNG screenshots")
    parser.add_argument("--input", required=True, help="Path to input .pptx")
    parser.add_argument("--output-dir", required=True, help="Destination directory")
    args = parser.parse_args()

    input_pptx = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    screenshots = render_slide_screenshots(input_pptx, output_dir)
    print(
        json.dumps(
            {
                "status": "ok",
                "input": str(input_pptx),
                "output_dir": str(output_dir),
                "slides": len(screenshots),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
