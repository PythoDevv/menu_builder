"""Kunlik cron: Excel faylni yangilab turadi."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import EXPORT_FILE, EXPORT_HOUR, EXPORT_MINUTE, TIMEZONE
from utils.excel import build_excel

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=TIMEZONE)


async def _job() -> None:
    try:
        await build_excel()
    except Exception:
        logger.exception("Excel cron xatosi")


async def start_scheduler() -> None:
    scheduler.add_job(
        _job,
        CronTrigger(hour=EXPORT_HOUR, minute=EXPORT_MINUTE),
        id="daily_excel",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("Cron ishga tushdi: har kuni %02d:%02d", EXPORT_HOUR, EXPORT_MINUTE)

    # fayl umuman bo'lmasa — birinchi marta hoziroq yaratamiz
    if not EXPORT_FILE.exists():
        await _job()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
