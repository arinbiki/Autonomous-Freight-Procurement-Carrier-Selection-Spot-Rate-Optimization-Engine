"""
Domain models and enumerations for Autonomous Freight Procurement & Carrier Selection.
Matches Sections 4, 5, 8, and 13 of plan.md.
"""
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TransportMode(str, Enum):
    ROAD_FTL = "ROAD_FTL"
    ROAD_LTL = "ROAD_LTL"
    PARCEL = "PARCEL"
    INTERMODAL = "INTERMODAL"
    OCEAN = "OCEAN"
    AIR = "AIR"
    RAIL = "RAIL"
    COURIER = "COURIER"
    DEDICATED_FLEET = "DEDICATED_FLEET"

class EquipmentType(str, Enum):
    DRY_VAN_53 = "DRY_VAN_53"
    REEFER_53 = "REEFER_53"
    FLATBED = "FLATBED"
    STEP_DECK = "STEP_DECK"
    BOX_TRUCK = "BOX_TRUCK"
    CONTAINER_40HC = "CONTAINER_40HC"
    CONTAINER_20GP = "CONTAINER_20GP"
    AIR_PALLET = "AIR_PALLET"
    SPRINTER_VAN = "SPRINTER_VAN"

class ShipmentPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    STANDARD = "STANDARD"
    LOW = "LOW"

class CustomerTier(str, Enum):
    TIER_1_STRATEGIC = "TIER_1_STRATEGIC"
    TIER_2_ENTERPRISE = "TIER_2_ENTERPRISE"
    TIER_3_STANDARD = "TIER_3_STANDARD"
    TIER_4_SPOT = "TIER_4_SPOT"

class ShipmentStatus(str, Enum):
    DRAFT = "DRAFT"
    NORMALIZED = "NORMALIZED"
    ENRICHED = "ENRICHED"
    ELIGIBILITY_FILTERED = "ELIGIBILITY_FILTERED"
    SCORED = "SCORED"
    OPTIMIZED = "OPTIMIZED"
    RFQ_REQUIRED = "RFQ_REQUIRED"
    QUOTING = "QUOTING"
    EVALUATED = "EVALUATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    AWARDED = "AWARDED"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    EXCEPTION = "EXCEPTION"
    DELIVERED = "DELIVERED"
    SETTLED = "SETTLED"
    CLOSED = "CLOSED"

class RateType(str, Enum):
    CONTRACT = "CONTRACT"
    SPOT = "SPOT"
    HYBRID = "HYBRID"

class ApprovalTier(str, Enum):
    TIER_1_AUTO = "TIER_1_AUTO"
    TIER_2_SUPERVISOR = "TIER_2_SUPERVISOR"
    TIER_3_PROCUREMENT_MANAGER = "TIER_3_PROCUREMENT_MANAGER"
    TIER_4_VP_SUPPLY_CHAIN = "TIER_4_VP_SUPPLY_CHAIN"

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Location(BaseModel):
    location_id: str
    name: str
    address: Optional[str] = None
    city: str
    state: str
    country: str = "USA"
    postal_code: str
    latitude: float
    longitude: float
    dock_constraints: Optional[str] = None
    operating_hours: Optional[str] = "08:00-17:00"
    appointment_required: bool = True
    avg_dwell_hours: float = 2.5

class Commodity(BaseModel):
    description: str
    hs_code: Optional[str] = None
    value_usd: float = 50000.0
    weight_lbs: float
    volume_cbf: Optional[float] = None
    pallet_count: int = 24
    is_stackable: bool = True
    is_fragile: bool = False
    is_hazmat: bool = False
    hazmat_class: Optional[str] = None
    is_temp_controlled: bool = False
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    security_level: str = "STANDARD"

class Shipment(BaseModel):
    shipment_id: str
    customer_id: str
    customer_name: str
    customer_tier: CustomerTier = CustomerTier.TIER_2_ENTERPRISE
    priority: ShipmentPriority = ShipmentPriority.STANDARD
    origin: Location
    destination: Location
    commodity: Commodity
    equipment_needed: EquipmentType = EquipmentType.DRY_VAN_53
    requested_pickup: datetime
    requested_delivery: datetime
    budget_ceiling_usd: Optional[float] = None
    status: ShipmentStatus = ShipmentStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Carrier(BaseModel):
    carrier_id: str
    name: str
    scac: str
    modes: List[TransportMode]
    equipment_types: List[EquipmentType]
    safety_score: float = 95.0
    insurance_valid: bool = True
    insurance_coverage_usd: float = 1000000.0
    claims_rate_pct: float = 0.5
    on_time_delivery_rate: float = 0.94
    tender_acceptance_rate: float = 0.90
    carbon_efficiency_score: float = 85.0
    financial_risk_score: float = 15.0
    is_active: bool = True

class ContractRate(BaseModel):
    rate_id: str
    carrier_id: str
    lane_id: str
    mode: TransportMode
    equipment_type: EquipmentType
    base_rate_usd: float
    fuel_surcharge_pct: float = 18.0
    detention_hourly_rate: float = 75.0
    detention_free_hours: float = 2.0
    valid_until: datetime

class SpotQuote(BaseModel):
    quote_id: str
    rfq_id: str
    carrier_id: str
    carrier_name: str
    base_rate_usd: float
    fuel_surcharge_usd: float
    accessorials_usd: float = 0.0
    total_quote_usd: float
    transit_days_promised: float
    valid_hours: int = 24
    is_equipment_guaranteed: bool = True
    received_at: datetime = Field(default_factory=datetime.utcnow)

class CostBreakdown(BaseModel):
    base_freight: float
    fuel_surcharge: float
    accessorials: float
    expected_detention: float
    expected_delay_penalty: float
    risk_premium: float
    carbon_cost: float
    volume_discount: float = 0.0
    total_expected_cost: float

class TransitPrediction(BaseModel):
    p50_hours: float
    p80_hours: float
    p90_hours: float
    expected_hours: float
    on_time_probability: float
    risk_buffer_hours: float

class CarrierScore(BaseModel):
    cost_score: float
    service_score: float
    risk_score: float
    capacity_score: float
    sustainability_score: float
    composite_score: float

class AlternativeOption(BaseModel):
    carrier_id: str
    carrier_name: str
    mode: TransportMode
    rate_type: RateType
    total_expected_cost: float
    expected_transit_hours: float
    on_time_probability: float
    risk_severity: RiskSeverity
    composite_score: float
    category_label: str  # e.g., "Best Cost", "Fastest Service", "Lowest Risk", "Lowest Carbon"

class Recommendation(BaseModel):
    recommendation_id: str
    shipment_id: str
    recommended_carrier_id: str
    carrier_name: str
    mode: TransportMode
    rate_type: RateType
    route_summary: str
    cost_breakdown: CostBreakdown
    transit_prediction: TransitPrediction
    risk_score: float
    risk_severity: RiskSeverity
    capacity_confidence: float
    carbon_kg_co2e: float
    approval_tier: ApprovalTier
    explanation: Dict[str, Any]
    alternatives: List[AlternativeOption]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ApprovalRecord(BaseModel):
    approval_id: str
    recommendation_id: str
    shipment_id: str
    required_tier: ApprovalTier
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuditLogEntry(BaseModel):
    log_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    entity_type: str
    entity_id: str
    event_type: str
    rule_name: str
    input_summary: str
    output_summary: str
    confidence: float
    actor: str
