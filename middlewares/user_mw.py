"""Har bir update'da foydalanuvchini bazaga yozib/yangilab boradi.

`/start ref<id>` payloadi ham shu yerda o'qiladi — obuna va telefon
tekshiruvidan oldin ishlagani uchun taklif hech qachon yo'qolmaydi.
"""

import logging
from contextlib import suppress
from typing import Any, Awaitable, Callable, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import TelegramObject, User

from db.queries import get_or_create_user, get_referral_count
from utils.referral import parse_ref_payload

logger = logging.getLogger(__name__)

NEW_REFERRAL_TEXT = (
    "🎉 <b>Yangi taklif!</b>\n\n"
    "Sizning havolangiz orqali yana bir kishi botga qo'shildi.\n"
    "👥 Jami takliflaringiz: <b>{count}</b> ta"
)


def _referrer_id(event: TelegramObject) -> Optional[int]:
    """Update ichidagi `/start ref<id>` dan taklif qilgan odamning ID sini oladi."""
    message = getattr(event, "message", None)
    text = getattr(message, "text", None) or ""
    if not text.startswith("/start "):
        return None
    return parse_ref_payload(text.split(maxsplit=1)[1].strip())


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if tg_user and not tg_user.is_bot:
            db_user, referrer_id = await get_or_create_user(
                tg_user.id,
                tg_user.full_name,
                tg_user.username,
                _referrer_id(event),
            )
            data["db_user"] = db_user
            if referrer_id is not None:
                await _notify_referrer(data.get("bot"), referrer_id)
        return await handler(event, data)


async def _notify_referrer(bot: Optional[Bot], referrer_id: int) -> None:
    """Taklif qilgan odamga xabar. U botni bloklagan bo'lsa jim o'tib ketamiz."""
    if bot is None:
        return
    count = await get_referral_count(referrer_id)
    logger.info("Yangi taklif: %s -> jami %s ta", referrer_id, count)
    with suppress(TelegramAPIError):
        await bot.send_message(referrer_id, NEW_REFERRAL_TEXT.format(count=count))
