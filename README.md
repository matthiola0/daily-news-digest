# News Digest MVP

A daily news digest that runs on GitHub Actions (or locally) and collects:

- **Twitter / X** content via configurable RSS feeds (Nitter, RSSHub, or any RSS source)
- **GitHub Trending** repositories (scraped from github.com/trending)
- **AI News** from a curated set of RSS feeds (arXiv, OpenAI blog, Hugging Face, DeepLearning.AI, HN)

The digest is written to `output/digest_YYYY-MM-DD.md`, posted to the GitHub Actions job summary, uploaded as a workflow artifact, and optionally sent to a Discord channel.

---

## Quick start (local)

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd news-digest-mvp

# 2. Copy example env file and edit as needed
cp .env.example .env

# 3. Run (the script creates a .venv and installs deps automatically)
./scripts/run_local.sh

# Dry-run: print the digest to stdout without saving
./scripts/run_local.sh --dry-run
```

The script prefers **uv** (faster) when it is installed; otherwise falls back to `python3 -m venv` + `pip`.

---

## Requirements

- Python 3.10+
- Internet access (for fetching feeds and GitHub Trending)
- No paid API keys required for the deterministic fallback mode

---

## Configuration

Copy `.env.example` to `.env` and fill in the values you want.
All variables are optional — the pipeline always produces a digest even with an empty `.env`.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | _(empty)_ | If set, uses OpenAI-compatible API for a smarter summary |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name for the chat completion call |
| `OPENAI_BASE_URL` | _(empty)_ | Override API base URL (Ollama, LiteLLM, Azure, etc.) |
| `TWITTER_RSS_FEEDS` | _(empty)_ | Comma-separated RSS URLs for Twitter-style content (see below) |
| `AI_NEWS_RSS_FEEDS` | _(built-in list)_ | Override the built-in AI news feed list |
| `GITHUB_TRENDING_LANGUAGES` | _(all)_ | Comma-separated language filters, e.g. `python,typescript` |
| `GITHUB_TRENDING_SINCE` | `daily` | `daily`, `weekly`, or `monthly` |
| `OUTPUT_DIR` | `output` | Directory where digest files are written |
| `DIGEST_TIMEZONE` | `Asia/Taipei` | Timezone used for the digest timestamp |
| `DISCORD_WEBHOOK_URL` | _(empty)_ | If set, posts the digest to Discord |
| `MAX_ITEMS_PER_SOURCE` | `10` | Maximum news items fetched per source |
| `MAX_DESCRIPTION_CHARS` | `300` | Max description length in fallback summarizer |

### Summarization modes

**With `OPENAI_API_KEY`:** the pipeline calls the configured OpenAI-compatible API to generate a curated, bullet-pointed summary with key takeaways.

**Without `OPENAI_API_KEY`:** a deterministic fallback summarizer produces a structured Markdown list grouped by source — no external calls, always works.

---

## Twitter / Nitter / RSSHub setup

Twitter's official API requires a paid subscription; we avoid it entirely.
Instead, configure **RSS feed URLs** from free proxies:

```
# In your .env or GitHub Actions variable TWITTER_RSS_FEEDS:
TWITTER_RSS_FEEDS=https://nitter.net/OpenAI/rss,https://nitter.net/karpathy/rss
```

**Nitter** (https://nitter.net and community mirrors) exposes `/<user>/rss` endpoints.
**RSSHub** (https://rsshub.app) exposes `twitter/user/<user>` among many other routes.

> **Important limitations:**
> - Public Nitter instances go up and down frequently. Self-hosting Nitter is the most reliable option.
> - RSSHub's Twitter routes may require a self-hosted instance or a paid tier to avoid rate limits.
> - If a feed URL is unreachable, the pipeline logs a warning and continues — it will not fail.
> - Leave `TWITTER_RSS_FEEDS` empty to simply skip the Twitter section.

**Finding a working Nitter instance:** https://status.d420.de/ lists live instances.

**Example RSSHub routes:**

| Content | URL pattern |
|---|---|
| User timeline | `https://rsshub.app/twitter/user/USERNAME` |
| Search | `https://rsshub.app/twitter/keyword/KEYWORD` |
| List | `https://rsshub.app/twitter/list/OWNER/LIST_SLUG` |

---

## Default AI news feeds

When `AI_NEWS_RSS_FEEDS` is empty the following feeds are used:

- `https://rss.arxiv.org/rss/cs.AI` — arXiv CS.AI papers
- `https://openai.com/news/rss.xml` — OpenAI news
- `https://huggingface.co/blog/feed.xml` — Hugging Face blog
- `https://www.technologyreview.com/feed/` — MIT Technology Review
- `https://hnrss.org/frontpage?q=AI+OR+LLM+OR+GPT+OR+machine+learning` — Hacker News AI filter

---

## GitHub Actions setup

### Cron schedule — 08:00 Asia/Taipei

Asia/Taipei is UTC+8 year-round (no DST).
`08:00 CST − 8 h = 00:00 UTC`

```yaml
on:
  schedule:
    - cron: "0 0 * * *"   # 00:00 UTC = 08:00 Asia/Taipei
```

### Secrets and variables to configure

In your repository go to **Settings → Secrets and variables → Actions**:

| Name | Type | Required | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | Secret | No | Enables LLM summarization |
| `DISCORD_WEBHOOK_URL` | Secret | No | Enables Discord posting |
| `TWITTER_RSS_FEEDS` | Variable | No | Comma-separated RSS URLs |
| `AI_NEWS_RSS_FEEDS` | Variable | No | Override default AI feed list |
| `GITHUB_TRENDING_LANGUAGES` | Variable | No | e.g. `python,go` |
| `OPENAI_MODEL` | Variable | No | Default: `gpt-4o-mini` |
| `OPENAI_BASE_URL` | Variable | No | For non-OpenAI endpoints |

### Manual trigger

Go to **Actions → Daily News Digest → Run workflow** to trigger manually.
Set `dry_run = true` to see the output in the job logs without saving.

### Outputs

- **Job summary** — the full digest is appended to the workflow run summary page.
- **Artifact** — uploaded as `digest-<run-id>` with 90-day retention.
- **Committed file** — the workflow commits `output/digest_YYYY-MM-DD.md` back to the repo.

To disable the commit-back step, remove or comment the "Commit digest to repository" step in `.github/workflows/daily_digest.yml`.

---

## Running tests

```bash
# Install deps first (or use run_local.sh which does this automatically)
.venv/bin/pip install -r requirements.txt

# Unit tests (no network required)
.venv/bin/pytest tests/test_collectors.py -v

# Smoke test (runs full pipeline with --dry-run; exercises live network)
.venv/bin/python tests/smoke_test.py
```

---

## Project structure

```
news-digest-mvp/
├── .env.example                  # Copy to .env and fill in
├── .github/workflows/
│   └── daily_digest.yml          # GitHub Actions workflow
├── output/                       # Generated digests land here
├── requirements.txt
├── scripts/
│   └── run_local.sh              # Local runner (creates venv, installs deps)
├── src/
│   ├── config.py                 # Centralised env-var config
│   ├── main.py                   # Pipeline entry point
│   ├── collectors/
│   │   ├── base.py               # NewsItem dataclass
│   │   ├── rss_collector.py      # RSS/Atom fetcher (Twitter + AI news)
│   │   └── github_trending.py    # GitHub Trending scraper
│   ├── summarizer/
│   │   ├── simple_summarizer.py  # Deterministic fallback (no API)
│   │   └── openai_summarizer.py  # OpenAI-compatible LLM summarizer
│   ├── digest/
│   │   └── builder.py            # Assembles and writes Markdown digest
│   └── notifiers/
│       └── discord.py            # Optional Discord webhook
└── tests/
    ├── test_collectors.py        # Unit tests (mocked network)
    └── smoke_test.py             # End-to-end dry-run smoke check
```

---

## Limitations

- **GitHub Trending** uses HTML scraping. GitHub may change their markup; update the CSS selectors in `src/collectors/github_trending.py` if it breaks.
- **Twitter/Nitter** feeds are inherently fragile. Nitter instances block, go offline, or get throttled. Budget time to maintain feed URLs.
- **arXiv feed** returns many papers daily; `MAX_ITEMS_PER_SOURCE` caps this.
- The workflow requires `contents: write` permission to commit digest files back to the repo. Remove the commit step if you prefer artifact-only output.
