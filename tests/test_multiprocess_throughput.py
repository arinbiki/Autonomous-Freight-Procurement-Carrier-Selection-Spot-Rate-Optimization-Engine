import sys
import io
import os
import time
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.models import (
    Shipment, Location, Commodity, EquipmentType, ShipmentPriority, CustomerTier,
    Carrier, ContractRate, SpotQuote, TransportMode
)
from core.optimization import run_procurement_optimization
from core.database import get_all_carriers

HUBS = [
    ("CHICAGO", "IL", "60601", 41.8781, -87.6298),
    ("DALLAS", "TX", "75201", 32.7767, -96.7970),
    ("ATLANTA", "GA", "30303", 33.7490, -84.3880),
    ("LOS ANGELES", "CA", "90012", 34.0522, -118.2437),
    ("NEW YORK", "NY", "10001", 40.7128, -74.0060),
    ("SAVANNAH", "GA", "31401", 32.0809, -81.0912),
    ("MEMPHIS", "TN", "38103", 35.1495, -90.0490),
    ("HOUSTON", "TX", "77002", 29.7604, -95.3698),
    ("KANSAS CITY", "MO", "64105", 39.0997, -94.5786),
    ("SEATTLE", "WA", "98101", 47.6062, -122.3321),
    ("LAREDO", "TX", "78040", 27.5036, -99.5076),
    ("DETROIT", "MI", "48226", 42.3314, -83.0458),
]

COMMODITIES = [
    {"desc": "Packaged Dry Groceries", "reefer": False, "haz": False, "weight": 42000.0, "val": 45000.0, "equip": EquipmentType.DRY_VAN_53},
    {"desc": "Pharmaceutical Biologics & Vaccines", "reefer": True, "haz": False, "t_min": 2.0, "t_max": 8.0, "weight": 28000.0, "val": 450000.0, "equip": EquipmentType.REEFER_53},
    {"desc": "Class 3 Flammable Solvents", "reefer": False, "haz": True, "haz_cls": "3", "weight": 38000.0, "val": 95000.0, "equip": EquipmentType.DRY_VAN_53},
    {"desc": "Industrial Electronics", "reefer": False, "haz": False, "weight": 31000.0, "val": 180000.0, "equip": EquipmentType.DRY_VAN_53},
    {"desc": "Fresh Premium Produce", "reefer": True, "haz": False, "t_min": 1.0, "t_max": 4.0, "weight": 39000.0, "val": 55000.0, "equip": EquipmentType.REEFER_53},
]

def build_static_objects():
    locs = {
        h[0]: Location(
            location_id=f"LOC-{h[0][:3]}",
            name=f"{h[0]} Hub",
            city=h[0],
            state=h[1],
            postal_code=h[2],
            latitude=h[3],
            longitude=h[4]
        ) for h in HUBS
    }
    
    comms = []
    for c in COMMODITIES:
        comms.append((
            Commodity(
                description=c["desc"],
                weight_lbs=c["weight"],
                value_usd=c["val"],
                is_temp_controlled=c["reefer"],
                temp_min_c=c.get("t_min"),
                temp_max_c=c.get("t_max"),
                is_hazmat=c["haz"],
                hazmat_class=c.get("haz_cls")
            ),
            c["equip"],
            ShipmentPriority.HIGH if (c["reefer"] or c["haz"]) else ShipmentPriority.STANDARD
        ))
        
    return locs, comms

def worker_batch(start_idx: int, count: int, seed: int):
    random.seed(seed)
    carriers = get_all_carriers()
    now = datetime.now(timezone.utc)
    p_time = now + timedelta(days=2)
    d_time = now + timedelta(days=7)
    
    loc_map, comm_list = build_static_objects()
    hub_keys = list(loc_map.keys())
    
    # Contract cache by lane and equipment
    contract_cache = {}
    for o_k in hub_keys:
        for d_k in hub_keys:
            if o_k == d_k:
                continue
            lane = f"{o_k[:4]}_{loc_map[o_k].state}-{d_k[:4]}_{loc_map[d_k].state}"
            for eq in [EquipmentType.DRY_VAN_53, EquipmentType.REEFER_53]:
                contract_cache[(lane, eq)] = [
                    ContractRate(
                        rate_id=f"CTR-APX-{lane}",
                        carrier_id="CARRIER-APEX",
                        lane_id=lane,
                        mode=TransportMode.ROAD_FTL,
                        equipment_type=eq,
                        base_rate_usd=2100.0,
                        fuel_surcharge_pct=18.0,
                        valid_until=now + timedelta(days=90)
                    ),
                    ContractRate(
                        rate_id=f"CTR-GRN-{lane}",
                        carrier_id="CARRIER-GREEN",
                        lane_id=lane,
                        mode=TransportMode.ROAD_FTL,
                        equipment_type=eq,
                        base_rate_usd=1950.0,
                        fuel_surcharge_pct=18.0,
                        valid_until=now + timedelta(days=90)
                    )
                ]
    
    total_cost = 0.0
    arbitrage_savings = 0.0
    tier_counts = {"TIER_1_AUTO": 0, "TIER_2_SUPERVISOR": 0, "TIER_3_PROCUREMENT_MANAGER": 0, "TIER_4_VP_SUPPLY_CHAIN": 0}
    spot_awarded_count = 0
    total_co2_kg = 0.0
    
    t0 = time.time()
    for i in range(count):
        o_city = random.choice(hub_keys)
        d_city = random.choice(hub_keys)
        while d_city == o_city:
            d_city = random.choice(hub_keys)
            
        comm_obj, equip, prio = random.choice(comm_list)
        orig_loc = loc_map[o_city]
        dest_loc = loc_map[d_city]
        lane = f"{o_city[:4]}_{orig_loc.state}-{d_city[:4]}_{dest_loc.state}"
        
        shp = Shipment(
            shipment_id=f"SHP-10M-{start_idx + i:08d}",
            created_at=now,
            customer_id="CUST-GLOBAL-10M",
            customer_name="Global Strategic Shipper",
            customer_tier=CustomerTier.TIER_1_STRATEGIC,
            priority=prio,
            origin=orig_loc,
            destination=dest_loc,
            commodity=comm_obj,
            equipment_needed=equip,
            requested_pickup=p_time,
            requested_delivery=d_time
        )
        
        contracts = contract_cache.get((lane, equip), [])
        
        spot_quotes = []
        if random.random() < 0.40:
            spot_carrier = random.choice(["CARRIER-SWIFT", "CARRIER-APEX", "CARRIER-GREEN"])
            base_spot = random.uniform(1350.0, 2200.0)
            spot_quotes.append(SpotQuote(
                quote_id=f"Q-SPOT-{i}",
                rfq_id=f"RFQ-{i}",
                carrier_id=spot_carrier,
                carrier_name="SwiftHaul Transportation" if spot_carrier == "CARRIER-SWIFT" else ("Apex Freight" if spot_carrier == "CARRIER-APEX" else "GreenLine Logistics"),
                base_rate_usd=base_spot,
                fuel_surcharge_usd=180.0,
                accessorials_usd=25.0,
                total_quote_usd=base_spot + 205.0,
                transit_days_promised=random.randint(2, 4),
                valid_hours=24,
                is_equipment_guaranteed=True
            ))
            
        rec = run_procurement_optimization(
            shipment=shp,
            available_carriers=carriers,
            active_spot_quotes=spot_quotes,
            contract_rates=contracts,
            persist=False
        )
        cost = rec.cost_breakdown.total_expected_cost
        total_cost += cost
        total_co2_kg += rec.carbon_kg_co2e
        tier_val = rec.approval_tier.value if hasattr(rec.approval_tier, 'value') else str(rec.approval_tier)
        tier_counts[tier_val] = tier_counts.get(tier_val, 0) + 1
        
        rate_type_val = rec.rate_type.value if hasattr(rec.rate_type, 'value') else str(rec.rate_type)
        if rate_type_val == "SPOT":
            spot_awarded_count += 1
            arbitrage_savings += max(0.0, 1950.0 - cost)
            
    elapsed = time.time() - t0
    return {
        "count": count,
        "elapsed": elapsed,
        "total_cost": total_cost,
        "arbitrage_savings": arbitrage_savings,
        "tier_counts": tier_counts,
        "spot_awarded": spot_awarded_count,
        "total_co2_kg": total_co2_kg
    }

if __name__ == "__main__":
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    chunk = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
    num_workers = os.cpu_count() or 4
    
    print(f"Testing Optimized Zero-IPC Multiprocessing: {total:,} shipments across {num_workers} worker processes...")
    t_start = time.time()
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for start_idx in range(0, total, chunk):
            c = min(chunk, total - start_idx)
            seed = random.randint(1000, 999999)
            futures.append(executor.submit(worker_batch, start_idx, c, seed))
            
        done_count = 0
        tot_cost = 0.0
        tot_savings = 0.0
        tot_co2 = 0.0
        tot_spot = 0
        tot_tiers = {"TIER_1_AUTO": 0, "TIER_2_SUPERVISOR": 0, "TIER_3_PROCUREMENT_MANAGER": 0, "TIER_4_VP_SUPPLY_CHAIN": 0}
        
        for f in futures:
            res = f.result()
            done_count += res["count"]
            tot_cost += res["total_cost"]
            tot_savings += res["arbitrage_savings"]
            tot_co2 += res["total_co2_kg"]
            tot_spot += res["spot_awarded"]
            for k, v in res["tier_counts"].items():
                tot_tiers[k] += v
            elapsed = time.time() - t_start
            print(f" -> Completed {done_count:,}/{total:,} ({done_count/total*100:.1f}%) | Throughput: {done_count/elapsed:,.0f} shipments/sec")
            
    total_time = time.time() - t_start
    print("\n" + "=" * 80)
    print("OPTIMIZED MULTIPROCESS RESULTS:")
    print(f"Shipments:       {done_count:,}")
    print(f"Wall Time:       {total_time:.2f} s")
    print(f"Throughput:      {done_count/total_time:,.0f} shipments/second")
    print(f"Spend:           ${tot_cost:,.2f}")
    print(f"Spot Arbitrage:  ${tot_savings:,.2f} ({tot_spot:,} spot awards, {tot_spot/done_count*100:.1f}%)")
    print(f"Carbon:          {tot_co2/1000:,.1f} tons CO2e")
    print("Tiers:", tot_tiers)
    print("=" * 80)
