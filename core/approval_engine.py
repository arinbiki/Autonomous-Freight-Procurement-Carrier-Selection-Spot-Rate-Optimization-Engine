"""
Approval Engine and Financial Governance Module.
Applies tiered procurement approval matrix based on total cost, spot rate variance,
risk severity level, and customer budget compliance.
"""
import uuid
from datetime import datetime
from typing import Tuple, List
from core.models import (
    Shipment, Recommendation, ApprovalTier, ApprovalRecord,
    ApprovalStatus, RiskSeverity
)
from core.config import APPROVAL_TIERS

def determine_approval_requirement(
    shipment: Shipment,
    recommendation_id: str,
    total_cost: float,
    risk_severity: RiskSeverity,
    spot_variance_pct: float = 0.0
) -> Tuple[ApprovalTier, ApprovalRecord, List[str]]:
    """
    Evaluates corporate approval matrix:
    - Tier 1 Auto: <= $2,500, Low/Medium Risk, Spot Variance <= 5%
    - Tier 2 Supervisor: <= $5,000, Spot Variance <= 10%
    - Tier 3 Procurement Manager: <= $25,000, High Risk, Spot Variance <= 20%
    - Tier 4 VP Supply Chain / CFO: > $25,000, Critical Risk, or Budget Overrun
    
    Returns:
        (required_tier, approval_record, trigger_reasons)
    """
    reasons = []
    
    # 1. Budget overrun check
    if shipment.budget_ceiling_usd and total_cost > shipment.budget_ceiling_usd:
        reasons.append(
            f"Budget overrun: Landed cost (${total_cost:,.2f}) exceeds customer ceiling (${shipment.budget_ceiling_usd:,.2f})."
        )
        tier = ApprovalTier.TIER_4_VP_SUPPLY_CHAIN
        status = ApprovalStatus.PENDING
    # 2. Risk severity check
    elif risk_severity == RiskSeverity.CRITICAL:
        reasons.append("Critical operational or cargo risk severity requires VP Supply Chain sign-off.")
        tier = ApprovalTier.TIER_4_VP_SUPPLY_CHAIN
        status = ApprovalStatus.PENDING
    elif total_cost > APPROVAL_TIERS["TIER_3_PROCUREMENT_MANAGER"]["max_cost"]:
        reasons.append(f"Freight spend (${total_cost:,.2f}) exceeds Tier 3 limit ($25,000).")
        tier = ApprovalTier.TIER_4_VP_SUPPLY_CHAIN
        status = ApprovalStatus.PENDING
    elif total_cost > APPROVAL_TIERS["TIER_2_SUPERVISOR"]["max_cost"] or risk_severity == RiskSeverity.HIGH or spot_variance_pct > 10.0:
        if total_cost > APPROVAL_TIERS["TIER_2_SUPERVISOR"]["max_cost"]:
            reasons.append(f"Freight cost (${total_cost:,.2f}) requires Procurement Manager review (>$5,000).")
        if risk_severity == RiskSeverity.HIGH:
            reasons.append("High risk classification requires Procurement Manager verification.")
        if spot_variance_pct > 10.0:
            reasons.append(f"Spot quote premium ({spot_variance_pct:+.1f}%) exceeds supervisor allowance.")
        tier = ApprovalTier.TIER_3_PROCUREMENT_MANAGER
        status = ApprovalStatus.PENDING
    elif total_cost > APPROVAL_TIERS["TIER_1_AUTO"]["max_cost"] or spot_variance_pct > 5.0:
        if total_cost > APPROVAL_TIERS["TIER_1_AUTO"]["max_cost"]:
            reasons.append(f"Spend (${total_cost:,.2f}) exceeds auto-award ceiling ($2,500).")
        if spot_variance_pct > 5.0:
            reasons.append(f"Spot variance ({spot_variance_pct:+.1f}%) requires supervisor confirmation.")
        tier = ApprovalTier.TIER_2_SUPERVISOR
        status = ApprovalStatus.PENDING
    else:
        # Tier 1 Auto-Award
        tier = ApprovalTier.TIER_1_AUTO
        status = ApprovalStatus.APPROVED
        reasons.append("Autonomous procurement criteria satisfied: cost <= $2,500, nominal risk, verified compliance.")

    approval_rec = ApprovalRecord(
        approval_id=f"APPR-{uuid.uuid4().hex[:8].upper()}",
        recommendation_id=recommendation_id,
        shipment_id=shipment.shipment_id,
        required_tier=tier,
        status=status,
        approved_by="SYSTEM_AUTOMATIC" if status == ApprovalStatus.APPROVED else None,
        decided_at=datetime.utcnow() if status == ApprovalStatus.APPROVED else None,
        comments="; ".join(reasons),
        created_at=datetime.utcnow()
    )
    
    return tier, approval_rec, reasons
