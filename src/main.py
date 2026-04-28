"""Entry point for the news digest pipeline."""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

import pytz

from src import config
from src.collectors.github_trending import collect_github_trending
from src.collectors.rss_collector import collect_ai_news_feeds, collect_twitter_feeds
from src.digest.builder import build_digest, write_digest
from src.notifiers.discord import send_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _choose_summarizer():
    if config.OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY detected — using OpenAI-compatible summarizer.")
        from src.summarizer import openai_summarizer as s
    else:
        logger.info("No OPENAI_API_KEY — using deterministic fallback summarizer.")
        from src.summarizer import simple_summarizer as s
    return s


def run(dry_run: bool = False) -> int:
    """Run the full digest pipeline. Returns exit code."""
    logger.info("=== News Digest Pipeline starting ===")

    # ── Collect ───────────────────────────────────────────────────────────────
    logger.info("--- Collecting Twitter/RSS feeds ---")
    twitter_items = collect_twitter_feeds()

    logger.info("--- Collecting GitHub Trending ---")
    github_items = collect_github_trending()

    logger.info("--- Collecting AI News feeds ---")
    ai_items = collect_ai_news_feeds()

    total = len(twitter_items) + len(github_items) + len(ai_items)
    logger.info("Collected %d items total.", total)

    if total == 0:
        logger.warning("No items collected. Writing empty digest.")

    # ── Summarise ─────────────────────────────────────────────────────────────
    summarizer = _choose_summarizer()
    sections = summarizer.summarize(twitter_items, github_items, ai_items)

    sources: list[str] = []
    if twitter_items:
        sources.append(f"Twitter/RSS ({len(twitter_items)})")
    if github_items:
        sources.append(f"GitHub Trending ({len(github_items)})")
    if ai_items:
        sources.append(f"AI News ({len(ai_items)})")
    source_summary = ", ".join(sources) if sources else "none"

    # ── Build & write digest ──────────────────────────────────────────────────
    tz = pytz.timezone(config.DIGEST_TIMEZONE)
    now = datetime.now(tz)
    markdown = build_digest(sections, source_summary, run_date=now)

    if dry_run:
        print("\n" + "=" * 60)
        print(markdown)
        print("=" * 60)
        logger.info("Dry-run mode: digest printed, not saved.")
        return 0

    digest_path = write_digest(markdown, date_str=now.strftime("%Y-%m-%d"))

    # ── Notify ────────────────────────────────────────────────────────────────
    send_digest(markdown)

    # ── GitHub Actions job summary ────────────────────────────────────────────
    _write_gha_summary(markdown)

    logger.info("=== Pipeline complete. Output: %s ===", digest_path)
    return 0


def _write_gha_summary(markdown: str) -> None:
    """Append to $GITHUB_STEP_SUMMARY if running inside GitHub Actions."""
    import os

    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    try:
        with open(summary_file, "a", encoding="utf-8") as fh:
            fh.write(markdown)
        logger.info("GitHub Actions job summary written.")
    except Exception as exc:
        logger.warning("Could not write GHA step summary: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily news digest generator")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print digest to stdout instead of writing to disk.",
    )
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
