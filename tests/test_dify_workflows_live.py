"""
Live End-to-End Verification Test for Dify Freight Procurement Workflows.
Tests the 4 newly created & published workflows via their REST API tokens:
1. Freight-Shipment-Request-Extractor-v1
2. Freight-Carrier-Quote-Extractor-v1
3. Freight-Analyst-Copilot-v1
4. Freight-Recommendation-Explainer-v1
"""
import sys
import json
import requests
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
KEYS_FILE = BASE_DIR / "dify_workflows" / "dify_app_keys.json"
DIFY_BASE = os.getenv("DIFY_BASE_URL", "http://localhost:3000")

def test_workflow(app_name: str, token: str, inputs: dict):
    print("=" * 80)
    print(f"TESTING LIVE DIFY WORKFLOW: {app_name}")
    print(f"Token: {token[:12]}...")
    print(f"Inputs: {json.dumps(inputs, indent=2)}")
    print("=" * 80)
    
    url = f"{DIFY_BASE}/v1/workflows/run"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": inputs,
        "response_mode": "blocking",
        "user": "freight-autotesting-agent"
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        print(f"HTTP Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            outputs = data.get("data", {}).get("outputs", {})
            print("Execution SUCCESS!")
            print(f"Outputs:\n{json.dumps(outputs, indent=2)}")
            return True
        else:
            print(f"Execution Error ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"Request Exception: {e}")
        return False

def main():
    keys_data = {}
    if KEYS_FILE.exists():
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                keys_data = json.load(f)
        except Exception:
            pass

    results = {}
    
    # 1. Test Shipment Request Extractor
    w1_key = keys_data.get("Freight-Shipment-Request-Extractor-v1", {}).get("token") or os.getenv("DIFY_EXTRACTOR_KEY", "")
    if w1_key.startswith("your_"):
        w1_key = os.getenv("DIFY_EXTRACTOR_KEY", "")
    w1_inputs = {
        "raw_request_text": "Need urgent reefer transport for 42,000 lbs of organic produce from Salinas CA (93901) to Chicago IL (60601). Maintain 34F temperature. Pickup tomorrow 8AM.",
        "shipper_name": "Salinas Valley Farms"
    }
    results["Shipment-Extractor"] = test_workflow("Freight-Shipment-Request-Extractor-v1", w1_key, w1_inputs)

    # 2. Test Carrier Quote Extractor
    w2_key = keys_data.get("Freight-Carrier-Quote-Extractor-v1", {}).get("token") or os.getenv("DIFY_QUOTE_KEY", "")
    if w2_key.startswith("your_"):
        w2_key = os.getenv("DIFY_QUOTE_KEY", "")
    w2_inputs = {
        "carrier_quote_text": "Apex Freight Logistics can handle this load for $2,100 all-in (Base $1,850 + Fuel $200 + Reefer $50). Delivery guaranteed in 48 hours. Valid for 12 hours.",
        "rfq_id": "RFQ-SALINAS-CHIC-01"
    }
    results["Quote-Extractor"] = test_workflow("Freight-Carrier-Quote-Extractor-v1", w2_key, w2_inputs)

    # 3. Test Freight Analyst Copilot
    w4_key = keys_data.get("Freight-Analyst-Copilot-v1", {}).get("token") or os.getenv("DIFY_COPILOT_KEY", "")
    if w4_key.startswith("your_"):
        w4_key = os.getenv("DIFY_COPILOT_KEY", "")
    w4_inputs = {
        "analyst_query": "Compare spot vs contract rate economics on the Chicago to Dallas corridor under 95% capacity tightness.",
        "lane_context": "CHICAGO, IL -> DALLAS, TX"
    }
    results["Analyst-Copilot"] = test_workflow("Freight-Analyst-Copilot-v1", w4_key, w4_inputs)

    # 4. Test Recommendation Explainer
    w5_key = keys_data.get("Freight-Recommendation-Explainer-v1", {}).get("token") or os.getenv("DIFY_EXPLAINER_KEY", "")
    if w5_key.startswith("your_"):
        w5_key = os.getenv("DIFY_EXPLAINER_KEY", "")
    w5_inputs = {
        "decision_json": json.dumps({
            "shipment_id": "SHP-LIVE-001",
            "recommended_carrier": "GreenLine Eco-Logistics",
            "mode": "ROAD_FTL",
            "total_expected_cost": 2042.0,
            "on_time_probability": 0.921,
            "capacity_confidence": 0.884,
            "carbon_kg_co2e": 1567.9,
            "approval_tier": "TIER_1_AUTO"
        })
    }
    results["Recommendation-Explainer"] = test_workflow("Freight-Recommendation-Explainer-v1", w5_key, w5_inputs)

    print("\n" + "=" * 80)
    print("DIFY WORKFLOWS TEST SUMMARY")
    print("=" * 80)
    for name, ok in results.items():
        status = "PASSED [OK]" if ok else "FAILED [ERR]"
        print(f" {status} - {name}")
    print("=" * 80)

if __name__ == "__main__":
    main()
