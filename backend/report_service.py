import os
from datetime import datetime, date
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from utils.logger import get_logger
from utils.llm_connector import run_llm
import json
from .database import SessionLocal
from . import models

logger = get_logger("ReportService")

REPORTS_DIR = "/opt/preslaes/AI_Projects/FariSight_Analytics/reports"



def generate_bank_charges_report(target_date: date = None) -> str:
    """
    Generate PDF report of bank charges collected today.
    Returns the path to the generated report.
    """
    
    if not target_date:
        target_date = date.today()

    db = SessionLocal()
    try:
        # fetch today's transactions
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())

        txns = (
            db.query(models.Transaction)
            .filter(models.Transaction.TRN_DATE >= start)
            .filter(models.Transaction.TRN_DATE <= end)
            .all()
        )

        # aggregate
        summary = {
            "DEPOSIT": {"count": 0, "amount": Decimal("0"), "charges": Decimal("0")},
            "TRANSFER": {"count": 0, "amount": Decimal("0"), "charges": Decimal("0")},
            "LOAN_PAYMENT": {
                "count": 0,
                "amount": Decimal("0"),
                "charges": Decimal("0"),
            },
            "BILL_PAYMENT": {
                "count": 0,
                "amount": Decimal("0"),
                "charges": Decimal("0"),
            },
        }

        for t in txns:
            t_type = (t.TRN_TYPE or "").upper()
            if t_type not in summary:
                continue
            summary[t_type]["count"] += 1
            summary[t_type]["amount"] += Decimal(str(t.TRN_AMOUNT))
            summary[t_type]["charges"] += Decimal(str(t.BANK_CHARGES))

        # totals
        total_count = sum(v["count"] for v in summary.values())
        total_amount = sum(v["amount"] for v in summary.values())
        total_charges = sum(v["charges"] for v in summary.values())

        # build pdf
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filename = f"bank_charges_report_{target_date.isoformat()}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        title = Paragraph(
            f"<b>Bank Charges Report - {target_date.isoformat()}</b>", styles["Title"]
        )
        elements.append(title)
        elements.append(Spacer(1, 12))

        data = [
            ["Transaction Type", "Number of  Transactions", "Transaction Amount", "Charges Collected"]
        ]
        for k, v in summary.items():
            data.append(
                [k, str(v["count"]), f"{v['amount']:.2f}", f"{v['charges']:.2f}"]
            )

        data.append(
            ["TOTAL", str(total_count), f"{total_amount:.2f}", f"{total_charges:.2f}"]
        )

        table = Table(data, colWidths=[120, 120, 150, 150])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )

        elements.append(table)
        doc.build(elements)

        logger.info(f"Report generated: {filepath}")
        return filepath
    finally:
        db.close()



def generate_failure_timeline_report(target_date: date = None) -> str:
    """
    Generate PDF report of failed transactions with timelines and LLM-generated probable causes.
    """
    if not target_date:
        target_date = date.today()

    db = SessionLocal()
    try:
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())

        txns = (
            db.query(models.Transaction)
            .filter(models.Transaction.TRN_DATE >= start)
            .filter(models.Transaction.TRN_DATE <= end)
            .filter(models.Transaction.STATUS == "FAILED")
            .all()
        )

        # Step 1: Aggregate failures by hour
        timeline = {}
        for t in txns:
            hour = t.TRN_DATE.strftime("%H:00")
            timeline[hour] = timeline.get(hour, 0) + 1

        # Step 2: Ask LLM to generate probable causes
        if timeline:
            context = "\n".join([f"{h}: {c} failures" for h, c in sorted(timeline.items())])
            prompt = f"""
            You are analyzing failed bank transactions. 
            For each time bucket, generate 1 short probable cause. 
            Keep responses simple and realistic (network issues, server timeout, insufficient balance, etc).
            Respond in JSON like:
            {{
                "08:00": "Network congestion",
                "09:00": "Insufficient balance spikes"
            }}

            Data:
            {context}
            """

            llm_response = run_llm(prompt)
            try:
                causes = json.loads(llm_response) if isinstance(llm_response, str) else llm_response
            except Exception:
                causes = {}
        else:
            causes = {}

        # Step 3: Build PDF
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filename = f"failure_timeline_report_{target_date.isoformat()}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        title = Paragraph(
            f"<b>Failure Timeline Report - {target_date.isoformat()}</b>", styles["Title"]
        )
        elements.append(title)
        elements.append(Spacer(1, 12))

        data = [["Time Period", "Failed Txns", "Probable Cause"]]
        for hour, count in sorted(timeline.items()):
            cause = causes.get(hour, "-")
            data.append([hour, str(count), cause])

        table = Table(data, colWidths=[120, 120, 250])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#660000")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ])
        )

        elements.append(table)
        doc.build(elements)

        logger.info(f"Failure report generated: {filepath}")
        return filepath

    finally:
        db.close()
