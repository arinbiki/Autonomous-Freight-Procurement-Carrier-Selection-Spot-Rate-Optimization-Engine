"""
Dify Workflow Integration Client.
Connects the Freight Procurement Engine with configured Dify Workflows:
1. Freight-Procurement-Auction-Engine-v1 (Master Auction & Monte Carlo TCO Engine)
2. Freight-Shipment-Request-Extractor-v1 (Unstructured tender ingestion)
3. Freight-Carrier-Quote-Extractor-v1 (Carrier quote & tariff extraction)
4. Freight-Analyst-Copilot-v1 (Natural language procurement copilot)
5. Freight-Recommendation-Explainer-v1 (Auditable executive trade-off rationale)
"""
import json
import logging
from typing import Dict, Any, Optional
import requests
from core.config import (
    DIFY_BASE_URL,
    DIFY_API_KEY,
    DIFY_EXTRACTOR_KEY,
    DIFY_QUOTE_KEY,
    DIFY_COPILOT_KEY,
    DIFY_EXPLAINER_KEY
)
from core.models import Shipment

logger = logging.getLogger(__name__)

def run_dify_workflow(token: str, inputs: Dict[str, Any], user_id: str = "freight-engine-admin") -> Dict[str, Any]:
    """Helper to run any published Dify workflow via /v1/workflows/run."""
    if not token:
        return {"status": "SKIPPED", "reason": "Workflow token not configured"}

    url = f"{DIFY_BASE_URL.rstrip('/')}/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": inputs,
        "response_mode": "blocking",
        "user": user_id
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return {"status": "SUCCESS", "outputs": data.get("data", {}).get("outputs", {})}
        else:
            return {"status": "ERROR", "status_code": resp.status_code, "error": resp.text}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def extract_shipment_request(raw_text: str, shipper_name: str = "") -> Dict[str, Any]:
    """Invokes Freight-Shipment-Request-Extractor-v1 to parse unstructured tenders."""
    return run_dify_workflow(
        token=DIFY_EXTRACTOR_KEY or DIFY_API_KEY,
        inputs={"raw_request_text": raw_text, "shipper_name": shipper_name}
    )

def extract_carrier_quote(quote_text: str, rfq_id: str = "") -> Dict[str, Any]:
    """Invokes Freight-Carrier-Quote-Extractor-v1 to parse carrier spot bids."""
    return run_dify_workflow(
        token=DIFY_QUOTE_KEY or DIFY_API_KEY,
        inputs={"carrier_quote_text": quote_text, "rfq_id": rfq_id}
    )

def ask_analyst_copilot(query: str, lane_context: str = "") -> Dict[str, Any]:
    """Invokes Freight-Analyst-Copilot-v1 to answer natural language procurement queries."""
    return run_dify_workflow(
        token=DIFY_COPILOT_KEY or DIFY_API_KEY,
        inputs={"analyst_query": query, "lane_context": lane_context}
    )

def generate_recommendation_explanation(decision_data: Dict[str, Any]) -> Dict[str, Any]:
    """Invokes Freight-Recommendation-Explainer-v1 to synthesize auditable executive rationale."""
    raw_json = json.dumps(decision_data, indent=2) if isinstance(decision_data, dict) else str(decision_data)
    return run_dify_workflow(
        token=DIFY_EXPLAINER_KEY or DIFY_API_KEY,
        inputs={"decision_json": raw_json}
    )

def execute_dify_freight_workflow(
    shipment: Shipment,
    user_id: str = "freight-engine-admin"
) -> Dict[str, Any]:
    """
    Executes the Master Dify workflow: Freight-Procurement-Auction-Engine-v1.
    """
    if not DIFY_API_KEY:
        logger.warning("DIFY_API_KEY is not configured in .env; skipping Dify execution.")
        return {"status": "SKIPPED", "reason": "DIFY_API_KEY missing"}

    url = f"{DIFY_BASE_URL.rstrip('/')}/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    temp_str = "None"
    if shipment.commodity.is_temp_controlled:
        temp_str = "2-8C Ambient Controlled"

    hazmat_str = "Non-Hazmat"
    if shipment.commodity.is_hazmat:
        hazmat_str = "Class 3 Flammable Liquid"

    urgency_map = {
        "CRITICAL": "EXPEDITED_CRITICAL",
        "HIGH": "EXPEDITED_CRITICAL",
        "STANDARD": "STANDARD_COMMERCIAL",
        "LOW": "DEFERRED_ECONOMY"
    }
    urgency = urgency_map.get(shipment.priority.value, "STANDARD_COMMERCIAL")

    inputs = {
        "origin": f"{shipment.origin.city}, {shipment.origin.state}",
        "destination": f"{shipment.destination.city}, {shipment.destination.state}",
        "cargo_description": shipment.commodity.description,
        "cargo_weight_kg": round(shipment.commodity.weight_lbs / 2.20462, 1),
        "cargo_volume_cbm": round((shipment.commodity.volume_cbf or 3200.0) / 35.3147, 1),
        "temperature_required": temp_str,
        "hazmat_class": hazmat_str,
        "delivery_deadline": shipment.requested_delivery.strftime("%Y-%m-%d"),
        "incoterms": "DDP",
        "urgency_level": urgency
    }

    payload = {
        "inputs": inputs,
        "response_mode": "blocking",
        "user": user_id
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.error(f"Dify workflow failed [{resp.status_code}]: {resp.text}")
            return {
                "status": "ERROR",
                "status_code": resp.status_code,
                "error": resp.text
            }
    except Exception as e:
        logger.error(f"Dify workflow connection error: {e}")
        return {"status": "ERROR", "error": str(e)}
