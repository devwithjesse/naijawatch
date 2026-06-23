"""
Utility: search_by_state.py
Search Google News RSS for a specific Nigerian state and import security-relevant articles into the DB.

Usage:
  python -m app.utils.search_by_state --state Taraba --db naijawatch.db --bodies --save-json

This script reuses collector logic from app.services.pipeline to keep behavior consistent.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import time
from datetime import datetime

from app.services import pipeline
from app.services.pipeline import (
    _process_article_worker,
    fetch_feed_with_retry,
    is_security_relevant,
    make_hash,
)


def build_gnews_url(state: str) -> str:
    q = f"{state} Nigeria"
    return f"https://news.google.com/rss/search?q={q.replace(' ', '+')}&hl=en-NG&gl=NG&ceid=NG:en"


def normalize_entry(entry: dict, feed_name: str) -> dict:
    title = entry.get("title", "").strip()
    summary = entry.get("summary", "")[:500]
    link = entry.get("link", "").strip()
    published_parsed = entry.get("published_parsed")
    published_at = (
        datetime(*published_parsed[:6]).isoformat() if published_parsed else None
    )
    return {
        "title": title,
        "raw_summary": summary,
        "body": None,
        "url": link,
        "real_url": None,
        "content_hash": make_hash(link),
        "source": feed_name,
        "feed_name": feed_name,
        "published_at": published_at,
        "processed": False,
        "extraction_status": "pending",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search Google News RSS for a specific Nigerian state and import relevant articles."
    )
    parser.add_argument("--state", required=True, help="State name, e.g. Taraba")
    parser.add_argument("--db", default=pipeline.DEFAULT_DB, help="SQLite DB path")
    parser.add_argument(
        "--bodies", action="store_true", help="Attempt to fetch article bodies"
    )
    parser.add_argument(
        "--save-json", action="store_true", help="Save collected JSON to file"
    )
    parser.add_argument(
        "--limit", type=int, default=200, help="Max number of articles to import"
    )
    args = parser.parse_args()

    state = args.state.strip()
    db_path = args.db

    url = build_gnews_url(state)
    feed_name = f"GNews: {state}"

    print(f"Fetching feed for state: {state} → {url}")
    # Use pipeline.fetch_feed_with_retry which returns a list of entry dicts
    entries = fetch_feed_with_retry(feed_name, url)
    if not entries:
        print("No feed entries found.")
        return

    # Normalize and filter
    articles = []
    for e in entries:
        norm = normalize_entry(e, feed_name)
        if is_security_relevant(norm["title"], norm["raw_summary"]):
            articles.append(norm)

    if not articles:
        print("No security-relevant articles found for this state.")
        return

    if args.limit:
        articles = articles[: args.limit]

    print(f"Collected {len(articles)} security-relevant articles (before bodies).")

    if args.bodies and pipeline.NEWSPAPER_AVAILABLE:
        print(
            f"Fetching bodies for {len(articles)} articles using {pipeline.PARALLEL_WORKERS} workers..."
        )
        ctx = multiprocessing.get_context("spawn")
        processed = []
        with ctx.Pool(
            processes=min(pipeline.PARALLEL_WORKERS, max(1, len(articles)))
        ) as pool:
            futures = {
                pool.apply_async(_process_article_worker, (a,)): a for a in articles
            }
            for i, (future, original) in enumerate(futures.items(), 1):
                label = original["title"][:60]
                try:
                    result = future.get(timeout=pipeline.BODY_TIMEOUT_SECONDS)
                    processed.append(result)
                    print(f"  [{i}/{len(articles)}] OK - {label}")
                except multiprocessing.TimeoutError:
                    print(f"  [{i}/{len(articles)}] TIMEOUT - {label}")
                    original["real_url"] = original["url"]
                    processed.append(original)
                except Exception as exc:
                    print(f"  [{i}/{len(articles)}] ERROR - {label} - {exc}")
                    original["real_url"] = original["url"]
                    processed.append(original)
                time.sleep(pipeline.BODY_DELAY)
        articles = processed

    # Optionally save JSON snapshot
    if args.save_json:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"state_{state.replace(' ', '_')}_{ts}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"Saved JSON snapshot → {out}")

    # Import to DB
    print("Importing into DB...")
    stats = pipeline.import_to_db(articles, db_path)
    print(f"Import results: {stats}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
