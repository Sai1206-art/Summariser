"""Thin ffmpeg helpers around the imageio-ffmpeg bundled binary."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def run(args: list[str], quiet: bool = True, cwd: str | Path | None = None) -> None:
    cmd = [FFMPEG, "-hide_banner", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.splitlines()[-15:])
        raise RuntimeError(f"ffmpeg failed:\n  {' '.join(cmd)}\n{tail}")
    if not quiet and proc.stderr:
        print(proc.stderr)


def duration(path: str | Path) -> float:
    """Media duration in seconds (parsed from ffmpeg, no ffprobe needed)."""
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    matches = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", proc.stderr)
    if not matches:
        raise RuntimeError(f"Could not determine duration of {path}")
    h, m, s = matches[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)
