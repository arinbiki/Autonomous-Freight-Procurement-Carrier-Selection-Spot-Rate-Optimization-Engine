"""
Data Enrichment Module for Freight Procurement.
Calculates geodesic route distances with road circuity, assesses corridor congestion,
weather exposure, seasonal rate benchmarks, and historical lane reliability.
"""
import math
from typing import Dict, Any
from core.models import Shipment, TransportMode

def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in miles.
    """
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_route_distance(origin_lat: float, origin_lon: float,
                             dest_lat: float, dest_lon: float,
                             mode: TransportMode = TransportMode.ROAD_FTL) -> float:
    """
    Applies empirical circuity multiplier to great circle distance:
    - Highway/Road: 1.17x
    - Intermodal/Rail: 1.24x
    - Ocean: 1.35x
    - Air: 1.05x
    """
    gc_dist = haversine_distance_miles(origin_lat, origin_lon, dest_lat, dest_lon)
    
    circuity_factors = {
        TransportMode.ROAD_FTL: 1.17,
        TransportMode.ROAD_LTL: 1.20,
        TransportMode.INTERMODAL: 1.24,
        TransportMode.RAIL: 1.28,
        TransportMode.OCEAN: 1.35,
        TransportMode.AIR: 1.05,
        TransportMode.COURIER: 1.15,
        TransportMode.DEDICATED_FLEET: 1.16,
    }
    factor = circuity_factors.get(mode, 1.17)
    return round(max(gc_dist * factor, 25.0), 1)

def enrich_shipment_context(shipment: Shipment) -> Dict[str, Any]:
    """
    Enriches the normalized shipment with computed distance, lane ID,
    congestion factor, seasonal tightness, and baseline benchmark cost.
    """
    orig = shipment.origin
    dest = shipment.destination
    
    road_miles = calculate_route_distance(
        orig.latitude, orig.longitude, dest.latitude, dest.longitude, TransportMode.ROAD_FTL
    )
    
    lane_id = f"{orig.city.upper()[:4]}_{orig.state.upper()}-{dest.city.upper()[:4]}_{dest.state.upper()}"
    
    # Corridor Congestion Factor (heuristics based on major metropolitan bottlenecks)
    congested_hubs = {"CHICAGO", "LOS ANGELES", "NEW YORK", "ATLANTA", "DALLAS"}
    congestion_score = 1.0
    if orig.city.upper() in congested_hubs:
        congestion_score += 0.08
    if dest.city.upper() in congested_hubs:
        congestion_score += 0.08
        
    # Weather Risk (higher in winter months Nov-Feb for northern lanes)
    pickup_month = shipment.requested_pickup.month
    northern_states = {"IL", "MI", "OH", "PA", "NY", "IN", "WI", "MN", "WA"}
    weather_risk = 0.05
    if pickup_month in (11, 12, 1, 2) and (orig.state.upper() in northern_states or dest.state.upper() in northern_states):
        weather_risk = 0.22  # elevated snow/ice risk
        
    # Baseline Spot Rate Benchmark per mile (e.g. $2.35/mi standard dry van, $2.95/mi reefer)
    base_rpm = 2.95 if shipment.commodity.is_temp_controlled else 2.35
    if shipment.commodity.is_hazmat:
        base_rpm += 0.45
        
    benchmark_linehaul = round(road_miles * base_rpm, 2)
    benchmark_fuel = round(benchmark_linehaul * 0.18, 2)
    
    return {
        "lane_id": lane_id,
        "road_miles": road_miles,
        "intermodal_miles": calculate_route_distance(orig.latitude, orig.longitude, dest.latitude, dest.longitude, TransportMode.INTERMODAL),
        "congestion_factor": round(congestion_score, 2),
        "weather_risk_factor": round(weather_risk, 2),
        "benchmark_linehaul_usd": benchmark_linehaul,
        "benchmark_fuel_usd": benchmark_fuel,
        "benchmark_total_usd": round(benchmark_linehaul + benchmark_fuel, 2),
        "is_long_haul": road_miles > 500.0,
        "requires_team_drivers": road_miles > 1100.0
    }
