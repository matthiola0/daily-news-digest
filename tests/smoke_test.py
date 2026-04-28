#!/usr/bin/env python3
"""
Smoke test: runs the full pipeline with --dry-run.
Exits 0 on success, non-zero on failure.
Does NOT require any API keys; uses the deterministic summarizer.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main() -> int:
    print("Running smoke test (dry-run, no network calls required for imports)…")

    # Ensure no API key is set so we exercise the fallback path
    env = {**os.environ, "OPENAI_API_KEY": "", "TWITTER_RSS_FEEDS": ""}

    result = subprocess.run(
        [sys.executable, "-m", "src.main", "--dry-run"],
        cwd=str(ROOT),
        env=env,
        capture_output=False,
        timeout=120,
    )

    if result.returncode == 0:
        print("\nSmoke test PASSED.")
    else:
        print(f"\nSmoke test FAILED (exit code {result.returncode}).")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
