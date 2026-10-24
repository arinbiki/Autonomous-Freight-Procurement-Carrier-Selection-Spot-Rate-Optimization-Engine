"""
Transit Time Intelligence Engine.
Predicts statistical transit time distributions (P50, P80, P90),
DOT Hours-of-Service driver rest, dwell buffers, and on-time arrival probabilities.
"""
import math
from typing import Tuple
from core.models import Shipment, Carrier, TransportMode, TransitPrediction
from core.config import MODE_AVERAGE_SPEED_MPH

def predict_transit_metrics(
    shipment: Shipment,
    carrier: Carrier,
    mode: TransportMode,
    road_miles: float,
    congestion_factor: float = 1.0,
    weather_risk_factor: float = 0.05
) -> TransitPrediction:
    """
    Computes statistical transit time distribution and delivery window SLA adherence.
    """
    avg_speed = MODE_AVERAGE_SPEED_MPH.get(mode.value, 48.0)
    
    # 1. Pure Driving Time
    driving_hours = road_miles / avg_speed
    
    # 2. DOT Hours of Service (HOS) Rest Periods (10h rest per 11h driving for solo drivers)
    is_team_driver = road_miles > 1100.0 or carrier.name.lower().find("expedite") != -1
    if is_team_driver or mode in (TransportMode.AIR, TransportMode.RAIL, TransportMode.INTERMODAL):
        hos_rest_hours = 0.0
    else:
        rest_cycles = int(driving_hours // 11)
        hos_rest_hours = rest_cycles * 10.0
        
    # 3. Dwell & Handling Time
    origin_handling = max(1.5, shipment.origin.avg_dwell_hours)
    dest_handling = max(1.5, shipment.destination.avg_dwell_hours)
    base_dwell_hours = origin_handling + dest_handling
    
    # 4. Corridor Congestion & Weather Buffers
    congestion_delay = driving_hours * (congestion_factor - 1.0)
    weather_delay = driving_hours * weather_risk_factor
    risk_buffer = round(congestion_delay + weather_delay, 1)
    
    # 5. Statistical Distributions (P50, P80, P90)
    p50_hours = round(driving_hours + hos_rest_hours + base_dwell_hours, 1)
    # Carrier historical on-time delivery rate adjusts variance
    carrier_variance_factor = 1.0 + (1.0 - carrier.on_time_delivery_rate)
    
    p80_hours = round(p50_hours + (risk_buffer * 1.3 * carrier_variance_factor), 1)
    p90_hours = round(p50_hours + (risk_buffer * 2.2 * carrier_variance_factor), 1)
    expected_hours = round((p50_hours * 0.5) + (p80_hours * 0.3) + (p90_hours * 0.2), 1)
    
    # 6. Available Time Window
    available_hours = (shipment.requested_delivery - shipment.requested_pickup).total_seconds() / 3600.0
    available_hours = max(available_hours, 1.0)
    
    # 7. Probability of On-Time Delivery
    # Modeled via sigmoid/cumulative distribution
    time_slack = available_hours - p50_hours
    if time_slack <= -12.0:
        on_time_prob = 0.05
    elif time_slack >= (p90_hours - p50_hours):
        # Slack easily accommodates P90
        base_otd = carrier.on_time_delivery_rate
        on_time_prob = min(0.99, max(0.70, base_otd * (1.0 - (weather_risk_factor * 0.5))))
    else:
        # Interpolate between 0.30 and carrier historical baseline
        fraction = max(0.0, time_slack / max(1.0, (p90_hours - p50_hours)))
        on_time_prob = round(0.30 + (fraction * (carrier.on_time_delivery_rate - 0.30)), 3)
        
    return TransitPrediction(
        p50_hours=p50_hours,
        p80_hours=p80_hours,
        p90_hours=p90_hours,
        expected_hours=expected_hours,
        on_time_probability=round(on_time_prob, 3),
        risk_buffer_hours=risk_buffer
    )
