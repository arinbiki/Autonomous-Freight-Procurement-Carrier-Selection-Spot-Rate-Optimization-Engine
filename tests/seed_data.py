"""
Database Seeding Script.
Populates enterprise carrier directory, lane contracts, and baseline historical records
into SQLite database for testing and real-time n8n procurement workflows.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ensure parent directory is on python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import (
    Carrier, ContractRate, TransportMode, EquipmentType
)
from core.database import (
    init_db, save_carrier, save_contract_rate, get_all_carriers
)

def seed_enterprise_data():
    print("Initializing SQLite schema...")
    init_db()

    print("Seeding Tier-1 Master Carriers...")
    carriers = [
        Carrier(
            carrier_id="CARRIER-APEX",
            name="Apex Freight Logistics",
            scac="APXF",
            modes=[TransportMode.ROAD_FTL, TransportMode.DEDICATED_FLEET],
            equipment_types=[EquipmentType.DRY_VAN_53, EquipmentType.REEFER_53],
            safety_score=96.5,
            insurance_valid=True,
            insurance_coverage_usd=2500000.0,
            claims_rate_pct=0.35,
            on_time_delivery_rate=0.965,
            tender_acceptance_rate=0.94,
            carbon_efficiency_score=88.0,
            financial_risk_score=12.0,
            is_active=True
        ),
        Carrier(
            carrier_id="CARRIER-SWIFT",
            name="SwiftHaul Transportation",
            scac="SWFT",
            modes=[TransportMode.ROAD_FTL, TransportMode.ROAD_LTL],
            equipment_types=[EquipmentType.DRY_VAN_53, EquipmentType.BOX_TRUCK],
            safety_score=91.0,
            insurance_valid=True,
            insurance_coverage_usd=1000000.0,
            claims_rate_pct=0.75,
            on_time_delivery_rate=0.915,
            tender_acceptance_rate=0.91,
            carbon_efficiency_score=82.0,
            financial_risk_score=18.0,
            is_active=True
        ),
        Carrier(
            carrier_id="CARRIER-GREEN",
            name="GreenLine Eco-Logistics",
            scac="GLEL",
            modes=[TransportMode.ROAD_FTL, TransportMode.INTERMODAL],
            equipment_types=[EquipmentType.DRY_VAN_53, EquipmentType.CONTAINER_40HC],
            safety_score=95.0,
            insurance_valid=True,
            insurance_coverage_usd=1500000.0,
            claims_rate_pct=0.40,
            on_time_delivery_rate=0.945,
            tender_acceptance_rate=0.92,
            carbon_efficiency_score=96.0,
            financial_risk_score=14.0,
            is_active=True
        ),
        Carrier(
            carrier_id="CARRIER-TITAN",
            name="Titan Heavy & Hazmat Transport",
            scac="THHT",
            modes=[TransportMode.ROAD_FTL],
            equipment_types=[EquipmentType.DRY_VAN_53, EquipmentType.REEFER_53, EquipmentType.FLATBED, EquipmentType.STEP_DECK],
            safety_score=98.5,
            insurance_valid=True,
            insurance_coverage_usd=5000000.0,
            claims_rate_pct=0.15,
            on_time_delivery_rate=0.975,
            tender_acceptance_rate=0.96,
            carbon_efficiency_score=84.0,
            financial_risk_score=8.0,
            is_active=True
        ),
        Carrier(
            carrier_id="CARRIER-TRANS",
            name="TransGlobal Intermodal Rail",
            scac="TGIR",
            modes=[TransportMode.INTERMODAL, TransportMode.RAIL],
            equipment_types=[EquipmentType.CONTAINER_40HC, EquipmentType.CONTAINER_20GP],
            safety_score=94.0,
            insurance_valid=True,
            insurance_coverage_usd=2000000.0,
            claims_rate_pct=0.50,
            on_time_delivery_rate=0.905,
            tender_acceptance_rate=0.88,
            carbon_efficiency_score=94.0,
            financial_risk_score=10.0,
            is_active=True
        )
    ]

    for c in carriers:
        save_carrier(c)
        print(f" -> Saved Carrier: {c.name} ({c.carrier_id})")

    print("\nSeeding Contract Rates across strategic corridors...")
    valid_year = datetime.utcnow() + timedelta(days=365)
    
    contract_rates = [
        # Chicago to Dallas (~920 miles)
        ContractRate(
            rate_id="RATE-APX-CHIC-DALL",
            carrier_id="CARRIER-APEX",
            lane_id="CHIC_IL-DALL_TX",
            mode=TransportMode.ROAD_FTL,
            equipment_type=EquipmentType.DRY_VAN_53,
            base_rate_usd=2150.0,
            fuel_surcharge_pct=17.5,
            detention_hourly_rate=75.0,
            detention_free_hours=2.0,
            valid_until=valid_year
        ),
        ContractRate(
            rate_id="RATE-APX-CHIC-DALL-REEFER",
            carrier_id="CARRIER-APEX",
            lane_id="CHIC_IL-DALL_TX",
            mode=TransportMode.ROAD_FTL,
            equipment_type=EquipmentType.REEFER_53,
            base_rate_usd=2650.0,
            fuel_surcharge_pct=19.0,
            detention_hourly_rate=85.0,
            detention_free_hours=2.0,
            valid_until=valid_year
        ),
        ContractRate(
            rate_id="RATE-SWF-CHIC-DALL",
            carrier_id="CARRIER-SWIFT",
            lane_id="CHIC_IL-DALL_TX",
            mode=TransportMode.ROAD_FTL,
            equipment_type=EquipmentType.DRY_VAN_53,
            base_rate_usd=1980.0,
            fuel_surcharge_pct=18.0,
            detention_hourly_rate=70.0,
            detention_free_hours=2.0,
            valid_until=valid_year
        ),
        ContractRate(
            rate_id="RATE-GRN-CHIC-DALL-IM",
            carrier_id="CARRIER-GREEN",
            lane_id="CHIC_IL-DALL_TX",
            mode=TransportMode.INTERMODAL,
            equipment_type=EquipmentType.CONTAINER_40HC,
            base_rate_usd=1680.0,
            fuel_surcharge_pct=12.0,
            detention_hourly_rate=60.0,
            detention_free_hours=4.0,
            valid_until=valid_year
        ),
        ContractRate(
            rate_id="RATE-TTN-CHIC-DALL",
            carrier_id="CARRIER-TITAN",
            lane_id="CHIC_IL-DALL_TX",
            mode=TransportMode.ROAD_FTL,
            equipment_type=EquipmentType.DRY_VAN_53,
            base_rate_usd=2400.0,
            fuel_surcharge_pct=18.0,
            detention_hourly_rate=90.0,
            detention_free_hours=2.0,
            valid_until=valid_year
        ),
        # Atlanta to Los Angeles (~2,170 miles)
        ContractRate(
            rate_id="RATE-APX-ATLA-LOSA",
            carrier_id="CARRIER-APEX",
            lane_id="ATLA_GA-LOSA_CA",
            mode=TransportMode.ROAD_FTL,
            equipment_type=EquipmentType.DRY_VAN_53,
            base_rate_usd=4850.0,
            fuel_surcharge_pct=18.5,
            detention_hourly_rate=80.0,
            detention_free_hours=2.0,
            valid_until=valid_year
        ),
        ContractRate(
            rate_id="RATE-TRN-ATLA-LOSA-IM",
            carrier_id="CARRIER-TRANS",
            lane_id="ATLA_GA-LOSA_CA",
            mode=TransportMode.INTERMODAL,
            equipment_type=EquipmentType.CONTAINER_40HC,
            base_rate_usd=3750.0,
            fuel_surcharge_pct=14.0,
            detention_hourly_rate=65.0,
            detention_free_hours=4.0,
            valid_until=valid_year
        )
    ]

    for r in contract_rates:
        save_contract_rate(r)
        print(f" -> Saved Contract: {r.lane_id} | Carrier: {r.carrier_id} | Base: ${r.base_rate_usd:,.2f}")

    total_carriers = len(get_all_carriers())
    print(f"\n[OK] Seeding complete. {total_carriers} carriers active in SQLite database.")

if __name__ == "__main__":
    seed_enterprise_data()
