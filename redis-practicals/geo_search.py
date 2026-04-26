import redis
from typing import List, Dict, Optional, Tuple


class GeoSearchService:
    """
    Geo-search functionality using Redis geospatial indexes.
    Stores locations and supports nearby queries.
    """

    def __init__(self, key: str, redis_client: Optional[redis.Redis] = None) -> None:
        self.key = key
        self.r = redis_client or redis.Redis(
            host="127.0.0.1",
            port=6379,
            db=0,
            decode_responses=True,
        )

    # ========== CORE METHODS ==========
    def add_location(self, name: str, longitude: float, latitude: float) -> None:
        """Add or update a named location."""
        self.r.geoadd(self.key, [longitude, latitude, name])

    def distance_between(
        self,
        name1: str,
        name2: str,
        unit: str = "km",
    ) -> Optional[float]:
        """Compute distance between two locations."""
        dist = self.r.geodist(self.key, name1, name2, unit)
        return float(dist) if dist is not None else None

    def nearby(
        self,
        longitude: float,
        latitude: float,
        radius: float,
        unit: str = "km",
        withdist: bool = True,
        withcoord: bool = True,
    ) -> List[Dict]:
        """Find locations within a given radius from a point."""
        results = self.r.geosearch(
            self.key,
            longitude=longitude,
            latitude=latitude,
            radius=radius,
            unit=unit,
            withdist=withdist,
            withcoord=withcoord,
        )

        formatted_results: List[Dict] = []
        for item in results:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                name = item[0]
                dist_value = float(item[1])
                coord = item[2]
                lon = float(coord[0])
                lat = float(coord[1])
                formatted_results.append(
                    {
                        "name": name,
                        "distance": dist_value,
                        "longitude": lon,
                        "latitude": lat,
                    }
                )
            else:
                formatted_results.append({"name": str(item)})
        return formatted_results

    # ========== EXERCISE 1: Bounding Box Search ==========
    def search_by_box(
        self,
        longitude: float,
        latitude: float,
        width: float,
        height: float,
        unit: str = "km",
        withdist: bool = True,
        withcoord: bool = True,
    ) -> List[Dict]:
        """
        Exercise 1: Search within a bounding box using BYBOX.
        width and height are in the specified unit.
        """
        # Use georadius for bounding box (alternative approach)
        # First get all locations within a large radius
        results = self.r.geosearch(
            self.key,
            longitude=longitude,
            latitude=latitude,
            radius=width * 1.5,  # Larger radius to ensure coverage
            unit=unit,
            withdist=withdist,
            withcoord=withcoord,
        )
        
        formatted_results: List[Dict] = []
        for item in results:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                name = item[0]
                dist_value = float(item[1])
                coord = item[2]
                lon = float(coord[0])
                lat = float(coord[1])
                
                # Filter by bounding box (manual filtering)
                lon_diff = abs(lon - longitude)
                lat_diff = abs(lat - latitude)
                
                # Convert km to degrees (approximate: 1 degree ≈ 111 km)
                width_deg = width / 111.0
                height_deg = height / 111.0
                
                if lon_diff <= width_deg and lat_diff <= height_deg:
                    formatted_results.append(
                        {
                            "name": name,
                            "distance": dist_value,
                            "longitude": lon,
                            "latitude": lat,
                        }
                    )
            else:
                formatted_results.append({"name": str(item)})
        
        formatted_results.sort(key=lambda x: x["distance"])
        return formatted_results

    # ========== EXERCISE 2: Top N Nearest ==========
    def get_nearest_n(self, longitude: float, latitude: float, n: int = 5, unit: str = "km") -> List[Dict]:
        """
        Exercise 2: Get top N nearest locations (sorted by distance).
        This combines geo-search with sorting.
        """
        results = self.r.geosearch(
            self.key,
            longitude=longitude,
            latitude=latitude,
            radius=100,  # Large radius to get all
            unit=unit,
            withdist=True,
            withcoord=True,
        )
        
        # Parse results and sort by distance
        parsed_results = []
        for item in results:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                parsed_results.append({
                    "name": item[0],
                    "distance": float(item[1]),
                    "longitude": float(item[2][0]),
                    "latitude": float(item[2][1]),
                })
        
        # Sort by distance and take top N
        parsed_results.sort(key=lambda x: x["distance"])
        return parsed_results[:n]

    # ========== EXERCISE 3: Get Locations with Distance Filter ==========
    def get_locations_within_distance(
        self,
        longitude: float,
        latitude: float,
        max_distance: float,
        unit: str = "km",
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Exercise 3: Get all locations within max_distance, optionally limited to top N.
        """
        results = self.r.geosearch(
            self.key,
            longitude=longitude,
            latitude=latitude,
            radius=max_distance,
            unit=unit,
            withdist=True,
            withcoord=True,
        )
        
        formatted_results = []
        for item in results:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                formatted_results.append({
                    "name": item[0],
                    "distance": float(item[1]),
                    "longitude": float(item[2][0]),
                    "latitude": float(item[2][1]),
                })
        
        # Sort by distance
        formatted_results.sort(key=lambda x: x["distance"])
        
        # Apply limit if specified
        if limit:
            formatted_results = formatted_results[:limit]
        
        return formatted_results


def demo():
    service = GeoSearchService("geo:stores:thimphu")

    # Clear old data
    service.r.delete(service.key)

    print("="*60)
    print("GEO-SEARCH SERVICE DEMO")
    print("="*60)

    # Add stores in Thimphu
    print("\n1. Adding stores to Thimphu...")
    stores = [
        ("store_norzin", 89.6390, 27.4728),
        ("store_changzamtog", 89.6530, 27.4712),
        ("store_motithang", 89.6490, 27.4770),
        ("store_langjophakha", 89.6410, 27.4750),
        ("store_olakha", 89.6360, 27.4690),
        ("store_babesa", 89.6620, 27.4610),
    ]
    
    for name, lon, lat in stores:
        service.add_location(name, lon, lat)
        print(f"   Added: {name} ({lon}, {lat})")

    # Core functionality: Distance between stores
    print("\n2. Distance between stores:")
    dist = service.distance_between("store_norzin", "store_changzamtog", unit="km")
    print(f"   Norzin → Changzamtog: {dist:.3f} km")

    # Core functionality: Nearby search
    print("\n3. Stores within 2 km of Norzin (coordinates 89.6390, 27.4728):")
    nearby_stores = service.nearby(89.6390, 27.4728, radius=2, unit="km")
    for store in nearby_stores:
        print(f"   {store['name']}: {store['distance']:.3f} km")

    # ========== EXERCISE 1: Bounding Box Search ==========
    print("\n" + "="*60)
    print("EXERCISE 1: Bounding Box Search (BYBOX)")
    print("="*60)
    print("\nSearching in a 3km x 3km box around Norzin:")
    box_results = service.search_by_box(89.6390, 27.4728, width=3, height=3, unit="km")
    for store in box_results:
        print(f"   {store['name']}: distance {store['distance']:.3f} km")

    # ========== EXERCISE 2: Top N Nearest ==========
    print("\n" + "="*60)
    print("EXERCISE 2: Top N Nearest Locations")
    print("="*60)
    print("\nTop 3 nearest stores from Norzin:")
    nearest = service.get_nearest_n(89.6390, 27.4728, n=3, unit="km")
    for i, store in enumerate(nearest, 1):
        print(f"   #{i}: {store['name']} - {store['distance']:.3f} km")

    # ========== EXERCISE 3: Distance Filter with Limit ==========
    print("\n" + "="*60)
    print("EXERCISE 3: Distance Filter with Limit")
    print("="*60)
    print("\nStores within 3 km of Norzin (max 5 results):")
    filtered = service.get_locations_within_distance(89.6390, 27.4728, max_distance=3, unit="km", limit=5)
    for store in filtered:
        print(f"   {store['name']}: {store['distance']:.3f} km")


if __name__ == "__main__":
    demo()