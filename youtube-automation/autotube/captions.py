"""Caption generation: SRT sidecar (uploaded to YouTube) + styled ASS (burned in)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

MAX_WORDS = 5
MAX_SECONDS = 3.0


def _chunks(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten per-segment word timings into caption chunks with absolute times."""
    chunks = []
    offset = 0.0
    for seg in segments:
        cur: list[dict[str, Any]] = []
        for w in seg["words"]:
            if cur and (
                len(cur) >= MAX_WORDS or w["end"] - cur[0]["start"] > MAX_SECONDS
            ):
                chunks.append(
                    {
                        "text": " ".join(x["word"] for x in cur),
                        "start": offset + cur[0]["start"],
                        "end": offset + cur[-1]["end"],
                    }
                )
                cur = []
            cur.append(w)
        if cur:
            chunks.append(
                {
                    "text": " ".join(x["word"] for x in cur),
                    "start": offset + cur[0]["start"],
                    "end": offset + cur[-1]["end"],
                }
            )
        offset += seg["duration"]
    return chunks


def _srt_time(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def _ass_time(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_srt(segments: list[dict[str, Any]], path: Path) -> Path:
    lines = []
    for i, c in enumerate(_chunks(segments), 1):
        lines += [str(i), f"{_srt_time(c['start'])} --> {_srt_time(c['end'])}", c["text"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,0,0,1,{outline},2,{align},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(
    segments: list[dict[str, Any]],
    path: Path,
    resolution: tuple[int, int],
    shorts: bool = False,
) -> Path:
    w, h = resolution
    size = int(h * (0.055 if not shorts else 0.042))
    header = ASS_HEADER.format(
        w=w,
        h=h,
        size=size,
        outline=max(2, size // 14),
        align=2 if not shorts else 5,  # bottom-center for long, middle for shorts
        margin_v=int(h * 0.06),
    )
    events = [
        f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},Cap,,0,0,0,,"
        + c["text"].replace("\n", " ").upper()
        for c in _chunks(segments)
    ]
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path
