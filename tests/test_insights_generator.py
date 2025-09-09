import pytest
import json
from backend.insights_generator import generate_insights_from_kpis
from utils import llm_connector

DUMMY_KPIS = {
    "total_transactions": 120,
    "total_amount_usd": "25000",
    "total_amount_rm": "110000",
    "dr_count": 70,
    "cr_count": 50,
    "txn_per_customer": 3.5,
    "failure_rate": 0.12,
    "total_bank_charges": "350",
    "txn_type_split": {
        "TRANSFER": {"count": 40},
        "DEPOSIT": {"count": 30},
        "LOAN_PAYMENT": {"count": 20},
        "BILL_PAYMENT": {"count": 30},
    },
}


# ---------- MOCKED TEST ----------
def test_generate_insights_with_mock(monkeypatch):
    """Simulate LLM returning valid JSON, no subprocess call needed."""

    def fake_run_llm(prompt: str, timeout: int = 60):
        return json.dumps([
            {"icon": "chart-line", "color": "#1565c0", "text": "Mock: Volume rising fast"},
            {"icon": "triangle-exclamation", "color": "#e67e22", "text": "Mock: Failures trending up"}
        ])

    monkeypatch.setattr(llm_connector, "run_llm", fake_run_llm)

    insights = generate_insights_from_kpis(DUMMY_KPIS)

    assert isinstance(insights, list)
    assert len(insights) == 2
    assert insights[0]["icon"] == "chart-line"


# ---------- REAL LLM TEST ----------
@pytest.mark.integration
def test_generate_insights_with_real_llm():
    """This test calls ollama run openchat:latest for real. May be slower."""

    insights = generate_insights_from_kpis(DUMMY_KPIS)

    assert isinstance(insights, list)
    assert len(insights) > 0
    for ins in insights:
        assert "icon" in ins
        assert "text" in ins
