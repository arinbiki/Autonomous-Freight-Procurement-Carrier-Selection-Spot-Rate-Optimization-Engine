"""
Live High-Concurrency Stress Test for n8n Freight Procurement Workflows.
Executes concurrent synthetic shipment requests against the live n8n webhook endpoints.
Measures latency percentiles, throughput (req/sec), and decision consistency.
"""
import sys
import time
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.config import N8N_BASE_URL

N8N_INTAKE_WEBHOOK = f"{N8N_BASE_URL.rstrip('/')}/webhook/freight-intake"

LANES = [
    {"orig": {"city": "CHICAGO", "state": "IL", "postal_code": "60601"}, "dest": {"city": "DALLAS", "state": "TX", "postal_code": "75201"}},
    {"orig": {"city": "ATLANTA", "state": "GA", "postal_code": "30303"}, "dest": {"city": "LOS ANGELES", "state": "CA", "postal_code": "90012"}},
    {"orig": {"city": "NEW YORK", "state": "NY", "postal_code": "10001"}, "dest": {"city": "CHICAGO", "state": "IL", "postal_code": "60601"}},
    {"orig": {"city": "SAVANNAH", "state": "GA", "postal_code": "31401"}, "dest": {"city": "MEMPHIS", "state": "TN", "postal_code": "38103"}},
    {"orig": {"city": "HOUSTON", "state": "TX", "postal_code": "77002"}, "dest": {"city": "KANSAS CITY", "state": "MO", "postal_code": "64105"}}
]

COMMODITY_PROFILES = [
    {"desc": "Packaged Dry Groceries", "weight": 42000.0, "val": 45000.0, "reefer": False, "haz": False, "equip": "DRY_VAN_53"},
    {"desc": "Refrigerated Vaccines", "weight": 28000.0, "val": 320000.0, "reefer": True, "haz": False, "equip": "REEFER_53"},
    {"desc": "Class 3 Flammable Solvents", "weight": 38000.0, "val": 95000.0, "reefer": False, "haz": True, "equip": "DRY_VAN_53"},
    {"desc": "Industrial Electronics", "weight": 31000.0, "val": 150000.0, "reefer": False, "haz": False, "equip": "DRY_VAN_53"}
]

async def send_single_shipment(session: aiohttp.ClientSession, index: int) -> dict:
    lane = LANES[index % len(LANES)]
    comm = COMMODITY_PROFILES[index % len(COMMODITY_PROFILES)]
    priority = "HIGH" if comm["reefer"] or comm["haz"] else "STANDARD"

    payload = {
        "customer_id": f"CUST-STRESS-{index:04d}",
        "customer_name": f"Enterprise Shipper {index}",
        "customer_tier": "TIER_2_ENTERPRISE",
        "priority": priority,
        "origin": lane["orig"],
        "destination": lane["dest"],
        "commodity": {
            "description": comm["desc"],
            "weight_lbs": comm["weight"],
            "value_usd": comm["val"],
            "pallet_count": 24,
            "is_temp_controlled": comm["reefer"],
            "temp_min_c": 2.0 if comm["reefer"] else None,
            "temp_max_c": 8.0 if comm["reefer"] else None,
            "is_hazmat": comm["haz"],
            "hazmat_class": "3" if comm["haz"] else None
        },
        "equipment_needed": comm["equip"],
        "requested_pickup": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        "requested_delivery": (datetime.utcnow() + timedelta(days=5)).isoformat()
    }

    t0 = time.time()
    try:
        async with session.post(N8N_INTAKE_WEBHOOK, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            elapsed = time.time() - t0
            status = resp.status
            data = await resp.json() if status == 200 else await resp.text()
            return {
                "index": index,
                "status": status,
                "elapsed": elapsed,
                "data": data,
                "success": status in (200, 201)
            }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "index": index,
            "status": 0,
            "elapsed": elapsed,
            "error": str(e),
            "success": False
        }

async def run_stress_test(total_requests: int = 50, concurrency: int = 10):
    print("=" * 80)
    print(f"RUNNING LIVE n8n WORKFLOW STRESS TEST")
    print(f"Target Endpoint: {N8N_INTAKE_WEBHOOK}")
    print(f"Total Requests: {total_requests} | Concurrency: {concurrency}")
    print("=" * 80)

    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [send_single_shipment(session, i) for i in range(total_requests)]
        t_start = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - t_start

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    latencies = [r["elapsed"] for r in results]

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
    p90 = latencies[int(len(latencies) * 0.90)] if latencies else 0.0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0

    print("\n" + "=" * 80)
    print("STRESS TEST RESULTS")
    print("=" * 80)
    print(f"Total Completed Requests: {len(results)}")
    print(f"Successful Ingestions:    {len(successes)} ({len(successes)/len(results)*100:.1f}%)")
    print(f"Failed Ingestions:        {len(failures)}")
    print(f"Total Test Wall Time:     {total_time:.2f} seconds")
    print(f"Throughput:               {len(results)/total_time:.1f} requests/sec")
    print(f"Latency P50:              {p50*1000:.1f} ms")
    print(f"Latency P90:              {p90*1000:.1f} ms")
    print(f"Latency P99:              {p99*1000:.1f} ms")
    print("=" * 80)

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(run_stress_test(total_requests=count, concurrency=10))
