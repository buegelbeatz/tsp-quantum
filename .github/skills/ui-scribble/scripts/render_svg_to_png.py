"""SVG-to-PNG rasterization wrapper for diagram rendering pipelines.

Purpose:
    Convert SVG diagram files to PNG format using Cairo.
    Provides standardized rasterization for documentation and report generation.

Security:
    Reads only SVG files from specified paths. Writes PNG output to configured destinations.
    CairoSVG processes local files only; no remote rendering.
"""

import sys
from pathlib import Path

import cairosvg  # type: ignore[import-untyped]


def render(svg_path: str, png_path: str):
    """TODO: add docstring for render."""
    cairosvg.svg2png(url=svg_path, write_to=png_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python render_svg_to_png.py input.svg output.png")
        sys.exit(1)

    svg_file = Path(sys.argv[1])
    png_file = Path(sys.argv[2])

    if not svg_file.exists():
        print(f"Input file not found: {svg_file}")
        sys.exit(1)

    render(str(svg_file), str(png_file))
    print(f"Rendered: {png_file}")
