"""
Spot vs Contract Rate Optimization Engine.
Performs expected value arbitrage comparing contracted rates against spot market quotes.
Determines whether to execute via Contract, Spot, or Hybrid procurement strategy.
"""
from typing import Dict, Any, Tuple, Optional
from core.models import RateType, CostBreakdown, Carrier

def evaluate_spot_vs_contract(
    contract_cost: Optional[CostBreakdown],
    spot_cost: Optional[CostBreakdown],
    contract_carrier: Optional[Carrier],
    spot_carrier: Optional[Carrier],
    contract_capacity_confidence: float = 0.85,
    spot_capacity_confidence: float = 0.90
) -> Tuple[RateType, str, Dict[str, Any]]:
    """
    Evaluates expected value arbitrage between contract rates and spot offers:
      EV_Contract = Cost + Risk + Delay - ReliabilityBenefit
      EV_Spot = Cost + Risk + Delay + CapacityRisk - AvailabilityBenefit
    
    Returns:
        (optimal_rate_type, rational_narrative, metrics)
    """
    # Case 1: Only Contract is available
    if contract_cost and not spot_cost:
        narrative = "Contracted tariff applied. No active spot quote submitted for this lane."
        return RateType.CONTRACT, narrative, {"contract_ev": contract_cost.total_expected_cost}
        
    # Case 2: Only Spot is available (no contract or contract capacity fully exhausted)
    if spot_cost and not contract_cost:
        narrative = "Spot rate utilized. No active contracted carrier servicing this lane with required equipment."
        return RateType.SPOT, narrative, {"spot_ev": spot_cost.total_expected_cost}
        
    # Case 3: Both options exist -> Rigorous Expected Value Arbitrage
    c_cost = contract_cost.total_expected_cost
    s_cost = spot_cost.total_expected_cost
    
    # Contract reliability bonus (stable billing, pre-vetted compliance, SLA guarantees)
    c_reliability_bonus = 75.0 if contract_carrier and contract_carrier.tender_acceptance_rate >= 0.90 else 25.0
    
    # Spot capacity penalty (higher risk of day-of-pickup fall-through or rate renegotiation)
    s_fallthrough_penalty = (1.0 - spot_capacity_confidence) * 200.0
    
    contract_ev = c_cost - c_reliability_bonus
    spot_ev = s_cost + s_fallthrough_penalty
    
    variance_pct = round(((s_cost - c_cost) / max(1.0, c_cost)) * 100.0, 1)
    
    metrics = {
        "contract_landed_cost": c_cost,
        "spot_landed_cost": s_cost,
        "contract_expected_value": round(contract_ev, 2),
        "spot_expected_value": round(spot_ev, 2),
        "spot_variance_vs_contract_pct": variance_pct,
        "contract_capacity_confidence": contract_capacity_confidence,
        "spot_capacity_confidence": spot_capacity_confidence
    }
    
    # Decision Rules
    if contract_capacity_confidence < 0.65:
        decision = RateType.SPOT
        narrative = (
            f"Spot execution recommended. Contracted carrier capacity certainty is dangerously low "
            f"({contract_capacity_confidence*100:.0f}%), risking load cancellation."
        )
    elif variance_pct < -12.0 and spot_capacity_confidence >= 0.85:
        # Spot is > 12% cheaper landed with high capacity confidence
        decision = RateType.SPOT
        narrative = (
            f"Spot market capture recommended. Spot rate delivers ${c_cost - s_cost:,.2f} "
            f"({abs(variance_pct):.1f}%) landed savings with high equipment certainty."
        )
    elif contract_capacity_confidence >= 0.70 and contract_ev <= spot_ev:
        decision = RateType.CONTRACT
        narrative = (
            f"Contract rate selected. Contract tariff provides superior cost stability "
            f"(${c_cost:,.2f} vs spot ${s_cost:,.2f}) and lower cancellation exposure."
        )
    else:
        # Hybrid strategy: Tender primary to contract carrier, keep spot on 2-hour standby
        decision = RateType.HYBRID
        narrative = (
            f"Hybrid strategy deployed. Tender primary load to contracted carrier with spot backup on standby "
            f"due to moderate capacity variance ({variance_pct:+.1f}%)."
        )
        
    return decision, narrative, metrics
