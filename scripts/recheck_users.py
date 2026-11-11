#!/usr/bin/env python3
"""Har bir foydalanuvchiga bot yoza olishini tekshirib, holatini aniq yozib chiqadi.

    python scripts/recheck_users.py              # hamma foydalanuvchi
    python scripts/recheck_users.py --inactive   # faqat hozir nofaollar

Hech qanday xabar yuborilmaydi: `sendChatAction` ("typing") ishlatiladi.
Telegram unga ham rassilkadagi kabi aniq xato qaytaradi:
bloklagan / akkaunt o'chirilgan / botga /start bosmagan. Chat ochiq turgan
odam bir necha soniya "yozmoqda..." ni ko'rishi mumkin, xolos.

Natijada:
* yetib boradi        -> is_active = true,  inactive_reason = NULL
* bloklagan           -> is_active = false, inactive_reason = 'blocked'
* akkaunt o'chirilgan -> is_active = false, inactive_reason = 'deactivated'
* /start bosmagan     -> is_active = false, inactive_reason = 'not_started'
  (statistikadan chiqadi)

Bot ishlab turganda ham ishga tushirsa bo'ladi; qayta ishga tushirish xavfsiz.
Tezlik ~20 ta/soniya: 90 000 foydalanuvchi ~75 daqiqa.
"""

import argparse
import asyncio
import logging
import sys
from collections import Counter
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from sqlalchemy import select, update

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import BOT_TOKEN  # noqa: E402
from db.base import close_db, session_maker  # noqa: E402
from db.models import User  # noqa: E402
from utils.user_status import inactive_reason  # noqa: E402

logger = logging.getLogger("recheck_users")

DELAY = 0.05
REACHABLE = "reachable"
FAILED = "failed"


async def _probe(bot: Bot, tg_id: int) -> str:
    for attempt in range(3):
        try:
            await bot.send_chat_action(tg_id, "typing")
            return REACHABLE
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except TelegramAPIError as e:
            return inactive_reason(e) or FAILED
    return FAILED


async def _save(tg_id: int, result: str) -> None:
    if result == FAILED:
        return
    values = (
        {"is_active": True, "inactive_reason": None}
        if result == REACHABLE
        else {"is_active": False, "inactive_reason": result}
    )
    async with session_maker() as s:
        await s.execute(update(User).where(User.tg_id == tg_id).values(**values))
        await s.commit()


async def main(only_inactive: bool) -> None:
    if not BOT_TOKEN:
        raise SystemExit("❌ .env faylida BOT_TOKEN yo'q")

    query = select(User.tg_id).order_by(User.id)
    if only_inactive:
        query = query.where(User.is_active.is_(False))
    async with session_maker() as s:
        ids = list(await s.scalars(query))
    logger.info("Tekshiriladi: %s ta foydalanuvchi", len(ids))

    counts: Counter[str] = Counter()
    bot = Bot(BOT_TOKEN)
    try:
        for i, tg_id in enumerate(ids, start=1):
            result = await _probe(bot, tg_id)
            counts[result] += 1
            await _save(tg_id, result)
            if i % 1000 == 0:
                logger.info("%s/%s  %s", i, len(ids), dict(counts))
            await asyncio.sleep(DELAY)
    finally:
        await bot.session.close()
        await close_db()

    logger.info("✅ Tayyor: %s", dict(counts))
    logger.info(
        "Yetib boradi: %s | bloklagan: %s | akkaunt o'chirilgan: %s | "
        "/start bosmagan: %s | aniqlanmadi: %s",
        counts[REACHABLE],
        counts["blocked"],
        counts["deactivated"],
        counts["not_started"],
        counts[FAILED],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--inactive", action="store_true", help="faqat hozir nofaol foydalanuvchilar"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    asyncio.run(main(args.inactive))
