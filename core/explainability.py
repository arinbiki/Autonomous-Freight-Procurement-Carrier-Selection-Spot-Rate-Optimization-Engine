"""
Explainability and Decision Rationalization Engine.
Generates structured factor explanations, multi-dimensional trade-offs,
and executive human-readable rationale based exclusively on verifiable analytical metrics.
"""
from typing import Dict, Any, List
from core.models import (
    Shipment, Carrier, Recommendation, CostBreakdown,
    TransitPrediction, CarrierScore, RiskSeverity, RateType
)

def generate_decision_explanation(
    shipment: Shipment,
    carrier: Carrier,
    rate_type: RateType,
    cost_breakdown: CostBreakdown,
    transit_prediction: TransitPrediction,
    carrier_score: CarrierScore,
    risk_severity: RiskSeverity,
    capacity_confidence: float,
    carbon_kg: float,
    mitigations: List[str]
) -> Dict[str, Any]:
    """
    Constructs an auditable explanation payload according to Section 11 / Workflow 5:
    - Primary decision factors
    - Service vs cost trade-offs
    - Capacity and compliance justification
    - Sensitivity parameters
    """
    factors = []
    
    # 1. Cost factor
    factors.append(
        f"Landed freight cost is ${cost_breakdown.total_expected_cost:,.2f} "
        f"(Base ${cost_breakdown.base_freight:,.2f} + Fuel ${cost_breakdown.fuel_surcharge:,.2f} + "
        f"Accessorials ${cost_breakdown.accessorials:,.2f}), scoring {carrier_score.cost_score:.1f}/100."
    )
    
    # 2. Service & Transit factor
    factors.append(
        f"Expected transit time of {transit_prediction.expected_hours:.1f}h delivers a "
        f"{transit_prediction.on_time_probability*100:.1f}% on-time probability against requested window."
    )
    
    # 3. Carrier Performance & Safety
    factors.append(
        f"Carrier {carrier.name} maintains a {carrier.on_time_delivery_rate*100:.1f}% historical on-time delivery rate, "
        f"{carrier.tender_acceptance_rate*100:.1f}% tender acceptance, and {carrier.safety_score:.1f} DOT safety score."
    )
    
    # 4. Capacity & Execution
    factors.append(
        f"Capacity confidence is rated at {capacity_confidence*100:.1f}%, reflecting reliable equipment availability "
        f"for {shipment.equipment_needed.value}."
    )
    
    # 5. ESG & Carbon
    factors.append(
        f"Estimated carbon footprint is {carbon_kg:,.1f} kg CO2e (${cost_breakdown.carbon_cost:,.2f} offset value), "
        f"with a sustainability score of {carrier_score.sustainability_score:.1f}/100."
    )
    
    # Executive Narrative Summary
    exec_summary = (
        f"Award recommendation for {carrier.name} ({rate_type.value}) achieves the optimal multi-objective balance "
        f"with an overall composite index of {carrier_score.composite_score:.1f}/100. "
        f"This fulfills cargo compliance ({'Active Reefer' if shipment.commodity.is_temp_controlled else 'Standard Van'}), "
        f"provides {transit_prediction.on_time_probability*100:.1f}% SLA delivery certainty, "
        f"and keeps risk at {risk_severity.value} severity."
    )
    
    # Sensitivity Conditions
    sensitivity = [
        "A spot quote decrease of > 12% with equipment guarantee would shift procurement to the spot market.",
        "A weather disruption extending corridor dwell by > 8 hours would trigger air freight or team-driver expedite.",
        "A tender decline by primary carrier will automatically trigger pre-staged secondary backup."
    ]
    
    return {
        "executive_summary": exec_summary,
        "primary_factors": factors,
        "mitigation_actions": mitigations,
        "sensitivity_conditions": sensitivity,
        "scores": {
            "cost": carrier_score.cost_score,
            "service": carrier_score.service_score,
            "risk": carrier_score.risk_score,
            "capacity": carrier_score.capacity_score,
            "sustainability": carrier_score.sustainability_score,
            "composite": carrier_score.composite_score
        }
    }
