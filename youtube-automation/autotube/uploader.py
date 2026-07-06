"""YouTube Data API v3: OAuth, resumable upload, thumbnail, captions, scheduling.

Setup (one time):
  1. Google Cloud Console -> new project -> enable "YouTube Data API v3".
  2. OAuth consent screen -> External -> add yourself as a test user.
  3. Credentials -> Create OAuth client ID -> Desktop app -> download JSON to
     the path in YOUTUBE_CLIENT_SECRETS (default ./client_secret.json).
  4. python run.py auth   (opens browser once, stores a refresh token)

Quota: an upload costs ~1600 units of the default 10,000/day — roughly 6
uploads/day maximum on default quota.
"""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import ROOT, Config, env

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _token_path() -> Path:
    return (ROOT / env("YOUTUBE_TOKEN_FILE", "./state/youtube_token.json")).resolve()


def _secrets_path() -> Path:
    return (ROOT / env("YOUTUBE_CLIENT_SECRETS", "./client_secret.json")).resolve()


def authenticate(force: bool = False):
    """Return authorized credentials, running the browser OAuth flow if needed."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_file = _token_path()
    creds = None
    if token_file.exists() and not force:
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid or force:
        secrets = _secrets_path()
        if not secrets.exists():
            raise SystemExit(
                f"OAuth client secrets not found at {secrets}.\n"
                "Download them from Google Cloud Console (see autotube/uploader.py docstring)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _service():
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=authenticate(), cache_discovery=False)


def next_slot(cfg: Config) -> str:
    """Next configured schedule time (RFC3339 UTC) at least 1h in the future."""
    times = cfg.upload.get("schedule_times", ["15:00"])
    now = datetime.now().astimezone()
    for day in range(0, 8):
        date = (now + timedelta(days=day)).date()
        for t in sorted(times):
            hh, mm = (int(x) for x in t.split(":"))
            candidate = datetime.combine(date, time(hh, mm)).astimezone()
            if candidate > now + timedelta(hours=1):
                return candidate.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise RuntimeError("No schedule slot found")


def upload_video(
    video: Path,
    meta: dict[str, Any],
    cfg: Config,
    thumbnail: Path | None = None,
    srt: Path | None = None,
    privacy: str | None = None,
    publish_at: str | None = None,
) -> str:
    from googleapiclient.http import MediaFileUpload

    yt = _service()
    status: dict[str, Any] = {
        "privacyStatus": "private" if publish_at else (privacy or cfg.upload.get("privacy", "private")),
        "selfDeclaredMadeForKids": bool(cfg.upload.get("made_for_kids", False)),
    }
    if publish_at:
        status["publishAt"] = publish_at
    if cfg.compliance.get("ai_disclosure", True):
        # Realistic AI-generated/altered content must be declared in Studio;
        # the API exposes this progressively — set it in Studio if unavailable.
        status["containsSyntheticMedia"] = True

    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "27"),
            "defaultLanguage": cfg.channel["channel"].get("language", "en"),
            "defaultAudioLanguage": cfg.channel["channel"].get("language", "en"),
        },
        "status": status,
    }

    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    print(f"  uploading {video.name} ...")
    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            print(f"    {int(progress.progress() * 100)}%")
    video_id = response["id"]
    print(f"  video id: {video_id}")

    if thumbnail and thumbnail.exists():
        try:
            yt.thumbnails().set(
                videoId=video_id, media_body=MediaFileUpload(str(thumbnail))
            ).execute()
            print("  thumbnail set")
        except Exception as e:  # thumbnail perms need a verified channel
            print(f"  ! thumbnail failed (verify your channel at youtube.com/verify): {e}")

    if srt and srt.exists():
        try:
            yt.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "language": cfg.channel["channel"].get("language", "en"),
                        "name": "English",
                        "isDraft": False,
                    }
                },
                media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream"),
            ).execute()
            print("  captions uploaded")
        except Exception as e:
            print(f"  ! caption upload failed: {e}")

    return video_id


def load_production(folder: Path) -> dict[str, Any]:
    with open(folder / "metadata.json", encoding="utf-8") as f:
        return json.load(f)
