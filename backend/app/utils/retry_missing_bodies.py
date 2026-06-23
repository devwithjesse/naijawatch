"""
Utility: retry_missing_bodies.py
Find articles in the DB with empty/null body and attempt to re-fetch their bodies using
the same worker logic in app.services.pipeline.

Usage:
  python -m app.utils.retry_missing_bodies --sqlite naijawatch.db --limit 100 --commit
  python -m app.utils.retry_missing_bodies --limit 100

This updates the `articles` table in-place: fills `body` and updates `url` to the resolved real_url
if found. It leaves `extraction_status` as-is but ensures `processed=False` so extractor can pick up.
"""

from __future__ import annotations

import argparse
import multiprocessing
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..database import engine as e
from ..models import Article
from ..services.pipeline import (
    BODY_DELAY,
    PARALLEL_WORKERS,
    _process_article_worker,
)


def fetch_targets(session: Session, limit: int | None = None) -> List[Article]:
    q = session.query(Article).filter((Article.body == None) | (Article.body == ""))
    if limit:
        q = q.limit(limit)
    return q.all()


def main():
    parser = argparse.ArgumentParser(
        description="Retry and fill missing article bodies in the DB"
    )
    parser.add_argument("--sqlite", default="naijawatch.db", help="SQLite DB path")
    parser.add_argument("--limit", type=int, default=100, help="Max articles to retry")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write changes to DB (dry-run otherwise)",
    )
    args = parser.parse_args()

    db_path = args.sqlite

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}) if db_path else e
        

    with Session(engine) as session:
        targets = fetch_targets(session, args.limit)
        if not targets:
            print("No articles with missing bodies found.")
            return

        print(f"Found {len(targets)} articles with missing bodies")

        # Build lightweight dicts for processing
        jobs = []
        for art in targets:
            jobs.append(
                {
                    "title": art.title,
                    "url": art.url,
                    "real_url": art.url,
                    "content_hash": art.content_hash,
                    "source": art.source_id,
                    "feed_name": None,
                    "published_at": art.published_at.isoformat()
                    if art.published_at is not None
                    else None,
                    "processed": False,
                    "extraction_status": art.extraction_status or "pending",
                }
            )

        # Process in parallel similar to pipeline
        ctx = multiprocessing.get_context("spawn")
        results = []
        with ctx.Pool(processes=min(PARALLEL_WORKERS, max(1, len(jobs)))) as pool:
            futures = [pool.apply_async(_process_article_worker, (j,)) for j in jobs]
            for i, f in enumerate(futures, 1):
                try:
                    res = f.get(timeout=BODY_DELAY * 20 + 10)
                    results.append(res)
                    print(f"[{i}/{len(futures)}] OK - {res.get('title', '(no title)')}")
                except multiprocessing.TimeoutError:
                    print(f"[{i}/{len(futures)}] TIMEOUT")
                    results.append(None)
                except Exception as e:
                    print(f"[{i}/{len(futures)}] ERROR - {e}")
                    results.append(None)

        # Apply updates (dry-run unless --commit)
        updated = 0
        for art_obj, result in zip(targets, results):
            if not result:
                continue
            body = result.get("body")
            real_url = result.get("real_url") or result.get("url")
            if body:
                print(f"Will update article id={art_obj.id} title={art_obj.title[:40]}")
                if args.commit:
                    art_obj.body = body
                    art_obj.url = real_url
                    art_obj.processed = False
                    # keep extraction_status as-is to allow manual review if needed
                    session.add(art_obj)
                    updated += 1
            else:
                print(f"No body found for article id={art_obj.id}")

        if args.commit:
            session.commit()
            print(f"Committed {updated} updates to DB")
        else:
            print(
                f"Dry-run: {updated} would be updated (use --commit to write changes)"
            )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
