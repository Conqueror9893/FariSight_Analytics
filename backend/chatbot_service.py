from fastapi import HTTPException
from sqlalchemy.orm import Session
from utils.llm_connector import run_llm
from utils.logger import get_logger
from . import crud, models
from .report_service import generate_bank_charges_report, generate_failure_timeline_report
import json
import os

logger = get_logger("ChatbotService")

BACKEND_BASE_URL = "http://localhost:8081"
def get_chatbot_response(query: str, db: Session) -> dict:
    """
    Generate chatbot response using the LLM connector and latest KPI data.
    Always returns a dict with keys:
      - query: str
      - answer: str
      - report_file: str | None
      - raw: dict | None
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        logger.info(f"Chatbot query received: {query}")

        # --- report generation ---
        if "report" in query.lower() and "bank charges" in query.lower():
            filepath = generate_bank_charges_report()
            return {
                "query": query,
                "answer": "Report generated successfully. Use the button below to download.",
                "report_file": filepath,
                "raw": None,
            }

        if "failed" in query.lower() and "transactions" in query.lower():
            filepath = generate_failure_timeline_report()
            return {
                "query": query,
                "answer": "Failure timeline report generated successfully. Use the button below to download.",
                "report_file": filepath,
                "raw": None,
            }

        # --- fetch latest KPIs from DB ---
        latest_kpis = crud.compute_kpis(db)
        kpi_context = json.dumps(latest_kpis, indent=2, default=str)

        # --- build prompt with KPI context ---
        prompt = f"""
        You are an AI assistant analyzing financial KPIs.
        Use the following KPI data when answering questions:

        {kpi_context}

        Question: {query}

        Answer in concise professional format, return JSON like:
        {{
            "answer": "<your response here>"
        }}
        """

        # --- call LLM utility (expects JSON string) ---
        raw_response = run_llm(prompt=prompt)

        # --- ensure parsed JSON safely ---
        response = {"answer": ""}
        if isinstance(raw_response, dict):
            response = raw_response
        elif isinstance(raw_response, str):
            try:
                response = json.loads(raw_response)
            except json.JSONDecodeError:
                logger.warning("LLM returned non-JSON, wrapping in JSON object")
                response = {"answer": raw_response}

        return {
            "query": query,
            "answer": str(response.get("answer", "")),
            "report_file": None,  # always present, even if not a report
            "raw": response,
        }

    except Exception as e:
        logger.exception("Error while generating chatbot response")
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")
