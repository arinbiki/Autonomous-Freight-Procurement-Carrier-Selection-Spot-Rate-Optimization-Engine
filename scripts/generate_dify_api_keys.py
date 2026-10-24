"""
Generate and retrieve API keys for Dify Freight workflows via bsk session.
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

def get_or_create_key(session_id: str, app_name: str, app_id: str) -> str:
    js_code = f"""
    (async () => {{
        try {{
            const csrf = document.cookie.split('; ').find(row => row.startsWith('csrf_token='))?.split('=')[1];
            // Check existing keys
            const listRes = await fetch('/console/api/apps/{app_id}/api-keys', {{
                headers: {{ 'X-CSRF-Token': csrf }}
            }});
            const listData = await listRes.json();
            if (listData.data && listData.data.length > 0) {{
                window._keyResult = {{ app: '{app_name}', token: listData.data[0].token }};
                return window._keyResult;
            }}
            // Create key
            const createRes = await fetch('/console/api/apps/{app_id}/api-keys', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrf
                }},
                body: JSON.stringify({{}})
            }});
            const createData = await createRes.json();
            window._keyResult = {{ app: '{app_name}', token: createData.token }};
            return window._keyResult;
        }} catch(e) {{
            window._keyResult = {{ error: e.message }};
            return window._keyResult;
        }}
    }})()
    """
    subprocess.run([BSK_CLI, "evaluate", "--session", session_id, js_code], capture_output=True, text=True, cwd=str(BASE_DIR))
    res = subprocess.run([BSK_CLI, "evaluate", "--session", session_id, "window._keyResult"], capture_output=True, text=True, cwd=str(BASE_DIR))
    try:
        data = json.loads(res.stdout.strip())
        return data.get("token", "")
    except Exception:
        return ""

def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else "ooto"
    print("=" * 80)
    print("GENERATING & RETRIEVING API KEYS FOR DIFY FREIGHT WORKFLOWS")
    print("=" * 80)
    keys = {}
    for name, aid in APP_IDS.items():
        k = get_or_create_key(session_id, name, aid)
        keys[name] = {"app_id": aid, "token": k}
        print(f" -> {name}: token = {k}")

    out_file = BASE_DIR / "dify_workflows" / "dify_app_keys.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2)
    print(f"\nSaved keys metadata to {out_file.name}")

if __name__ == "__main__":
    main()
