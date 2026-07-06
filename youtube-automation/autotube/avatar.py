"""HeyGen talking-avatar integration (licensed realistic presenters).

Setup:
  1. Create an account at heygen.com (~$29/mo Creator plan fits daily use).
  2. Settings -> API -> copy your API key into HEYGEN_API_KEY.
  3. `python run.py avatars`  to list avatar_id / voice_id options, then set
     them in config/channel.yaml under `avatar:`.

If HEYGEN_API_KEY is not set, the pipeline falls back to voice-over-visuals
(edge-tts narration over tech b-roll) so it still produces a video.

API (stable v2):
  POST https://api.heygen.com/v2/video/generate      -> data.video_id
  GET  https://api.heygen.com/v1/video_status.get     -> data.status / video_url
  GET  https://api.heygen.com/v2/avatars              -> data.avatars[]
  GET  https://api.heygen.com/v2/voices               -> data.voices[]
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests

from .config import Config, env

BASE = "https://api.heygen.com"


def available() -> bool:
    return bool(env("HEYGEN_API_KEY"))


def _headers() -> dict[str, str]:
    return {"X-Api-Key": env("HEYGEN_API_KEY"), "Content-Type": "application/json"}


def _avatar_cfg(cfg: Config) -> dict[str, Any]:
    return cfg.channel.get("avatar", {})


# ---------------------------------------------------------------------------
# Discovery helpers (for `python run.py avatars`)
# ---------------------------------------------------------------------------

def list_avatars(limit: int = 40) -> list[dict[str, str]]:
    r = requests.get(f"{BASE}/v2/avatars", headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json().get("data", {})
    avatars = data.get("avatars", data.get("avatar_list", []))
    out = []
    for a in avatars[:limit]:
        out.append(
            {
                "avatar_id": a.get("avatar_id") or a.get("id", ""),
                "name": a.get("avatar_name") or a.get("name", ""),
                "gender": a.get("gender", ""),
            }
        )
    return out


def list_voices(limit: int = 40) -> list[dict[str, str]]:
    r = requests.get(f"{BASE}/v2/voices", headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json().get("data", {})
    voices = data.get("voices", data.get("voice_list", []))
    out = []
    for v in voices[:limit]:
        out.append(
            {
                "voice_id": v.get("voice_id") or v.get("id", ""),
                "name": v.get("name", ""),
                "language": v.get("language", ""),
                "gender": v.get("gender", ""),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _background(cfg: Config) -> dict[str, Any]:
    bg = _avatar_cfg(cfg).get("background", "#0a0e2a")
    if isinstance(bg, str) and bg.startswith("http"):
        return {"type": "image", "url": bg}
    return {"type": "color", "value": bg}


def _generate(text: str, cfg: Config, res: tuple[int, int]) -> str:
    av = _avatar_cfg(cfg)
    avatar_id = av.get("avatar_id")
    voice_id = av.get("voice_id")
    if not avatar_id or not voice_id:
        raise SystemExit(
            "avatar.avatar_id / avatar.voice_id are not set in channel.yaml. "
            "Run `python run.py avatars` to list options."
        )
    w, h = res
    body = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": av.get("avatar_style", "normal"),
                },
                "voice": {
                    "type": "text",
                    "input_text": text,
                    "voice_id": voice_id,
                    "speed": float(av.get("speed", 1.0)),
                },
                "background": _background(cfg),
            }
        ],
        "dimension": {"width": w, "height": h},
    }
    r = requests.post(
        f"{BASE}/v2/video/generate", headers=_headers(), json=body, timeout=60
    )
    if r.status_code >= 400:
        raise RuntimeError(f"HeyGen generate failed ({r.status_code}): {r.text[:300]}")
    payload = r.json()
    data = payload.get("data") or {}
    video_id = data.get("video_id") or payload.get("video_id")
    if not video_id:
        raise RuntimeError(f"HeyGen returned no video_id: {payload}")
    return video_id


def _wait(video_id: str, timeout: int = 900) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = requests.get(
            f"{BASE}/v1/video_status.get",
            headers=_headers(),
            params={"video_id": video_id},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        status = data.get("status")
        if status in ("completed", "success"):
            url = data.get("video_url") or data.get("video_url_caption")
            if not url:
                raise RuntimeError(f"HeyGen completed but returned no URL: {data}")
            return url
        if status in ("failed", "error"):
            raise RuntimeError(f"HeyGen render failed: {data.get('error') or data}")
        time.sleep(10)
    raise TimeoutError(f"HeyGen video {video_id} not ready after {timeout}s")


def _download(url: str, out: Path) -> Path:
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return out


def render_segment(text: str, cfg: Config, res: tuple[int, int], out: Path) -> Path:
    """Render one avatar-spoken segment to an mp4 (video + audio)."""
    video_id = _generate(text, cfg, res)
    url = _wait(video_id)
    return _download(url, out)
