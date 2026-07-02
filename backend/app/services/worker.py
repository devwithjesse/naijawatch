import time
from datetime import datetime

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import (
    Article,
    Event,
    EventSource,
    EventStatistics,
    EventType,
    Location,
    State,
)
from .extractor import ExtractorService
from .geocoder import GeocoderService


class ExtractionWorker:
    def __init__(self):
        self.extractor = ExtractorService()
        self.geocoder = GeocoderService()
        self.db = SessionLocal()

        # Cache for lookup tables to minimize DB queries
        self.event_types = {
            et.name.lower(): et.id for et in self.db.query(EventType).all()
        }
        self.states = {s.name.lower(): s.id for s in self.db.query(State).all()}

    def process_pending_articles(self, limit: int = 10, delay: float = 2.5):
        """
        Fetches unprocessed articles (recent first) and runs extraction.
        """
        pending = (
            self.db.query(Article)
            .filter(Article.processed == False, Article.body != None)
            .order_by(Article.published_at.desc())  # Process most recent first
            .limit(limit)
            .all()
        )

        if not pending:
            print("No pending articles to process.")
            return

        print(f"Processing {len(pending)} articles (most recent first)...")

        try:
            for i, article in enumerate(pending, 1):
                print(f"  - [{i}] Analyzing: {article.title[:60]}...")

                result = self.extractor.extract_event(article.title, article.body)

                if result["status"] == "success":
                    self._handle_success(article, result["data"])
                elif result["status"] == "irrelevant":
                    self._handle_irrelevant(article)
                elif result["status"] == "rate_limited":
                    print(
                        "\n[🛑 RATE LIMIT] Groq API quota reached. Stopping gracefully."
                    )
                    print(f"Error: {result.get('error')}")
                    # Article final update is not commited yet, so it stays 'pending'
                    return
                else:
                    self._handle_failure(article, result.get("error"))

                self.db.commit()

                # Wait to avoid burning tokens/hitting limits too fast
                time.sleep(delay)
        except KeyboardInterrupt:
            print("\n[EXIT] Worker stopped by user. Gracefully exiting...")
            return

    def _handle_success(self, article: Article, data: dict):
        """
        Maps LLM JSON output to database records with deduplication.
        """
        # 1. Map Event Type
        et_name_raw = data.get("event_type")
        et_name = str(et_name_raw).lower() if et_name_raw else "other"
        if et_name == "jailbreak":
            et_name = "jail_break"

        et_id = self.event_types.get(et_name, self.event_types.get("other"))

        # 2. Map State
        state_name_raw = data.get("state")
        state_name_lower = str(state_name_raw).lower() if state_name_raw else ""
        if "fct" in state_name_lower or "abuja" in state_name_lower:
            state_id = self.states.get("fct abuja")
        else:
            state_id = self.states.get(state_name_lower)

        if not state_id:
            article.extraction_status = "failed"
            article.processed = True
            return

        # 3. Handle Location
        loc_name = str(data.get("location", "Unknown")).strip()

        # 4. Deduplication Logic
        # Strategy: If an event of the same type occurred in the same state on the same day
        # with similar casualty counts, it's likely the same event.
        event_date = None
        if data.get("event_date"):
            try:
                event_date = datetime.strptime(data["event_date"], "%Y-%m-%d").date()
            except Exception:
                pass

        if event_date:
            existing_event = (
                self.db.query(Event)
                .join(Location, Location.id == Event.location_id)
                .join(EventStatistics, EventStatistics.event_id == Event.id)
                .filter(
                    Event.event_type_id == et_id,
                    Location.state_id == state_id,
                    Event.event_date == event_date,
                    EventStatistics.killed
                    == int(data.get("killed", 0) if data.get("killed") and type(data.get("killed")) is int else 0),
                    EventStatistics.injured
                    == int(data.get("injured", 0) if data.get("injured") and type(data.get("injured")) is int else 0),
                    EventStatistics.abducted
                    == int(data.get("abducted", 0) if data.get("abducted") and type(data.get("abducted")) is int else 0),
                )
                .first()
            )

            if existing_event:
                # Link this article to the existing event instead of creating a new one
                link = EventSource(event_id=existing_event.id, article_id=article.id)
                self.db.add(link)
                article.processed = True
                article.extraction_status = "success"
                print(
                    f"    [DEDUPLICATED] Linked article to existing event ID: {existing_event.id}"
                )
                return

        # 5. Geocode if not deduplicated
        location = (
            self.db.query(Location)
            .filter(Location.state_id == state_id, Location.name == loc_name)
            .first()
        )

        if not location:
            state_obj = self.db.get(State, state_id)
            lat, lng = self.geocoder.get_coordinates(loc_name, state_obj.name)
            location = Location(
                state_id=state_id, name=loc_name, latitude=lat, longitude=lng
            )
            self.db.add(location)
            self.db.flush()
            time.sleep(1.0)

        # 6. Create New Event
        event = Event(
            event_type_id=et_id,
            location_id=location.id,
            event_date=event_date,
            confidence=data.get("confidence", 0.0),
            summary=data.get("summary"),
        )
        self.db.add(event)
        self.db.flush()

        def safe_int(val):
            if val is None or val == "":
                return 0
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0

        stats = EventStatistics(
            event_id=event.id,
            killed=safe_int(data.get("killed")),
            injured=safe_int(data.get("injured")),
            abducted=safe_int(data.get("abducted")),
        )
        self.db.add(stats)

        link = EventSource(event_id=event.id, article_id=article.id)
        self.db.add(link)

        article.processed = True
        article.extraction_status = "success"
        print(f"    [SUCCESS] Created new event ID: {event.id} in {loc_name}")

    def _handle_irrelevant(self, article: Article):
        article.processed = True
        article.extraction_status = "irrelevant"
        print("    [SKIPPED] Article not a security incident.")

    def _handle_failure(self, article: Article, error: str):
        # We do NOT set processed = True here so the article stays in the 'pending' queue
        article.extraction_status = "failed"
        print(f"    [FAILED] {error} (Will be retried in next run)")


if __name__ == "__main__":
    worker = ExtractionWorker()
    worker.process_pending_articles(limit=100)
