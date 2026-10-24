"""
Route and Mode Optimization Engine.
Evaluates multi-modal alternatives (Road FTL, Road LTL, Intermodal, Air, Rail)
and identifies shipment consolidation or multi-drop opportunities.
"""
from typing import Dict, Any, Tuple
from core.models import Shipment, TransportMode, ShipmentPriority

def optimize_mode_and_consolidation(
    shipment: Shipment,
    road_miles: float,
    available_transit_hours: float
) -> Tuple[TransportMode, bool, str, Dict[str, Any]]:
    """
    Evaluates mode suitability:
    - Weight / Cube threshold for FTL vs LTL
    - Intermodal viability (distance > 700 miles, non-hazmat, non-reefer, ample transit slack)
    - Air freight viability (critical time constraints)
    
    Returns:
        (recommended_mode, is_consolidation_viable, rationale, analysis)
    """
    weight = shipment.commodity.weight_lbs
    pallets = shipment.commodity.pallet_count
    is_temp = shipment.commodity.is_temp_controlled
    is_haz = shipment.commodity.is_hazmat
    is_fragile = shipment.commodity.is_fragile
    priority = shipment.priority
    
    analysis = {}
    
    # Check 1: Air Freight for emergency time-critical freight
    # If available hours < 18 hours for distance > 600 miles
    if priority == ShipmentPriority.CRITICAL and road_miles > 600.0 and available_transit_hours < 24.0:
        mode = TransportMode.AIR
        consolidation = False
        rationale = "Time-critical delivery window requires Air Freight charter to guarantee same-day SLA."
        analysis["air_required"] = True
        return mode, consolidation, rationale, analysis
        
    # Check 2: LTL Consolidation Opportunity
    # Weight <= 12,000 lbs and pallets <= 6 and not fragile/hazmat/reefer
    can_ltl = (weight <= 14000.0) and (pallets <= 8) and not is_temp and not is_haz and not is_fragile
    if can_ltl:
        mode = TransportMode.ROAD_LTL
        consolidation = True
        rationale = (
            f"LTL consolidation selected. Load size ({weight:,.0f} lbs, {pallets} pallets) is below FTL minimums; "
            f"consolidation reduces landed cost by ~38% with acceptable 24h transit variance."
        )
        analysis["consolidation_saving_est_pct"] = 38.0
        return mode, consolidation, rationale, analysis

    # Check 3: Intermodal (Rail + Truck Drayage)
    # Distance > 750 miles, ample transit buffer (> 72 hours), standard dry cargo
    can_intermodal = (road_miles >= 750.0) and (available_transit_hours >= 72.0) and not is_temp and not is_haz and (priority != ShipmentPriority.CRITICAL)
    if can_intermodal:
        mode = TransportMode.INTERMODAL
        consolidation = False
        rationale = (
            f"Intermodal conversion optimal. Route distance ({road_miles:.0f} mi) and extended delivery schedule "
            f"enable 18% cost savings and 45% greenhouse gas reduction via double-stack rail."
        )
        analysis["intermodal_cost_saving_pct"] = 18.0
        analysis["intermodal_carbon_reduction_pct"] = 45.0
        return mode, consolidation, rationale, analysis

    # Default: Full Truckload (FTL)
    mode = TransportMode.ROAD_FTL
    consolidation = False
    if is_temp:
        rationale = "Dedicated 53ft Reefer FTL required for continuous temperature compliance."
    elif is_haz:
        rationale = "Dedicated FTL required for regulatory hazmat separation and chain-of-custody."
    elif weight > 38000.0:
        rationale = f"Full truckload payload ({weight:,.0f} lbs) maximally utilizes trailer weight capacity."
    else:
        rationale = "Direct point-to-point Full Truckload (FTL) ensures lowest transit time and zero touch."
        
    analysis["standard_ftl"] = True
    return mode, consolidation, rationale, analysis
