import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _parse_admins(raw: str) -> list[int]:
    return [int(p) for p in raw.replace(" ", "").split(",") if p.lstrip("-").isdigit()]


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMINS = _parse_admins(os.getenv("ADMINS", ""))

DB_URL = os.getenv(
    "DB_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/menu_builder"
)

TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

EXPORT_DIR = BASE_DIR / "exports"
EXPORT_FILE = EXPORT_DIR / "users.xlsx"
EXPORT_DIR.mkdir(exist_ok=True)

EXPORT_HOUR = int(os.getenv("EXPORT_HOUR", "0"))
EXPORT_MINUTE = int(os.getenv("EXPORT_MINUTE", "5"))

# Obuna tekshiruvi natijasi necha soniya keshda tursin (qayta-qayta so'ramaslik uchun)
SUB_CACHE_TTL = 300

# Broadcast paytida xabarlar orasidagi pauza (soniya)
BROADCAST_DELAY = 0.05
