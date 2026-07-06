"""Claude API wrapper for script/idea/metadata generation.

Uses the official ``anthropic`` SDK when ANTHROPIC_API_KEY is set; otherwise
returns None so callers fall back to demo-mode templates. All calls stream
(long outputs) and use adaptive thinking.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .config import env

DEFAULT_MODEL = "claude-opus-4-8"


def available() -> bool:
    if not env("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def _client():
    import anthropic

    return anthropic.Anthropic()


def _extract_json(text: str) -> Any:
    """Parse the first JSON object/array in a model response."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    if start == -1:
        raise ValueError(f"No JSON found in model response: {text[:200]}")
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(text[start:])
    return obj


def generate_json(
    system: str, prompt: str, max_tokens: int = 16000, web_search: bool = False
) -> Any:
    """One streamed Messages call returning parsed JSON. Raises on failure.

    When web_search=True, Claude may run live web searches (server-side tool)
    before answering — used to pull real, current news.
    """
    import anthropic

    client = _client()
    model = env("AUTOTUBE_MODEL", DEFAULT_MODEL)
    kwargs: dict[str, Any] = dict(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if web_search:
        kwargs["tools"] = [
            {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}
        ]
    try:
        with client.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()
    except anthropic.APIStatusError as e:
        # Older models don't support the newer web_search tool version; retry.
        if web_search and e.status_code == 400:
            kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
            with client.messages.stream(**kwargs) as stream:
                message = stream.get_final_message()
        else:
            raise RuntimeError(f"Claude API error ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Could not reach the Claude API: {e}") from e

    text = "".join(b.text for b in getattr(message, "content", []) if b.type == "text")
    return _extract_json(text)
