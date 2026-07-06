"""Script generation: structured, retention-optimized narration scripts.

Output schema (script.json):
{
  "title": str,           # working title (SEO pass happens in metadata.py)
  "hook": str,            # first 15 seconds — decides retention
  "scenes": [ {"narration": str, "visual_query": str} ],
  "cta": str,             # soft subscribe ask near the end
  "thumbnail_text": str,  # <= 4 punchy words
  "demo": bool            # true when template-generated (do not publish)
}
"""

from __future__ import annotations

from typing import Any

from . import llm
from .config import Config

WORDS_PER_MINUTE = 155  # edge-tts at +8% rate

SCRIPT_SYSTEM = """You are a professional YouTube scriptwriter for a faceless
narration channel. You write original, deeply researched, conversational
scripts that hold attention: strong hooks, open loops, pattern interrupts every
30-40 seconds, concrete examples and numbers, short punchy sentences a narrator
can read aloud naturally. Never invent facts; if something is contested, say so.
No medical/legal/financial advice. Write text exactly as it should be SPOKEN
(no headings, no stage directions, no emojis, no markdown)."""

SCRIPT_PROMPT = """Write a complete {length_desc} YouTube narration script.

Channel niche: {label}
Audience: {audience}
Tone: {tone}
Topic: {topic}
Angle: {angle}

Requirements:
- Total narration length: about {words} words.
- Open with a hook (2-4 sentences) that creates an information gap in the
  first 10 seconds. Never start with "Have you ever wondered".
- Split the narration into {min_scenes}-{max_scenes} scenes. A scene is a
  continuous narration beat of roughly 40-80 words.
- For each scene provide "visual_query": 2-4 concrete stock-footage search
  words matching the scene (style guide: {visual_style}).
- End with a one-sentence soft call to action referencing the channel.
- Also produce a working title (curiosity-driven, under 70 characters, no
  clickbait lies) and thumbnail_text (max 4 words, ALL CAPS).

Respond with ONLY this JSON:
{{
  "title": "...",
  "hook": "...",
  "scenes": [{{"narration": "...", "visual_query": "..."}}],
  "cta": "...",
  "thumbnail_text": "..."
}}"""


def _demo_script(cfg: Config, topic: str, words: int) -> dict[str, Any]:
    """Template fallback so the pipeline runs with zero API keys.

    Clearly marked demo=True: fine for testing the pipeline end-to-end, but
    templated narration must not be published (quality + policy risk).
    """
    styles = [s.strip() for s in cfg.niche["visual_style"].split(",")]
    n_scenes = max(4, min(12, words // 60))
    scenes = []
    beats = [
        f"Let's start with what {topic} actually is, because most explanations get it wrong.",
        f"Researchers who have studied {topic} keep running into the same surprising pattern.",
        f"Here is where {topic} shows up in your everyday life, usually without you noticing.",
        f"There is a common myth about {topic} that simply does not survive the evidence.",
        f"The mechanism behind {topic} is simpler than it sounds, and it changes how you see it.",
        f"Once you understand {topic}, you start to notice it everywhere.",
        f"There is also a practical side to {topic} that almost nobody talks about.",
        f"So what does this mean for you? More than you might think.",
    ]
    for i in range(n_scenes):
        scenes.append(
            {
                "narration": beats[i % len(beats)]
                + " This is placeholder demo narration. Add your ANTHROPIC_API_KEY "
                "to generate a real, original script before publishing.",
                "visual_query": styles[i % len(styles)],
            }
        )
    return {
        "title": topic.title(),
        "hook": f"There's something about {topic} that almost everyone gets wrong. "
        "And once you see it, you can't unsee it.",
        "scenes": scenes,
        "cta": f"If this changed how you think, subscribe to {cfg.channel['channel']['name']} — "
        "we publish one of these every week.",
        "thumbnail_text": " ".join(
            [w for w in topic.split() if w.lower() not in
             {"the", "a", "an", "of", "in", "on", "to", "and", "why", "how"}][:3]
            or topic.split()[:3]
        ).upper(),
        "demo": True,
    }


def write_script(
    cfg: Config, topic: str, angle: str = "", fmt: str = "long"
) -> dict[str, Any]:
    if fmt == "short":
        words = int(cfg.shorts.get("target_seconds", 45) / 60 * WORDS_PER_MINUTE)
        length_desc = f"~{cfg.shorts.get('target_seconds', 45)}-second YouTube Short"
        min_scenes, max_scenes = 3, 5
    else:
        minutes = cfg.video.get("target_minutes", 8)
        words = minutes * WORDS_PER_MINUTE
        length_desc = f"{minutes}-minute"
        min_scenes, max_scenes = max(6, minutes), minutes * 2

    if not llm.available():
        print("  ! No ANTHROPIC_API_KEY — using DEMO template script (do not publish).")
        return _demo_script(cfg, topic, words)

    script = llm.generate_json(
        SCRIPT_SYSTEM,
        SCRIPT_PROMPT.format(
            length_desc=length_desc,
            label=cfg.niche["label"],
            audience=cfg.niche["audience"],
            tone=cfg.niche["tone"],
            topic=topic,
            angle=angle or "(pick the most compelling angle)",
            words=words,
            min_scenes=min_scenes,
            max_scenes=max_scenes,
            visual_style=cfg.niche["visual_style"],
        ),
    )
    script["demo"] = False
    script.setdefault("scenes", [])
    if not script["scenes"]:
        raise RuntimeError("Model returned a script with no scenes")
    return script


def full_narration(script: dict[str, Any]) -> str:
    parts = [script.get("hook", "")]
    parts += [s["narration"] for s in script["scenes"]]
    parts.append(script.get("cta", ""))
    return "\n\n".join(p for p in parts if p)
