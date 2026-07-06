"""Persistent channel state: topics used, videos produced, upload log.

Keeps the pipeline from repeating topics and records what has been published —
important both for content variety and for YouTube's inauthentic-content
policy (repetitious uploads risk demonetization).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from .config import STATE_DIR

STATE_FILE = STATE_DIR / "history.json"


def _load() -> dict[str, Any]:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"topics_used": [], "produced": [], "uploads": []}


def _save(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "video"


def topics_used() -> list[str]:
    return _load()["topics_used"]


def mark_topic_used(topic: str) -> None:
    state = _load()
    if topic not in state["topics_used"]:
        state["topics_used"].append(topic)
    _save(state)


def record_produced(entry: dict[str, Any]) -> None:
    state = _load()
    entry["produced_at"] = datetime.now(timezone.utc).isoformat()
    state["produced"].append(entry)
    _save(state)


def record_upload(entry: dict[str, Any]) -> None:
    state = _load()
    entry["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    state["uploads"].append(entry)
    _save(state)


def upload_count() -> int:
    return len(_load()["uploads"])
