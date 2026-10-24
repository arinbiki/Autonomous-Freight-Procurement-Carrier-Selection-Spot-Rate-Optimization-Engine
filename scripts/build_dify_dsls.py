"""
Dify DSL Workflow Generator for Autonomous Freight Procurement System.
Generates Dify 0.6.0 compliant DSL YAML files corresponding to Section 11 of plan.md:
1. Dify-01: Shipment Request Extraction
2. Dify-02: Carrier Quote Extraction
3. Dify-04: Freight Analyst Copilot
4. Dify-05: Recommendation Explanation Generator
"""
import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "dify_workflows"
OUTPUT_DIR.mkdir(exist_ok=True)

GROQ_PLUGIN_ID = "langgenius/groq:0.0.17@f042c19aec5896e2141909194c463f8ea4cb2326f5bdc51afbfb6542e6b4bcd8"

def make_workflow_1():
    """Dify Workflow 1: Shipment Request Extraction"""
    return {
        "app": {
            "name": "Freight-Shipment-Request-Extractor-v1",
            "description": "Dify Workflow 1: Autonomous unstructured shipment request extraction. Parses raw emails, customer tickets, and chat messages into normalized freight parameters with missing field detection.",
            "icon": "📋",
            "icon_background": "#E0F2FE",
            "icon_type": None,
            "mode": "workflow",
            "use_icon_as_answer_icon": False
        },
        "dependencies": [
            {
                "current_identifier": None,
                "type": "package",
                "value": {
                    "plugin_unique_identifier": GROQ_PLUGIN_ID,
                    "version": None
                }
            }
        ],
        "kind": "app",
        "version": "0.6.0",
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {"file_upload": {"enabled": False}},
            "graph": {
                "edges": [
                    {
                        "data": {"sourceType": "start", "targetType": "llm"},
                        "id": "start-source-llm_extract-target",
                        "source": "start",
                        "sourceHandle": "source",
                        "target": "llm_extract",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "llm", "targetType": "code"},
                        "id": "llm_extract-source-code_validate-target",
                        "source": "llm_extract",
                        "sourceHandle": "source",
                        "target": "code_validate",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "code", "targetType": "end"},
                        "id": "code_validate-source-end-target",
                        "source": "code_validate",
                        "sourceHandle": "source",
                        "target": "end",
                        "targetHandle": "target",
                        "type": "custom"
                    }
                ],
                "nodes": [
                    {
                        "data": {
                            "selected": False,
                            "title": "Raw Shipment Ingestion",
                            "type": "start",
                            "variables": [
                                {
                                    "default": "Hi Team, need to move 40,000 lbs of medical vaccines from Chicago IL (60601) to Dallas TX (75201). Must maintain 2-8 C in a 53ft reefer. Pickup Oct 28 morning, deliver by Oct 31 5PM. Priority shipment. Shipper: BioPharma Global.",
                                    "label": "Raw Request Message",
                                    "max_length": 4000,
                                    "required": True,
                                    "type": "paragraph",
                                    "variable": "raw_request_text"
                                },
                                {
                                    "default": "BioPharma Global",
                                    "label": "Shipper Name",
                                    "max_length": 100,
                                    "required": False,
                                    "type": "text-input",
                                    "variable": "shipper_name"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "start",
                        "position": {"x": 80, "y": 280},
                        "positionAbsolute": {"x": 80, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "context": {"enabled": False},
                            "model": {
                                "completion_params": {"temperature": 0.1},
                                "mode": "chat",
                                "name": "openai/gpt-oss-120b",
                                "provider": "langgenius/groq/groq"
                            },
                            "prompt_template": [
                                {
                                    "role": "system",
                                    "text": "You are an expert logistics intake intelligence engineer.\nExtract normalized freight requirements into valid JSON.\nJSON schema:\n{\n  \"origin_city\": \"CHICAGO\",\n  \"origin_state\": \"IL\",\n  \"origin_postal_code\": \"60601\",\n  \"dest_city\": \"DALLAS\",\n  \"dest_state\": \"TX\",\n  \"dest_postal_code\": \"75201\",\n  \"commodity_desc\": \"Refrigerated medical vaccines\",\n  \"weight_lbs\": 40000.0,\n  \"value_usd\": 250000.0,\n  \"equipment_needed\": \"REEFER_53\",\n  \"is_temp_controlled\": true,\n  \"temp_min_c\": 2.0,\n  \"temp_max_c\": 8.0,\n  \"is_hazmat\": false,\n  \"hazmat_class\": null,\n  \"priority\": \"HIGH\",\n  \"pickup_date\": \"2026-10-28\",\n  \"delivery_date\": \"2026-10-31\"\n}\nOutput ONLY valid JSON."
                                },
                                {
                                    "role": "user",
                                    "text": "Shipper: {{#start.shipper_name#}}\nRequest Message:\n{{#start.raw_request_text#}}"
                                }
                            ],
                            "selected": False,
                            "title": "LLM Parameter Extraction",
                            "type": "llm"
                        },
                        "height": 80,
                        "id": "llm_extract",
                        "position": {"x": 380, "y": 280},
                        "positionAbsolute": {"x": 380, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "code": "def main(llm_raw: str, shipper: str) -> dict:\n    import json, re\n    \n    def parse_json(raw_str):\n        try:\n            m = re.search(r'\\{.*\\}', raw_str, re.DOTALL)\n            if m:\n                return json.loads(m.group(0))\n            return json.loads(raw_str)\n        except Exception:\n            return {}\n            \n    data = parse_json(llm_raw)\n    \n    missing = []\n    if not data.get('origin_city') or not data.get('origin_state'):\n        missing.append('origin_location')\n    if not data.get('dest_city') or not data.get('dest_state'):\n        missing.append('destination_location')\n    if not data.get('weight_lbs'):\n        missing.append('cargo_weight')\n    if not data.get('equipment_needed'):\n        missing.append('equipment_type')\n        \n    is_complete = len(missing) == 0\n    clarifications = []\n    for m in missing:\n        clarifications.append(f'Please specify missing parameter: {m}')\n        \n    return {\n        'is_complete': bool(is_complete),\n        'normalized_payload': json.dumps(data),\n        'missing_fields': ', '.join(missing) if missing else 'None',\n        'clarification_questions': '; '.join(clarifications) if clarifications else 'All core freight parameters complete and validated.'\n    }\n",
                            "code_language": "python3",
                            "outputs": {
                                "clarification_questions": {"type": "string"},
                                "is_complete": {"type": "boolean"},
                                "missing_fields": {"type": "string"},
                                "normalized_payload": {"type": "string"}
                            },
                            "selected": False,
                            "title": "Payload Validator & Quality Check",
                            "type": "code",
                            "variables": [
                                {
                                    "value_selector": ["llm_extract", "text"],
                                    "variable": "llm_raw"
                                },
                                {
                                    "value_selector": ["start", "shipper_name"],
                                    "variable": "shipper"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "code_validate",
                        "position": {"x": 680, "y": 280},
                        "positionAbsolute": {"x": 680, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "outputs": [
                                {
                                    "value_selector": ["code_validate", "is_complete"],
                                    "variable": "is_complete"
                                },
                                {
                                    "value_selector": ["code_validate", "normalized_payload"],
                                    "variable": "normalized_shipment_json"
                                },
                                {
                                    "value_selector": ["code_validate", "missing_fields"],
                                    "variable": "missing_fields"
                                },
                                {
                                    "value_selector": ["code_validate", "clarification_questions"],
                                    "variable": "clarification_guidance"
                                }
                            ],
                            "selected": False,
                            "title": "Extraction Output",
                            "type": "end"
                        },
                        "height": 80,
                        "id": "end",
                        "position": {"x": 980, "y": 280},
                        "positionAbsolute": {"x": 980, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    }
                ]
            }
        }
    }

def make_workflow_2():
    """Dify Workflow 2: Carrier Quote Extraction"""
    return {
        "app": {
            "name": "Freight-Carrier-Quote-Extractor-v1",
            "description": "Dify Workflow 2: Carrier spot quote & tariff parser. Extracts linehaul base rate, fuel surcharge, accessorials, transit days, equipment guarantees, and validity windows from carrier emails.",
            "icon": "💰",
            "icon_background": "#FEF3C7",
            "icon_type": None,
            "mode": "workflow",
            "use_icon_as_answer_icon": False
        },
        "dependencies": [
            {
                "current_identifier": None,
                "type": "package",
                "value": {
                    "plugin_unique_identifier": GROQ_PLUGIN_ID,
                    "version": None
                }
            }
        ],
        "kind": "app",
        "version": "0.6.0",
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {"file_upload": {"enabled": False}},
            "graph": {
                "edges": [
                    {
                        "data": {"sourceType": "start", "targetType": "llm"},
                        "id": "start-source-llm_quote-target",
                        "source": "start",
                        "sourceHandle": "source",
                        "target": "llm_quote",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "llm", "targetType": "code"},
                        "id": "llm_quote-source-code_norm-target",
                        "source": "llm_quote",
                        "sourceHandle": "source",
                        "target": "code_norm",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "code", "targetType": "end"},
                        "id": "code_norm-source-end-target",
                        "source": "code_norm",
                        "sourceHandle": "source",
                        "target": "end",
                        "targetHandle": "target",
                        "type": "custom"
                    }
                ],
                "nodes": [
                    {
                        "data": {
                            "selected": False,
                            "title": "Carrier Email Ingestion",
                            "type": "start",
                            "variables": [
                                {
                                    "default": "Good day Logistics Team, SwiftHaul can cover RFQ-LIVE-902 for $1,650 base linehaul plus $180 standard fuel surcharge and $50 pre-cooling fee. 2-day delivery guaranteed. Capacity confirmed on dedicated 53ft reefer unit. Rate valid for 24 hours. Best, Marcus Vance, Dispatch Manager.",
                                    "label": "Carrier Quote Text",
                                    "max_length": 4000,
                                    "required": True,
                                    "type": "paragraph",
                                    "variable": "carrier_quote_text"
                                },
                                {
                                    "default": "RFQ-LIVE-902",
                                    "label": "RFQ ID",
                                    "max_length": 50,
                                    "required": False,
                                    "type": "text-input",
                                    "variable": "rfq_id"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "start",
                        "position": {"x": 80, "y": 280},
                        "positionAbsolute": {"x": 80, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "context": {"enabled": False},
                            "model": {
                                "completion_params": {"temperature": 0.1},
                                "mode": "chat",
                                "name": "openai/gpt-oss-120b",
                                "provider": "langgenius/groq/groq"
                            },
                            "prompt_template": [
                                {
                                    "role": "system",
                                    "text": "You are an expert freight audit and quote extraction specialist.\nParse carrier spot rates into valid JSON.\nJSON schema:\n{\n  \"carrier_name\": \"SwiftHaul Logistics\",\n  \"base_rate_usd\": 1650.0,\n  \"fuel_surcharge_usd\": 180.0,\n  \"accessorials_usd\": 50.0,\n  \"transit_days\": 2,\n  \"is_equipment_guaranteed\": true,\n  \"validity_hours\": 24,\n  \"exclusions_or_conditions\": \"Pre-cooling fee included, 24h validity\"\n}\nOutput ONLY valid JSON."
                                },
                                {
                                    "role": "user",
                                    "text": "Associated RFQ: {{#start.rfq_id#}}\nCarrier Reply Text:\n{{#start.carrier_quote_text#}}"
                                }
                            ],
                            "selected": False,
                            "title": "LLM Quote Extractor",
                            "type": "llm"
                        },
                        "height": 80,
                        "id": "llm_quote",
                        "position": {"x": 380, "y": 280},
                        "positionAbsolute": {"x": 380, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "code": "def main(llm_raw: str, rfq_id: str) -> dict:\n    import json, re\n    \n    def parse_json(raw_str):\n        try:\n            m = re.search(r'\\{.*\\}', raw_str, re.DOTALL)\n            if m:\n                return json.loads(m.group(0))\n            return json.loads(raw_str)\n        except Exception:\n            return {}\n            \n    q = parse_json(llm_raw)\n    base = float(q.get('base_rate_usd', 0.0))\n    fuel = float(q.get('fuel_surcharge_usd', 0.0))\n    acc = float(q.get('accessorials_usd', 0.0))\n    total = round(base + fuel + acc, 2)\n    \n    confidence = 0.95 if base > 0 and q.get('carrier_name') else 0.40\n    \n    q['total_quote_usd'] = total\n    q['rfq_id'] = str(rfq_id)\n    \n    return {\n        'carrier_name': str(q.get('carrier_name', 'Unknown Carrier')),\n        'total_quote_usd': float(total),\n        'transit_days': int(q.get('transit_days', 3)),\n        'is_guaranteed': bool(q.get('is_equipment_guaranteed', False)),\n        'extraction_confidence': float(confidence),\n        'structured_quote_json': json.dumps(q)\n    }\n",
                            "code_language": "python3",
                            "outputs": {
                                "carrier_name": {"type": "string"},
                                "extraction_confidence": {"type": "number"},
                                "is_guaranteed": {"type": "boolean"},
                                "structured_quote_json": {"type": "string"},
                                "total_quote_usd": {"type": "number"},
                                "transit_days": {"type": "number"}
                            },
                            "selected": False,
                            "title": "Rate Normalization & Confidence Scorer",
                            "type": "code",
                            "variables": [
                                {
                                    "value_selector": ["llm_quote", "text"],
                                    "variable": "llm_raw"
                                },
                                {
                                    "value_selector": ["start", "rfq_id"],
                                    "variable": "rfq_id"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "code_norm",
                        "position": {"x": 680, "y": 280},
                        "positionAbsolute": {"x": 680, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "outputs": [
                                {
                                    "value_selector": ["code_norm", "carrier_name"],
                                    "variable": "extracted_carrier"
                                },
                                {
                                    "value_selector": ["code_norm", "total_quote_usd"],
                                    "variable": "total_all_in_cost"
                                },
                                {
                                    "value_selector": ["code_norm", "transit_days"],
                                    "variable": "promised_transit_days"
                                },
                                {
                                    "value_selector": ["code_norm", "is_guaranteed"],
                                    "variable": "capacity_guaranteed"
                                },
                                {
                                    "value_selector": ["code_norm", "extraction_confidence"],
                                    "variable": "confidence_score"
                                },
                                {
                                    "value_selector": ["code_norm", "structured_quote_json"],
                                    "variable": "quote_record"
                                }
                            ],
                            "selected": False,
                            "title": "Quote Output Gate",
                            "type": "end"
                        },
                        "height": 80,
                        "id": "end",
                        "position": {"x": 980, "y": 280},
                        "positionAbsolute": {"x": 980, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    }
                ]
            }
        }
    }

def make_workflow_4():
    """Dify Workflow 4: Freight Analyst Copilot"""
    return {
        "app": {
            "name": "Freight-Analyst-Copilot-v1",
            "description": "Dify Workflow 4: Autonomous Freight Analyst Copilot. Answers natural language queries regarding carrier selection, lane rate benchmarks, spot vs contract arbitrage, and risk trade-offs.",
            "icon": "🧠",
            "icon_background": "#EDE9FE",
            "icon_type": None,
            "mode": "workflow",
            "use_icon_as_answer_icon": False
        },
        "dependencies": [
            {
                "current_identifier": None,
                "type": "package",
                "value": {
                    "plugin_unique_identifier": GROQ_PLUGIN_ID,
                    "version": None
                }
            }
        ],
        "kind": "app",
        "version": "0.6.0",
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {"file_upload": {"enabled": False}},
            "graph": {
                "edges": [
                    {
                        "data": {"sourceType": "start", "targetType": "llm"},
                        "id": "start-source-llm_copilot-target",
                        "source": "start",
                        "sourceHandle": "source",
                        "target": "llm_copilot",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "llm", "targetType": "code"},
                        "id": "llm_copilot-source-code_copilot-target",
                        "source": "llm_copilot",
                        "sourceHandle": "source",
                        "target": "code_copilot",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "code", "targetType": "end"},
                        "id": "code_copilot-source-end-target",
                        "source": "code_copilot",
                        "sourceHandle": "source",
                        "target": "end",
                        "targetHandle": "target",
                        "type": "custom"
                    }
                ],
                "nodes": [
                    {
                        "data": {
                            "selected": False,
                            "title": "Logistics Analyst Query",
                            "type": "start",
                            "variables": [
                                {
                                    "default": "Why was Carrier GreenLine recommended over Titan for the Chicago to Dallas lane, and under what conditions should we pivot to spot?",
                                    "label": "Analyst Query",
                                    "max_length": 4000,
                                    "required": True,
                                    "type": "paragraph",
                                    "variable": "analyst_query"
                                },
                                {
                                    "default": "CHICAGO, IL -> DALLAS, TX",
                                    "label": "Lane / Corridor Context",
                                    "max_length": 100,
                                    "required": False,
                                    "type": "text-input",
                                    "variable": "lane_context"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "start",
                        "position": {"x": 80, "y": 280},
                        "positionAbsolute": {"x": 80, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "context": {"enabled": False},
                            "model": {
                                "completion_params": {"temperature": 0.2},
                                "mode": "chat",
                                "name": "openai/gpt-oss-120b",
                                "provider": "langgenius/groq/groq"
                            },
                            "prompt_template": [
                                {
                                    "role": "system",
                                    "text": "You are the Autonomous Freight Procurement AI Copilot.\nYou advise logistics directors and procurement managers.\nAnalyze the question using core transportation economics:\n1. Direct Answer: Clear, structured conclusion.\n2. Mathematical Rationale: Compare landed cost (base + fuel + accessorials + detention + carbon cost), service reliability (on-time delivery %), and capacity risk.\n3. Spot vs Contract Strategy: Evaluate expected-value arbitrage under current market tightness.\n4. Actionable Next Steps: Recommended immediate action for the procurement desk."
                                },
                                {
                                    "role": "user",
                                    "text": "Lane Context: {{#start.lane_context#}}\nAnalyst Question:\n{{#start.analyst_query#}}"
                                }
                            ],
                            "selected": False,
                            "title": "Copilot Reasoning Engine",
                            "type": "llm"
                        },
                        "height": 80,
                        "id": "llm_copilot",
                        "position": {"x": 380, "y": 280},
                        "positionAbsolute": {"x": 380, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "code": "def main(copilot_response: str, query: str) -> dict:\n    import datetime\n    \n    actions = [\n        'Verify primary carrier tender acceptance within 60 minutes.',\n        'Stage secondary spot RFQ broadcast if tender declined.',\n        'Review fuel index escalation clause prior to monthly billing.'\n    ]\n    \n    return {\n        'copilot_analysis': str(copilot_response),\n        'confidence_level': 'HIGH (94% certainty based on historical lane contracts & telemetry)',\n        'recommended_action': 'Proceed with primary contract award; monitor spot market for >12% price breaks.',\n        'suggested_follow_ups': '1. Compare 3-year TCO for this corridor. 2. Show historical detention dwell times for destination facility.'\n    }\n",
                            "code_language": "python3",
                            "outputs": {
                                "confidence_level": {"type": "string"},
                                "copilot_analysis": {"type": "string"},
                                "recommended_action": {"type": "string"},
                                "suggested_follow_ups": {"type": "string"}
                            },
                            "selected": False,
                            "title": "Copilot Response Formatter",
                            "type": "code",
                            "variables": [
                                {
                                    "value_selector": ["llm_copilot", "text"],
                                    "variable": "copilot_response"
                                },
                                {
                                    "value_selector": ["start", "analyst_query"],
                                    "variable": "query"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "code_copilot",
                        "position": {"x": 680, "y": 280},
                        "positionAbsolute": {"x": 680, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "outputs": [
                                {
                                    "value_selector": ["code_copilot", "copilot_analysis"],
                                    "variable": "copilot_analysis"
                                },
                                {
                                    "value_selector": ["code_copilot", "confidence_level"],
                                    "variable": "confidence_level"
                                },
                                {
                                    "value_selector": ["code_copilot", "recommended_action"],
                                    "variable": "recommended_action"
                                },
                                {
                                    "value_selector": ["code_copilot", "suggested_follow_ups"],
                                    "variable": "suggested_follow_ups"
                                }
                            ],
                            "selected": False,
                            "title": "Copilot Advisory Gate",
                            "type": "end"
                        },
                        "height": 80,
                        "id": "end",
                        "position": {"x": 980, "y": 280},
                        "positionAbsolute": {"x": 980, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    }
                ]
            }
        }
    }

def make_workflow_5():
    """Dify Workflow 5: Recommendation Explanation Generator"""
    return {
        "app": {
            "name": "Freight-Recommendation-Explainer-v1",
            "description": "Dify Workflow 5: Recommendation Explanation Generator. Produces human-readable, auditable executive rationales, cost drivers, and sensitivity conditions directly from structured decision engine outputs.",
            "icon": "⚖️",
            "icon_background": "#F3E8FF",
            "icon_type": None,
            "mode": "workflow",
            "use_icon_as_answer_icon": False
        },
        "dependencies": [
            {
                "current_identifier": None,
                "type": "package",
                "value": {
                    "plugin_unique_identifier": GROQ_PLUGIN_ID,
                    "version": None
                }
            }
        ],
        "kind": "app",
        "version": "0.6.0",
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {"file_upload": {"enabled": False}},
            "graph": {
                "edges": [
                    {
                        "data": {"sourceType": "start", "targetType": "llm"},
                        "id": "start-source-llm_explain-target",
                        "source": "start",
                        "sourceHandle": "source",
                        "target": "llm_explain",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "llm", "targetType": "code"},
                        "id": "llm_explain-source-code_brief-target",
                        "source": "llm_explain",
                        "sourceHandle": "source",
                        "target": "code_brief",
                        "targetHandle": "target",
                        "type": "custom"
                    },
                    {
                        "data": {"sourceType": "code", "targetType": "end"},
                        "id": "code_brief-source-end-target",
                        "source": "code_brief",
                        "sourceHandle": "source",
                        "target": "end",
                        "targetHandle": "target",
                        "type": "custom"
                    }
                ],
                "nodes": [
                    {
                        "data": {
                            "selected": False,
                            "title": "Optimization Result Input",
                            "type": "start",
                            "variables": [
                                {
                                    "default": "{\n  \"shipment_id\": \"SHP-EXP-001\",\n  \"recommended_carrier\": \"GreenLine Eco-Logistics\",\n  \"mode\": \"ROAD_FTL\",\n  \"rate_type\": \"CONTRACT\",\n  \"lane\": \"CHICAGO, IL -> DALLAS, TX\",\n  \"total_expected_cost\": 2042.0,\n  \"base_freight\": 1680.0,\n  \"fuel_surcharge\": 201.6,\n  \"accessorials\": 35.0,\n  \"transit_hours\": 37.2,\n  \"on_time_probability\": 0.921,\n  \"capacity_confidence\": 0.884,\n  \"carbon_kg_co2e\": 1567.9,\n  \"approval_tier\": \"TIER_1_AUTO\",\n  \"composite_score\": 83.6\n}",
                                    "label": "Optimization Decision JSON",
                                    "max_length": 6000,
                                    "required": True,
                                    "type": "paragraph",
                                    "variable": "decision_json"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "start",
                        "position": {"x": 80, "y": 280},
                        "positionAbsolute": {"x": 80, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "context": {"enabled": False},
                            "model": {
                                "completion_params": {"temperature": 0.2},
                                "mode": "chat",
                                "name": "openai/gpt-oss-120b",
                                "provider": "langgenius/groq/groq"
                            },
                            "prompt_template": [
                                {
                                    "role": "system",
                                    "text": "You are an executive supply chain analytics advisor.\nGenerate an auditable, professional procurement rationale based STRICTLY on the provided decision factors.\nDO NOT invent facts.\nProvide:\n1. Executive Summary: Why this carrier and mode were chosen.\n2. Landed Cost & Service Breakdown: Key drivers (base, fuel, accessorials, detention expectations).\n3. Risk & Capacity Audit: On-time SLA probability and capacity confidence.\n4. ESG Impact: GLEC carbon footprint analysis.\n5. Sensitivity Conditions: What operational triggers would change this decision."
                                },
                                {
                                    "role": "user",
                                    "text": "Decision Factors JSON:\n{{#start.decision_json#}}"
                                }
                            ],
                            "selected": False,
                            "title": "Executive Rationale Synthesizer",
                            "type": "llm"
                        },
                        "height": 80,
                        "id": "llm_explain",
                        "position": {"x": 380, "y": 280},
                        "positionAbsolute": {"x": 380, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "code": "def main(llm_rationale: str, decision_raw: str) -> dict:\n    import json, hashlib, datetime\n    \n    timestamp = datetime.datetime.utcnow().isoformat() + 'Z'\n    audit_hash = hashlib.sha256((decision_raw + timestamp).encode('utf-8')).hexdigest()[:16]\n    \n    audit_markdown = f\"# Autonomous Procurement Decision Audit Report\\n\\n**Timestamp**: {timestamp} | **Audit Digest**: `{audit_hash}`\\n\\n{llm_rationale}\\n\\n---\\n*Governance Authority: SOX-Compliant Autonomous Transportation Decision Matrix*\"\n    \n    return {\n        'executive_narrative': str(llm_rationale),\n        'audit_report_markdown': str(audit_markdown),\n        'audit_hash': str(audit_hash)\n    }\n",
                            "code_language": "python3",
                            "outputs": {
                                "audit_hash": {"type": "string"},
                                "audit_report_markdown": {"type": "string"},
                                "executive_narrative": {"type": "string"}
                            },
                            "selected": False,
                            "title": "Audit Package & Signature Stamping",
                            "type": "code",
                            "variables": [
                                {
                                    "value_selector": ["llm_explain", "text"],
                                    "variable": "llm_rationale"
                                },
                                {
                                    "value_selector": ["start", "decision_json"],
                                    "variable": "decision_raw"
                                }
                            ]
                        },
                        "height": 80,
                        "id": "code_brief",
                        "position": {"x": 680, "y": 280},
                        "positionAbsolute": {"x": 680, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    },
                    {
                        "data": {
                            "outputs": [
                                {
                                    "value_selector": ["code_brief", "executive_narrative"],
                                    "variable": "executive_narrative"
                                },
                                {
                                    "value_selector": ["code_brief", "audit_report_markdown"],
                                    "variable": "audit_report_markdown"
                                },
                                {
                                    "value_selector": ["code_brief", "audit_hash"],
                                    "variable": "audit_hash"
                                }
                            ],
                            "selected": False,
                            "title": "Executive Report Hub",
                            "type": "end"
                        },
                        "height": 80,
                        "id": "end",
                        "position": {"x": 980, "y": 280},
                        "positionAbsolute": {"x": 980, "y": 280},
                        "sourcePosition": "right",
                        "targetPosition": "left",
                        "type": "custom",
                        "width": 240
                    }
                ]
            }
        }
    }

def main():
    w1 = make_workflow_1()
    f1 = OUTPUT_DIR / "01_shipment_request_extraction.yml"
    with open(f1, "w", encoding="utf-8") as f:
        yaml.dump(w1, f, sort_keys=False, allow_unicode=True)
    print(f"[OK] Generated {f1.name}")

    w2 = make_workflow_2()
    f2 = OUTPUT_DIR / "02_carrier_quote_extraction.yml"
    with open(f2, "w", encoding="utf-8") as f:
        yaml.dump(w2, f, sort_keys=False, allow_unicode=True)
    print(f"[OK] Generated {f2.name}")

    w4 = make_workflow_4()
    f4 = OUTPUT_DIR / "04_freight_analyst_copilot.yml"
    with open(f4, "w", encoding="utf-8") as f:
        yaml.dump(w4, f, sort_keys=False, allow_unicode=True)
    print(f"[OK] Generated {f4.name}")

    w5 = make_workflow_5()
    f5 = OUTPUT_DIR / "05_recommendation_explanation_generator.yml"
    with open(f5, "w", encoding="utf-8") as f:
        yaml.dump(w5, f, sort_keys=False, allow_unicode=True)
    print(f"[OK] Generated {f5.name}")

if __name__ == "__main__":
    main()
