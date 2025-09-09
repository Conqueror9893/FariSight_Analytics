import os
import random
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import sys
from sqlalchemy import func
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
from backend.models import Account, Transaction
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


from utils.logger import get_logger  # adjust path as needed
logger = get_logger("generator")

# ------------------------
# Config
# ------------------------


load_dotenv()
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "presales")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "farisight")

TARGET_CUSTOMERS = [
    "223345",
    "445566",
    "786052",
    "78605200",
    "BFLUK012025",
    "SIUAE2025",
]
ACCOUNT_CURRENCIES = ["USD", "RM"]
TXN_CURRENCIES = ["USD", "RM"]


# Realistic USD?RM conversion (center ~4.23, mild jitter)
def get_fx_rate(base: str, quote: str) -> Decimal:
    if base == quote:
        return Decimal("1.0")
    mid = 4.23
    jitter = random.uniform(-0.05, 0.05) 
    usdrm = Decimal(str(mid + jitter)).quantize(Decimal("0.0001"))
    if base == "USD" and quote == "RM":
        return usdrm
    if base == "RM" and quote == "USD":
        return (Decimal("1.0") / usdrm).quantize(Decimal("0.0001"))
    return Decimal("1.0")


DESCS = [
    "Treasury Settlement",
    "Trade Finance Payment",
    "Corporate Loan Disbursal",
    "Cross-border Payment",
    "Payroll Batch",
    "Vendor AP Payment",
    "Card Settlement",
    "Fee/Charges",
]

COUNTERPARTIES = [
    "CPT-ACME-001",
    "CPT-GLOBEX-017",
    "CPT-INITECH-233",
    "CPT-UMBRELLA-559",
    "CPT-WAYNE-882",
    "CPT-STARK-312",
]

AMOUNT_USD_RANGE = (10, 10000)
AMOUNT_RM_RANGE = (40, 40000)


def ensure_accounts(db: Session):
    for cust in TARGET_CUSTOMERS:
        for ccy in ACCOUNT_CURRENCIES:
            suffix = "1" if ccy == "USD" else "2"
            acct_no = f"7{abs(hash(cust)) % 10**10:010d}{suffix}"[:12]
            # Check if account exists
            account = db.query(Account).filter(Account.ACCOUNT_NO == acct_no).first()
            if not account:
                if ccy == "USD":
                    seed = Decimal(str(random.randint(80, 35000)))
                else:
                    seed = Decimal(str(random.randint(30, 15000)))
                account = Account(
                    ACCOUNT_NO=acct_no,
                    CUSTOMER_ID=cust,
                    ACCOUNT_CCY=ccy,
                    BALANCE=seed,
                )
                db.add(account)
    db.commit()


def quant2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_one(db: Session):
    account = db.query(Account).order_by(func.rand()).first()
    if not account:
        return

    account_no = account.ACCOUNT_NO
    customer_id = account.CUSTOMER_ID
    account_ccy = account.ACCOUNT_CCY
    opening_balance = account.BALANCE

    # Adjusted realistic transaction ranges
    if account_ccy == "USD":
        amt = Decimal(str(random.randint(10, 10000)))
        trn_ccy = "USD"
    else:
        amt = Decimal(str(random.randint(40, 40000)))
        trn_ccy = "RM"

    # Debit / Credit ratio
    drcr = random.choices(["CR", "DR"], weights=[55, 45], k=1)[0]

    # Convert to account currency if needed
    if trn_ccy == account_ccy:
        amt_in_account_ccy = amt
    else:
        rate = get_fx_rate(trn_ccy, account_ccy)
        amt_in_account_ccy = (amt * rate).quantize(Decimal("0.01"))

    # Assign transaction type with weighted probabilities
    trn_type = random.choices(
        ["TRANSFER", "DEPOSIT", "LOAN_PAYMENT", "BILL_PAYMENT"],
        weights=[40, 20, 10, 30],
        k=1
    )[0]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    trn_ref = f"TRN-{uuid.uuid4().hex[:20].upper()}"
    trn_desc = random.choice(DESCS)
    credit_acct = random.choice(COUNTERPARTIES)
    credit_ccy = random.choice(["USD", "RM"])

    # --- Failure check ---
    status = "SUCCESS"
    if drcr == "DR" and opening_balance < amt_in_account_ccy:
        status = "FAILED"
    elif random.random() < 0.02:  # 2% random failure
        status = "FAILED"

    # Calculate balances if success
    if status == "SUCCESS":
        if drcr == "CR":
            closing_balance = opening_balance + amt_in_account_ccy
        else:
            closing_balance = opening_balance - amt_in_account_ccy
    else:
        closing_balance = opening_balance  # no change if failed

    closing_balance = quant2(closing_balance)
    running_balance = closing_balance

    # --- Bank charges ---
    bank_charges = Decimal("0.00")
    if status == "SUCCESS":
        if trn_type == "TRANSFER":
            bank_charges = quant2(min(max(amt_in_account_ccy * Decimal("0.002"), 2), 200))
        elif trn_type == "LOAN_PAYMENT":
            bank_charges = Decimal("10.00")
        elif trn_type == "BILL_PAYMENT":
            bank_charges = Decimal("5.00")

    # Build transaction
    transaction = Transaction(
        TRN_REF_NO=trn_ref,
        ACCOUNT_NO=account_no,
        CUSTOMER_ID=customer_id,
        TRN_DATE=now,
        TRN_DESC=trn_desc,
        DRCR_INDICATOR=drcr,
        TRN_AMOUNT=quant2(amt),
        TRN_CCY=trn_ccy,
        ACCOUNT_CCY=account_ccy,
        OPENING_BALANCE=quant2(opening_balance),
        CLOSING_BALANCE=quant2(closing_balance),
        RUNNING_BALANCE=quant2(running_balance),
        TRN_TYPE=trn_type,
        BANK_CHARGES=quant2(bank_charges),
        STATUS=status,
        CREDIT_ACCOUNT=credit_acct,
        CREDIT_ACCOUNT_CCY=credit_ccy,
        CREATED_AT=now,
    )
    logger.info(f"Generated txn: amt={amt} {trn_ccy}, acct_ccy={account_ccy}, amt_in_account_ccy={amt_in_account_ccy}, balance before={opening_balance}, status={status}")

    db.add(transaction)

    # Update account balance if success
    if status == "SUCCESS":
        account.BALANCE = closing_balance
        account.UPDATED_AT = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise e


if __name__ == "__main__":
    while True:
        db = SessionLocal()
        try:
            ensure_accounts(db)
            logger.info("[generator] Accounts ensured. Starting stream... (Ctrl+C to stop)")
            while True:
                with SessionLocal() as db:
                    generate_one(db)
                time.sleep(random.uniform(2.0, 3.0))
        except KeyboardInterrupt:
            logger.info("Generator stopped.")
            break
        except Exception as e:
            logger.error(f"[generator] error: {e}")
            time.sleep(1.0)
        finally:
            db.close()
