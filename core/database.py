"""
Relational SQLite Persistence & Immutable Audit Log Store for Freight Procurement.
Matches Sections 13, 16, and 18 of plan.md.
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.config import DB_PATH
from core.models import (
    Shipment, Carrier, Location, ContractRate, SpotQuote,
    Recommendation, ApprovalRecord, AuditLogEntry, ShipmentStatus, ApprovalStatus
)

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Locations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        location_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        address TEXT,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        country TEXT NOT NULL,
        postal_code TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        dock_constraints TEXT,
        operating_hours TEXT,
        appointment_required INTEGER NOT NULL,
        avg_dwell_hours REAL NOT NULL
    );
    """)

    # Lanes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lanes (
        lane_id TEXT PRIMARY KEY,
        origin_city TEXT NOT NULL,
        origin_state TEXT NOT NULL,
        dest_city TEXT NOT NULL,
        dest_state TEXT NOT NULL,
        mode TEXT NOT NULL,
        distance_miles REAL NOT NULL,
        avg_transit_hours REAL NOT NULL,
        transit_std_dev REAL NOT NULL,
        delay_rate REAL NOT NULL,
        spot_rate_avg REAL NOT NULL,
        spot_volatility REAL NOT NULL
    );
    """)

    # Carriers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carriers (
        carrier_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        scac TEXT NOT NULL,
        modes_json TEXT NOT NULL,
        equipment_json TEXT NOT NULL,
        safety_score REAL NOT NULL,
        insurance_valid INTEGER NOT NULL,
        insurance_coverage_usd REAL NOT NULL,
        claims_rate_pct REAL NOT NULL,
        on_time_delivery_rate REAL NOT NULL,
        tender_acceptance_rate REAL NOT NULL,
        carbon_efficiency_score REAL NOT NULL,
        financial_risk_score REAL NOT NULL,
        is_active INTEGER NOT NULL
    );
    """)

    # Carrier Lane performance table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS carrier_lanes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        carrier_id TEXT NOT NULL,
        lane_id TEXT NOT NULL,
        historical_volume INTEGER NOT NULL,
        on_time_rate REAL NOT NULL,
        tender_accept_rate REAL NOT NULL,
        avg_delay_hours REAL NOT NULL,
        FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id),
        FOREIGN KEY (lane_id) REFERENCES lanes(lane_id)
    );
    """)

    # Contract Rates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contract_rates (
        rate_id TEXT PRIMARY KEY,
        carrier_id TEXT NOT NULL,
        lane_id TEXT NOT NULL,
        mode TEXT NOT NULL,
        equipment_type TEXT NOT NULL,
        base_rate_usd REAL NOT NULL,
        fuel_surcharge_pct REAL NOT NULL,
        detention_hourly_rate REAL NOT NULL,
        detention_free_hours REAL NOT NULL,
        valid_until TEXT NOT NULL,
        FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id),
        FOREIGN KEY (lane_id) REFERENCES lanes(lane_id)
    );
    """)

    # Shipments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        shipment_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_tier TEXT NOT NULL,
        priority TEXT NOT NULL,
        origin_id TEXT NOT NULL,
        dest_id TEXT NOT NULL,
        commodity_json TEXT NOT NULL,
        equipment_needed TEXT NOT NULL,
        requested_pickup TEXT NOT NULL,
        requested_delivery TEXT NOT NULL,
        budget_ceiling_usd REAL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (origin_id) REFERENCES locations(location_id),
        FOREIGN KEY (dest_id) REFERENCES locations(location_id)
    );
    """)

    # RFQ Requests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rfq_requests (
        rfq_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        target_carriers_json TEXT NOT NULL,
        broadcast_at TEXT NOT NULL,
        deadline_at TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
    );
    """)

    # Spot Quotes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS spot_quotes (
        quote_id TEXT PRIMARY KEY,
        rfq_id TEXT NOT NULL,
        carrier_id TEXT NOT NULL,
        carrier_name TEXT NOT NULL,
        base_rate_usd REAL NOT NULL,
        fuel_surcharge_usd REAL NOT NULL,
        accessorials_usd REAL NOT NULL,
        total_quote_usd REAL NOT NULL,
        transit_days_promised REAL NOT NULL,
        valid_hours INTEGER NOT NULL,
        is_equipment_guaranteed INTEGER NOT NULL,
        received_at TEXT NOT NULL,
        FOREIGN KEY (rfq_id) REFERENCES rfq_requests(rfq_id),
        FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id)
    );
    """)

    # Recommendations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        recommendation_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        recommended_carrier_id TEXT NOT NULL,
        carrier_name TEXT NOT NULL,
        mode TEXT NOT NULL,
        rate_type TEXT NOT NULL,
        route_summary TEXT NOT NULL,
        cost_json TEXT NOT NULL,
        transit_json TEXT NOT NULL,
        risk_score REAL NOT NULL,
        risk_severity TEXT NOT NULL,
        capacity_confidence REAL NOT NULL,
        carbon_kg_co2e REAL NOT NULL,
        approval_tier TEXT NOT NULL,
        explanation_json TEXT NOT NULL,
        alternatives_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
        FOREIGN KEY (recommended_carrier_id) REFERENCES carriers(carrier_id)
    );
    """)

    # Approvals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        approval_id TEXT PRIMARY KEY,
        recommendation_id TEXT NOT NULL,
        shipment_id TEXT NOT NULL,
        required_tier TEXT NOT NULL,
        status TEXT NOT NULL,
        approved_by TEXT,
        decided_at TEXT,
        comments TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (recommendation_id) REFERENCES recommendations(recommendation_id),
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
    );
    """)

    # Settlements table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settlements (
        settlement_id TEXT PRIMARY KEY,
        shipment_id TEXT NOT NULL,
        carrier_id TEXT NOT NULL,
        estimated_cost REAL NOT NULL,
        actual_cost REAL NOT NULL,
        variance_amount REAL NOT NULL,
        variance_pct REAL NOT NULL,
        invoice_approved INTEGER NOT NULL,
        settled_at TEXT NOT NULL,
        FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
        FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id)
    );
    """)

    # Immutable Audit Log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        rule_name TEXT NOT NULL,
        input_summary TEXT NOT NULL,
        output_summary TEXT NOT NULL,
        confidence REAL NOT NULL,
        actor TEXT NOT NULL
    );
    """)

    # Performance Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contract_rates_lookup ON contract_rates(lane_id, equipment_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_shipment ON recommendations(shipment_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_id);")

    conn.commit()
    conn.close()

def log_audit(entity_type: str, entity_id: str, event_type: str, rule_name: str,
              input_summary: str, output_summary: str, confidence: float = 1.0, actor: str = "SYSTEM"):
    conn = get_connection()
    import uuid
    log_id = f"LOG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    conn.execute("""
    INSERT INTO audit_logs (log_id, timestamp, entity_type, entity_id, event_type, rule_name, input_summary, output_summary, confidence, actor)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (log_id, datetime.utcnow().isoformat(), entity_type, entity_id, event_type, rule_name, input_summary, output_summary, confidence, actor))
    conn.commit()
    conn.close()

def save_shipment(s: Shipment):
    conn = get_connection()
    now_iso = datetime.utcnow().isoformat()
    conn.execute("""
    INSERT OR REPLACE INTO shipments (
        shipment_id, customer_id, customer_name, customer_tier, priority, origin_id, dest_id,
        commodity_json, equipment_needed, requested_pickup, requested_delivery, budget_ceiling_usd,
        status, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        s.shipment_id, s.customer_id, s.customer_name, s.customer_tier.value, s.priority.value,
        s.origin.location_id, s.destination.location_id, s.commodity.model_dump_json(),
        s.equipment_needed.value, s.requested_pickup.isoformat(), s.requested_delivery.isoformat(),
        s.budget_ceiling_usd, s.status.value, s.created_at.isoformat(), now_iso
    ))
    conn.commit()
    conn.close()

def get_shipment(shipment_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM shipments WHERE shipment_id = ?;", (shipment_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["commodity"] = json.loads(d["commodity_json"])
    return d

def get_location(location_id: str) -> Optional[Location]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM locations WHERE location_id = ?;", (location_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return Location(
        location_id=row["location_id"],
        name=row["name"],
        address=row["address"],
        city=row["city"],
        state=row["state"],
        country=row["country"],
        postal_code=row["postal_code"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        dock_constraints=row["dock_constraints"],
        operating_hours=row["operating_hours"],
        appointment_required=bool(row["appointment_required"]),
        avg_dwell_hours=row["avg_dwell_hours"]
    )

def get_lane(origin_city: str, origin_state: str, dest_city: str, dest_state: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("""
    SELECT * FROM lanes 
    WHERE origin_city = ? AND origin_state = ? AND dest_city = ? AND dest_state = ?;
    """, (origin_city, origin_state, dest_city, dest_state)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_carriers() -> List[Carrier]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM carriers WHERE is_active = 1;").fetchall()
    conn.close()
    carriers = []
    for r in rows:
        carriers.append(Carrier(
            carrier_id=r["carrier_id"],
            name=r["name"],
            scac=r["scac"],
            modes=json.loads(r["modes_json"]),
            equipment_types=json.loads(r["equipment_json"]),
            safety_score=r["safety_score"],
            insurance_valid=bool(r["insurance_valid"]),
            insurance_coverage_usd=r["insurance_coverage_usd"],
            claims_rate_pct=r["claims_rate_pct"],
            on_time_delivery_rate=r["on_time_delivery_rate"],
            tender_acceptance_rate=r["tender_acceptance_rate"],
            carbon_efficiency_score=r["carbon_efficiency_score"],
            financial_risk_score=r["financial_risk_score"],
            is_active=bool(r["is_active"])
        ))
    return carriers

def get_contract_rates(carrier_id: Optional[str] = None, lane_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    sql = "SELECT * FROM contract_rates WHERE 1=1"
    params = []
    if carrier_id:
        sql += " AND carrier_id = ?"
        params.append(carrier_id)
    if lane_id:
        sql += " AND lane_id = ?"
        params.append(lane_id)
    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_recommendation(rec: Recommendation):
    conn = get_connection()
    conn.execute("""
    INSERT OR REPLACE INTO recommendations (
        recommendation_id, shipment_id, recommended_carrier_id, carrier_name, mode, rate_type,
        route_summary, cost_json, transit_json, risk_score, risk_severity, capacity_confidence,
        carbon_kg_co2e, approval_tier, explanation_json, alternatives_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        rec.recommendation_id, rec.shipment_id, rec.recommended_carrier_id, rec.carrier_name,
        rec.mode.value, rec.rate_type.value, rec.route_summary, rec.cost_breakdown.model_dump_json(),
        rec.transit_prediction.model_dump_json(), rec.risk_score, rec.risk_severity.value,
        rec.capacity_confidence, rec.carbon_kg_co2e, rec.approval_tier.value,
        json.dumps(rec.explanation), json.dumps([a.model_dump() for a in rec.alternatives]),
        rec.created_at.isoformat()
    ))
    conn.commit()
    conn.close()

def save_approval(approval_obj_or_rec_id, shipment_id: Optional[str] = None, tier: Optional[str] = None) -> str:
    import uuid
    conn = get_connection()
    if isinstance(approval_obj_or_rec_id, ApprovalRecord):
        rec = approval_obj_or_rec_id
        conn.execute("""
        INSERT OR REPLACE INTO approvals (
            approval_id, recommendation_id, shipment_id, required_tier, status,
            approved_by, decided_at, comments, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            rec.approval_id, rec.recommendation_id, rec.shipment_id,
            rec.required_tier.value if hasattr(rec.required_tier, "value") else str(rec.required_tier),
            rec.status.value if hasattr(rec.status, "value") else str(rec.status),
            rec.approved_by, rec.decided_at.isoformat() if rec.decided_at else None,
            rec.comments, rec.created_at.isoformat()
        ))
        conn.commit()
        conn.close()
        return rec.approval_id
    else:
        rec_id = approval_obj_or_rec_id
        app_id = f"APP-{datetime.utcnow().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"
        conn.execute("""
        INSERT INTO approvals (approval_id, recommendation_id, shipment_id, required_tier, status, created_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?);
        """, (app_id, rec_id, shipment_id, tier, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return app_id

def decide_approval(approval_id: str, action: str, approver: str, comments: Optional[str] = None):
    conn = get_connection()
    now_iso = datetime.utcnow().isoformat()
    conn.execute("""
    UPDATE approvals 
    SET status = ?, approved_by = ?, decided_at = ?, comments = ?
    WHERE approval_id = ?;
    """, (action, approver, now_iso, comments, approval_id))
    conn.commit()
    conn.close()

def save_carrier(c: Carrier):
    conn = get_connection()
    modes_json = json.dumps([m.value if hasattr(m, "value") else str(m) for m in c.modes])
    eq_json = json.dumps([e.value if hasattr(e, "value") else str(e) for e in c.equipment_types])
    conn.execute("""
    INSERT OR REPLACE INTO carriers (
        carrier_id, name, scac, modes_json, equipment_json, safety_score,
        insurance_valid, insurance_coverage_usd, claims_rate_pct, on_time_delivery_rate,
        tender_acceptance_rate, carbon_efficiency_score, financial_risk_score, is_active
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        c.carrier_id, c.name, c.scac, modes_json, eq_json, c.safety_score,
        1 if c.insurance_valid else 0, c.insurance_coverage_usd, c.claims_rate_pct,
        c.on_time_delivery_rate, c.tender_acceptance_rate, c.carbon_efficiency_score,
        c.financial_risk_score, 1 if c.is_active else 0
    ))
    conn.commit()
    conn.close()

def save_contract_rate(r: ContractRate):
    conn = get_connection()
    conn.execute("""
    INSERT OR REPLACE INTO contract_rates (
        rate_id, carrier_id, lane_id, mode, equipment_type, base_rate_usd,
        fuel_surcharge_pct, detention_hourly_rate, detention_free_hours, valid_until
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        r.rate_id, r.carrier_id, r.lane_id,
        r.mode.value if hasattr(r.mode, "value") else str(r.mode),
        r.equipment_type.value if hasattr(r.equipment_type, "value") else str(r.equipment_type),
        r.base_rate_usd, r.fuel_surcharge_pct, r.detention_hourly_rate,
        r.detention_free_hours, r.valid_until.isoformat()
    ))
    conn.commit()
    conn.close()

def get_all_carriers() -> List[Carrier]:
    return get_carriers()

def get_contract_rates_by_lane(lane_id: str) -> List[ContractRate]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM contract_rates WHERE lane_id = ?;", (lane_id,)).fetchall()
    conn.close()
    rates = []
    from core.models import TransportMode, EquipmentType
    for r in rows:
        rates.append(ContractRate(
            rate_id=r["rate_id"],
            carrier_id=r["carrier_id"],
            lane_id=r["lane_id"],
            mode=TransportMode(r["mode"]),
            equipment_type=EquipmentType(r["equipment_type"]),
            base_rate_usd=r["base_rate_usd"],
            fuel_surcharge_pct=r["fuel_surcharge_pct"],
            detention_hourly_rate=r["detention_hourly_rate"],
            detention_free_hours=r["detention_free_hours"],
            valid_until=datetime.fromisoformat(r["valid_until"])
        ))
    return rates

def save_audit_log(entity_type: str, entity_id: str, event_type: str, rule_name: str,
                   input_summary: str, output_summary: str, confidence: float = 1.0, actor: str = "SYSTEM"):
    log_audit(entity_type, entity_id, event_type, rule_name, input_summary, output_summary, confidence, actor)

