import folium
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="travel_planner")

def get_coords(city_name: str) -> list[float] | None:
    """
    Fetches the geographic coordinates (latitude, longitude) for a given city name.

    Args:
        city_name (str): The name of the city to geocode.

    Returns:
        list[float] | None: A list [latitude, longitude] if found, else None.
    """
    try:
        print(f"Geocoding city: {city_name}")
        location = geolocator.geocode(city_name, timeout=10)
        if location:
            print(f"Found: {city_name} at {location.latitude}, {location.longitude}")
            return [location.latitude, location.longitude]
        print(f"NOT FOUND: {city_name}")
        return None
    except Exception as e:
        print("Geopy error:", e)
        return None


def build_basic_route_map(origin_city: str, dest_city: str) -> folium.Map:
    """
    Builds a Folium route map between two cities using their coordinates.

    Args:
        origin_city (str): The starting city name.
        dest_city (str): The destination city name.

    Returns:
        folium.Map: A Folium map object with origin/destination markers and a route line.
    """
    origin_coords = get_coords(origin_city)
    dest_coords = get_coords(dest_city)

    if not origin_coords or not dest_coords:
        # Show a blank map with a warning
        m = folium.Map(location=[20,0], zoom_start=2)
        folium.Marker([20, 0], tooltip="No route available").add_to(m)
        return m

    m = folium.Map(location=origin_coords, zoom_start=4)
    folium.Marker(origin_coords, tooltip="Origin", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(dest_coords, tooltip="Destination", icon=folium.Icon(color='red')).add_to(m)
    folium.PolyLine([origin_coords, dest_coords], color="blue", weight=3).add_to(m)
    return m
