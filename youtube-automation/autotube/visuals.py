"""Per-scene stock footage: Pexels -> Pixabay -> generated gradient fallback.

Both stock APIs are free. Every clip is trimmed/looped to its scene's narration
duration by the assembler; here we just fetch the best-matching source clip.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import requests

from . import ff
from .config import Config, env


def _download(url: str, out: Path) -> Path:
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return out


def _pexels(query: str, portrait: bool, used: set[str]) -> dict[str, Any] | None:
    key = env("PEXELS_API_KEY")
    if not key:
        return None
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": key},
        params={
            "query": query,
            "per_page": 12,
            "orientation": "portrait" if portrait else "landscape",
        },
        timeout=30,
    )
    if r.status_code != 200:
        return None
    for video in r.json().get("videos", []):
        vid = f"pexels-{video['id']}"
        if vid in used:
            continue
        files = sorted(
            (f for f in video.get("video_files", []) if f.get("width")),
            key=lambda f: f["width"] * f.get("height", 0),
            reverse=True,
        )
        # smallest file that still covers 1080p on the long edge
        pick = None
        for f in files:
            if max(f["width"], f.get("height", 0)) >= 1920:
                pick = f
            else:
                break
        pick = pick or (files[0] if files else None)
        if pick:
            return {"id": vid, "url": pick["link"]}
    return None


def _pixabay(query: str, portrait: bool, used: set[str]) -> dict[str, Any] | None:
    key = env("PIXABAY_API_KEY")
    if not key:
        return None
    r = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": key, "q": query, "per_page": 12},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    for hit in r.json().get("hits", []):
        vid = f"pixabay-{hit['id']}"
        if vid in used:
            continue
        best = hit.get("videos", {}).get("large") or hit.get("videos", {}).get("medium")
        if best and best.get("url"):
            return {"id": vid, "url": best["url"]}
    return None


def _gradient_clip(query: str, duration: float, res: tuple[int, int], out: Path) -> Path:
    """Zero-key fallback: animated gradient so the pipeline always completes."""
    seed = int(hashlib.md5(query.encode()).hexdigest()[:6], 16)
    palette = [
        ("0d1321", "1d2d44"), ("1a1423", "3d2c8d"), ("07231c", "1b4332"),
        ("2b2d42", "8d99ae"), ("10002b", "3c096c"), ("001219", "005f73"),
    ]
    c0, c1 = palette[seed % len(palette)]
    w, h = res
    ff.run(
        ["-f", "lavfi",
         "-i", f"gradients=s={w}x{h}:c0=0x{c0}:c1=0x{c1}:speed=0.02",
         "-t", f"{duration:.2f}", "-r", "30",
         "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out)]
    )
    return out


def fetch_scene_clips(
    scenes: list[dict[str, Any]],
    durations: list[float],
    cfg: Config,
    workdir: Path,
    portrait: bool = False,
    used: set[str] | None = None,
) -> list[Path]:
    """Return one local video file per scene (>= narration duration where stock).

    Pass a shared ``used`` set across calls to avoid repeating the same clip.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    res = tuple(cfg.shorts["resolution"] if portrait else cfg.video["resolution"])
    if used is None:
        used = set()
    clips: list[Path] = []
    have_keys = bool(env("PEXELS_API_KEY") or env("PIXABAY_API_KEY"))
    if not have_keys:
        print("  ! No PEXELS_API_KEY/PIXABAY_API_KEY — using generated gradient visuals.")

    for i, (scene, dur) in enumerate(zip(scenes, durations)):
        query = scene.get("visual_query") or cfg.niche["visual_style"].split(",")[0]
        out = workdir / f"clip_{i:03d}.mp4"
        result = None
        if have_keys:
            try:
                result = _pexels(query, portrait, used) or _pixabay(query, portrait, used)
            except requests.RequestException as e:
                print(f"  ! Stock API error for '{query}': {e}")
        if result:
            used.add(result["id"])
            try:
                _download(result["url"], out)
                clips.append(out)
                print(f"  clip {i + 1}/{len(scenes)}: {result['id']} ({query})")
                continue
            except requests.RequestException as e:
                print(f"  ! Download failed ({e}); generating fallback clip")
        _gradient_clip(query, dur + 0.5, res, out)
        clips.append(out)
    return clips
