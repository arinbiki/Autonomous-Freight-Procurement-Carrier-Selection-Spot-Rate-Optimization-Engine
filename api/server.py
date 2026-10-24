import uvicorn
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.models import (
    Shipment, Recommendation, SpotQuote, ApprovalStatus
)
from core.normalization import normalize_shipment_request
from core.optimization import run_procurement_optimization
from core.qwen_nlp import generate_rfq_email, extract_carrier_quote
from core.config import (
    DECISION_ENGINE_PORT, DECISION_ENGINE_HOST,
    OLLAMA_BASE_URL, DIFY_BASE_URL, N8N_BASE_URL
)
from core.database import (
    get_shipment, get_all_carriers, get_connection,
    decide_approval, save_audit_log
)

app = FastAPI(
    title="Autonomous Freight Procurement Engine API",
    description="Enterprise-grade carrier selection, multi-objective landed cost optimization, spot rate arbitrage, and approval routing.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DecisionPayload(BaseModel):
    action: str  # "APPROVED" or "REJECTED"
    approver: str
    comments: Optional[str] = None

class QuoteTextPayload(BaseModel):
    raw_text: str

class OptimizationRequest(BaseModel):
    shipment_payload: Dict[str, Any]
    active_spot_quotes: Optional[List[Dict[str, Any]]] = None

@app.get("/api/v1/health")
def health_check():
    """Returns real-time engine health and integration endpoints."""
    return {
        "status": "HEALTHY",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "sqlite_database": "CONNECTED",
            "ollama_nlp": OLLAMA_BASE_URL,
            "dify_copilot": DIFY_BASE_URL,
            "n8n_orchestrator": N8N_BASE_URL
        }
    }

@app.post("/api/v1/shipments/intake")
def intake_shipment(payload: Dict[str, Any] = Body(...)):
    """
    Ingests and normalizes an unstructured/semi-structured freight request
    into a standardized Shipment entity.
    """
    try:
        shipment = normalize_shipment_request(payload)
        return {
            "status": "NORMALIZED",
            "shipment": shipment.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Normalization failed: {str(e)}")

@app.post("/api/v1/procurement/optimize")
def optimize_procurement(req: OptimizationRequest):
    """
    Executes the master 5-layer multi-objective procurement algorithm:
    1. Enrichment & Route Geodesics
    2. Hard Constraint Filtering (Compliance, Equipment, Safety)
    3. Landed Cost, Transit Distribution, Risk & Capacity Modeling
    4. Spot vs Contract Expected Value Arbitrage
    5. Tiered Approval Routing & Explainability
    """
    try:
        shipment = normalize_shipment_request(req.shipment_payload)
        
        spot_quotes = []
        if req.active_spot_quotes:
            for sq_dict in req.active_spot_quotes:
                spot_quotes.append(SpotQuote(**sq_dict))
                
        recommendation = run_procurement_optimization(shipment, active_spot_quotes=spot_quotes)
        return {
            "status": "SUCCESS",
            "shipment_id": shipment.shipment_id,
            "recommendation": recommendation.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Procurement optimization failed: {str(e)}")

@app.post("/api/v1/rfq/generate")
def generate_rfq(payload: Dict[str, Any] = Body(...)):
    """
    Drafts an enterprise RFQ broadcast package for carrier partners.
    """
    try:
        shipment = normalize_shipment_request(payload)
        carriers = get_all_carriers()
        rfq_email = generate_rfq_email(shipment, carriers)
        return {
            "shipment_id": shipment.shipment_id,
            "rfq_email_draft": rfq_email,
            "target_carriers_count": len(carriers)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"RFQ generation error: {str(e)}")

@app.post("/api/v1/rfq/extract-quote")
def extract_quote(payload: QuoteTextPayload):
    """
    Extracts structured quote terms from carrier emails or PDF text via Qwen NLP.
    """
    try:
        quote_attrs = extract_carrier_quote(payload.raw_text)
        return {
            "status": "EXTRACTED",
            "quote": quote_attrs
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Quote extraction error: {str(e)}")

@app.post("/api/v1/approvals/{approval_id}/decide")
def submit_approval_decision(approval_id: str, payload: DecisionPayload):
    """
    Records human logistics supervisor, procurement manager, or VP approval decision.
    """
    action = payload.action.upper()
    if action not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Action must be 'APPROVED' or 'REJECTED'")
        
    decide_approval(approval_id, action, payload.approver, payload.comments)
    save_audit_log(
        entity_type="PROCUREMENT_APPROVAL",
        entity_id=approval_id,
        event_type=f"APPROVAL_{action}",
        rule_name="HUMAN_GOVERNANCE_GATEWAY",
        input_summary=f"Approver: {payload.approver}",
        output_summary=f"Status set to {action}: {payload.comments or 'No comment'}",
        actor=payload.approver
    )
    return {
        "approval_id": approval_id,
        "status": action,
        "decided_at": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/shipments/{shipment_id}")
def get_shipment_details(shipment_id: str):
    """
    Retrieves complete shipment lifecycle state, winning recommendation,
    and immutable audit log history.
    """
    s = get_shipment(shipment_id)
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
        
    conn = get_connection()
    rec_row = conn.execute("SELECT * FROM recommendations WHERE shipment_id = ? ORDER BY created_at DESC LIMIT 1;", (shipment_id,)).fetchone()
    app_row = conn.execute("SELECT * FROM approvals WHERE shipment_id = ? ORDER BY created_at DESC LIMIT 1;", (shipment_id,)).fetchone()
    audit_rows = conn.execute("SELECT * FROM audit_logs WHERE entity_id = ? ORDER BY timestamp ASC;", (shipment_id,)).fetchall()
    conn.close()

    return {
        "shipment": s,
        "recommendation": dict(rec_row) if rec_row else None,
        "approval": dict(app_row) if app_row else None,
        "audit_trail": [dict(r) for r in audit_rows]
    }

@app.get("/api/v1/carriers/scorecards")
def get_carrier_scorecards():
    """
    Retrieves active master carrier directory with live scorecard KPIs.
    """
    carriers = get_all_carriers()
    return {
        "total_active_carriers": len(carriers),
        "scorecards": [c.model_dump() for c in carriers]
    }

if __name__ == "__main__":
    uvicorn.run(app, host=DECISION_ENGINE_HOST, port=DECISION_ENGINE_PORT)
