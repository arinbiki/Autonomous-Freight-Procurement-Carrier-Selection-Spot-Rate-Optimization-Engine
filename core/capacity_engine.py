"""
Capacity Intelligence Engine.
Estimates tender acceptance probability, equipment availability confidence,
and triggers spot RFQ discovery if capacity certainty falls below safe operational limits.
"""
from typing import Tuple, Dict, Any
from core.models import Shipment, Carrier, EquipmentType

def evaluate_capacity_confidence(
    shipment: Shipment,
    carrier: Carrier,
    rate_competitiveness_ratio: float = 1.0,
    market_tightness_factor: float = 1.0
) -> Tuple[float, bool, Dict[str, Any]]:
    """
    Computes capacity confidence:
      Capacity Confidence = P(Acceptance) * P(Equipment) * Market Stability Factor
    
    Returns:
        (capacity_confidence, is_rfq_recommended, breakdown)
    """
    # 1. Tender Acceptance Probability based on lead time and carrier relationship
    lead_time_days = max(0.5, (shipment.requested_pickup - shipment.created_at).total_seconds() / 86400.0)
    
    # Lead time factor: > 3 days is ideal; < 1 day (same day) drops acceptance rate by 20%
    if lead_time_days >= 3.0:
        lead_time_multiplier = 1.05
    elif lead_time_days >= 1.5:
        lead_time_multiplier = 1.0
    elif lead_time_days >= 0.75:
        lead_time_multiplier = 0.88
    else:
        lead_time_multiplier = 0.72  # Urgent same-day load
        
    # Rate attractiveness multiplier: if rate is above benchmark, carrier is much more likely to accept
    rate_factor = min(1.15, max(0.80, rate_competitiveness_ratio))
    
    p_acceptance = carrier.tender_acceptance_rate * lead_time_multiplier * rate_factor
    p_acceptance = min(0.98, max(0.20, p_acceptance))
    
    # 2. Equipment Availability Probability
    # Reefer equipment is scarcer during produce seasons
    p_equipment = 0.95
    if shipment.equipment_needed == EquipmentType.REEFER_53:
        p_equipment = 0.88
    elif shipment.equipment_needed in (EquipmentType.FLATBED, EquipmentType.STEP_DECK):
        p_equipment = 0.85
        
    # 3. Market Stability Factor
    market_stability = max(0.70, min(1.0, 1.0 / market_tightness_factor))
    
    # Capacity Confidence Score (0.0 to 1.0)
    capacity_confidence = round(p_acceptance * p_equipment * market_stability, 3)
    
    # RFQ Trigger Rule: If capacity confidence < 0.75 or same-day lead time with tight market
    is_rfq_recommended = (capacity_confidence < 0.75) or (lead_time_days < 1.0 and capacity_confidence < 0.82)
    
    details = {
        "p_acceptance": round(p_acceptance, 3),
        "p_equipment": round(p_equipment, 3),
        "lead_time_days": round(lead_time_days, 1),
        "market_stability": round(market_stability, 2),
        "capacity_confidence": capacity_confidence,
        "rfq_recommended": is_rfq_recommended
    }
    
    return capacity_confidence, is_rfq_recommended, details
