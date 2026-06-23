from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..cache.redis_client import get_json, set_json
from ..database import get_db
from ..models import (
    Article,
    Event,
    EventStatistics,
    EventType,
    Location,
    RiskSnapshot,
    State,
)
from ..services.risk_engine import RiskEngine

router = APIRouter()

#  Priority: LLM-extracted event_date > article published_at > system created_at
EFFECTIVE_DATE = func.coalesce(Event.event_date, Article.published_at, Event.created_at)

# ── Risk formula weights ───────────────────────────────────────────────────────
W_INCIDENTS = 0.40
W_FATALITIES = 0.25
W_ABDUCTED = 0.20
W_INJURED = 0.10
W_RECENCY = 0.05  # proportion of incidents in last 7 days vs full period


@router.get("/summary", status_code=200)
def get_stats_summary(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Period for statistics summary"),
):
    """
    Description: Aggregated national incident summary.
    Details: Returns total counts for fatalities (total_killed), injuries (total_injured), abductions
    (total_abducted), and total_incidents based on the effective incident date over a specified number
    of days (default: 30).
    """
    query = (
        db.query(
            func.sum(EventStatistics.killed).label("total_killed"),
            func.sum(EventStatistics.injured).label("total_injured"),
            func.sum(EventStatistics.abducted).label("total_abducted"),
            func.count(func.distinct(Event.id)).label("total_incidents"),
        )
        .join(EventStatistics, EventStatistics.event_id == Event.id)
        .join(Event.articles)
    )  # M2M Join to get published_at

    if days > 0:
        since_date = datetime.now() - timedelta(days=days)
        query = query.filter(EFFECTIVE_DATE >= since_date)

    stats = query.first()

    if not stats:
        return {
            "period_days": days,
            "total_killed": 0,
            "total_injured": 0,
            "total_abducted": 0,
            "total_incidents": 0,
        }

    return {
        "period_days": days,
        "total_killed": stats.total_killed or 0,
        "total_injured": stats.total_injured or 0,
        "total_abducted": stats.total_abducted or 0,
        "total_incidents": stats.total_incidents or 0,
    }


@router.get("/trends", status_code=200)
def get_stats_trends(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Period for trend data"),
):
    """
    Description: Time-series incident data for charts.
    Details: Returns a chronological list of dates and their corresponding incident counts to
    visualize trends over a specified period.
    """
    query = db.query(
        func.date(EFFECTIVE_DATE).label("date"),
        func.count(func.distinct(Event.id)).label("count"),
    ).join(Event.articles)

    if days > 0:
        since_date = datetime.now() - timedelta(days=days)
        query = query.filter(EFFECTIVE_DATE >= since_date)

    trend_data = (
        query.group_by(func.date(EFFECTIVE_DATE))
        .order_by(func.date(EFFECTIVE_DATE).asc())
        .all()
    )

    return [{"date": row.date, "count": row.count} for row in trend_data]


@router.get("/event-types", status_code=200)
def get_event_types_distribution(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Period for risk calculation"),
    state: Optional[str] = Query(None, description="Filter by state name"),
):
    """
    Description: Incident distribution by category (Pie Chart endpoint).
    Details: Returns aggregated counts of incidents grouped by event type (e.g., Kidnapping, Banditry)
    formatted specifically for pie charts. Supports an optional state query parameter to filter the
    pie chart for a specific state.
    """
    query = db.query(EventType.name, func.count(Event.id).label("value")).join(
        Event, Event.event_type_id == EventType.id
    )

    if days > 0:
        since_date = datetime.now() - timedelta(days=days)
        query = query.filter(
            func.coalesce(Event.event_date, Event.created_at) >= since_date
        )

    if state:
        query = (
            query.join(Location, Event.location_id == Location.id)
            .join(State, Location.state_id == State.id)
            .filter(State.name.ilike(state))
        )

    results = query.group_by(EventType.name).all()

    return [{"name": row.name, "value": row.value} for row in results]


@router.get("/states", status_code=200)
def get_state_risk_rankings(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Period for risk calculation"),
):
    """
    Description: Comprehensive state risk rankings.
    Details: Calculates and returns the weighted risk index, Safety Index, risk label (e.g., "High",
    "Critical"), and granular incident metrics for all 37 states. Includes a 7-day trend analysis (up,
    down, stable).
    """
    # 1. Get all states from DB
    all_states = db.query(State).all()

    # Try cache first
    cache_key = f"state_rankings:days={days}"
    cached = get_json(cache_key)
    if cached:
        return cached

    # 2. Get metrics from engine
    state_scores = RiskEngine.get_state_risk_scores(db, days)

    # 3. Get snapshots for trends
    last_week = datetime.now() - timedelta(days=7)
    snapshot_rows = (
        db.query(RiskSnapshot)
        .filter(
            RiskSnapshot.scope == "state",
            RiskSnapshot.snapshot_at >= last_week,
        )
        .order_by(RiskSnapshot.snapshot_at.desc())
        .all()
    )
    snapshot_map = {}
    for snap in snapshot_rows:
        if snap.state_id not in snapshot_map:
            snapshot_map[snap.state_id] = snap.score

    results = []
    for s in all_states:
        data = state_scores.get(s.name)

        if data:
            risk_score = data["risk_score"]
            # Entry already has everything from RiskEngine
            entry = {
                "state": s.name,
                "risk_score": risk_score,
                "safety_index": data["safety_index"],
                "risk_label": data["risk_label"],
                "incidents": data["incidents"],
                "fatalities": data["fatalities"],
                "abducted": data["abducted"],
                "injured": data["injured"],
            }
        else:
            # Default for states with no incidents
            risk_score = 0.0
            entry = {
                "state": s.name,
                "risk_score": 0.0,
                "safety_index": 100.0,
                "risk_label": "Low",
                "incidents": 0,
                "fatalities": 0,
                "abducted": 0,
                "injured": 0,
            }

        # Trend logic
        prev_score = snapshot_map.get(s.id)
        if prev_score is None:
            trend = "new"
            delta = None
        else:
            delta = round(risk_score - prev_score, 1)
            if delta > 1:
                trend = "up"
            elif delta < -1:
                trend = "down"
            else:
                trend = "stable"

        entry.update({"trend": trend, "delta": delta})
        results.append(entry)

    results.sort(key=lambda x: x["risk_score"], reverse=True)

    try:
        set_json(cache_key, results, ex=60*60*24)  # cache every day.
        print("Yes")
    except Exception as e:
        print(f"failed: {e}")
        pass

    return results


@router.get("/national-risk", status_code=200)
def get_national_risk_score(
    db: Session = Depends(get_db),
    days: int = Query(30, description="Period for score calculation"),
):
    """
    Description: Overall national danger score.
    Details: Computes a composite national score (0–100) using incident volume, fatality rates,
    abduction rates, geographical spread, and recency. Returns the score, corresponding Safety Index,
    and weekly trend data.
    """
    cache_key = f"national_risk:days={days}"
    cached = get_json(cache_key)
    if cached:
        return cached

    result = RiskEngine.get_national_risk_score(db, days)
    try:
        set_json(cache_key, result, ex=60*60*24)  # cache every day.
    except Exception:
        pass
    return result
