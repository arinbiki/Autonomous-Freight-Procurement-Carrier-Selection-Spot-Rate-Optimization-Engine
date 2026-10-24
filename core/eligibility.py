"""
Carrier Eligibility and Hard Constraint Filtering Module.
Applies non-negotiable compliance, equipment, safety, insurance,
and operational constraints before mathematical scoring and ranking.
"""
from typing import List, Dict, Any, Tuple
from core.models import Shipment, Carrier, EquipmentType, TransportMode

def filter_eligible_carriers(
    shipment: Shipment,
    carriers: List[Carrier],
    road_miles: float
) -> Tuple[List[Carrier], List[Dict[str, Any]]]:
    """
    Evaluates each carrier candidate against hard constraints:
    1. Active Status & Compliance
    2. Insurance Coverage >= Cargo Value
    3. Equipment Compatibility (Reefer, Dry Van, Hazmat)
    4. Safety Score Threshold
    5. Transit Time Feasibility
    
    Returns:
        (eligible_carriers, disqualification_log)
    """
    eligible = []
    disqualified = []
    
    # Calculate minimum physical driving hours (at 55 mph highway + 10hr rest per 11hr driving)
    driving_hours = road_miles / 50.0
    rest_periods = int(driving_hours // 11)
    min_physical_transit_hours = driving_hours + (rest_periods * 10)
    
    available_hours = (shipment.requested_delivery - shipment.requested_pickup).total_seconds() / 3600.0
    
    time_feasible = available_hours >= min_physical_transit_hours
    
    for c in carriers:
        reasons = []
        
        # 1. Active status
        if not c.is_active:
            reasons.append("Carrier account is inactive or under suspension.")
            
        # 2. Insurance validity & coverage
        if not c.insurance_valid:
            reasons.append("Carrier insurance certificate is expired or invalid.")
        elif c.insurance_coverage_usd < shipment.commodity.value_usd:
            reasons.append(
                f"Insufficient cargo insurance: ${c.insurance_coverage_usd:,.0f} "
                f"below required cargo value ${shipment.commodity.value_usd:,.0f}."
            )
            
        # 3. Equipment capability
        needed_equip = shipment.equipment_needed
        if needed_equip not in c.equipment_types:
            reasons.append(f"Missing required equipment type: {needed_equip.value}.")
            
        # 4. Temperature control capability
        if shipment.commodity.is_temp_controlled:
            if EquipmentType.REEFER_53 not in c.equipment_types:
                reasons.append("Cargo requires active temperature control; carrier lacks reefer fleet.")
                
        # 5. Hazmat & safety compliance
        if shipment.commodity.is_hazmat:
            if c.safety_score < 96.0:
                reasons.append(f"Carrier safety rating ({c.safety_score:.1f}) is below enterprise hazmat threshold (96.0).")
            if c.claims_rate_pct > 0.35:
                reasons.append(f"Carrier claim rate ({c.claims_rate_pct:.2f}%) exceeds strict safety limit for hazardous materials (0.35%).")
                
        # 6. Overall safety baseline
        if c.safety_score < 80.0:
            reasons.append(f"Carrier safety score ({c.safety_score:.1f}) fails minimum corporate threshold (80.0).")
            
        # 7. Time feasibility (team driver / dedicated fleet reduces transit hours by avoiding single-driver rest delays)
        effective_min_transit = (driving_hours * 1.1) if (TransportMode.DEDICATED_FLEET in c.modes) else min_physical_transit_hours
        if available_hours < effective_min_transit:
            reasons.append(f"Transit window ({available_hours:.1f}h) is tighter than physical linehaul limit ({effective_min_transit:.1f}h).")

        if not reasons:
            eligible.append(c)
        else:
            disqualified.append({
                "carrier_id": c.carrier_id,
                "carrier_name": c.name,
                "disqualification_reasons": reasons
            })
            
    return eligible, disqualified
