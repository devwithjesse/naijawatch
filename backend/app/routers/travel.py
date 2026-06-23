from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..cache.redis_client import get_json, set_json
from ..database import get_db
from ..schemas import TravelRequest
from ..services.geocoder import GeocoderService
from ..services.llm import LLMService
from ..services.risk_engine import RiskEngine
from ..services.travel_engine import TravelEngine

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

geocoder = GeocoderService()
travel_engine = TravelEngine()
llm_service = LLMService()


@router.post("/risk")
@limiter.limit("2/5minutes")
async def check_travel_risk(
    request: Request, payload: TravelRequest, db: Session = Depends(get_db)
):
    """
    Description: AI-powered travel risk assessment.
    Details: Accepts an origin and destination, geocodes the locations, calculates the driving route,
    and evaluates the security risk across the states the route passes through. Generates a dynamic AI
    travel advisory based on the aggregated risk score.
    """
    # 1. Geocode origin and destination
    start_lat, start_lon = geocoder.get_coordinates("General", payload.origin)
    end_lat, end_lon = geocoder.get_coordinates("General", payload.destination)

    if not start_lat or not end_lat:
        raise HTTPException(
            status_code=400, detail="Could not locate origin or destination."
        )

    # 2. Check route/states cache (keyed by rounded start/end coordinates)
    def _route_key(slat, slng, elat, elng):
        return f"route_states:{slat:.4f}:{slng:.4f}:{elat:.4f}:{elng:.4f}"

    cache_key = _route_key(start_lat, start_lon, end_lat, end_lon)
    cached = get_json(cache_key)
    if cached:
        route_info = cached
    else:
        # 3. Get route geometry
        route_data = travel_engine.get_route((start_lat, start_lon), (end_lat, end_lon))
        if not route_data:
            raise HTTPException(status_code=500, detail="Could not calculate route.")

        # 4. Extract states and route info
        route_info = travel_engine.extract_route_info(route_data)
        # Cache the route info (states, distance, duration) for 7 days.
        try:
            set_json(cache_key, route_info, ex=24 * 3600 * 7)
        except Exception:
            pass

    states_along_route = route_info.get("states", [])
    distance_km = route_info.get("distance_km", 0)
    duration_mins = route_info.get("duration_mins", 0)

    if not states_along_route:
        # Fallback to origin/destination states if sampling fails
        origin_state = geocoder.reverse_geocode(start_lat, start_lon)
        dest_state = geocoder.reverse_geocode(end_lat, end_lon)
        states_along_route = list(set(filter(None, [origin_state, dest_state])))

    # 4. Aggregate risk data for these states
    all_state_scores = RiskEngine.get_state_risk_scores(db)

    journey_states_data = []
    total_risk = 0
    count = 0

    for state in states_along_route:
        state_data = all_state_scores.get(state)
        if state_data:
            journey_states_data.append({"state": state, **state_data})
            total_risk += state_data["risk_score"]
            count += 1
        else:
            journey_states_data.append(
                {
                    "state": state,
                    "risk_score": 0,
                    "safety_index": 100,
                    "risk_label": "Unknown/Low",
                    "incidents": 0,
                }
            )

    # 5. Final Report
    avg_risk = round(total_risk / count, 1) if count > 0 else 0
    journey_safety_index = round(100 - avg_risk, 1)

    # 6. Generate AI Advisory
    advisory = llm_service.get_travel_advisory(
        origin=payload.origin,
        destination=payload.destination,
        risk_score=avg_risk,
        states=states_along_route,
        distance=distance_km,
    )

    return {
        "origin": payload.origin,
        "destination": payload.destination,
        "trip_details": {
            "distance_km": distance_km,
            "estimated_duration_mins": duration_mins,
            "hours": int(duration_mins // 60),
            "minutes": int(duration_mins % 60),
        },
        "route_summary": {
            "states_passed": states_along_route,
            "journey_risk_score": avg_risk,
            "journey_safety_index": journey_safety_index,
            "overall_label": RiskEngine.classify_risk(avg_risk),
        },
        "state_breakdown": journey_states_data,
        "advisory": advisory,
    }
