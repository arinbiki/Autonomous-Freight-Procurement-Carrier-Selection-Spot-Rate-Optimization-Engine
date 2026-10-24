"""
Risk Intelligence Engine.
Evaluates multi-factor operational, carrier, lane, and commodity risk.
Generates composite risk scores, severity classifications, and targeted mitigation recommendations.
"""
from typing import Dict, Any, List, Tuple
from core.models import Shipment, Carrier, RiskSeverity, ShipmentPriority

def evaluate_shipment_risk(
    shipment: Shipment,
    carrier: Carrier,
    weather_risk_factor: float,
    congestion_factor: float,
    road_miles: float
) -> Tuple[float, RiskSeverity, List[str], Dict[str, float]]:
    """
    Computes weighted risk score across 4 pillars:
    1. Carrier Risk (Safety, Claims, Financial stability)
    2. Lane Risk (Weather, Highway congestion, Distance)
    3. Shipment / Cargo Risk (Value, Hazmat, Temp sensitivity)
    4. Capacity / Execution Risk (Tender acceptance, Driver availability)
    
    Returns:
        (total_risk_score, severity_enum, mitigation_recommendations, risk_factor_breakdown)
    """
    # 1. Carrier Risk Score (0 to 100, where higher is riskier)
    # safety score 100 -> 0 risk; safety score 80 -> 20 risk
    carrier_safety_risk = max(0.0, 100.0 - carrier.safety_score)
    carrier_claim_risk = min(100.0, carrier.claims_rate_pct * 30.0)
    carrier_fin_risk = carrier.financial_risk_score
    carrier_risk = (carrier_safety_risk * 0.4) + (carrier_claim_risk * 0.4) + (carrier_fin_risk * 0.2)
    
    # 2. Lane Risk Score (0 to 100)
    weather_risk_pts = weather_risk_factor * 100.0
    congestion_risk_pts = max(0.0, (congestion_factor - 1.0) * 200.0)
    distance_risk_pts = min(40.0, (road_miles / 2500.0) * 40.0)
    lane_risk = (weather_risk_pts * 0.4) + (congestion_risk_pts * 0.3) + (distance_risk_pts * 0.3)
    
    # 3. Cargo / Shipment Risk (0 to 100)
    cargo_risk = 10.0
    if shipment.commodity.value_usd > 100000.0:
        cargo_risk += min(35.0, (shipment.commodity.value_usd / 500000.0) * 35.0)
    if shipment.commodity.is_hazmat:
        cargo_risk += 30.0
    if shipment.commodity.is_temp_controlled:
        cargo_risk += 25.0
    if shipment.commodity.is_fragile:
        cargo_risk += 15.0
    cargo_risk = min(100.0, cargo_risk)
    
    # 4. Capacity / Execution Risk
    capacity_risk = max(0.0, (1.0 - carrier.tender_acceptance_rate) * 100.0)
    if road_miles > 1000.0 and carrier.tender_acceptance_rate < 0.88:
        capacity_risk += 15.0
    capacity_risk = min(100.0, capacity_risk)
    
    # Weighted Composite Risk Score
    # For critical shipments, cargo and lane risk have higher weights
    if shipment.priority == ShipmentPriority.CRITICAL:
        weights = {"carrier": 0.25, "lane": 0.30, "cargo": 0.30, "capacity": 0.15}
    else:
        weights = {"carrier": 0.30, "lane": 0.25, "cargo": 0.25, "capacity": 0.20}
        
    total_risk = round(
        (carrier_risk * weights["carrier"]) +
        (lane_risk * weights["lane"]) +
        (cargo_risk * weights["cargo"]) +
        (capacity_risk * weights["capacity"]),
        1
    )
    
    # Classify Severity Level
    if total_risk >= 70.0:
        severity = RiskSeverity.CRITICAL
    elif total_risk >= 45.0:
        severity = RiskSeverity.HIGH
    elif total_risk >= 25.0:
        severity = RiskSeverity.MEDIUM
    else:
        severity = RiskSeverity.LOW
        
    # Generate Targeted Mitigation Recommendations
    mitigations = []
    if shipment.commodity.is_temp_controlled:
        mitigations.append("Deploy cellular real-time temperature data logger with 15-minute excursion alerts.")
    if shipment.commodity.value_usd > 100000.0:
        mitigations.append("Require electronic seal (e-seal), team drivers, and geo-fence deviation alerts.")
    if shipment.commodity.is_hazmat:
        mitigations.append("Verify hazmat driver endorsement, dangerous goods declaration, and emergency response guide.")
    if weather_risk_factor >= 0.15:
        mitigations.append("Pre-book southern corridor detour to avoid anticipated winter storm disruptions.")
    if capacity_risk >= 30.0:
        mitigations.append("Contract secondary spot backup carrier with guaranteed tender penalty clause.")
    if severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL):
        mitigations.append("Escalate load to senior logistics supervisor for proactive 4-hour check calls.")
        
    if not mitigations:
        mitigations.append("Standard automated track-and-trace monitoring via EDI 214 milestones.")
        
    breakdown = {
        "carrier_risk": round(carrier_risk, 1),
        "lane_risk": round(lane_risk, 1),
        "cargo_risk": round(cargo_risk, 1),
        "capacity_risk": round(capacity_risk, 1),
        "total_risk_score": total_risk
    }
    
    return total_risk, severity, mitigations, breakdown
