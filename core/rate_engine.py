"""
Rate Intelligence and Landed Cost Engine.
Computes Total Expected Freight Cost including base rate, fuel surcharge,
probabilistic detention, late delivery penalties, cargo risk premium, and carbon cost adjustment.
"""
from typing import Tuple
from core.models import (
    Shipment, Carrier, ContractRate, SpotQuote, CostBreakdown,
    RateType, ShipmentPriority, CustomerTier
)
from core.config import CARBON_PRICE_PER_TON

def calculate_landed_cost(
    shipment: Shipment,
    carrier: Carrier,
    rate_source: RateType,
    contract_rate: ContractRate = None,
    spot_quote: SpotQuote = None,
    road_miles: float = 500.0,
    carbon_kg_co2e: float = 500.0,
    delay_probability: float = 0.05
) -> Tuple[CostBreakdown, float]:
    """
    Computes rigorous landed cost and rate confidence score.
    Formula:
      Total = Base + Fuel + Accessorials + E[Detention] + E[Delay Penalty] + Risk Premium + Carbon Cost - Discounts
    """
    accessorials = 0.0
    
    # 1. Base Freight & Fuel Surcharge
    if rate_source == RateType.CONTRACT and contract_rate:
        base_freight = contract_rate.base_rate_usd
        fuel_surcharge = round(base_freight * (contract_rate.fuel_surcharge_pct / 100.0), 2)
        detention_hourly = contract_rate.detention_hourly_rate
        rate_confidence = 0.95
    elif rate_source == RateType.SPOT and spot_quote:
        base_freight = spot_quote.base_rate_usd
        fuel_surcharge = spot_quote.fuel_surcharge_usd
        accessorials += spot_quote.accessorials_usd
        detention_hourly = 85.0
        rate_confidence = 0.88
    else:
        # Benchmark fallback calculation based on road miles
        rpm = 2.85 if shipment.commodity.is_temp_controlled else 2.30
        base_freight = round(road_miles * rpm, 2)
        fuel_surcharge = round(base_freight * 0.18, 2)
        detention_hourly = 80.0
        rate_confidence = 0.75

    # 2. Accessorials based on cargo and facility needs
    if shipment.commodity.is_temp_controlled:
        accessorials += 125.0  # Reefer continuous monitoring & pre-cooling
    if shipment.commodity.is_hazmat:
        accessorials += 250.0  # Hazardous materials compliance & placarding
    if shipment.origin.appointment_required:
        accessorials += 35.0   # Mandatory dock appointment fee

    # 3. Expected Detention Cost: P(Detention) * E[Detention Hours] * Hourly Rate
    origin_dwell = shipment.origin.avg_dwell_hours
    dest_dwell = shipment.destination.avg_dwell_hours
    # Over 2 free hours triggers detention
    excess_hours = max(0.0, (origin_dwell - 2.0)) + max(0.0, (dest_dwell - 2.0))
    p_detention = 0.35 if excess_hours > 0 else 0.10
    expected_detention = round(p_detention * excess_hours * detention_hourly, 2)

    # 4. Expected Delay Penalty Cost
    # Penalty depends on customer tier and shipment priority
    tier_penalty_scale = {
        CustomerTier.TIER_1_STRATEGIC: 1200.0,
        CustomerTier.TIER_2_ENTERPRISE: 600.0,
        CustomerTier.TIER_3_STANDARD: 250.0,
        CustomerTier.TIER_4_SPOT: 100.0
    }
    base_penalty = tier_penalty_scale.get(shipment.customer_tier, 400.0)
    if shipment.priority == ShipmentPriority.CRITICAL:
        base_penalty *= 2.5
    elif shipment.priority == ShipmentPriority.HIGH:
        base_penalty *= 1.5

    expected_delay_penalty = round(delay_probability * base_penalty, 2)

    # 5. Risk Premium (Cargo Claim Exposure)
    # Carrier claim rate % * cargo value
    claim_pct = max(0.1, carrier.claims_rate_pct) / 100.0
    risk_premium = round(shipment.commodity.value_usd * claim_pct * 0.25, 2)

    # 6. Carbon Cost Adjustment ($/metric ton CO2e)
    carbon_tons = carbon_kg_co2e / 1000.0
    carbon_cost = round(carbon_tons * CARBON_PRICE_PER_TON, 2)

    # 7. Volume Discounts (for contract carriers with tender acceptance > 92%)
    volume_discount = 0.0
    if rate_source == RateType.CONTRACT and carrier.tender_acceptance_rate >= 0.92:
        volume_discount = round(base_freight * 0.03, 2)

    total_expected = round(
        base_freight + fuel_surcharge + accessorials +
        expected_detention + expected_delay_penalty +
        risk_premium + carbon_cost - volume_discount,
        2
    )

    breakdown = CostBreakdown(
        base_freight=base_freight,
        fuel_surcharge=fuel_surcharge,
        accessorials=accessorials,
        expected_detention=expected_detention,
        expected_delay_penalty=expected_delay_penalty,
        risk_premium=risk_premium,
        carbon_cost=carbon_cost,
        volume_discount=volume_discount,
        total_expected_cost=total_expected
    )

    return breakdown, rate_confidence
