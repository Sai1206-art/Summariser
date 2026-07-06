"""Configuration loading: channel.yaml + niches.yaml + .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"
STATE_DIR = ROOT / "state"
ASSETS_DIR = ROOT / "assets"

load_dotenv(ROOT / ".env")


@dataclass
class Config:
    channel: dict[str, Any]
    niche_key: str
    niche: dict[str, Any]

    @property
    def video(self) -> dict[str, Any]:
        return self.channel.get("video", {})

    @property
    def shorts(self) -> dict[str, Any]:
        return self.channel.get("shorts", {})

    @property
    def voice(self) -> dict[str, Any]:
        return self.channel.get("voice", {})

    @property
    def upload(self) -> dict[str, Any]:
        return self.channel.get("upload", {})

    @property
    def compliance(self) -> dict[str, Any]:
        return self.channel.get("compliance", {})

    def voice_name(self) -> str:
        return self.voice.get("override_voice") or self.niche.get(
            "voice", "en-US-ChristopherNeural"
        )


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def load_config(niche_override: str | None = None) -> Config:
    with open(CONFIG_DIR / "channel.yaml", encoding="utf-8") as f:
        channel = yaml.safe_load(f)
    with open(CONFIG_DIR / "niches.yaml", encoding="utf-8") as f:
        niches = yaml.safe_load(f)

    niche_key = niche_override or channel.get("niche", "psychology")
    if niche_key not in niches:
        raise SystemExit(
            f"Unknown niche '{niche_key}'. Available: {', '.join(sorted(niches))}"
        )
    return Config(channel=channel, niche_key=niche_key, niche=niches[niche_key])
