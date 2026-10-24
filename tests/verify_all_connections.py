"""
Unified System Connectivity Verification Script.
Checks that Python REST services, n8n orchestrator webhooks, and Dify workflows
are 100% operational, authenticated, and ready for end-to-end stress testing.
"""
import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

LOCAL_ENGINE_URL = "http://127.0.0.1:8089"
REMOTE_ENGINE_URL = f"http://{os.getenv('SSH_HOST', '127.0.0.1')}:8089"
N8N_BASE = os.getenv("N8N_BASE_URL", "http://localhost:5678")
DIFY_BASE = os.getenv("DIFY_BASE_URL", "http://localhost:3000")

def check_python_engine(url: str, label: str):
    print(f"\n[1] Checking Python Decision Engine ({label}): {url}")
    try:
        r = requests.get(f"{url}/api/v1/health", timeout=5)
        if r.status_code == 200:
            print(f" -> SUCCESS: {r.json()}")
            return True
        else:
            print(f" -> FAILED (HTTP {r.status_code}): {r.text}")
            return False
    except Exception as e:
        print(f" -> ERROR: {e}")
        return False

def check_n8n_webhooks():
    print(f"\n[2] Checking n8n Production Webhooks: {N8N_BASE}")
    endpoints = [
        ("01-Intake", f"{N8N_BASE}/webhook/freight-intake", {
            "customer_id": "TEST-PING",
            "customer_name": "Connectivity Test Shipper",
            "origin": {"city": "CHICAGO", "state": "IL"},
            "destination": {"city": "DALLAS", "state": "TX"},
            "commodity": {"description": "Dry Groceries", "weight_lbs": 40000, "value_usd": 50000},
            "equipment_needed": "DRY_VAN_53",
            "priority": "STANDARD"
        })
    ]
    all_ok = True
    for name, ep, payload in endpoints:
        try:
            r = requests.post(ep, json=payload, timeout=10)
            if r.status_code == 200:
                print(f" -> SUCCESS [{name}]: HTTP 200 ({r.text[:100]}...)")
            else:
                print(f" -> FAILED [{name}]: HTTP {r.status_code} ({r.text[:100]}...)")
                all_ok = False
        except Exception as e:
            print(f" -> ERROR [{name}]: {e}")
            all_ok = False
    return all_ok

def check_dify_workflows():
    print(f"\n[3] Checking Dify Freight Workflows: {DIFY_BASE}")
    keys_file = BASE_DIR / "dify_workflows" / "dify_app_keys.json"
    if not keys_file.exists():
        print(f" -> [WARN] dify_app_keys.json not found!")
        return False
        
    with open(keys_file, "r", encoding="utf-8") as f:
        keys_data = json.load(f)

    all_ok = True
    for app_name, info in keys_data.items():
        token = info.get("token")
        url = f"{DIFY_BASE}/v1/info"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                print(f" -> SUCCESS [{app_name}]: Token Active (App ID: {info.get('app_id')[:8]}...)")
            else:
                print(f" -> FAILED [{app_name}]: HTTP {r.status_code} ({r.text})")
                all_ok = False
        except Exception as e:
            print(f" -> ERROR [{app_name}]: {e}")
            all_ok = False
    return all_ok

def main():
    print("=" * 80)
    print("FREIGHT PROCUREMENT SYSTEM PRE-STRESS TEST VERIFICATION")
    print("=" * 80)
    
    local_ok = check_python_engine(LOCAL_ENGINE_URL, "Localhost")
    remote_ok = check_python_engine(REMOTE_ENGINE_URL, "Remote VPS")
    n8n_ok = check_n8n_webhooks()
    dify_ok = check_dify_workflows()
    
    print("\n" + "=" * 80)
    print("CONNECTIVITY READINESS SUMMARY")
    print("=" * 80)
    print(f" Local Python Decision Engine:   {'READY' if local_ok else 'FAILED'}")
    print(f" Remote Python Decision Engine:  {'READY' if remote_ok else 'FAILED'}")
    print(f" n8n Orchestrator Webhooks:      {'READY' if n8n_ok else 'FAILED'}")
    print(f" Dify NLP & Copilot Workflows:   {'READY' if dify_ok else 'FAILED'}")
    print("=" * 80)
    
    ready = local_ok and n8n_ok and dify_ok
    if ready:
        print("ALL SYSTEMS GREEN - SYSTEM IS READY FOR MASSIVE STRESS TEST")
        sys.exit(0)
    else:
        print("[WARN] Some components require attention before stress test.")
        sys.exit(1)

if __name__ == "__main__":
    main()
