import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _parse_admins(raw: str) -> list[int]:
    return [int(p) for p in raw.replace(" ", "").split(",") if p.lstrip("-").isdigit()]


def _optional_int_env(name: str) -> int | None:
    """Bo'sh yoki noto'g'ri qiymatni sozlanmagan deb qabul qiladi."""
    raw = os.getenv(name, "").strip()
    return int(raw) if raw.lstrip("-").isdigit() else None


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMINS = _parse_admins(os.getenv("ADMINS", ""))

# Rich-formatdagi forward qilingan postlar shu yopiq kanalga nusxalanadi.
# Bot u yerda admin bo'lishi, kanal ID esa -100... ko'rinishida bo'lishi kerak.
CONTENT_ARCHIVE_CHAT_ID = _optional_int_env("CONTENT_ARCHIVE_CHAT_ID")

DB_URL = os.getenv(
    "DB_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/menu_builder"
)

TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

EXPORT_DIR = BASE_DIR / "exports"
EXPORT_FILE = EXPORT_DIR / "users.xlsx"
EXPORT_DIR.mkdir(exist_ok=True)

DUMPS_DIR = BASE_DIR / "dumps"

EXPORT_HOUR = int(os.getenv("EXPORT_HOUR", "0"))
EXPORT_MINUTE = int(os.getenv("EXPORT_MINUTE", "5"))

# Obuna tekshiruvi natijasi necha soniya keshda tursin (qayta-qayta so'ramaslik uchun)
SUB_CACHE_TTL = 300

# Broadcast paytida xabarlar orasidagi pauza (soniya)
BROADCAST_DELAY = 0.05
