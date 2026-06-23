import logging

from apscheduler.schedulers.background import BackgroundScheduler

# Cron wrappers
from ..cron.process import run_process
from ..cron.retrieve import run_retrieve
from ..cron.mailer import run_mailer
from .config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_full_pipeline():
    """
    Combined task to fetch news and then run extraction.
    """
    logger.info("Starting scheduled pipeline run...")
    try:
        # 1. Retrieve (collect + import)
        db_path = config.DATABASE_URL.replace("sqlite:///", "")
        run_retrieve(fetch_bodies=True, db_path=db_path)
        # 2. Process (extraction)
        run_process(limit=50)
        logger.info("Scheduled pipeline run completed successfully.")
    except Exception as e:
        logger.error(f"Scheduled pipeline run failed: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run every 6 hours
    scheduler.add_job(run_full_pipeline, "interval", hours=6)

    # Run every week
    scheduler.add_job(run_mailer, "interval", hours=24*6)

    scheduler.start()
    logger.info("Background scheduler started")
