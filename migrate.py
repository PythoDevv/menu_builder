"""SQL migratsiyalarni qo'llaydi.

    python migrate.py

`migrations/` papkasidagi `.sql` fayllar nomi bo'yicha tartib bilan bajariladi.
Qaysi biri qo'llangani `schema_migrations` jadvalida saqlanadi, shuning uchun
skriptni xohlagancha qayta ishga tushirish mumkin — bajarilgani takrorlanmaydi.

Fayl ichidagi buyruqlar `;` bilan ajratiladi (asyncpg bir so'rovda bitta
buyruqni bajaradi), shuning uchun SQL ichida `;` faqat buyruq oxirida turishi kerak.
"""

import asyncio
import logging
import re
import sys
from pathlib import Path

from sqlalchemy import text

from db.base import close_db, engine

logger = logging.getLogger("migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

CREATE_HISTORY = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    name       TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

COMMENT_RE = re.compile(r"--[^\n]*")


def _statements(sql: str) -> list[str]:
    sql = COMMENT_RE.sub("", sql)
    return [part.strip() for part in sql.split(";") if part.strip()]


async def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
    try:
        return await _run()
    finally:
        await close_db()


async def _run() -> int:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        logger.info("Migratsiya fayllari topilmadi")
        return 0

    async with engine.begin() as conn:
        await conn.execute(text(CREATE_HISTORY))
        rows = await conn.execute(text("SELECT name FROM schema_migrations"))
        applied = {r[0] for r in rows}

    new = 0
    for path in files:
        if path.name in applied:
            logger.info("↷ %s — allaqachon qo'llangan", path.name)
            continue
        logger.info("→ %s qo'llanmoqda...", path.name)
        async with engine.begin() as conn:
            for stmt in _statements(path.read_text(encoding="utf-8")):
                await conn.execute(text(stmt))
            await conn.execute(
                text("INSERT INTO schema_migrations (name) VALUES (:name)"),
                {"name": path.name},
            )
        logger.info("✅ %s tayyor", path.name)
        new += 1

    logger.info("Yakun: %s ta yangi migratsiya qo'llandi", new)
    return 0


if __name__ == "__main__":
    try:
        code = asyncio.run(main())
    except Exception:
        logging.exception("❌ Migratsiya bajarilmadi")
        code = 1
    sys.exit(code)
