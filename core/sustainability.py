"""
Sustainability and Carbon Emissions Engine.
Computes GLEC Framework-compliant greenhouse gas emissions (CO2e kg),
mode carbon comparisons, and ESG corporate sustainability scores.
"""
from typing import Dict, Any, Tuple
from core.models import Shipment, TransportMode, Carrier
from core.config import EMISSION_FACTORS, CARBON_PRICE_PER_TON

def calculate_shipment_emissions(
    shipment: Shipment,
    carrier: Carrier,
    mode: TransportMode,
    miles: float
) -> Tuple[float, float, float]:
    """
    Computes greenhouse gas emissions based on GLEC Framework:
    - Distance converted to km
    - Weight converted to metric tonnes
    - Emission factor (g CO2e / ton-km)
    - Carrier carbon efficiency score adjustment
    
    Returns:
        (carbon_kg_co2e, carbon_cost_usd, esg_score)
    """
    distance_km = miles * 1.60934
    weight_metric_tonnes = max(0.5, shipment.commodity.weight_lbs / 2204.62)
    
    base_factor = EMISSION_FACTORS.get(mode.value, 62.0)
    
    # Carrier efficiency multiplier: score 100 -> 0.85x emissions; score 60 -> 1.25x emissions
    efficiency_multiplier = 1.0 - ((carrier.carbon_efficiency_score - 80.0) / 100.0 * 0.5)
    efficiency_multiplier = max(0.75, min(1.30, efficiency_multiplier))
    
    # Total grams CO2e = km * tonnes * g/ton-km * efficiency
    total_grams_co2e = distance_km * weight_metric_tonnes * base_factor * efficiency_multiplier
    
    # Refrigerated shipments use ~15% additional energy for APU/reefer compressor
    if shipment.commodity.is_temp_controlled:
        total_grams_co2e *= 1.15
        
    carbon_kg = round(total_grams_co2e / 1000.0, 1)
    carbon_tonnes = carbon_kg / 1000.0
    carbon_cost_usd = round(carbon_tonnes * CARBON_PRICE_PER_TON, 2)
    
    # Normalized ESG score (0 - 100), where lower emissions + high carrier ESG = higher score
    mode_baseline = distance_km * weight_metric_tonnes * 62.0 / 1000.0
    relative_carbon_ratio = carbon_kg / max(1.0, mode_baseline)
    
    raw_esg = (carrier.carbon_efficiency_score * 0.6) + ((1.5 - relative_carbon_ratio) * 40.0)
    esg_score = round(max(10.0, min(100.0, raw_esg)), 1)
    
    return carbon_kg, carbon_cost_usd, esg_score

def compare_modes_carbon(
    shipment: Shipment,
    carrier: Carrier,
    road_miles: float
) -> Dict[str, float]:
    """
    Returns carbon footprint across alternative modes for ESG reporting.
    """
    comparisons = {}
    for m in [TransportMode.ROAD_FTL, TransportMode.INTERMODAL, TransportMode.RAIL, TransportMode.AIR]:
        kg, _, _ = calculate_shipment_emissions(shipment, carrier, m, road_miles)
        comparisons[m.value] = kg
    return comparisons
