from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
import os
from .database import engine, get_db, SessionLocal
from . import models, crud
from .kpi_worker import start as start_kpi_worker
from .insights_generator import generate_insights_from_kpis
from .chatbot_service import get_chatbot_response
from utils.logger import get_logger

logger = get_logger("BackendFlaskApp")
# create tables if they don't exist (accounts/transactions from story1 exist; this ensures kpis as well)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="FariSight Analytics Backend", version="1.0")

# Make sure reports directory exists
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Serve reports at /reports
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start KPI worker when app starts. In uvicorn reload mode this may run twice; for demo it's okay.
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        if not db.query(models.KPI).first():
            crud.compute_kpis(db)
    finally:
        db.close()
    start_kpi_worker()


# Dependency
def get_db_dep():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Transactions endpoint
@app.get("/transactions")
def get_transactions(
    limit: int = Query(50, gt=0, le=1000),
    page: int = Query(1, gt=0),
    type: str = Query(None, description="Filter by TRN_TYPE"),
    status: str = Query(None, description="Filter by STATUS (SUCCESS or FAILED)"),
    since: str = Query(
        None,
        description="Filter by time window: 'past_hour' or 'past_24h'",
    ),
    db: Session = Depends(get_db_dep),
):
    offset = (page - 1) * limit
    q = db.query(models.Transaction)

    # --- Apply filters ---
    if type:
        q = q.filter(models.Transaction.TRN_TYPE == type.upper())
    if status:
        q = q.filter(models.Transaction.STATUS == status.upper())
    if since:
        now = datetime.now(timezone.utc)
        if since == "past_hour":
            q = q.filter(models.Transaction.TRN_DATE >= now - timedelta(hours=1))
        elif since == "past_24h":
            q = q.filter(models.Transaction.TRN_DATE >= now - timedelta(hours=24))

    # --- Pagination ---
    q = q.order_by(models.Transaction.id.desc()).offset(offset).limit(limit).all()

    result = []
    for t in q:
        result.append({
            "TRN_REF_NO": t.TRN_REF_NO,
            "ACCOUNT_NO": t.ACCOUNT_NO,
            "CUSTOMER_ID": t.CUSTOMER_ID,
            "TRN_DATE": t.TRN_DATE.isoformat() if t.TRN_DATE else None,
            "TRN_DESC": t.TRN_DESC,
            "DRCR_INDICATOR": t.DRCR_INDICATOR,
            "TRN_AMOUNT": str(t.TRN_AMOUNT),
            "TRN_CCY": t.TRN_CCY,
            "ACCOUNT_CCY": t.ACCOUNT_CCY,
            "OPENING_BALANCE": str(t.OPENING_BALANCE),
            "CLOSING_BALANCE": str(t.CLOSING_BALANCE),
            "RUNNING_BALANCE": str(t.RUNNING_BALANCE),
            "CREDIT_ACCOUNT": t.CREDIT_ACCOUNT,
            "CREDIT_ACCOUNT_CCY": t.CREDIT_ACCOUNT_CCY,
            "TRN_TYPE": t.TRN_TYPE,
            "STATUS": t.STATUS,
            "BANK_CHARGES": str(t.BANK_CHARGES),
        })

    return {"page": page, "limit": limit, "transactions": result}


# --- KPIs endpoint
@app.get("/kpis")
def get_kpis(
    history: bool = Query(False),
    limit: int = Query(10, gt=0, le=100),
    db: Session = Depends(get_db_dep),
):
    if history:
        rows = (
            db.query(models.KPI)
            .order_by(models.KPI.computed_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "history": [
                {
                    "computed_at": r.computed_at.isoformat(),
                    "total_transactions": r.total_transactions,
                    "total_amount_usd": str(r.total_amount_usd),
                    "total_amount_rm": str(r.total_amount_rm),
                    "dr_count": r.dr_count,
                    "cr_count": r.cr_count,
                    "txn_per_customer": r.txn_per_customer,
                    "failure_rate": float(r.failure_rate),
                    "total_bank_charges": str(r.total_bank_charges),
                    # 👇 include fail_count + failure_rate by type
                    "txn_type_split": {
                        "TRANSFER": {
                            "count": r.transfer_count,
                        },
                        "DEPOSIT": {
                            "count": r.deposit_count,
                        },
                        "LOAN_PAYMENT": {
                            "count": r.loan_payment_count,
                        },
                        "BILL_PAYMENT": {
                            "count": r.bill_payment_count,
                        },
                    },
                }
                for r in rows
            ]
        }
    else:
        r = db.query(models.KPI).order_by(models.KPI.computed_at.desc()).first()
        if not r:
            raise HTTPException(
                status_code=404,
                detail="No KPI snapshot found yet. Wait for scheduler to run.",
            )

        # 👇 Instead of reconstructing txn_type_split here, call compute_kpis again
        # so we can reuse the enriched txn_types (with fail_count + failure_rate)
        latest = crud.compute_kpis(db)

        return latest


# In-memory cache for insights
INSIGHTS_CACHE = {
    "last_generated": None,
    "last_count": 0,
    "data": []
}

@app.get("/insights")
def get_insights(
    db: Session = Depends(get_db_dep),
):
    global INSIGHTS_CACHE
    now = datetime.now(timezone.utc)

    should_refresh = False
    if not INSIGHTS_CACHE["last_generated"]:
        should_refresh = True
    else:
        elapsed = (now - INSIGHTS_CACHE["last_generated"]).total_seconds()
        INSIGHTS_CACHE["last_count"] += 1
        if elapsed >= 60 or INSIGHTS_CACHE["last_count"] >= 10:
            should_refresh = True

    if should_refresh:
        logger.info("Refreshing insights...")
        latest_kpis = crud.compute_kpis(db)
        logger.info(latest_kpis)
        INSIGHTS_CACHE["data"] = generate_insights_from_kpis(latest_kpis)
        logger.info(f"New insights: {INSIGHTS_CACHE['data']}")
        INSIGHTS_CACHE["last_generated"] = now
        INSIGHTS_CACHE["last_count"] = 0

    return {"insights": INSIGHTS_CACHE["data"]}

# --- Chatbot endpoint
@app.post("/chatbot")
def chatbot(query: str = Body(..., embed=True), db: Session = Depends(get_db_dep)):
    return get_chatbot_response(query, db)

# --- Report serving endpoint ---
@app.get("/reports/{filename}")
def get_report(filename: str):
    from .report_service import REPORTS_DIR
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)