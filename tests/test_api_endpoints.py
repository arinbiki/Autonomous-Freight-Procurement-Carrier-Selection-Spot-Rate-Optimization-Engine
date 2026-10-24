"""
Integration Test for FastAPI Decision Engine Server.
Verifies all REST endpoints: /health, /intake, /optimize, /rfq/generate, /rfq/extract-quote, /scorecards.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)

def test_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    print("[PASS] /api/v1/health returned HEALTHY")

def test_intake():
    payload = {
        "customer_id": "CUST-TEST",
        "customer_name": "Test Shipper",
        "origin": {"city": "CHICAGO", "state": "IL"},
        "destination": {"city": "DALLAS", "state": "TX"},
        "commodity": {"description": "Electronics", "weight_lbs": 30000.0, "value_usd": 80000.0}
    }
    res = client.post("/api/v1/shipments/intake", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "NORMALIZED"
    assert data["shipment"]["origin"]["city"] == "CHICAGO"
    print("[PASS] /api/v1/shipments/intake normalized shipment successfully")

def test_optimize():
    payload = {
        "shipment_payload": {
            "customer_id": "CUST-TARGET",
            "customer_name": "Target Retail",
            "origin": {"city": "CHICAGO", "state": "IL"},
            "destination": {"city": "DALLAS", "state": "TX"},
            "commodity": {"description": "Retail Merchandise", "weight_lbs": 42000.0, "value_usd": 60000.0},
            "requested_pickup": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "requested_delivery": (datetime.utcnow() + timedelta(days=4)).isoformat()
        }
    }
    res = client.post("/api/v1/procurement/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "recommendation" in data
    rec = data["recommendation"]
    print(f"[PASS] /api/v1/procurement/optimize selected {rec['carrier_name']} (${rec['cost_breakdown']['total_expected_cost']:,.2f})")

def test_rfq_and_extract():
    payload = {
        "origin": {"city": "CHICAGO", "state": "IL"},
        "destination": {"city": "DALLAS", "state": "TX"},
        "commodity": {"description": "Auto Parts", "weight_lbs": 35000.0}
    }
    rfq_res = client.post("/api/v1/rfq/generate", json=payload)
    assert rfq_res.status_code == 200
    print("[PASS] /api/v1/rfq/generate produced RFQ draft")

    quote_text = "We can take this load for $2,100 all-in with 2-day delivery guaranteed. SwiftHaul Logistics."
    extract_res = client.post("/api/v1/rfq/extract-quote", json={"raw_text": quote_text})
    assert extract_res.status_code == 200
    quote_data = extract_res.json()["quote"]
    assert quote_data["total_quote_usd"] == 2100.0
    print("[PASS] /api/v1/rfq/extract-quote accurately extracted rate ($2,100.00)")

def test_scorecards():
    res = client.get("/api/v1/carriers/scorecards")
    assert res.status_code == 200
    data = res.json()
    assert data["total_active_carriers"] >= 5
    print(f"[PASS] /api/v1/carriers/scorecards returned {data['total_active_carriers']} active carrier scorecards")

if __name__ == "__main__":
    test_health()
    test_intake()
    test_optimize()
    test_rfq_and_extract()
    test_scorecards()
    print("\nALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")
