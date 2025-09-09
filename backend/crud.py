# backend/crud.py
from decimal import Decimal, ROUND_HALF_UP
import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from .models import Transaction, KPI
from utils.logger import get_logger

logger = get_logger("crud")


# FX helper (same approach as generator for consistency)
def get_fx_rate(base: str, quote: str) -> Decimal:
    if base == quote:
        return Decimal("1.0")
    mid = Decimal("4.23")
    jitter = Decimal(str(random.uniform(-0.05, 0.05))).quantize(Decimal("0.0001"))
    usdrm = (mid + jitter).quantize(Decimal("0.0001"))
    if base == "USD" and quote == "RM":
        return usdrm
    if base == "RM" and quote == "USD":
        return (Decimal("1.0") / usdrm).quantize(Decimal("0.0001"))
    return Decimal("1.0")


def quant2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_kpis(db: Session):
    """
    Aggregate all transactions into KPIs and persist a new KPI row.
    """
    # Basic counts
    total_txns = db.query(func.count(Transaction.id)).scalar() or 0
    dr_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.DRCR_INDICATOR == "DR")
        .scalar()
        or 0
    )
    cr_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.DRCR_INDICATOR == "CR")
        .scalar()
        or 0
    )

    # Success vs failure
    success_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.STATUS == "SUCCESS")
        .scalar()
        or 0
    )
    fail_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.STATUS == "FAILED")
        .scalar()
        or 0
    )
    failure_rate = round((fail_count / total_txns) * 100, 2) if total_txns > 0 else 0.0

    # Bank charges → sum only for successful txns
    bank_charges = db.query(
        func.coalesce(
            func.sum(
                case(
                    (Transaction.STATUS == "SUCCESS", Transaction.BANK_CHARGES),
                    else_=Decimal("0.00"),
                )
            ),
            0,
        )
    ).scalar() or Decimal("0.00")

    # Amount aggregates across currencies
    total_usd = Decimal("0")
    total_rm = Decimal("0")

    # Retrieve all transactions (or relevant subset)
    all_txns = db.query(Transaction.TRN_AMOUNT, Transaction.TRN_CCY).all()

    for amt, ccy in all_txns:
        amt = Decimal(str(amt or 0))
        # Convert txn amount to both USD and RM
        if ccy == "USD":
            total_usd += amt
            total_rm += amt * get_fx_rate("USD", "RM")
        elif ccy == "RM":
            total_rm += amt
            total_usd += amt * get_fx_rate("RM", "USD")

    total_usd = quant2(total_usd)
    total_rm = quant2(total_rm)

    # Per-customer stats (in USD)
    per_cust = {}
    cust_rows = (
        db.query(
            Transaction.CUSTOMER_ID,
            func.count(Transaction.id),
            func.sum(Transaction.TRN_AMOUNT),
            Transaction.TRN_CCY,
        )
        .group_by(Transaction.CUSTOMER_ID, Transaction.TRN_CCY)
        .all()
    )
    temp = {}
    for row in cust_rows:
        customer_id, cnt, sum_amount, ccy = row
        sum_amount = Decimal(str(sum_amount or 0))
        if ccy == "USD":
            sum_usd = sum_amount
        else:
            sum_usd = sum_amount * get_fx_rate("RM", "USD")
        if customer_id not in temp:
            temp[customer_id] = {"count": 0, "amount_usd": Decimal("0")}
        temp[customer_id]["count"] += int(cnt or 0)
        temp[customer_id]["amount_usd"] += sum_usd

    for cust, vals in temp.items():
        per_cust[cust] = {
            "count": vals["count"],
            "amount_usd": str(quant2(vals["amount_usd"])),
        }

    # --- Transaction type breakdown ---
    type_rows = (
        db.query(
            Transaction.TRN_TYPE,
            func.count(Transaction.id),
            func.sum(Transaction.TRN_AMOUNT),
            func.sum(case((Transaction.STATUS == "FAILED", 1), else_=0)),
        )
        .group_by(Transaction.TRN_TYPE)
        .all()
    )

    txn_types = {}
    for row in type_rows:
        ttype = row[0]
        count = int(row[1] or 0)
        sum_amount = Decimal(str(row[2] or 0))
        fails = int(row[3] or 0)
        fail_rate = (fails / count * 100) if count > 0 else 0
        txn_types[ttype] = {
            "count": count,
            "amount_usd": str(quant2(sum_amount)),  # or convert to USD if needed
            "fail_count": fails,
            "failure_rate": round(fail_rate, 2),
        }
    logger.info(f"Transaction types split: {txn_types}")
    # Reset + insert KPI row
    db.query(KPI).delete()
    db.commit()
    kpi = KPI(
        computed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        total_transactions=total_txns,
        total_amount_usd=str(total_usd),
        total_amount_rm=str(total_rm),
        dr_count=dr_count,
        cr_count=cr_count,
        success_count=success_count,
        failed_txn_count=fail_count,
        failure_rate=Decimal(str(failure_rate)),
        total_bank_charges=str(quant2(Decimal(str(bank_charges)))),
        txn_per_customer=per_cust,
        transfer_count=txn_types.get("TRANSFER", {}).get("count", 0),
        deposit_count=txn_types.get("DEPOSIT", {}).get("count", 0),
        loan_payment_count=txn_types.get("LOAN_PAYMENT", {}).get("count", 0),
        bill_payment_count=txn_types.get("BILL_PAYMENT", {}).get("count", 0),
    )
    db.add(kpi)
    db.commit()
    db.refresh(kpi)
    logger.info(f"[Scheduler] recomputing KPIs at {datetime.now(timezone.utc)}")
    result = {
        "id": kpi.id,
        "computed_at": kpi.computed_at.isoformat(),
        "total_transactions": kpi.total_transactions,
        "total_amount_usd": kpi.total_amount_usd,
        "total_amount_rm": kpi.total_amount_rm,
        "dr_count": kpi.dr_count,
        "cr_count": kpi.cr_count,
        "txn_per_customer": kpi.txn_per_customer,
        "txn_type_split": txn_types,  # 👈 new
        "success_count": success_count,
        "fail_count": fail_count,
        "failure_rate": round(failure_rate, 2),
        "total_bank_charges": str(quant2(kpi.total_bank_charges)),
        "transfer_count": kpi.transfer_count,
        "deposit_count": kpi.deposit_count,
        "loan_payment_count": kpi.loan_payment_count,
        "bill_payment_count": kpi.bill_payment_count,
    }
    return result
