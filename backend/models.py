# backend/models.py
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Enum,
    DECIMAL,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ACCOUNT_NO = Column(String(32), unique=True, nullable=False)
    CUSTOMER_ID = Column(String(64), index=True, nullable=False)
    ACCOUNT_CCY = Column(String(3), nullable=False)
    BALANCE = Column(DECIMAL(18, 2), nullable=False, default=0.00)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    TRN_REF_NO = Column(String(64), unique=True, nullable=False)
    ACCOUNT_NO = Column(String(32), nullable=False)
    CUSTOMER_ID = Column(String(64), nullable=False)
    TRN_DATE = Column(DateTime, nullable=False)
    TRN_DESC = Column(String(255))
    DRCR_INDICATOR = Column(Enum("DR", "CR"), nullable=False)
    TRN_AMOUNT = Column(DECIMAL(18, 2), nullable=False)
    TRN_CCY = Column(String(3), nullable=False)
    ACCOUNT_CCY = Column(String(3), nullable=False)
    OPENING_BALANCE = Column(DECIMAL(18, 2), nullable=False)
    CLOSING_BALANCE = Column(DECIMAL(18, 2), nullable=False)
    RUNNING_BALANCE = Column(DECIMAL(18, 2), nullable=False)

    # New fields
    TRN_TYPE = Column(
        Enum("TRANSFER", "DEPOSIT", "LOAN_PAYMENT", "BILL_PAYMENT"), nullable=False
    )
    BANK_CHARGES = Column(DECIMAL(18, 2), nullable=False, default=0.00)
    STATUS = Column(Enum("SUCCESS", "FAILED"), nullable=False, default="SUCCESS")

    CREDIT_ACCOUNT = Column(String(32))
    CREDIT_ACCOUNT_CCY = Column(String(3))
    CREATED_AT = Column(DateTime, default=datetime.utcnow)


class KPI(Base):
    __tablename__ = "kpis"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    computed_at = Column(DateTime, nullable=False)

    # Existing aggregates
    total_transactions = Column(Integer, nullable=False)
    total_amount_usd = Column(DECIMAL(18, 2), nullable=False)
    total_amount_rm = Column(DECIMAL(18, 2), nullable=False)
    dr_count = Column(Integer, nullable=False)
    cr_count = Column(Integer, nullable=False)
    txn_per_customer = Column(JSON, nullable=False)

    # New fields for extended metrics
    transfer_count = Column(Integer, nullable=False, default=0)
    deposit_count = Column(Integer, nullable=False, default=0)
    loan_payment_count = Column(Integer, nullable=False, default=0)
    bill_payment_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    total_bank_charges = Column(DECIMAL(18, 2), nullable=False, default=0.00)
    failed_txn_count = Column(Integer, nullable=False, default=0)
    failure_rate = Column(DECIMAL(5, 2), nullable=False, default=0.00)


Index("idx_kpis_computed_at", KPI.computed_at)
