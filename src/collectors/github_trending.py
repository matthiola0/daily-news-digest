"""GitHub Trending scraper.

Scrapes https://github.com/trending[/language]?since=daily|weekly|monthly
using requests + BeautifulSoup.  No API key required.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from src import config
from src.collectors.base import NewsItem

logger = logging.getLogger(__name__)

TRENDING_BASE = "https://github.com/trending"


@dataclass
class TrendingRepo:
    name: str          # e.g. "owner/repo"
    url: str
    description: str
    language: str
    stars_today: str
    total_stars: str


def _scrape_trending(url: str) -> list[TrendingRepo]:
    logger.info("Scraping GitHub Trending: %s", url)
    try:
        resp = requests.get(
            url,
            headers=config.REQUEST_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch GitHub Trending: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    repos: list[TrendingRepo] = []

    for article in soup.select("article.Box-row"):
        try:
            # Repo name (owner/repo)
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            path = h2["href"].lstrip("/")
            repo_url = f"https://github.com/{path}"

            # Description
            desc_el = article.select_one("p")
            description = desc_el.get_text(strip=True) if desc_el else ""

            # Language
            lang_el = article.select_one("[itemprop='programmingLanguage']")
            language = lang_el.get_text(strip=True) if lang_el else ""

            # Stars today
            stars_today_el = article.select_one("span.d-inline-block.float-sm-right")
            stars_today = stars_today_el.get_text(strip=True) if stars_today_el else ""

            # Total stars
            total_stars_el = article.select_one("a[href$='/stargazers']")
            total_stars = total_stars_el.get_text(strip=True) if total_stars_el else ""

            repos.append(
                TrendingRepo(
                    name=path,
                    url=repo_url,
                    description=description,
                    language=language,
                    stars_today=stars_today,
                    total_stars=total_stars,
                )
            )
        except Exception as exc:
            logger.debug("Error parsing trending row: %s", exc)

    logger.info("  → %d trending repos", len(repos))
    return repos


def collect_github_trending() -> list[NewsItem]:
    """Return NewsItems for GitHub Trending repos across configured languages."""
    languages = config.GITHUB_TRENDING_LANGUAGES or [""]  # empty = all languages
    since = config.GITHUB_TRENDING_SINCE

    all_items: list[NewsItem] = []
    seen: set[str] = set()

    for lang in languages:
        path = f"/{lang}" if lang else ""
        url = f"{TRENDING_BASE}{path}?since={since}"
        repos = _scrape_trending(url)

        for repo in repos[: config.MAX_ITEMS_PER_SOURCE]:
            if repo.name in seen:
                continue
            seen.add(repo.name)

            stars_note = ""
            if repo.stars_today:
                stars_note = f" · {repo.stars_today}"
            if repo.total_stars:
                stars_note += f" ★{repo.total_stars}"

            lang_note = f" [{repo.language}]" if repo.language else ""

            all_items.append(
                NewsItem(
                    title=f"{repo.name}{lang_note}",
                    url=repo.url,
                    source="GitHub Trending",
                    description=(
                        f"{repo.description}{stars_note}".strip()
                        or "(no description)"
                    ),
                )
            )

    return all_items
