"""
Carrier Performance and Composite Scoring Engine.
Computes multi-dimensional performance scores (Cost, Service, Risk, Capacity, Sustainability)
with dynamic, context-aware weighting based on shipment priority and customer tier.
"""
from core.models import (
    Shipment, Carrier, CarrierScore, ShipmentPriority, CustomerTier
)

def score_carrier_candidate(
    shipment: Shipment,
    carrier: Carrier,
    expected_cost: float,
    benchmark_cost: float,
    on_time_probability: float,
    risk_score: float,
    capacity_confidence: float,
    esg_score: float
) -> CarrierScore:
    """
    Computes 5 normalized dimension scores (0 - 100) and weighted composite score.
    """
    # 1. Cost Score (0 - 100)
    # Ratio = expected_cost / benchmark_cost.
    # Cost ratio 0.50 -> 100 pts. Cost ratio 1.00 (at benchmark) -> 65 pts. Cost ratio 1.30 -> 35 pts.
    cost_ratio = expected_cost / max(1.0, benchmark_cost)
    cost_score = max(10.0, min(100.0, 100.0 - ((cost_ratio - 0.50) * 70.0)))
    
    # 2. Service Score (0 - 100)
    # Blend of carrier historical OTD and model-predicted on-time arrival probability
    otd_pts = carrier.on_time_delivery_rate * 100.0
    prob_pts = on_time_probability * 100.0
    tender_pts = carrier.tender_acceptance_rate * 100.0
    service_score = (otd_pts * 0.45) + (prob_pts * 0.35) + (tender_pts * 0.20)
    service_score = max(10.0, min(100.0, service_score))
    
    # 3. Risk Score (Inverted: higher score = lower risk / safer carrier)
    safety_pts = carrier.safety_score
    claim_deduction = carrier.claims_rate_pct * 25.0
    fin_deduction = carrier.financial_risk_score * 0.5
    raw_risk = safety_pts - claim_deduction - fin_deduction - (risk_score * 0.25)
    carrier_risk_score = max(10.0, min(100.0, raw_risk))
    
    # 4. Capacity Score (0 - 100)
    capacity_score = max(10.0, min(100.0, capacity_confidence * 100.0))
    
    # 5. Sustainability Score (0 - 100)
    sustainability_score = max(10.0, min(100.0, esg_score))
    
    # Dynamic Weighting depending on cargo type & priority
    if shipment.commodity.is_hazmat or shipment.commodity.is_temp_controlled:
        weights = {"cost": 0.15, "service": 0.30, "risk": 0.35, "capacity": 0.15, "esg": 0.05}
    elif shipment.priority == ShipmentPriority.CRITICAL:
        weights = {"cost": 0.10, "service": 0.45, "risk": 0.25, "capacity": 0.20, "esg": 0.00}
    elif shipment.priority == ShipmentPriority.HIGH:
        weights = {"cost": 0.20, "service": 0.40, "risk": 0.20, "capacity": 0.15, "esg": 0.05}
    elif shipment.priority == ShipmentPriority.LOW:
        # Strictly cost-driven freight (backhaul, bulk inventory replenishment)
        weights = {"cost": 0.60, "service": 0.15, "risk": 0.15, "capacity": 0.05, "esg": 0.05}
    elif shipment.customer_tier == CustomerTier.TIER_1_STRATEGIC:
        weights = {"cost": 0.25, "service": 0.35, "risk": 0.20, "capacity": 0.15, "esg": 0.05}
    else:
        # Standard cost-sensitive freight
        weights = {"cost": 0.45, "service": 0.25, "risk": 0.15, "capacity": 0.10, "esg": 0.05}
        
    composite = (
        (cost_score * weights["cost"]) +
        (service_score * weights["service"]) +
        (carrier_risk_score * weights["risk"]) +
        (capacity_score * weights["capacity"]) +
        (sustainability_score * weights["esg"])
    )
    
    return CarrierScore(
        cost_score=round(cost_score, 1),
        service_score=round(service_score, 1),
        risk_score=round(carrier_risk_score, 1),
        capacity_score=round(capacity_score, 1),
        sustainability_score=round(sustainability_score, 1),
        composite_score=round(composite, 1)
    )
