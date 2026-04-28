"""Deterministic fallback summarizer – no external API required."""
from __future__ import annotations

from collections import defaultdict

from src.collectors.base import NewsItem


def summarize(
    twitter_items: list[NewsItem],
    github_items: list[NewsItem],
    ai_items: list[NewsItem],
) -> dict[str, str]:
    """
    Returns a dict mapping section name → markdown text block.
    Each block is a bulleted list of items with title, link and short description.
    """
    sections: dict[str, str] = {}

    if twitter_items:
        sections["Twitter / Social"] = _render_section(twitter_items)

    if github_items:
        sections["GitHub Trending"] = _render_section(github_items)

    if ai_items:
        # Group AI items by source feed
        by_source: dict[str, list[NewsItem]] = defaultdict(list)
        for item in ai_items:
            by_source[item.source].append(item)

        parts: list[str] = []
        for source, items in by_source.items():
            parts.append(f"**{source}**\n\n{_render_section(items)}")
        sections["AI News"] = "\n\n".join(parts)

    return sections


def _render_section(items: list[NewsItem]) -> str:
    lines: list[str] = []
    for item in items:
        line = f"- **[{item.title}]({item.url})**"
        if item.description:
            line += f"\n  {item.description}"
        lines.append(line)
    return "\n".join(lines)
