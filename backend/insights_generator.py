import json
from typing import List, Dict
from utils.llm_connector import run_llm
from utils.logger import get_logger

logger = get_logger("InsightsGenerator")

SYSTEM_PROMPT = """
You are an assistant generating financial transaction insights.
Given KPI metrics (as JSON), return a JSON array of insights.
Each insight must have:
- "icon": a FontAwesome icon name (e.g., "chart-line", "triangle-exclamation", "arrow-up")
- "color": a hex color code
- "text": short insight sentence

Return ONLY valid JSON, no extra commentary.
"""

def generate_insights_from_kpis(kpis: Dict) -> List[Dict]:
    prompt = f"""{SYSTEM_PROMPT}

KPI DATA:
{kpis}

Your response:"""
    raw = run_llm(prompt)

    try:
        insights = json.loads(raw)
        if isinstance(insights, list):
            logger.info("Parsed %d insights from LLM", len(insights))
            return insights
        else:
            logger.warning("LLM returned non-list JSON. Falling back.")
    except Exception as e:
        logger.error("Failed to parse LLM JSON: %s", str(e))

    # --- Fallback dummy insights ---
    return [
        {"icon": "chart-line", "color": "#1565c0", "text": "Total transactions are steady."},
        {"icon": "triangle-exclamation", "color": "#e67e22", "text": "Failure rate requires monitoring."},
        {"icon": "arrow-up", "color": "#27ae60", "text": "Customer engagement is increasing."}
    ]