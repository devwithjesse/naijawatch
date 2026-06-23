import time
import requests
from typing import Optional, Tuple

class GeocoderService:
    def __init__(self):
        # Nominatim (OpenStreetMap)
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            "User-Agent": "NaijaWatch_Intelligence_System/1.0"
        }

    def get_coordinates(self, location_name: str, state_name: str, retries: int = 5) -> Tuple[Optional[float], Optional[float]]:
        """
        Converts location + state into Latitude and Longitude with retry logic.
        Strictly targets Nigeria to avoid international collisions (e.g. Lagos, Chile).
        """
        # Clean up query: If location is "General", just search the state.
        if location_name.lower() == "general":
            query = f"{state_name}, Nigeria"
        else:
            query = f"{location_name}, {state_name}, Nigeria"
        
        for attempt in range(1, retries + 1):
            try:
                response = requests.get(
                    self.base_url, 
                    params={
                        "q": query, 
                        "format": "json", 
                        "limit": 1,
                        "countrycodes": "ng" # STRICTLY limit search to Nigeria
                    }, 
                    headers=self.headers, 
                    timeout=15
                )
                
                if response.status_code == 429:
                    # Exponential backoff: 2, 4, 8, 16, 32 seconds
                    wait_time = 2 ** attempt
                    print(f"      [GEOCODE 429] Rate limit hit. Waiting {wait_time}s (Attempt {attempt}/{retries})...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                data = response.json()

                if data:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    return lat, lng
                
                # Fallback: Search just the state if specific location fails
                if location_name.lower() != "general" and attempt == 1:
                    print(f"      [GEOCODE] Location '{location_name}' failed. Falling back to state '{state_name}'...")
                    return self.get_coordinates("General", state_name, retries=2)
                    
                return 0.0, 0.0

            except requests.exceptions.RequestException as e:
                if attempt == retries:
                    print(f"      [GEOCODE ERROR] Failed for '{query}' after {retries} attempts: {e}")
                time.sleep(1 * attempt)
            except Exception as e:
                print(f"      [GEOCODE ERROR] Unexpected error for '{query}': {e}")
                return 0.0, 0.0
                
        return 0.0, 0.0

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Converts coordinates into a state name in Nigeria.
        """
        url = "https://nominatim.openstreetmap.org/reverse"
        try:
            response = requests.get(
                url,
                params={"lat": lat, "lon": lon, "format": "json"},
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            address = data.get("address", {})
            state = address.get("state")
            
            if state:
                state = state.replace(" State", "")
                if "Federal Capital Territory" in state:
                    return "FCT"
            return state
        except Exception as e:
            print(f"      [REVERSE GEOCODE ERROR] {e}")
            return ""
