"""Admin ro'yxati.

Ikki manba bor:
  * `.env` dagi `ADMINS` — asosiy (super) adminlar, paneldan o'chirib bo'lmaydi;
  * `admins` jadvali — panel orqali qo'shilganlar.

Har bir update'da bazaga bormaslik uchun ro'yxat xotirada saqlanadi va
faqat admin qo'shilganda/o'chirilganda yangilanadi.
"""

from config import ADMINS as SUPER_ADMINS
from db.queries import get_admin_ids

_cache: set[int] = set(SUPER_ADMINS)


async def refresh_admins() -> set[int]:
    """Keshni bazadan qayta yig'adi."""
    global _cache
    _cache = set(SUPER_ADMINS) | set(await get_admin_ids())
    return _cache


def is_admin(tg_id: int) -> bool:
    return tg_id in _cache


def is_super_admin(tg_id: int) -> bool:
    return tg_id in SUPER_ADMINS


def admin_ids() -> set[int]:
    return set(_cache)
