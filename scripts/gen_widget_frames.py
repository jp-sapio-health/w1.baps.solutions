#!/usr/bin/env python3
"""Regenerate the floating-widget animation frames (SVG sources + rasterized PNGs).

Single source of truth for the widget art so the look is reproducible instead of hand-edited.
Renders to transparent PNGs with headless Chrome (no extra Python deps).

    python scripts/gen_widget_frames.py

States produced in assets/widget/states/:
  idle_0..5         a single resting horizontal line (static)
  listening_0..11   a 9-bar waveform at 12 amplitude levels (live-driven by mic RMS)
  processing_0..3   four rotating dots
  reject_0..2       a red ✕ the waveform morphs into when a result is gated
"""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "assets" / "widget" / "states"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

WHITE = "#FFFFFF"
RED = "#FF453A"  # Apple system red — the reject cue

# Listening waveform geometry. Wider bar spacing (step 14) so the waveform reads as longer and
# fills more of the pill; symmetric amplitude profile peaks in the centre.
N_BARS = 9
BAR_W = 6
STEP = 14
PROFILE = [0.42, 0.76, 1.0, 0.60, 0.96, 0.60, 1.0, 0.76, 0.42]
CANVAS_W, CANVAS_H = 256, 96
CY = CANVAS_H / 2.0
SPAN = (N_BARS - 1) * STEP
X0 = (CANVAS_W - SPAN) / 2.0  # centre the bar group horizontally

_FILTER = (
    '<defs><filter id="g" x="-60%" y="-60%" width="220%" height="220%">'
    '<feGaussianBlur stdDeviation="1.5" result="b"/><feMerge>'
    '<feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>'
    '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
)


def _svg(body: str, w: int = CANVAS_W, h: int = CANVAS_H) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">{_FILTER}<g filter="url(#g)">{body}</g></svg>'
    )


def _bar(x: float, height: float, fill: str = WHITE) -> str:
    y = CY - height / 2.0
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{BAR_W}" height="{height:.1f}" rx="3" fill="{fill}"/>'


def listening_frame(level: int) -> str:
    """Bar heights for amplitude level 0..11 (0 = near-rest, 11 = loud)."""
    amp = level / 11.0
    bars = []
    for i, p in enumerate(PROFILE):
        height = 7.0 + 44.0 * amp * p
        bars.append(_bar(X0 + i * STEP, height))
    return _svg("".join(bars))


def _idle_line() -> str:
    w = 86
    x = (CANVAS_W - w) / 2.0
    y = CY - 3
    return _svg(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w}" height="6" rx="3" fill="{WHITE}"/>')


def processing_frame(step: int) -> str:
    # Four dots around a small circle; the lit dot rotates.
    dots = []
    r = 16
    for i in range(4):
        ang = math.pi / 2 * i
        cx = CANVAS_W / 2.0 + r * math.cos(ang)
        cy = CY + r * math.sin(ang)
        opacity = 1.0 if i == step else 0.3
        dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{WHITE}" opacity="{opacity}"/>')
    return _svg("".join(dots))


def reject_frame(step: int) -> str:
    # A red ✕ that scales in over three frames (the waveform "animates to ✕").
    scale = (step + 1) / 3.0
    half = 16 * scale
    cx, cy = CANVAS_W / 2.0, CY
    stroke = (
        f'<line x1="{cx-half:.1f}" y1="{cy-half:.1f}" x2="{cx+half:.1f}" y2="{cy+half:.1f}" '
        f'stroke="{RED}" stroke-width="6" stroke-linecap="round"/>'
        f'<line x1="{cx-half:.1f}" y1="{cy+half:.1f}" x2="{cx+half:.1f}" y2="{cy-half:.1f}" '
        f'stroke="{RED}" stroke-width="6" stroke-linecap="round"/>'
    )
    return _svg(stroke)


def _rasterize(svg_path: Path, png_path: Path, w: int, h: int) -> None:
    subprocess.run(
        [
            CHROME, "--headless", "--disable-gpu", "--force-device-scale-factor=2",
            "--default-background-color=00000000", f"--window-size={w},{h}",
            f"--screenshot={png_path}", f"file://{svg_path}",
        ],
        check=True, capture_output=True,
    )


def main() -> int:
    if not Path(CHROME).exists():
        print(f"Chrome not found at {CHROME}; cannot rasterize.", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)

    frames: dict[str, str] = {}
    for i in range(6):
        frames[f"idle_{i}"] = _idle_line()
    for i in range(12):
        frames[f"listening_{i}"] = listening_frame(i)
    for i in range(4):
        frames[f"processing_{i}"] = processing_frame(i)
    for i in range(3):
        frames[f"reject_{i}"] = reject_frame(i)

    for name, svg in frames.items():
        svg_path = OUT / f"{name}.svg"
        png_path = OUT / f"{name}.png"
        svg_path.write_text(svg, encoding="utf-8")
        _rasterize(svg_path, png_path, CANVAS_W, CANVAS_H)
    print(f"Generated {len(frames)} widget frames in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
