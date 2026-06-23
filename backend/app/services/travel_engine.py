from typing import Any, Dict, Optional

import requests

from ..core.config import settings
from .geocoder import GeocoderService


class TravelEngine:
    def __init__(self):
        self.ors_api_key = settings.ORS_API_KEY
        self.ors_base_url = (
            "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
        )
        self.geocoder = GeocoderService()

    def get_route(
        self, start_coords: tuple, end_coords: tuple
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches route geometry from OpenRouteService.
        coords are (lat, lon)
        """
        if not self.ors_api_key:
            print("[TRAVEL ENGINE] ORS_API_KEY not found in environment.")
            return None

        # ORS expects (lon, lat)
        body = {
            "coordinates": [
                [start_coords[1], start_coords[0]],
                [end_coords[1], end_coords[0]],
            ],
            "radiuses": [-1, -1],
        }
        headers = {
            "Accept": "application/geo+json, application/json",
            "Authorization": self.ors_api_key,
            "Content-Type": "application/json; charset=utf-8",
        }

        try:
            print(f"[TRAVEL ENGINE] Fetching route: {start_coords} -> {end_coords}")
            response = requests.post(
                self.ors_base_url, json=body, headers=headers, timeout=15
            )
            if response.status_code != 200:
                print(
                    f"[TRAVEL ENGINE] API Error {response.status_code}: {response.text}"
                )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[TRAVEL ENGINE] Exception during routing: {e}")
            return None

    def extract_route_info(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Samples coordinates along the route to identify states,
        and extracts distance/duration.
        """
        states = []
        state_set = set()
        distance_km = 0
        duration_mins = 0

        try:
            feature = route_data["features"][0]
            properties = feature.get("properties", {}).get("summary", {})

            # ORS returns distance in meters and duration in seconds
            distance_km = round(properties.get("distance", 0) / 1000, 1)
            duration_mins = round(properties.get("duration", 0) / 60, 0)

            geometry = feature["geometry"]["coordinates"]

            # Sample points to identify states in sequence
            total_points = len(geometry)
            sample_count = 12
            sample_rate = max(1, total_points // sample_count)

            sampled_coords = geometry[::sample_rate]
            if geometry[-1] not in sampled_coords:
                sampled_coords.append(geometry[-1])

            for lon, lat in sampled_coords:
                state = self.geocoder.reverse_geocode(lat, lon)
                if state and state not in state_set:
                    state_set.add(state)
                    states.append(state)

                # Nominatim rate limit safety
                import time

                time.sleep(1)

            return {
                "states": states,
                "distance_km": distance_km,
                "duration_mins": duration_mins,
            }
        except Exception as e:
            print(f"[TRAVEL ENGINE] Error extracting route info: {e}")
            return {
                "states": list(state_set),
                "distance_km": distance_km,
                "duration_mins": duration_mins,
            }
