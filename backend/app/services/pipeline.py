"""
NaijaWatch — Full Pipeline
===========================
Collects articles from RSS feeds and imports directly into SQLite DB.
Optionally saves a JSON snapshot for debugging.

Usage:
  python pipeline.py                        # collect + import
  python pipeline.py --save-json            # collect + import + save JSON
  python pipeline.py --json-only            # collect + save JSON, skip DB import
  python pipeline.py --file articles.json   # skip collect, import existing JSON
  python pipeline.py --no-bodies            # skip body fetch (faster, for testing)
  python pipeline.py --db path/to/other.db  # use a different DB file

Install:
  pip install feedparser requests newspaper3k lxml_html_clean googlenewsdecoder sqlalchemy
"""

import argparse
import hashlib
import json
import multiprocessing
import sys
import time
from datetime import datetime
from pathlib import Path

import feedparser
import requests
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.orm import Session

from app.models import Article, Source

# ── Optional deps ─────────────────────────────────────────────────────────────
try:
    from newspaper import Article as NewsArticle
    from newspaper import Config as NewsConfig

    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    print("[WARN] newspaper3k not installed. Body extraction disabled.")

try:
    from googlenewsdecoder import gnewsdecoder

    DECODER_AVAILABLE = True
except ImportError:
    DECODER_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_DB = "naijawatch.db"
DEFAULT_JSON = "collected_articles.json"

BODY_TIMEOUT_SECONDS = 12
REDIRECT_TIMEOUT = 8
FEED_FETCH_TIMEOUT = 12
FEED_FETCH_RETRIES = 3
PARALLEL_WORKERS = 3  # leave one core free on i5 4-core
BODY_DELAY = 0.3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

FEEDS = {
    "Premium Times": "https://www.premiumtimesng.com/feed",
    "Punch": "https://punchng.com/feed/",
    "Vanguard": "https://www.vanguardngr.com/feed/",
    "Daily Trust": "https://dailytrust.com/feed/",
    "Channels TV": "https://www.channelstv.com/feed/",
    "GNews: banditry": "https://news.google.com/rss/search?q=banditry+attack+Nigeria+when:24h&hl=en-NG&gl=NG&ceid=NG:en",
    "GNews: kidnapping": "https://news.google.com/rss/search?q=kidnapping+Nigeria+when:24h&hl=en-NG&gl=NG&ceid=NG:en",
    "GNews: Boko Haram": "https://news.google.com/rss/search?q=Boko+Haram&hl=en-NG&gl=NG&ceid=NG:en",
    "GNews: armed robbery": "https://news.google.com/rss/search?q=armed+robbery+Nigeria&hl=en-NG&gl=NG&ceid=NG:en",
    "GNews: terrorism": "https://news.google.com/rss/search?q=terrorist+attack+Nigeria+when:24h&hl=en-NG&gl=NG&ceid=NG:en",
    "GNews: communal clash": "https://news.google.com/rss/search?q=communal+clash+Nigeria&hl=en-NG&gl=NG&ceid=NG:en",
    "GNews: assassination": "https://news.google.com/rss/search?q=assassination+killed+Nigeria&hl=en-NG&gl=NG&ceid=NG:en",
}

KEYWORDS = [
    "kidnap",
    "abduct",
    "ransom",
    "bandit",
    "banditry",
    "robbery",
    "armed robber",
    "gunmen",
    "attack",
    "massacre",
    "killing",
    "killed",
    "terrorist",
    "terrorism",
    "bomb",
    "explosion",
    "insecurity",
    "troops",
    "soldier",
    "Boko Haram",
    "ISWAP",
    "ESN",
    "IPOB",
    "communal",
    "herdsmen",
    "clash",
    "assassination",
    "assassinate",
    "jailbreak",
    "prison break",
]


# ══════════════════════════════════════════════════════════════════════════════
# COLLECTOR
# ══════════════════════════════════════════════════════════════════════════════


def make_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def is_security_relevant(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(kw.lower() in text for kw in KEYWORDS)


# These run in child processes — can be hard-killed on timeout


def _resolve_redirect_worker(url: str) -> str:
    if "news.google.com" not in url:
        return url
    if DECODER_AVAILABLE:
        try:
            result = gnewsdecoder(url, interval=1)
            if result.get("status") and result.get("decoded_url"):
                return result["decoded_url"]
        except Exception:
            pass
    try:
        resp = requests.head(
            url, headers=HEADERS, allow_redirects=True, timeout=REDIRECT_TIMEOUT
        )
        if resp.url and "news.google.com" not in resp.url:
            return resp.url
    except Exception:
        pass
    return url


def _fetch_body_worker(url: str) -> str | None:
    if not NEWSPAPER_AVAILABLE:
        return None
    config = NewsConfig()
    config.browser_user_agent = HEADERS["User-Agent"]
    config.request_timeout = 7
    config.fetch_images = False
    config.memoize_articles = False
    try:
        article = NewsArticle(url, config=config)
        article.download()
        article.parse()
        return article.text.strip() if article.text else None
    except Exception:
        return None


def _process_article_worker(article: dict) -> dict:
    real_url = _resolve_redirect_worker(article["url"])
    article["real_url"] = real_url
    article["body"] = _fetch_body_worker(real_url)
    return article


def fetch_feed_with_retry(name: str, url: str) -> list[dict]:
    for attempt in range(1, FEED_FETCH_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=FEED_FETCH_TIMEOUT)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            articles = []
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:500]
                link = entry.get("link", "").strip()
                source = entry.get("source", {}).get("title", name)

                published_parsed = entry.get("published_parsed")
                published_at = (
                    datetime(*published_parsed[:6]).isoformat()
                    if published_parsed
                    else None
                )

                if not link:
                    continue

                articles.append(
                    {
                        "title": title,
                        "raw_summary": summary,
                        "body": None,
                        "url": link,
                        "real_url": None,
                        "content_hash": make_hash(link),
                        "source": source,
                        "feed_name": name,
                        "published_at": published_at,
                        "processed": False,
                        "extraction_status": "pending",
                    }
                )
            return articles

        except requests.exceptions.ConnectionError as e:
            wait = 2**attempt
            print(
                f"  [DNS/CONN ERROR] {name} (attempt {attempt}/{FEED_FETCH_RETRIES}): {e}"
            )
            if attempt < FEED_FETCH_RETRIES:
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)

        except requests.exceptions.HTTPError as e:
            print(f"  [HTTP {e.response.status_code}] {name} — skipping")
            return []

        except Exception as e:
            print(f"  [FETCH ERROR] {name}: {e}")
            return []

    print(f"  [GIVING UP] {name} after {FEED_FETCH_RETRIES} attempts")
    return []


_seen_hashes: set[str] = set()


def collect(fetch_bodies: bool = True) -> list[dict]:
    all_articles = []

    for name, url in FEEDS.items():
        print(f"\nFetching: {name}...")
        articles = fetch_feed_with_retry(name, url)

        if not articles:
            continue

        before = len(articles)
        articles = [
            a for a in articles if is_security_relevant(a["title"], a["raw_summary"])
        ]
        print(f"  {before} total → {len(articles)} security-relevant")

        unique = [a for a in articles if a["content_hash"] not in _seen_hashes]
        for a in unique:
            _seen_hashes.add(a["content_hash"])

        dupes = len(articles) - len(unique)
        if dupes:
            print(f"  {dupes} in-run duplicate(s) skipped")
        articles = unique

        if not articles:
            continue

        if fetch_bodies:
            print(f"  Fetching bodies for {len(articles)} articles...")
            processed = []
            ok = timeout_count = failed = 0

            ctx = multiprocessing.get_context("spawn")
            with ctx.Pool(processes=PARALLEL_WORKERS) as pool:
                futures = {
                    pool.apply_async(_process_article_worker, (a,)): a for a in articles
                }
                for i, (future, original) in enumerate(futures.items(), 1):
                    label = original["title"][:55]
                    try:
                        result = future.get(timeout=BODY_TIMEOUT_SECONDS)
                        status = "OK   " if result.get("body") else "EMPTY"
                        print(f"    [{i:>3}/{len(articles)}] {status} — {label}...")
                        processed.append(result)
                        ok += 1
                    except multiprocessing.TimeoutError:
                        print(f"    [{i:>3}/{len(articles)}] TIMEOUT — {label}...")
                        original["real_url"] = original["url"]
                        processed.append(original)
                        timeout_count += 1
                    except Exception as e:
                        print(
                            f"    [{i:>3}/{len(articles)}] ERROR ({str(e)[:30]}) — {label}..."
                        )
                        original["real_url"] = original["url"]
                        processed.append(original)
                        failed += 1
                    time.sleep(BODY_DELAY)

            print(f"  → OK: {ok} | Timeout: {timeout_count} | Error: {failed}")
            articles = processed

        all_articles.extend(articles)

    return all_articles


# ══════════════════════════════════════════════════════════════════════════════
# IMPORTER
# ══════════════════════════════════════════════════════════════════════════════


def parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def import_to_db(articles: list[dict], db_path: str) -> dict:
    """
    Import a list of article dicts into the provided database.

    db_path may be:
    - a file path (e.g. naijawatch.db) -> treated as SQLite
    - a sqlite URL (sqlite:///./naijawatch.db)
    - a full SQLAlchemy URL (postgresql://... or postgres://...)
    """
    # Determine engine based on db_path
    if isinstance(db_path, str) and (
        db_path.startswith("postgres://")
        or db_path.startswith("postgresql://")
        or "://" in db_path
        and not db_path.startswith("sqlite")
    ):
        engine = create_engine(db_path)
    else:
        # Treat as sqlite path
        # Support either 'sqlite:///./naijawatch.db' or plain 'naijawatch.db'
        if db_path.startswith("sqlite://"):
            sqlite_url = db_path
        else:
            sqlite_url = f"sqlite:///{db_path}"
        db_file = Path(sqlite_url.replace("sqlite:///", ""))
        if not db_file.exists():
            print(f"[ERROR] DB not found: {db_file}")
            print(f"        Run first: sqlite3 {db_file} < naijaintel_migrations.sql")
            sys.exit(1)

        engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    # For sqlite we enable foreign keys; for Postgres it's a no-op
    try:
        with engine.connect() as conn:
            if str(engine.url).startswith("sqlite"):
                conn.execute(text("PRAGMA foreign_keys = ON"))
    except Exception:
        # ignore; we'll surface errors during insert
        pass

    inserted = skipped = errors = 0

    with Session(engine) as session:
        # Load existing state upfront — avoids per-row queries
        source_cache = {row.name: row.id for row in session.query(Source).all()}
        existing_hashes = set()
        try:
            existing_hashes = {
                row[0]
                for row in session.execute(
                    text("SELECT content_hash FROM articles")
                ).fetchall()
            }
        except Exception:
            # Table may be empty/non-existent yet
            existing_hashes = set()

        print(f"\nImporting {len(articles)} articles into {db_path}...")
        print(f"  Sources already in DB : {len(source_cache)}")
        print(f"  Articles already in DB: {len(existing_hashes)}")

        for i, raw in enumerate(articles, 1):
            try:
                content_hash = raw.get("content_hash", "")
                if not content_hash:
                    skipped += 1
                    continue

                # DB-level deduplication (catches articles from previous runs)
                if content_hash in existing_hashes:
                    skipped += 1
                    continue

                title = raw.get("title", "").strip()
                if not title:
                    skipped += 1
                    continue

                # Source lookup / creation
                source_name = raw.get("source") or raw.get("feed_name") or "Unknown"
                feed_url = raw.get("url", "")

                if source_name not in source_cache:
                    source_type = "api" if "api" in feed_url.lower() else "rss"
                    new_source = Source(
                        name=source_name, type=source_type, url=feed_url
                    )
                    session.add(new_source)
                    session.flush()
                    source_cache[source_name] = new_source.id

                article = Article(
                    source_id=source_cache[source_name],
                    title=title[:500],
                    body=raw.get("body"),
                    url=raw.get("real_url") or raw.get("url", ""),
                    content_hash=content_hash,
                    published_at=parse_published_at(raw.get("published_at")),
                    processed=False,
                    extraction_status="pending",
                )
                session.add(article)
                existing_hashes.add(content_hash)
                inserted += 1

            except Exception as e:
                print(f"  [ERROR] Article {i}: {e}")
                errors += 1
                continue

        session.commit()

    return {"inserted": inserted, "skipped": skipped, "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="NaijaWatch pipeline — collect + import"
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite DB path")
    parser.add_argument(
        "--file", default=None, help="Skip collect, import this JSON file instead"
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save collected articles to JSON before importing",
    )
    parser.add_argument(
        "--json-only", action="store_true", help="Collect and save JSON, skip DB import"
    )
    parser.add_argument(
        "--no-bodies",
        action="store_true",
        help="Skip body fetch (faster, for testing feeds)",
    )
    args = parser.parse_args()

    start = datetime.now()
    print("=" * 60)
    print("NaijaWatch Pipeline")
    print(f"Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── Step 1: Get articles (collect or load from file) ──────────────────────
    if args.file:
        # Skip collection, load existing JSON
        json_file = Path(args.file)
        if not json_file.exists():
            print(f"[ERROR] File not found: {args.file}")
            sys.exit(1)
        with open(json_file, encoding="utf-8") as f:
            articles = json.load(f)
        print(f"Loaded {len(articles)} articles from {args.file}")

    else:
        # Run collector
        articles = collect(fetch_bodies=not args.no_bodies)
        bodies_ok = sum(1 for a in articles if a.get("body"))
        print(
            f"\nCollector done: {len(articles)} articles | {bodies_ok} with body text"
        )

        # Optionally save JSON snapshot
        if args.save_json or args.json_only:
            ts = start.strftime("%Y%m%d_%H%M%S")
            output_file = f"collected_{ts}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            print(f"Saved JSON snapshot → {output_file}")

        if args.json_only:
            print("--json-only flag set. Skipping DB import.")
            return

    # ── Step 2: Import to DB ──────────────────────────────────────────────────
    stats = import_to_db(articles, args.db)

    elapsed = (datetime.now() - start).seconds
    print(f"\n{'=' * 60}")
    print(f"Pipeline complete ({elapsed}s)")
    print(f"  Inserted : {stats['inserted']}")
    print(f"  Skipped  : {stats['skipped']}  (dupes or invalid)")
    print(f"  Errors   : {stats['errors']}")
    print(f"{'=' * 60}")

    if stats["inserted"] > 0:
        print(f"\nNext: run the LLM extractor on {stats['inserted']} pending articles")


if __name__ == "__main__":
    multiprocessing.freeze_support()  # required on Windows
    main()
