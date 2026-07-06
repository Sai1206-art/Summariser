"""Topic ideation: fresh, non-repeating video topics for the configured niche."""

from __future__ import annotations

from . import llm, state
from .config import Config

IDEA_SYSTEM = """You are the content strategist for a faceless YouTube channel.
You generate specific, high-click-potential video topics that are original —
not generic listicles — and that a narrator can cover compellingly with stock
footage. Topics must be factual/educational (no medical, legal or financial
advice framing; no fear-mongering)."""

IDEA_PROMPT = """Channel niche: {label}
Audience: {audience}
Tone: {tone}

Topics already covered (do NOT repeat or closely paraphrase these):
{used}

Generate {n} new video topic ideas for this channel. For each, give a working
angle that makes it fresh (a question, a twist, a surprising fact to lead with).

Respond with ONLY a JSON array:
[{{"topic": "...", "angle": "..."}}]"""


def next_topic(cfg: Config, topic_override: str | None = None) -> dict[str, str]:
    """Pick the next unused topic (LLM-generated, else niche seed bank)."""
    if topic_override:
        return {"topic": topic_override, "angle": ""}

    used = set(state.topics_used())

    if llm.available():
        ideas = llm.generate_json(
            IDEA_SYSTEM,
            IDEA_PROMPT.format(
                label=cfg.niche["label"],
                audience=cfg.niche["audience"],
                tone=cfg.niche["tone"],
                used="\n".join(f"- {t}" for t in sorted(used)) or "(none yet)",
                n=5,
            ),
            max_tokens=4000,
        )
        for idea in ideas:
            if idea.get("topic") and idea["topic"] not in used:
                return {"topic": idea["topic"], "angle": idea.get("angle", "")}

    # Demo-mode fallback: walk the niche seed bank
    for seed in cfg.niche.get("topic_seeds", []):
        if seed not in used:
            return {"topic": seed, "angle": ""}

    raise SystemExit(
        "All seed topics used. Set ANTHROPIC_API_KEY for unlimited fresh ideas, "
        "or pass --topic \"your topic\"."
    )
