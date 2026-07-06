"""SEO metadata: title, description (with chapters), tags."""

from __future__ import annotations

from typing import Any

from . import llm
from .config import Config

META_SYSTEM = """You are a YouTube SEO specialist. You write titles and
descriptions that rank in search and get clicks without lying. Titles under 70
characters, front-load the keyword, create curiosity. Descriptions: a 2-3
sentence summary rich in natural search keywords, then value bullets. Tags:
15-25 relevant terms, most specific first."""

META_PROMPT = """Video topic: {topic}
Working title: {title}
Niche: {label}
Hook: {hook}

Scene summaries (for chapter names):
{scenes}

Respond with ONLY this JSON:
{{
  "title": "final SEO title, <=70 chars",
  "description_intro": "2-3 sentence keyword-rich summary",
  "chapters": ["Intro", "..."],
  "tags": ["...", "..."]
}}"""


def _chapters_text(chapters: list[str], durations: list[float]) -> str:
    """YouTube chapter timestamps (needs >=3 chapters, first at 0:00)."""
    lines, t = [], 0.0
    for name, dur in zip(chapters, durations):
        m, s = divmod(int(t), 60)
        h, m = divmod(m, 60)
        stamp = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        lines.append(f"{stamp} {name}")
        t += dur
    return "\n".join(lines)


def build_metadata(
    cfg: Config,
    topic: str,
    script: dict[str, Any],
    durations: list[float],
    fmt: str = "long",
) -> dict[str, Any]:
    ch = cfg.channel["channel"]
    hashtags = " ".join(cfg.niche.get("hashtags", []))

    if llm.available() and not script.get("demo"):
        meta = llm.generate_json(
            META_SYSTEM,
            META_PROMPT.format(
                topic=topic,
                title=script.get("title", topic),
                label=cfg.niche["label"],
                hook=script.get("hook", ""),
                scenes="\n".join(
                    f"{i + 1}. {s['narration'][:110]}"
                    for i, s in enumerate(script["scenes"])
                ),
            ),
            max_tokens=4000,
        )
    else:
        meta = {
            "title": script.get("title", topic.title()),
            "description_intro": f"{script.get('hook', '')}",
            "chapters": ["Intro"]
            + [f"Part {i + 1}" for i in range(len(script["scenes"]))]
            + ["Wrap-up"],
            "tags": [w for w in topic.lower().split() if len(w) > 3]
            + [t.lstrip("#") for t in cfg.niche.get("hashtags", [])],
        }

    parts = [meta["description_intro"], ""]
    if fmt == "long" and len(meta.get("chapters", [])) >= 3 and len(durations) >= 3:
        chapters = meta["chapters"][: len(durations)]
        parts += ["Chapters:", _chapters_text(chapters, durations), ""]
    parts.append(f"Subscribe to {ch['name']} ({ch.get('handle', '')}) for more.")
    if cfg.compliance.get("ai_disclosure", True):
        parts += ["", "Narration voiced with AI text-to-speech."]
    parts += ["", hashtags]

    title = meta["title"][:100]
    if fmt == "short" and "#shorts" not in title.lower():
        title = (title[:91] + " #Shorts") if len(title) > 91 else title + " #Shorts"

    # tag list must stay under YouTube's 500-char total limit
    tags, total = [], 0
    for t in meta.get("tags", []):
        if total + len(t) + 2 > 480:
            break
        tags.append(t)
        total += len(t) + 2

    return {
        "title": title,
        "description": "\n".join(parts)[:4900],
        "tags": tags,
        "category_id": cfg.upload.get("category_id", "27"),
    }
