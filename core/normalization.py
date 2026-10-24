"""
Shipment Intake and Normalization Module.
Converts raw ingestion payloads into standardized Shipment domain models.
Implements validation, geocoding fallback, and default configuration.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from core.models import (
    Shipment, Location, Commodity, EquipmentType,
    ShipmentPriority, CustomerTier, ShipmentStatus
)

# Reference US logistics hubs for instant coordinate resolution
KNOWN_HUBS: Dict[str, Tuple[float, float, str, str]] = {
    "CHICAGO": (41.8781, -87.6298, "IL", "60601"),
    "DALLAS": (32.7767, -96.7970, "TX", "75201"),
    "ATLANTA": (33.7490, -84.3880, "GA", "30303"),
    "LOS ANGELES": (34.0522, -118.2437, "CA", "90012"),
    "NEW YORK": (40.7128, -74.0060, "NY", "10001"),
    "MEMPHIS": (35.1495, -90.0490, "TN", "38103"),
    "SAVANNAH": (32.0809, -81.0912, "GA", "31401"),
    "SEATTLE": (47.6062, -122.3321, "WA", "98101"),
    "HOUSTON": (29.7604, -95.3698, "TX", "77002"),
    "COLUMBUS": (39.9612, -82.9988, "OH", "43215"),
    "KANSAS CITY": (39.0997, -94.5786, "MO", "64105"),
    "PHILADELPHIA": (39.9526, -75.1652, "PA", "19107"),
    "DETROIT": (42.3314, -83.0458, "MI", "48226"),
    "INDIANAPOLIS": (39.7684, -86.1581, "IN", "46204"),
}

def resolve_location(raw_loc: Dict[str, Any], default_name: str) -> Location:
    city = str(raw_loc.get("city", "CHICAGO")).strip().upper()
    state = str(raw_loc.get("state", "IL")).strip().upper()
    
    lat = raw_loc.get("latitude")
    lon = raw_loc.get("longitude")
    postal = str(raw_loc.get("postal_code", "00000"))
    
    if lat is None or lon is None:
        if city in KNOWN_HUBS:
            h_lat, h_lon, h_state, h_postal = KNOWN_HUBS[city]
            lat, lon = h_lat, h_lon
            state = state or h_state
            postal = postal if postal != "00000" else h_postal
        else:
            # Fallback to central US coordinates
            lat, lon = 39.8283, -98.5795
            
    return Location(
        location_id=str(raw_loc.get("location_id", f"LOC-{city[:3]}-{uuid.uuid4().hex[:6]}")),
        name=str(raw_loc.get("name", default_name)),
        address=raw_loc.get("address"),
        city=city,
        state=state,
        country=str(raw_loc.get("country", "USA")),
        postal_code=postal,
        latitude=float(lat),
        longitude=float(lon),
        dock_constraints=raw_loc.get("dock_constraints"),
        operating_hours=raw_loc.get("operating_hours", "07:00-18:00"),
        appointment_required=bool(raw_loc.get("appointment_required", True)),
        avg_dwell_hours=float(raw_loc.get("avg_dwell_hours", 2.0))
    )

def parse_iso_datetime(dt_val: Any, default_offset_days: int = 1) -> datetime:
    if isinstance(dt_val, datetime):
        return dt_val
    if isinstance(dt_val, str) and dt_val:
        try:
            # Handle standard ISO formats
            clean_str = dt_val.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_str)
        except Exception:
            pass
    return datetime.utcnow() + timedelta(days=default_offset_days)

def normalize_shipment_request(payload: Dict[str, Any]) -> Shipment:
    """
    Standardizes a raw intake dictionary into a validated Shipment model.
    """
    shipment_id = str(payload.get("shipment_id") or f"SHP-{uuid.uuid4().hex[:8].upper()}")
    
    # Customer
    customer_id = str(payload.get("customer_id", "CUST-DEFAULT"))
    customer_name = str(payload.get("customer_name", "Enterprise Shipper"))
    raw_tier = str(payload.get("customer_tier", "TIER_2_ENTERPRISE")).upper()
    try:
        tier = CustomerTier(raw_tier)
    except ValueError:
        tier = CustomerTier.TIER_2_ENTERPRISE

    # Priority
    raw_prio = str(payload.get("priority", "STANDARD")).upper()
    try:
        priority = ShipmentPriority(raw_prio)
    except ValueError:
        priority = ShipmentPriority.STANDARD

    # Locations
    origin_raw = payload.get("origin") or {"city": "CHICAGO", "state": "IL"}
    dest_raw = payload.get("destination") or {"city": "DALLAS", "state": "TX"}
    origin = resolve_location(origin_raw, "Origin Distribution Center")
    destination = resolve_location(dest_raw, "Destination Fulfillment Center")

    # Commodity
    comm_raw = payload.get("commodity") or {}
    weight = float(comm_raw.get("weight_lbs", payload.get("weight_lbs", 42000.0)))
    val_usd = float(comm_raw.get("value_usd", payload.get("value_usd", 65000.0)))
    pallets = int(comm_raw.get("pallet_count", payload.get("pallet_count", 24)))
    is_hazmat = bool(comm_raw.get("is_hazmat", payload.get("is_hazmat", False)))
    is_temp = bool(comm_raw.get("is_temp_controlled", payload.get("is_temp_controlled", False)))

    commodity = Commodity(
        description=str(comm_raw.get("description", "Consumer Packaged Goods")),
        hs_code=comm_raw.get("hs_code"),
        value_usd=val_usd,
        weight_lbs=weight,
        volume_cbf=float(comm_raw.get("volume_cbf", 3200.0)) if comm_raw.get("volume_cbf") else None,
        pallet_count=pallets,
        is_stackable=bool(comm_raw.get("is_stackable", True)),
        is_fragile=bool(comm_raw.get("is_fragile", False)),
        is_hazmat=is_hazmat,
        hazmat_class=comm_raw.get("hazmat_class") if is_hazmat else None,
        is_temp_controlled=is_temp,
        temp_min_c=float(comm_raw.get("temp_min_c", 2.0)) if is_temp else None,
        temp_max_c=float(comm_raw.get("temp_max_c", 6.0)) if is_temp else None,
        security_level=str(comm_raw.get("security_level", "STANDARD"))
    )

    # Equipment
    equip_str = str(payload.get("equipment_needed", "DRY_VAN_53")).upper()
    if is_temp and "REEFER" not in equip_str:
        equip_str = "REEFER_53"
    try:
        equipment = EquipmentType(equip_str)
    except ValueError:
        equipment = EquipmentType.REEFER_53 if is_temp else EquipmentType.DRY_VAN_53

    # Dates
    pickup_dt = parse_iso_datetime(payload.get("requested_pickup"), default_offset_days=1)
    delivery_dt = parse_iso_datetime(payload.get("requested_delivery"), default_offset_days=3)
    if delivery_dt <= pickup_dt:
        delivery_dt = pickup_dt + timedelta(days=2)

    budget = payload.get("budget_ceiling_usd")
    budget_usd = float(budget) if budget is not None else None

    return Shipment(
        shipment_id=shipment_id,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_tier=tier,
        priority=priority,
        origin=origin,
        destination=destination,
        commodity=commodity,
        equipment_needed=equipment,
        requested_pickup=pickup_dt,
        requested_delivery=delivery_dt,
        budget_ceiling_usd=budget_usd,
        status=ShipmentStatus.NORMALIZED,
        created_at=datetime.utcnow()
    )
