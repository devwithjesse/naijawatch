from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..cache.redis_client import get_json, set_json
from ..database import get_db
from ..models import Article, Event

router = APIRouter()

# Helper for effective date (same as stats)
EFFECTIVE_DATE = func.coalesce(Event.event_date, Article.published_at, Event.created_at)


@router.get("/", response_model=List[schemas.Event], status_code=200)
def get_events(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of past days to include"),
    limit: int = Query(200, description="Max number of events to return"),
    state: Optional[str] = Query(None, description="Filter by state name"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
):
    """
    Description: Comprehensive list of security events.
    Details: Returns a detailed list of recent security events. Supports robust filtering via query
    parameters: days (lookback period), limit (max results), state (name filter), and event_type
    (category filter).
    """
    query = db.query(models.Event).join(models.Event.articles)

    # 1. Date Filter (using hierarchy)
    if days > 0:
        since_date = datetime.now() - timedelta(days=days)
        query = query.filter(EFFECTIVE_DATE >= since_date)

    # 2. State Filter
    if state:
        query = (
            query.join(models.Location)
            .join(models.State)
            .filter(models.State.name.ilike(state))
        )

    # 3. Event Type Filter
    if event_type:
        query = query.join(models.EventType).filter(
            models.EventType.name.ilike(event_type)
        )

    events = query.order_by(EFFECTIVE_DATE.desc()).limit(limit).all()
    return events


@router.get("/map", status_code=200)
def get_events_map(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of past days to include"),
    state: Optional[str] = Query(None, description="Filter by state name"),
):
    """
    Description: Lightweight event payload for map markers.
    Details: Returns highly optimized event data (only id, lat, lng, type, and summary) to ensure fast
    rendering of map components without heavy full-event payloads. Supports filtering by days and
    state.
    """
    query = (
        db.query(
            models.Event.id,
            models.Location.latitude,
            models.Location.longitude,
            models.EventType.name.label("event_type"),
            models.Event.summary,
        )
        .join(models.Location, models.Event.location_id == models.Location.id)
        .join(models.EventType, models.Event.event_type_id == models.EventType.id)
    )

    if days > 0:
        since_date = datetime.now() - timedelta(days=days)
        # Using Event.created_at as a fallback for map query simplicity,
        # or we could join articles but it slows the map query.
        query = query.filter(
            func.coalesce(models.Event.event_date, models.Event.created_at)
            >= since_date
        )

    if state:
        query = query.join(
            models.State, models.Location.state_id == models.State.id
        ).filter(models.State.name.ilike(state))

    # Filter out events without coordinates
    query = query.filter(
        models.Location.latitude != None, models.Location.longitude != None
    )

    # Build cache key
    cache_key = f"events_map:days={days}:state={(state or '__all').lower()}"
    cached = get_json(cache_key)
    if cached:
        return cached

    events = query.limit(500).all()

    payload = [
        {
            "id": e.id,
            "lat": e.latitude,
            "lng": e.longitude,
            "type": e.event_type,
            "summary": e.summary,
        }
        for e in events
    ]

    try:
        set_json(cache_key, payload, ex=60*60)  # cache 1hr
    except Exception:
        pass

    return payload


@router.get("/{event_id}", response_model=schemas.Event, status_code=200)
def get_event(event_id: int, db: Session = Depends(get_db)):
    """
    Description: Single event details.
    Details: Retrieves the full database record for a specific security event using its path parameter
    event_id. Returns a 404 if not found.
    """
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
