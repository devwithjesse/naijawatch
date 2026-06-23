"""process.py
Wrapper to run the ExtractionWorker that processes pending articles via the LLM extractor.

Usage:
  python -m app.cron.process --limit 100
"""

from __future__ import annotations

import argparse

from app.services.worker import ExtractionWorker


def run_process(limit: int = 100, delay: float = 2.5):
    print(f"Running extraction worker: limit={limit}, delay={delay}")
    worker = ExtractionWorker()
    worker.process_pending_articles(limit=limit, delay=delay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the extraction worker to process pending articles"
    )
    parser.add_argument(
        "--limit", type=int, default=100, help="Max articles to process"
    )
    parser.add_argument(
        "--delay", type=float, default=2, help="Delay between extractions (seconds)"
    )
    args = parser.parse_args()

    run_process(limit=args.limit, delay=args.delay)
