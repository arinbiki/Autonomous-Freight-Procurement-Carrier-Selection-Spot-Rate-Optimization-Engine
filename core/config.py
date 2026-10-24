"""
Configuration settings for Autonomous Freight Procurement, Carrier Selection & Spot Rate Optimization Engine.
Loads dynamically from .env with zero hardcoded credentials.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Database configuration (SQLite for self-contained execution, fully relational schema)
DB_PATH = os.environ.get("PROCUREMENT_DB", str(BASE_DIR / "freight_procurement.db"))

# Ollama NLP Service configuration (Local Qwen 3B / 2.5 models)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

# Dify LLM & Workflow Automation configuration
DIFY_BASE_URL = os.environ.get("DIFY_BASE_URL", "http://localhost:3000")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")
DIFY_EXTRACTOR_KEY = os.environ.get("DIFY_EXTRACTOR_KEY", "")
DIFY_QUOTE_KEY = os.environ.get("DIFY_QUOTE_KEY", "")
DIFY_COPILOT_KEY = os.environ.get("DIFY_COPILOT_KEY", "")
DIFY_EXPLAINER_KEY = os.environ.get("DIFY_EXPLAINER_KEY", "")

# Groq Cloud API configuration (optional high-speed fallback)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.6-27b")

# n8n Service configuration
N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
N8N_PUBLIC_API_KEY = os.environ.get("N8N_PUBLIC_API_KEY", "")
N8N_MCP_TOKEN = os.environ.get("N8N_MCP_TOKEN", "")
N8N_MCP_URL = f"{N8N_BASE_URL}/mcp-server/http"

# Decision Engine Service Port
DECISION_ENGINE_PORT = int(os.environ.get("DECISION_ENGINE_PORT", 8089))
DECISION_ENGINE_HOST = os.environ.get("DECISION_ENGINE_HOST", "0.0.0.0")

# Financial Approval Matrix Thresholds (USD)
APPROVAL_TIERS = {
    "TIER_1_AUTO": {"max_cost": 2500.0, "approver": "SYSTEM_AUTOMATIC", "spot_variance_limit": 0.05},
    "TIER_2_SUPERVISOR": {"max_cost": 5000.0, "approver": "LOGISTICS_SUPERVISOR", "spot_variance_limit": 0.10},
    "TIER_3_PROCUREMENT_MANAGER": {"max_cost": 25000.0, "approver": "PROCUREMENT_MANAGER", "spot_variance_limit": 0.20},
    "TIER_4_VP_SUPPLY_CHAIN": {"max_cost": float("inf"), "approver": "VP_SUPPLY_CHAIN_OR_CFO", "spot_variance_limit": 1.0}
}

# Mode Carbon Emission Factors (g CO2e per ton-km, based on GLEC Framework)
EMISSION_FACTORS = {
    "ROAD_FTL": 62.0,
    "ROAD_LTL": 105.0,
    "RAIL": 22.0,
    "INTERMODAL": 35.0,
    "OCEAN": 15.0,
    "AIR": 500.0,
    "COURIER": 120.0,
    "DEDICATED_FLEET": 58.0
}

# Default Carbon Price ($ / metric ton CO2)
CARBON_PRICE_PER_TON = float(os.environ.get("CARBON_PRICE_PER_TON", 50.0))

# Speed Averages by Mode (miles per hour including driver rest/handling)
MODE_AVERAGE_SPEED_MPH = {
    "ROAD_FTL": 48.0,
    "ROAD_LTL": 35.0,
    "RAIL": 20.0,
    "INTERMODAL": 25.0,
    "OCEAN": 18.0,
    "AIR": 400.0,
    "COURIER": 45.0,
    "DEDICATED_FLEET": 50.0
}
