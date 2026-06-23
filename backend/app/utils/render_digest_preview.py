"""Render the weekly digest to a local HTML file for preview without sending emails.

Usage:
  python backend/scripts/render_digest_preview.py --out preview.html

This will connect to the database (DATABASE_URL env or default sqlite), collect the same
information the mailer uses, render the Jinja template, and write it to an HTML file so you
can preview how the email will look in a browser.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime

from app.core.config import config
from app.models import Article, Event, EventType, Location, RiskSnapshot
from app.services.risk_engine import RiskEngine
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def collect_digest_data(db_url: str):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
        if db_url.startswith("sqlite")
        else {},
    )
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        latest_national = (
            session.query(RiskSnapshot)
            .filter_by(scope="national")
            .order_by(RiskSnapshot.snapshot_at.desc())
            .first()
        )
        state_scores = RiskEngine.get_state_risk_scores(session)

        national = {
            "risk_score": latest_national.score if latest_national else 0,
            "safety_index": round(
                100.0 - (latest_national.score if latest_national else 0), 1
            ),
            "label": RiskEngine.classify_risk(latest_national.score)
            if latest_national
            else "Unknown",
        }

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

        # Retrieve recent events
        recent_events_q = (
            session.query(
                Event.id,
                Event.summary,
                Event.event_date,
                Event.created_at,
                EventType.name.label("event_type"),
                Location.name.label("location_name"),
            )
            .join(EventType, Event.event_type_id == EventType.id)
            .join(Location, Event.location_id == Location.id)
            .join(Event.articles)
            .order_by(Event.event_date.desc())
            .limit(10)
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

        latest_articles_q = (
            session.query(Article)
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

        return {
            "app_name": config.APP_NAME,
            "generated_at": datetime.now().isoformat(),
            "national": national,
            "top_states": top_states_list,
            "recent_events": recent_events,
            "articles": latest_articles,
            "logo_url": f"{config.APP_BASE_URL}/logo.png",
            "unsubscribe_base": f"{config.APP_BASE_URL}/unsubscribe",
        }
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Render weekly digest to HTML file for preview"
    )
    parser.add_argument("--out", default="digest_preview.html", help="Output file path")
    parser.add_argument("--db", default=None, help="Optional DB URL (overrides env)")
    args = parser.parse_args()

    db_url = args.db or os.environ.get("DATABASE_URL") or config.DB_URL
    data = collect_digest_data(db_url)

    env = Environment(
        loader=FileSystemLoader("app/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("digest_weekly.html")
    html = template.render(**data)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Rendered digest preview to {args.out}")


if __name__ == "__main__":
    main()
