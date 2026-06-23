from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Article, Event, EventStatistics, Location, RiskSnapshot, State

# ── Risk formula weights ───────────────────────────────────────────────────────
W_INCIDENTS = 0.40
W_FATALITIES = 0.25
W_ABDUCTED = 0.20
W_INJURED = 0.10
W_RECENCY = 0.05

EFFECTIVE_DATE = func.coalesce(Event.event_date, Article.published_at, Event.created_at)


def _classify_risk(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Elevated"
    if score >= 15:
        return "Moderate"
    return "Low"


class RiskEngine:
    @staticmethod
    def classify_risk(score: float) -> str:
        if score >= 75:
            return "Critical"
        if score >= 55:
            return "High"
        if score >= 35:
            return "Elevated"
        if score >= 15:
            return "Moderate"
        return "Low"

    @staticmethod
    def get_state_risk_scores(db: Session, days: int = 30, recency: int = 7):
        since_date = datetime.now() - timedelta(days=days)
        since_xd = datetime.now() - timedelta(days=recency)

        # Base aggregates
        base = (
            db.query(
                State.id.label("state_id"),
                State.name.label("state_name"),
                func.count(func.distinct(Event.id)).label("incidents"),
                func.coalesce(func.sum(EventStatistics.killed), 0).label("fatalities"),
                func.coalesce(func.sum(EventStatistics.abducted), 0).label("abducted"),
                func.coalesce(func.sum(EventStatistics.injured), 0).label("injured"),
            )
            .join(Location, Location.state_id == State.id)
            .join(Event, Event.location_id == Location.id)
            .join(EventStatistics, EventStatistics.event_id == Event.id)
            .join(Event.articles)
            .filter(EFFECTIVE_DATE >= since_date)
            .filter(State.name != "Unknown")
            .group_by(State.id, State.name)
            .all()
        )

        if not base:
            return {}

        # Recency
        recency_rows = (
            db.query(
                State.id.label("state_id"),
                func.count(func.distinct(Event.id)).label("recent_incidents"),
            )
            .join(Location, Location.state_id == State.id)
            .join(Event, Event.location_id == Location.id)
            .join(Event.articles)
            .filter(EFFECTIVE_DATE >= since_xd)
            .group_by(State.id)
            .all()
        )
        recency_map = {r.state_id: r.recent_incidents for r in recency_rows}

        # Max values for normalization
        max_incidents = max((r.incidents for r in base), default=1) or 1
        max_fatalities = max((r.fatalities for r in base), default=1) or 1
        max_abducted = max((r.abducted for r in base), default=1) or 1
        max_injured = max((r.injured for r in base), default=1) or 1

        results = {}
        for row in base:
            recent = recency_map.get(row.state_id, 0)
            recency_ratio = recent / row.incidents if row.incidents else 0

            risk_score = round(
                (
                    (row.incidents / max_incidents) * W_INCIDENTS
                    + (row.fatalities / max_fatalities) * W_FATALITIES
                    + (row.abducted / max_abducted) * W_ABDUCTED
                    + (row.injured / max_injured) * W_INJURED
                    + recency_ratio * W_RECENCY
                )
                * 100,
                1,
            )

            results[row.state_name] = {
                "state_id": row.state_id,
                "risk_score": risk_score,
                "safety_index": round(100 - risk_score, 1),
                "risk_label": RiskEngine.classify_risk(risk_score),
                "incidents": row.incidents,
                "fatalities": row.fatalities,
                "abducted": row.abducted,
                "injured": row.injured,
                "recent_7d": recent,
            }

        return results

    @staticmethod
    def get_national_risk_score(db: Session, days: int = 30, recency: int = 7):
        TOTAL_STATES = 37
        INCIDENT_CEIL = 500
        since_date = datetime.now() - timedelta(days=days)
        since_xd = datetime.now() - timedelta(days=recency)

        totals = (
            db.query(
                func.count(func.distinct(Event.id)).label("total_incidents"),
                func.coalesce(func.sum(EventStatistics.killed), 0).label(
                    "total_killed"
                ),
                func.coalesce(func.sum(EventStatistics.abducted), 0).label(
                    "total_abducted"
                ),
                func.count(func.distinct(Location.state_id)).label("states_affected"),
            )
            .join(EventStatistics, EventStatistics.event_id == Event.id)
            .join(Location, Location.id == Event.location_id)
            .join(Article, Event.articles)
            .filter(EFFECTIVE_DATE >= since_date)
            .first()
        )

        recent_count = (
            db.query(func.count(func.distinct(Event.id)))
            .join(Article, Event.articles)
            .filter(EFFECTIVE_DATE >= since_xd)
            .scalar()
            or 0
        )

        ti = totals.total_incidents or 0
        tk = totals.total_killed or 0
        ta = totals.total_abducted or 0
        sa = totals.states_affected or 0

        incident_vol = min((ti / INCIDENT_CEIL) * 100, 100)
        fatality_rate = min((tk / ti / 5) * 100 if ti else 0, 100)
        abduction_rate = min((ta / ti / 10) * 100 if ti else 0, 100)
        geo_spread = (sa / TOTAL_STATES) * 100
        recency = min((recent_count / ti * 100) if ti else 0, 100)

        score = round(
            (incident_vol + fatality_rate + abduction_rate + geo_spread + recency) / 5,
            1,
        )

        last_snap = (
            db.query(RiskSnapshot)
            .filter_by(scope="national")
            .order_by(RiskSnapshot.snapshot_at.desc())
            .first()
        )
        if last_snap:
            delta = round(score - last_snap.score, 1)
            trend = "up" if delta > 1 else ("down" if delta < -1 else "stable")
        else:
            delta = None
            trend = "new"

        return {
            "risk_score": score,
            "safety_index": round(100 - score, 1),
            "label": _classify_risk(score),
            "delta": delta,
            "trend": trend,
            "computed_at": datetime.now().isoformat(),
        }
