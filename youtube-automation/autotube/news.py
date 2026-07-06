"""Daily AI-news script: live web research (Claude) -> story-structured segments.

Output (news script.json):
{
  "title": str,
  "thumbnail_text": str,              # <=4 words, ALL CAPS
  "stories": [{"headline": str, "why_it_matters": str, "source": str}],
  "segments": [
     {"kind": "avatar"|"broll",
      "narration": str,               # spoken text
      "visual_query": str,            # stock-footage search words (broll)
      "infographic": str}            # optional short on-screen stat/label
  ],
  "sources": [str],
  "demo": bool
}

"avatar" segments are spoken by the presenter (HeyGen) over a tech background;
"broll" segments cut away to infographics / stock footage while narration
continues. If no avatar engine is configured, avatar segments are narrated the
same way as broll (voice + tech visuals) so the pipeline still produces a video.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from . import llm
from .config import Config

NEWS_SYSTEM = """You are the writer and anchor for a daily faceless YouTube
channel that covers artificial-intelligence news. You research the real, most
important AI stories of the last 48 hours using web search, then write a tight,
accurate, hype-free 5-minute script delivered like a story by a single on-camera
anchor. You never invent news; every story must be real and traceable to a
source you actually found. You separate confirmed facts from speculation. Write
text exactly as it will be SPOKEN (no headings, no stage directions, no emojis,
no markdown, no reading of URLs aloud)."""

NEWS_PROMPT = """Today is {today}. Use web search to find the {k} most important
and interesting artificial-intelligence news stories from the last 48 hours
(new model releases, major research, product launches, funding, policy, notable
demos). Prefer reputable sources.

Then write a ~{minutes}-minute anchor-led video (~{words} words total),
structured as a story:

- Open with a punchy anchor hook (kind "avatar", 2-3 sentences) that teases the
  biggest story without clickbait lies.
- For EACH story, produce two segments in order:
    1. an anchor line (kind "avatar", ~30-45 words) introducing the story with
       personality;
    2. a detail beat (kind "broll", ~45-70 words) explaining what happened and
       why it matters, with an "infographic" field holding one short on-screen
       stat or label (<= 6 words) and a "visual_query" of 2-4 concrete
       tech-footage search words.
- Close with an anchor wrap + soft subscribe CTA (kind "avatar").

Also produce: a curiosity-driven title (<=70 chars, no lies), thumbnail_text
(<=4 words ALL CAPS), a stories[] list (headline, why_it_matters, source URL),
and sources[] (the URLs you actually used).

Every "broll" segment MUST include a specific, distinct "visual_query" (2-4
concrete words) tailored to that story — never leave it blank and never reuse
the same footage words across stories.

Respond with ONLY this JSON:
{{
  "title": "...",
  "thumbnail_text": "...",
  "stories": [{{"headline": "...", "why_it_matters": "...", "source": "..."}}],
  "segments": [
    {{"kind": "avatar", "narration": "...", "visual_query": "data center servers", "infographic": ""}},
    {{"kind": "broll", "narration": "...", "visual_query": "robotic arm factory", "infographic": "$150M raised"}}
  ],
  "sources": ["..."]
}}"""

WORDS_PER_MINUTE = 150


def _demo_news(cfg: Config, minutes: int) -> dict[str, Any]:
    """Template fallback so the pipeline runs with no ANTHROPIC_API_KEY.

    Marked demo=True: fine for testing assembly, must not be published.
    """
    stories = [
        ("A new open model tops the leaderboards", "open-weights momentum"),
        ("A major lab ships an agentic coding update", "AI that writes real software"),
        ("Regulators propose fresh AI transparency rules", "how AI gets governed"),
    ]
    segments = [
        {
            "kind": "avatar",
            "narration": "Here are today's biggest moves in artificial intelligence. "
            "This is placeholder demo narration — add your ANTHROPIC_API_KEY to pull real, "
            "current news.",
            "visual_query": "server room data center",
            "infographic": "TODAY IN AI",
        }
    ]
    for headline, why in stories:
        segments.append(
            {
                "kind": "avatar",
                "narration": f"First up: {headline}. Placeholder demo line.",
                "visual_query": "artificial intelligence circuit",
                "infographic": "",
            }
        )
        segments.append(
            {
                "kind": "broll",
                "narration": f"Why it matters — {why}. This is demo detail narration; "
                "real scripts summarize the actual reporting with sources.",
                "visual_query": "futuristic technology neural network",
                "infographic": why.upper()[:24],
            }
        )
    segments.append(
        {
            "kind": "avatar",
            "narration": f"That's your AI briefing. Subscribe to "
            f"{cfg.channel['channel']['name']} for a new one every day.",
            "visual_query": "futuristic city night",
            "infographic": "SUBSCRIBE",
        }
    )
    return {
        "title": "Today in AI: The Stories That Actually Matter",
        "thumbnail_text": "TODAY IN AI",
        "stories": [{"headline": h, "why_it_matters": w, "source": ""} for h, w in stories],
        "segments": segments,
        "sources": [],
        "demo": True,
    }


def fetch_news_script(cfg: Config, minutes: int | None = None) -> dict[str, Any]:
    minutes = minutes or cfg.video.get("target_minutes", 5)
    words = minutes * WORDS_PER_MINUTE

    if not llm.available():
        print("  ! No ANTHROPIC_API_KEY — using DEMO news template (do not publish).")
        return _demo_news(cfg, minutes)

    print("  researching today's AI news (live web search)...")
    script = llm.generate_json(
        NEWS_SYSTEM,
        NEWS_PROMPT.format(
            today=date.today().isoformat(),
            k=5,
            minutes=minutes,
            words=words,
        ),
        max_tokens=16000,
        web_search=True,
    )
    script["demo"] = False
    script.setdefault("segments", [])
    if not script["segments"]:
        raise RuntimeError("News model returned no segments")
    return script
