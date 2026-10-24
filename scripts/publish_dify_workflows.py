"""
Publish imported Dify workflows so they are production-ready.
Calls /console/api/apps/<app_id>/workflows/publish for each created freight app.
"""
import sys
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BSK_CLI = r"C:\Users\Arindam RoY\.local\bin\bsk.exe"

APP_IDS = {
    "Freight-Shipment-Request-Extractor-v1": "fca6be40-d451-4449-8470-7206dc57d1ab",
    "Freight-Carrier-Quote-Extractor-v1": "f591ec1b-5fe2-490f-861b-1cfbcf3f7d9d",
    "Freight-Analyst-Copilot-v1": "9a6bcacb-b7f9-4cf8-a16a-e4ef6b889e9e",
    "Freight-Recommendation-Explainer-v1": "db4de0b0-fc60-4d41-820f-f5a3d9f623d4"
}

def publish_app(session_id: str, app_name: str, app_id: str):
    print(f"Publishing {app_name} ({app_id})...")
    js_code = f"""
    (async () => {{
        try {{
            const csrf = document.cookie.split('; ').find(row => row.startsWith('csrf_token='))?.split('=')[1];
            const res = await fetch('/console/api/apps/{app_id}/workflows/publish', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrf
                }},
                body: JSON.stringify({{}})
            }});
            const data = await res.json();
            window._pubStatus = {{ status: res.status, data: data }};
            return window._pubStatus;
        }} catch(e) {{
            window._pubStatus = {{ error: e.message }};
            return window._pubStatus;
        }}
    }})()
    """
    cmd = [BSK_CLI, "evaluate", "--session", session_id, js_code]
    subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    
    cmd_res = [BSK_CLI, "evaluate", "--session", session_id, "window._pubStatus"]
    out = subprocess.run(cmd_res, capture_output=True, text=True, cwd=str(BASE_DIR))
    print(f" -> Result: {out.stdout.strip()}")

def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else "ooto"
    for name, aid in APP_IDS.items():
        publish_app(session_id, name, aid)

if __name__ == "__main__":
    main()
