import time

from app.database import SessionLocal
from app.models import Location, State
from app.services.geocoder import GeocoderService


def backfill_null_locations():
    """
    Finds all locations in the DB with null coordinates and attempts to geocode them.
    """
    db = SessionLocal()
    geocoder = GeocoderService()

    # Find locations that have missing lat/lng but are not strictly "Unknown"
    null_locations = (
        db.query(Location)
        .filter(
            Location.latitude == None,
            Location.longitude == None,
            Location.name != "Unknown",
        )
        .all()
    )

    if not null_locations:
        print("✅ No valid locations found missing coordinates.")
        return

    print(
        f"🔍 Found {len(null_locations)} locations missing coordinates. Starting backfill...\n"
    )

    success = 0
    failed = 0

    for loc in null_locations:
        state_obj = db.get(State, loc.state_id)
        if not state_obj:
            continue

        print(f"  - Geocoding: {loc.name}, {state_obj.name}...")

        lat, lng = geocoder.get_coordinates(loc.name, state_obj.name)

        if lat and lng:
            loc.latitude = lat
            loc.longitude = lng
            db.commit()
            print(f"    ✅ Success: {lat}, {lng}")
            success += 1
        else:
            print("    ❌ Failed to find coordinates.")
            failed += 1

        # Hard sleep to respect Nominatim 1req/sec limit across the entire batch
        time.sleep(1.5)

    print(f"\n📊 Backfill Complete: {success} fixed, {failed} still unknown.")


if __name__ == "__main__":
    backfill_null_locations()
