"""retrieve.py
Programmatic wrapper for the pipeline collector + importer.

Usage:
  python -m app.cron.retrieve --db naijawatch.db --save-json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Optional

from app.services import pipeline


def run_retrieve(
    fetch_bodies: bool = True, db_path: Optional[str] = None, save_json: bool = False
):
    """Collect articles and import into the provided DB path.

    Returns the import stats dict from import_to_db.
    """
    if db_path is None:
        db_path = pipeline.DEFAULT_DB

    print(f"Running retrieve: fetch_bodies={fetch_bodies}, db={db_path}")
    articles = pipeline.collect(fetch_bodies=fetch_bodies)

    if save_json:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = f"retrieve_{ts}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        print(f"Saved snapshot → {out}")

    stats = pipeline.import_to_db(articles, db_path)
    print(f"Import results: {stats}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the retrieval pipeline (collector + DB import)"
    )
    parser.add_argument(
        "--no-bodies",
        action="store_true",
        help="Do not attempt to fetch article bodies",
    )
    parser.add_argument(
        "--db", default=None, help="SQLite DB path (defaults to pipeline.DEFAULT_DB)"
    )
    parser.add_argument(
        "--save-json", action="store_true", help="Save collected JSON snapshot"
    )
    args = parser.parse_args()

    run_retrieve(
        fetch_bodies=not args.no_bodies, db_path=args.db, save_json=args.save_json
    )
