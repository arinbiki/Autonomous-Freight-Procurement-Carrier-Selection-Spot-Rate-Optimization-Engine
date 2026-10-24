"""
Import Dify Workflows via Tencent BrowserSkill session.
Uses the authenticated browser session in Chrome to invoke the Dify Console API
/console/api/apps/imports with CSRF validation.
"""
import sys
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BSK_CLI = r"C:\Users\Arindam RoY\.local\bin\bsk.exe"

def run_bsk_eval(session_id: str, js_code: str) -> dict:
    cmd = [BSK_CLI, "evaluate", "--session", session_id, js_code]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"[ERROR] bsk evaluate failed: {res.stderr}")
        return {"error": res.stderr}
    try:
        return json.loads(res.stdout.strip())
    except Exception:
        return {"raw": res.stdout.strip()}

def import_workflow(session_id: str, yml_path: Path):
    print("=" * 80)
    print(f"IMPORTING WORKFLOW: {yml_path.name}")
    print("=" * 80)
    
    with open(yml_path, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    payload_json = json.dumps({
        "mode": "yaml-content",
        "yaml_content": yaml_content
    })

    # Prepare JS to execute in the browser window
    js_code = f"""
    (async () => {{
        try {{
            const csrf = document.cookie.split('; ').find(row => row.startsWith('csrf_token='))?.split('=')[1];
            const body = {payload_json};
            const res = await fetch('/console/api/apps/imports', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrf
                }},
                body: JSON.stringify(body)
            }});
            const data = await res.json();
            
            // If pending confirmation, confirm it
            if (data.status === 'pending' && data.id) {{
                const confRes = await fetch(`/console/api/apps/imports/${{data.id}}/confirm`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrf
                    }}
                }});
                const confData = await confRes.json();
                window._importStatus = {{ phase: 'confirmed', res: confData }};
                return window._importStatus;
            }}
            window._importStatus = {{ phase: 'initial', res: data }};
            return window._importStatus;
        }} catch(e) {{
            window._importStatus = {{ error: e.message }};
            return window._importStatus;
        }}
    }})()
    """

    res = run_bsk_eval(session_id, js_code)
    print(f"Triggered import: {res}")
    
    # Read status back
    status = run_bsk_eval(session_id, "window._importStatus")
    print(f"Import Result: {json.dumps(status, indent=2)}")
    return status

def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else "ooto"
    workflow_files = [
        BASE_DIR / "dify_workflows" / "01_shipment_request_extraction.yml",
        BASE_DIR / "dify_workflows" / "02_carrier_quote_extraction.yml",
        BASE_DIR / "dify_workflows" / "04_freight_analyst_copilot.yml",
        BASE_DIR / "dify_workflows" / "05_recommendation_explanation_generator.yml"
    ]

    for wf in workflow_files:
        if wf.exists():
            import_workflow(session_id, wf)

if __name__ == "__main__":
    main()
