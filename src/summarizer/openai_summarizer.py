"""OpenAI-compatible summarizer using chat completion API."""
from __future__ import annotations

import logging

import requests

from src import config
from src.collectors.base import NewsItem

logger = logging.getLogger(__name__)


def _system_prompt() -> str:
    return f"""\
You are a concise tech news editor.
You receive raw news items grouped by category and must write only the final
"關鍵重點" summary bullets for the day.

Language requirement:
- Write in {config.SUMMARY_LANGUAGE}.

Rules:
- Output exactly 3 bullet points.
- Each bullet must be one concise sentence.
- Focus on the most important developments across AI, software, markets, crypto, and world news when available.
- Do not invent facts not present in the source items.
- Do not add headings, numbering, or preamble.
- Start directly with "- ".
"""


def _items_to_text(label: str, items: list[NewsItem]) -> str:
    if not items:
        return ""
    lines = [f"### {label}"]
    for it in items:
        desc = it.description[:400] if it.description else ""
        lines.append(f"- [{it.title}]({it.url}): {desc}")
    return "\n".join(lines)


def _describe_exception(exc: Exception) -> str:
    parts = [f"{type(exc).__name__}: {exc!s}"]
    if exc.__cause__:
        parts.append(f"cause={type(exc.__cause__).__name__}: {exc.__cause__!r}")
    if exc.__context__ and exc.__context__ is not exc.__cause__:
        parts.append(f"context={type(exc.__context__).__name__}: {exc.__context__!r}")
    return " | ".join(parts)


def _client_kwargs() -> dict[str, str]:
    base_url = config.OPENAI_BASE_URL.rstrip("/") if config.OPENAI_BASE_URL else "https://api.openai.com/v1"
    return {"base_url": base_url}


def _preflight_openai(api_key: str) -> None:
    url = _client_kwargs()["base_url"].rstrip("/") + "/models"
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        logger.info(
            "OpenAI preflight GET %s -> status=%s content-type=%s",
            url,
            response.status_code,
            response.headers.get("content-type", ""),
        )
    except Exception as exc:
        logger.warning("OpenAI preflight failed: %s", _describe_exception(exc))


def summarize(
    twitter_items: list[NewsItem],
    github_items: list[NewsItem],
    ai_items: list[NewsItem],
) -> dict[str, str]:
    """
    Hybrid mode:
    - base sections come from the deterministic summarizer (stable links/metadata)
    - OpenAI only writes the final "關鍵重點" bullets
    """
    from src.summarizer import simple_summarizer

    base_sections = simple_summarizer.summarize(twitter_items, github_items, ai_items)

    try:
        from openai import OpenAI  # import here so missing package is not fatal
    except ImportError:
        logger.warning("openai package not installed; returning deterministic digest without key-points summary.")
        return base_sections

    parts: list[str] = []
    if twitter_items:
        parts.append(_items_to_text("Twitter / Social", twitter_items))
    if github_items:
        parts.append(_items_to_text("GitHub Trending", github_items))
    if ai_items:
        parts.append(_items_to_text("AI News", ai_items))

    if not parts:
        return base_sections

    user_message = "\n\n".join(parts)

    client = OpenAI(api_key=config.OPENAI_API_KEY, **_client_kwargs())

    logger.info("Calling OpenAI-compatible API (model=%s)…", config.OPENAI_MODEL)
    _preflight_openai(config.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        key_points = (response.choices[0].message.content or "").strip()
        if key_points:
            section_name = "關鍵重點" if config.SUMMARY_LANGUAGE.lower().startswith(("traditional chinese", "zh", "繁")) else "Key Takeaways"
            base_sections[section_name] = key_points
        return base_sections
    except Exception as exc:
        logger.warning("OpenAI API call failed: %s; returning deterministic digest without key-points summary.", _describe_exception(exc))
        return base_sections
