"""retrieve.py
Script to capture risk snapshots and send weekly digest to subscribers

Usage:
  python -m app.cron.mailer
"""

from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func

from ..core.config import settings
from ..database import SessionLocal
from ..models import (
    Article,
    DigestSubscriber,
    Event,
    EventType,
    Location,
    RiskSnapshot,
    State,
)
from ..services.mailing import Mailer
from ..services.risk_engine import RiskEngine

FROM_EMAIL = settings.FROM_EMAIL
APP_BASE_URL = settings.APP_BASE_URL
APP_NAME = settings.APP_NAME


# Jinja environment for email templates (templates located in app/templates)
env = Environment(
    loader=FileSystemLoader("app/templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

EFFECTIVE_DATE = func.coalesce(Event.event_date, Article.published_at, Event.created_at)


def snapshot_risk_scores():
    """
    Saves states and national risk scores.
    """
    db = SessionLocal()
    try:
        # Sate Snapshots
        state_scores = RiskEngine.get_state_risk_scores(db)
        for state_name, data in state_scores.items():
            state = db.query(State).filter_by(name=state_name).first()
            if state:
                db.add(
                    RiskSnapshot(
                        scope="state", state_id=state.id, score=data["risk_score"]
                    )
                )

        # National Snapshot
        national_score = RiskEngine.get_national_risk_score(db)["risk_score"]
        db.add(RiskSnapshot(scope="national", score=national_score))

        db.commit()
        print("Weekly risk snapshot complete.")

    except Exception as e:
        db.rollback()
        print(f"Snapshot job failed. {e}")
    finally:
        db.close()


def send_weekly_digest():
    """
    Sends the digest to all confirmed subscribers.
    """
    db = SessionLocal()
    try:
        # Assuming snapshots were just taken:
        # 1. Get national risk score
        latest_national = (
            db.query(RiskSnapshot)
            .filter_by(scope="national")
            .order_by(RiskSnapshot.snapshot_at.desc())
            .first()
        )
        if not latest_national:
            return

        national = {
            "risk_score": latest_national.score,
            "safety_index": round(100.0 - latest_national.score, 1),
            "label": RiskEngine.classify_risk(latest_national.score)
            if hasattr(RiskEngine, "classify_risk")
            else "",
        }

        # 2. Get top 5 dangerous states
        state_scores = RiskEngine.get_state_risk_scores(db)
        top_states_list = []
        for state_name, data in sorted(
            state_scores.items(), key=lambda x: x[1]["risk_score"], reverse=True
        )[:5]:
            top_states_list.append(
                {
                    "state": state_name,
                    "risk_score": data.get("risk_score"),
                    "risk_label": data.get("risk_label"),
                }
            )

        # 3. Recent events (top 10)
        # First get the top 10 event ids ordered by effective date
        ids_subq = (
            db.query(Event.id.label("event_id"))
            .join(Article, Event.articles)
            .order_by(EFFECTIVE_DATE.desc())
            .limit(10)
            .subquery()
        )

        recent_events_q = (
            db.query(
                Event.id,
                Event.summary,
                Event.event_date,
                Event.created_at,
                EventType.name.label("event_type"),
                Location.name.label("location_name"),
            )
            .join(ids_subq, Event.id == ids_subq.c.event_id)
            .join(Location, Event.location_id == Location.id)
            .join(EventType, Event.event_type_id == EventType.id)
            .all()
        )

        recent_events = []
        for row in recent_events_q:
            recent_events.append(
                {
                    "id": row.id,
                    "summary": row.summary,
                    "event_date": row.event_date.isoformat()
                    if row.event_date
                    else None,
                    "created_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                    "event_type": row.event_type,
                    "location_name": row.location_name,
                }
            )

        # 4. Latest articles (5)
        latest_articles_q = (
            db.query(Article)
            .filter(Article.extraction_status != "irrelevant")
            .order_by(Article.published_at.desc())
            .limit(5)
            .all()
        )
        latest_articles = []
        for a in latest_articles_q:
            latest_articles.append(
                {
                    "title": a.title,
                    "url": a.url,
                    "published_at": a.published_at.isoformat()
                    if a.published_at is not None
                    else None,
                }
            )

        # Render and send per-subscriber (with personal unsubscribe link included)
        template = env.get_template("digest_weekly.html")
        subscribers = db.query(DigestSubscriber).filter_by(confirmed=True).all()
        for sub in subscribers:
            unsubscribe_link = f"{settings.APP_BASE_URL}/api/digest/unsubscribe?token={sub.unsubscribe_token}"
            rendered = template.render(
                app_name=APP_NAME,
                generated_at=datetime.now().isoformat(),
                national=national,
                top_states=top_states_list,
                recent_events=recent_events,
                articles=latest_articles,
                logo_url=f"{settings.APP_BASE_URL}/logo.png",
                unsubscribe_base=unsubscribe_link,
            )
            if Mailer.send_email(str(sub.email), f"{APP_NAME} Weekly Digest", rendered):
                print(f"Mail successfully sent to {sub.email}")
        print("Emails sent successfully.")
    finally:
        db.close()


def run_mailer():
    # 1. Take snapshot of risk scores
    snapshot_risk_scores()

    # 2. Send the digest
    send_weekly_digest()


if __name__ == "__main__":
    run_mailer()
