import redis
import random
import time
from typing import List, Dict, Optional


class RideHailingService:
    """
    Use Case Extension: Ride-hailing app with driver location tracking.
    """
    
    def __init__(self, city: str, redis_client: Optional[redis.Redis] = None):
        self.key = f"geo:drivers:{city}"
        self.r = redis_client or redis.Redis(
            host="127.0.0.1",
            port=6379,
            db=0,
            decode_responses=True,
        )
    
    def update_driver_location(self, driver_id: str, longitude: float, latitude: float):
        """Update driver's current location."""
        self.r.geoadd(self.key, [longitude, latitude, driver_id])
        print(f"Driver {driver_id} updated to ({longitude}, {latitude})")
    
    def find_nearby_drivers(self, passenger_lon: float, passenger_lat: float, radius_km: float) -> List[Dict]:
        """Find drivers within radius of passenger."""
        results = self.r.geosearch(
            self.key,
            longitude=passenger_lon,
            latitude=passenger_lat,
            radius=radius_km,
            unit="km",
            withdist=True,
            withcoord=True,
        )
        
        drivers = []
        for item in results:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                drivers.append({
                    "driver_id": item[0],
                    "distance": float(item[1]),
                    "longitude": float(item[2][0]),
                    "latitude": float(item[2][1]),
                })
        
        drivers.sort(key=lambda x: x["distance"])
        return drivers
    
    def remove_driver(self, driver_id: str):
        """Remove driver (e.g., when offline)."""
        removed = self.r.zrem(self.key, driver_id)
        if removed:
            print(f"Driver {driver_id} removed")
        return removed > 0


def demo():
    service = RideHailingService("thimphu")
    
    # Clear old data
    service.r.delete(service.key)
    
    print("="*60)
    print("RIDE-HAILING APP DEMO")
    print("="*60)
    
    # Add some drivers
    print("\n1. Adding drivers online...")
    drivers = [
        ("driver_001", 89.6390, 27.4728),  # Near Norzin
        ("driver_002", 89.6530, 27.4712),  # Changzamtog
        ("driver_003", 89.6490, 27.4770),  # Motithang
        ("driver_004", 89.6410, 27.4750),  # Langjophakha
        ("driver_005", 89.6360, 27.4690),  # Olakha
    ]
    
    for driver_id, lon, lat in drivers:
        service.update_driver_location(driver_id, lon, lat)
    
    # Passenger request at Norzin
    print("\n2. Passenger requesting ride from Norzin (89.6390, 27.4728):")
    nearby = service.find_nearby_drivers(89.6390, 27.4728, radius_km=2)
    
    print(f"\n   Found {len(nearby)} drivers within 2 km:")
    for i, driver in enumerate(nearby, 1):
        print(f"   #{i}: {driver['driver_id']} - {driver['distance']:.3f} km away")
    
    # Simulate driver accepting and moving
    print("\n3. Simulating driver_004 moving closer to passenger...")
    service.update_driver_location("driver_004", 89.6400, 27.4735)
    
    print("\n4. Updated nearby drivers:")
    nearby = service.find_nearby_drivers(89.6390, 27.4728, radius_km=2)
    for i, driver in enumerate(nearby, 1):
        print(f"   #{i}: {driver['driver_id']} - {driver['distance']:.3f} km away")
    
    # Driver goes offline
    print("\n5. Driver_002 goes offline...")
    service.remove_driver("driver_002")
    
    print("\n6. Final nearby drivers:")
    nearby = service.find_nearby_drivers(89.6390, 27.4728, radius_km=2)
    for i, driver in enumerate(nearby, 1):
        print(f"   #{i}: {driver['driver_id']} - {driver['distance']:.3f} km away")


if __name__ == "__main__":
    demo()