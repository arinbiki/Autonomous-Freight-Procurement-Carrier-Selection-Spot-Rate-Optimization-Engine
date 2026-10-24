"""
Master Multi-Objective Procurement Optimization Engine.
Integrates normalization, enrichment, hard constraint filtering, rate intelligence,
transit prediction, risk modeling, capacity confidence, and tiered approval governance.
Produces primary award recommendations and ranked scenario alternatives.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.models import (
    Shipment, Carrier, ContractRate, SpotQuote, Recommendation,
    AlternativeOption, RateType, RiskSeverity, ShipmentStatus,
    TransportMode, CostBreakdown, TransitPrediction, CarrierScore
)
from core.enrichment import enrich_shipment_context
from core.eligibility import filter_eligible_carriers
from core.transit_engine import predict_transit_metrics
from core.sustainability import calculate_shipment_emissions
from core.risk_engine import evaluate_shipment_risk
from core.capacity_engine import evaluate_capacity_confidence
from core.rate_engine import calculate_landed_cost
from core.spot_vs_contract import evaluate_spot_vs_contract
from core.carrier_scoring import score_carrier_candidate
from core.route_mode_optimizer import optimize_mode_and_consolidation
from core.approval_engine import determine_approval_requirement
from core.explainability import generate_decision_explanation
from core.database import (
    save_shipment, save_recommendation, save_approval,
    save_audit_log, get_all_carriers, get_contract_rates_by_lane
)

def run_procurement_optimization(
    shipment: Shipment,
    available_carriers: Optional[List[Carrier]] = None,
    active_spot_quotes: Optional[List[SpotQuote]] = None,
    contract_rates: Optional[List[ContractRate]] = None,
    persist: bool = True,
    fast_mode: bool = False
) -> Recommendation:
    """
    Executes the end-to-end 5-layer autonomous procurement optimization algorithm.
    """
    # 1. Fetch Master Carriers if not passed explicitly
    if not available_carriers:
        available_carriers = get_all_carriers()
        
    # 2. Enrich shipment intelligence
    enrichment = enrich_shipment_context(shipment)
    road_miles = enrichment["road_miles"]
    lane_id = enrichment["lane_id"]
    weather_factor = enrichment["weather_risk_factor"]
    congestion_factor = enrichment["congestion_factor"]
    benchmark_cost = enrichment["benchmark_total_usd"]

    # 3. Filter Hard Constraints
    eligible_carriers, disqualified = filter_eligible_carriers(shipment, available_carriers, road_miles)
    if not eligible_carriers:
        raise ValueError(
            f"Zero eligible carriers found for shipment {shipment.shipment_id}. "
            f"Disqualified {len(disqualified)} candidates due to strict compliance/equipment constraints."
        )

    # 4. Mode & Consolidation Assessment
    available_window_hours = max(1.0, (shipment.requested_delivery - shipment.requested_pickup).total_seconds() / 3600.0)
    opt_mode, is_consolidated, mode_rationale, _ = optimize_mode_and_consolidation(
        shipment, road_miles, available_window_hours
    )

    # 5. Load Known Contract Rates for Lane
    if contract_rates is None:
        contract_rates = get_contract_rates_by_lane(lane_id)
    contract_map = {r.carrier_id: r for r in contract_rates}
    spot_map = {sq.carrier_id: sq for sq in (active_spot_quotes or [])}

    # 6. Multi-Factor Evaluation Loop
    evaluated_options = []
    
    for carrier in eligible_carriers:
        # Rate availability
        c_rate = contract_map.get(carrier.carrier_id)
        s_quote = spot_map.get(carrier.carrier_id)
        rate_source = RateType.CONTRACT if c_rate else (RateType.SPOT if s_quote else RateType.CONTRACT)

        # Transit Prediction
        transit_pred = predict_transit_metrics(
            shipment, carrier, opt_mode, road_miles,
            congestion_factor=congestion_factor,
            weather_risk_factor=weather_factor
        )

        # Carbon Emissions
        carbon_kg, carbon_cost, esg_score = calculate_shipment_emissions(
            shipment, carrier, opt_mode, road_miles
        )

        # Risk Intelligence
        risk_score, risk_sev, mitigations, risk_breakdown = evaluate_shipment_risk(
            shipment, carrier, weather_factor, congestion_factor, road_miles
        )

        # Compute Contract Cost if contract exists
        c_cost = None
        if c_rate:
            c_cost, _ = calculate_landed_cost(
                shipment=shipment,
                carrier=carrier,
                rate_source=RateType.CONTRACT,
                contract_rate=c_rate,
                road_miles=road_miles,
                carbon_kg_co2e=carbon_kg,
                delay_probability=(1.0 - transit_pred.on_time_probability)
            )

        # Compute Spot Cost if spot quote exists
        s_cost = None
        if s_quote:
            s_cost, _ = calculate_landed_cost(
                shipment=shipment,
                carrier=carrier,
                rate_source=RateType.SPOT,
                spot_quote=s_quote,
                road_miles=road_miles,
                carbon_kg_co2e=carbon_kg,
                delay_probability=(1.0 - transit_pred.on_time_probability)
            )

        # Fallback if neither contract nor spot exists: compute benchmark
        if not c_cost and not s_cost:
            c_cost, _ = calculate_landed_cost(
                shipment=shipment,
                carrier=carrier,
                rate_source=RateType.CONTRACT,
                road_miles=road_miles,
                carbon_kg_co2e=carbon_kg,
                delay_probability=(1.0 - transit_pred.on_time_probability)
            )

        # Capacity Confidence
        capacity_conf, rfq_req, cap_details = evaluate_capacity_confidence(
            shipment, carrier,
            rate_competitiveness_ratio=(benchmark_cost / max(1.0, (s_cost or c_cost).total_expected_cost))
        )

        # Spot vs Contract Arbitrage
        eff_rate_type, arb_rationale, arb_metrics = evaluate_spot_vs_contract(
            contract_cost=c_cost,
            spot_cost=s_cost,
            contract_carrier=carrier if c_cost else None,
            spot_carrier=carrier if s_cost else None,
            contract_capacity_confidence=capacity_conf,
            spot_capacity_confidence=0.92 if s_cost else 0.70
        )

        cost_breakdown = s_cost if (eff_rate_type == RateType.SPOT and s_cost) else (c_cost or s_cost)

        # Multi-Factor Score
        carrier_score = score_carrier_candidate(
            shipment=shipment,
            carrier=carrier,
            expected_cost=cost_breakdown.total_expected_cost,
            benchmark_cost=benchmark_cost,
            on_time_probability=transit_pred.on_time_probability,
            risk_score=risk_score,
            capacity_confidence=capacity_conf,
            esg_score=esg_score
        )

        evaluated_options.append({
            "carrier": carrier,
            "rate_type": eff_rate_type,
            "cost_breakdown": cost_breakdown,
            "transit_prediction": transit_pred,
            "carbon_kg": carbon_kg,
            "risk_score": risk_score,
            "risk_severity": risk_sev,
            "mitigations": mitigations,
            "capacity_confidence": capacity_conf,
            "carrier_score": carrier_score,
            "composite_score": carrier_score.composite_score,
            "arb_rationale": arb_rationale
        })

    # 7. Multi-Objective Ranking
    # Primary sort by composite score descending, then by landed cost ascending
    evaluated_options.sort(key=lambda x: (x["composite_score"], -x["cost_breakdown"].total_expected_cost), reverse=True)
    winner = evaluated_options[0]

    # 8. Build Alternatives
    alternatives: List[AlternativeOption] = []
    if not fast_mode:
        # Best Cost
        best_cost_opt = min(evaluated_options, key=lambda x: x["cost_breakdown"].total_expected_cost)
        alternatives.append(AlternativeOption(
            carrier_id=best_cost_opt["carrier"].carrier_id,
            carrier_name=best_cost_opt["carrier"].name,
            mode=opt_mode,
            rate_type=best_cost_opt["rate_type"],
            total_expected_cost=best_cost_opt["cost_breakdown"].total_expected_cost,
            expected_transit_hours=best_cost_opt["transit_prediction"].expected_hours,
            on_time_probability=best_cost_opt["transit_prediction"].on_time_probability,
            risk_severity=best_cost_opt["risk_severity"],
            composite_score=best_cost_opt["composite_score"],
            category_label="Best Landed Cost"
        ))

        # Best Service / Highest On-Time Probability
        best_service_opt = max(evaluated_options, key=lambda x: x["transit_prediction"].on_time_probability)
        alternatives.append(AlternativeOption(
            carrier_id=best_service_opt["carrier"].carrier_id,
            carrier_name=best_service_opt["carrier"].name,
            mode=opt_mode,
            rate_type=best_service_opt["rate_type"],
            total_expected_cost=best_service_opt["cost_breakdown"].total_expected_cost,
            expected_transit_hours=best_service_opt["transit_prediction"].expected_hours,
            on_time_probability=best_service_opt["transit_prediction"].on_time_probability,
            risk_severity=best_service_opt["risk_severity"],
            composite_score=best_service_opt["composite_score"],
            category_label="Highest Service Reliability"
        ))

        # Lowest Risk
        lowest_risk_opt = min(evaluated_options, key=lambda x: x["risk_score"])
        alternatives.append(AlternativeOption(
            carrier_id=lowest_risk_opt["carrier"].carrier_id,
            carrier_name=lowest_risk_opt["carrier"].name,
            mode=opt_mode,
            rate_type=lowest_risk_opt["rate_type"],
            total_expected_cost=lowest_risk_opt["cost_breakdown"].total_expected_cost,
            expected_transit_hours=lowest_risk_opt["transit_prediction"].expected_hours,
            on_time_probability=lowest_risk_opt["transit_prediction"].on_time_probability,
            risk_severity=lowest_risk_opt["risk_severity"],
            composite_score=lowest_risk_opt["composite_score"],
            category_label="Lowest Operational Risk"
        ))

        # Lowest Carbon
        lowest_carbon_opt = min(evaluated_options, key=lambda x: x["carbon_kg"])
        alternatives.append(AlternativeOption(
            carrier_id=lowest_carbon_opt["carrier"].carrier_id,
            carrier_name=lowest_carbon_opt["carrier"].name,
            mode=opt_mode,
            rate_type=lowest_carbon_opt["rate_type"],
            total_expected_cost=lowest_carbon_opt["cost_breakdown"].total_expected_cost,
            expected_transit_hours=lowest_carbon_opt["transit_prediction"].expected_hours,
            on_time_probability=lowest_carbon_opt["transit_prediction"].on_time_probability,
            risk_severity=lowest_carbon_opt["risk_severity"],
            composite_score=lowest_carbon_opt["composite_score"],
            category_label="Lowest Carbon Footprint"
        ))

    # 9. Recommendation ID & Explanation
    rec_id = f"REC-{shipment.shipment_id}" if fast_mode else f"REC-{uuid.uuid4().hex[:8].upper()}"
    explanation = {} if fast_mode else generate_decision_explanation(
        shipment=shipment,
        carrier=winner["carrier"],
        rate_type=winner["rate_type"],
        cost_breakdown=winner["cost_breakdown"],
        transit_prediction=winner["transit_prediction"],
        carrier_score=winner["carrier_score"],
        risk_severity=winner["risk_severity"],
        capacity_confidence=winner["capacity_confidence"],
        carbon_kg=winner["carbon_kg"],
        mitigations=winner["mitigations"]
    )

    # 10. Financial Approval Matrix Evaluation
    approval_tier, approval_record, trigger_reasons = determine_approval_requirement(
        shipment=shipment,
        recommendation_id=rec_id,
        total_cost=winner["cost_breakdown"].total_expected_cost,
        risk_severity=winner["risk_severity"]
    )

    route_summary = f"{shipment.origin.city}, {shipment.origin.state} -> {shipment.destination.city}, {shipment.destination.state} ({road_miles:.0f} mi via {opt_mode.value})"

    rec = Recommendation(
        recommendation_id=rec_id,
        shipment_id=shipment.shipment_id,
        recommended_carrier_id=winner["carrier"].carrier_id,
        carrier_name=winner["carrier"].name,
        mode=opt_mode,
        rate_type=winner["rate_type"],
        route_summary=route_summary,
        cost_breakdown=winner["cost_breakdown"],
        transit_prediction=winner["transit_prediction"],
        risk_score=winner["risk_score"],
        risk_severity=winner["risk_severity"],
        capacity_confidence=winner["capacity_confidence"],
        carbon_kg_co2e=winner["carbon_kg"],
        approval_tier=approval_tier,
        explanation=explanation,
        alternatives=alternatives,
        created_at=datetime.utcnow()
    )

    # 11. Persist to Relational Database & Audit Log
    shipment.status = ShipmentStatus.OPTIMIZED
    if persist:
        save_shipment(shipment)
        save_recommendation(rec)
        save_approval(approval_record)
        save_audit_log(
            entity_type="SHIPMENT_PROCUREMENT",
            entity_id=shipment.shipment_id,
            event_type="RECOMMENDATION_GENERATED",
            rule_name="MULTI_OBJECTIVE_OPTIMIZATION_V1",
            input_summary=f"Lane {lane_id}, cargo ${shipment.commodity.value_usd:,.0f}, {road_miles:.0f}mi",
            output_summary=f"Awarded to {winner['carrier'].name} at ${winner['cost_breakdown'].total_expected_cost:,.2f} ({approval_tier.value})",
            confidence=winner["carrier_score"].composite_score / 100.0,
            actor="AUTONOMOUS_OPTIMIZATION_ENGINE"
        )

    return rec
