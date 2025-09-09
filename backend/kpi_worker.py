# backend/kpi_worker.py
import atexit
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .database import SessionLocal
from .crud import compute_kpis
from utils.logger import get_logger

logger = get_logger("kpi_worker")

scheduler = AsyncIOScheduler()
_scheduler_started = False


def _job_compute_kpis():
    db = SessionLocal()
    try:
        kpi = compute_kpis(db)  # returns dict
        logger.info(
            f"[kpi_worker] KPI computed_at={kpi.get('computed_at')}, txns={kpi.get('total_transactions')}"
        )
    except Exception as e:
        logger.error(f"[kpi_worker] error computing kpis: {e}")
    finally:
        db.close()


def start():
    global _scheduler_started
    if _scheduler_started:
        logger.info("[kpi_worker] Scheduler already running. Skipping.")
        return

    # run immediately
    _job_compute_kpis()

    # schedule every 5 seconds
    scheduler.add_job(_job_compute_kpis, "interval", seconds=5)

    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))

    _scheduler_started = True
    logger.info("[kpi_worker] Started AsyncIOScheduler (every 5s).")
