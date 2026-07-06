"""Video assembly with ffmpeg: scene clips + narration + music + captions."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from . import ff
from .config import ASSETS_DIR, Config


def _normalize_scene(
    clip: Path, dur: float, res: tuple[int, int], fps: int, out: Path
) -> Path:
    """Loop/trim a raw clip to the scene duration at uniform encode settings."""
    w, h = res
    ff.run(
        ["-stream_loop", "-1", "-i", str(clip),
         "-t", f"{dur:.3f}",
         "-vf",
         f"scale={w}:{h}:force_original_aspect_ratio=increase,"
         f"crop={w}:{h},fps={fps},setsar=1",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-pix_fmt", "yuv420p", str(out)]
    )
    return out


def _concat(files: list[Path], out: Path, workdir: Path, audio: bool = False) -> Path:
    listfile = workdir / f"concat_{'a' if audio else 'v'}.txt"
    listfile.write_text(
        "\n".join(f"file '{f.resolve()}'" for f in files), encoding="utf-8"
    )
    args = ["-f", "concat", "-safe", "0", "-i", str(listfile)]
    if audio:
        args += ["-c:a", "aac", "-b:a", "192k", str(out)]
    else:
        args += ["-c", "copy", str(out)]
    ff.run(args)
    return out


def _pick_music(seed: str) -> Path | None:
    music_dir = ASSETS_DIR / "music"
    tracks = sorted(
        p for p in music_dir.glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg")
    )
    if not tracks:
        return None
    idx = int(hashlib.md5(seed.encode()).hexdigest()[:6], 16) % len(tracks)
    return tracks[idx]


def assemble(
    segments: list[dict[str, Any]],   # tts output (audio + duration per segment)
    clips: list[Path],                # one normalized-source clip per segment
    cfg: Config,
    workdir: Path,
    out: Path,
    ass_path: Path | None = None,
    portrait: bool = False,
) -> Path:
    section = cfg.shorts if portrait else cfg.video
    res = tuple(section["resolution"])
    fps = cfg.video.get("fps", 30)

    print("  normalizing scene clips...")
    norm = [
        _normalize_scene(clip, seg["duration"], res, fps, workdir / f"norm_{i:03d}.mp4")
        for i, (clip, seg) in enumerate(zip(clips, segments))
    ]

    print("  concatenating video and narration...")
    video = _concat(norm, workdir / "video_concat.mp4", workdir)
    narration = _concat(
        [s["audio"] for s in segments], workdir / "narration.m4a", workdir, audio=True
    )

    music = None
    if section.get("background_music", cfg.video.get("background_music")):
        music = _pick_music(out.stem)
        if music is None:
            print("  (no tracks in assets/music — skipping background music)")

    burn = bool(ass_path) and section.get("burn_captions", True)

    inputs = ["-i", str(video), "-i", str(narration)]
    filters = []
    if music:
        inputs = ["-i", str(video), "-i", str(narration), "-stream_loop", "-1",
                  "-i", str(music)]
        vol = cfg.video.get("music_volume_db", -24)
        filters.append(f"[2:a]volume={vol}dB[m]")
        filters.append("[1:a][m]amix=inputs=2:duration=first:dropout_transition=3[aout]")
        amap = "[aout]"
    else:
        amap = "1:a"

    if burn:
        # subtitles filter needs a filename; run from the workdir to dodge escaping
        filters.append(f"[0:v]subtitles={ass_path.name}[vout]")
        vmap = "[vout]"
    else:
        vmap = "0:v"

    print("  final mux (captions/music)...")
    args = [*inputs]
    if filters:
        args += ["-filter_complex", ";".join(filters)]
    args += ["-map", vmap, "-map", amap,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", "-shortest", str(out)]
    ff.run(args, cwd=ass_path.parent if burn else None)
    return out


def grab_frame(video: Path, t: float, out: Path) -> Path:
    ff.run(["-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(out)])
    return out
