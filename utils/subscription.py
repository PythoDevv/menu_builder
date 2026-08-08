"""Kanalga obuna tekshiruvi.

Ochiq kanal  -> a'zomi?
Yopiq kanal  -> a'zomi YOKI qo'shilish so'rovi tashlaganmi?

Natija qisqa vaqt keshlanadi, shuning uchun har bosishda Telegram'ga so'rov ketmaydi.
"""

import time

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from config import SUB_CACHE_TTL
from db.models import Channel
from db.queries import get_channels, get_join_request_channel_ids

_OK_STATUSES = {"creator", "administrator", "member"}

# tg_id -> qachongacha "obuna bo'lgan" deb hisoblaymiz
_cache: dict[int, float] = {}


def clear_cache(tg_id: int | None = None) -> None:
    if tg_id is None:
        _cache.clear()
    else:
        _cache.pop(tg_id, None)


async def _is_member(bot: Bot, chat_id: int, tg_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, tg_id)
    except TelegramAPIError:
        # bot kanalda admin emas yoki kanal o'chirilgan -> foydalanuvchini to'smaymiz
        return True
    if member.status in _OK_STATUSES:
        return True
    if member.status == "restricted":
        return bool(getattr(member, "is_member", False))
    return False


async def get_missing_channels(bot: Bot, tg_id: int) -> list[Channel]:
    """Foydalanuvchi hali obuna bo'lmagan kanallar ro'yxati."""
    channels = await get_channels(active_only=True)
    if not channels:
        return []

    requested = await get_join_request_channel_ids(tg_id)
    missing: list[Channel] = []
    for ch in channels:
        if ch.is_private and ch.id in requested:
            continue  # zayafka tashlagan -> qayta so'ramaymiz
        if await _is_member(bot, ch.chat_id, tg_id):
            continue
        missing.append(ch)
    return missing


async def check_subscription(bot: Bot, tg_id: int) -> list[Channel]:
    """Keshni hisobga olgan tekshiruv. Bo'sh ro'yxat -> hammasi joyida."""
    now = time.monotonic()
    if _cache.get(tg_id, 0) > now:
        return []

    missing = await get_missing_channels(bot, tg_id)
    if not missing:
        _cache[tg_id] = now + SUB_CACHE_TTL
    return missing
