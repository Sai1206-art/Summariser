"""Voiceover generation with word-level timings.

Providers:
  edge        — Microsoft Edge neural voices via edge-tts. Free, no key, and
                returns word boundaries (exact caption timing).
  elevenlabs  — premium voices (ELEVENLABS_API_KEY); timings are estimated.
  silent      — offline placeholder audio for pipeline testing only.

Each script segment (hook / scene / cta) becomes one audio file so the
assembler can match visuals to narration exactly.

Returns a list of dicts:
  {"audio": Path, "duration": float, "words": [{"word","start","end"}]}
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import requests

from . import ff
from .config import Config, env

WORDS_PER_SECOND = 2.6  # for estimated timings


def _estimate_words(text: str, total: float) -> list[dict[str, Any]]:
    words = text.split()
    if not words:
        return []
    per = total / len(words)
    return [
        {"word": w, "start": round(i * per, 3), "end": round((i + 1) * per, 3)}
        for i, w in enumerate(words)
    ]


# ---------------------------------------------------------------------------
# edge-tts (default, free)
# ---------------------------------------------------------------------------

async def _edge_segment(
    text: str, voice: str, rate: str, pitch: str, out: Path
) -> list[dict[str, Any]]:
    import edge_tts

    tts = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    words: list[dict[str, Any]] = []
    with open(out, "wb") as f:
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append(
                    {
                        "word": chunk["text"],
                        "start": round(chunk["offset"] / 1e7, 3),
                        "end": round((chunk["offset"] + chunk["duration"]) / 1e7, 3),
                    }
                )
    return words


def _edge(segments: list[str], cfg: Config, workdir: Path) -> list[dict[str, Any]]:
    voice = cfg.voice_name()
    rate = cfg.voice.get("rate", "+0%")
    pitch = cfg.voice.get("pitch", "+0Hz")

    async def _all() -> list[list[dict[str, Any]]]:
        results = []
        for i, text in enumerate(segments):
            out = workdir / f"seg_{i:03d}.mp3"
            for attempt in range(3):
                try:
                    words = await _edge_segment(text, voice, rate, pitch, out)
                    results.append(words)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 * (attempt + 1))
        return results

    all_words = asyncio.run(_all())
    out = []
    for i, (text, words) in enumerate(zip(segments, all_words)):
        path = workdir / f"seg_{i:03d}.mp3"
        dur = ff.duration(path)
        out.append(
            {"audio": path, "duration": dur, "words": words or _estimate_words(text, dur)}
        )
    return out


# ---------------------------------------------------------------------------
# ElevenLabs (optional premium)
# ---------------------------------------------------------------------------

def _elevenlabs(segments: list[str], cfg: Config, workdir: Path) -> list[dict[str, Any]]:
    key = env("ELEVENLABS_API_KEY")
    voice_id = env("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    out = []
    for i, text in enumerate(segments):
        path = workdir / f"seg_{i:03d}.mp3"
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": key},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=120,
        )
        r.raise_for_status()
        path.write_bytes(r.content)
        dur = ff.duration(path)
        out.append({"audio": path, "duration": dur, "words": _estimate_words(text, dur)})
    return out


# ---------------------------------------------------------------------------
# Silent placeholder (offline testing only)
# ---------------------------------------------------------------------------

def _silent(segments: list[str], cfg: Config, workdir: Path) -> list[dict[str, Any]]:
    out = []
    for i, text in enumerate(segments):
        dur = max(1.5, len(text.split()) / WORDS_PER_SECOND)
        path = workdir / f"seg_{i:03d}.mp3"
        ff.run(
            ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
             "-t", f"{dur:.2f}", "-q:a", "9", str(path)]
        )
        out.append({"audio": path, "duration": dur, "words": _estimate_words(text, dur)})
    return out


PROVIDERS = {"edge": _edge, "elevenlabs": _elevenlabs, "silent": _silent}


def synthesize(
    segments: list[str], cfg: Config, workdir: Path, provider: str | None = None
) -> list[dict[str, Any]]:
    workdir.mkdir(parents=True, exist_ok=True)
    name = provider or cfg.voice.get("provider", "edge")
    if name == "elevenlabs" and not env("ELEVENLABS_API_KEY"):
        print("  ! ELEVENLABS_API_KEY missing — falling back to edge-tts")
        name = "edge"
    if name not in PROVIDERS:
        raise SystemExit(f"Unknown TTS provider '{name}'. Options: {', '.join(PROVIDERS)}")
    if name == "silent":
        print("  ! Using SILENT placeholder audio (testing only — do not publish).")
    return PROVIDERS[name](segments, cfg, workdir)
