"""Botning shaxsiy chatida yozgan foydalanuvchini bazaga yozib/yangilab boradi.

Faqat shaxsiy chatdagi xabar va tugma bosish hisoblanadi — ya'ni botga /start
bosgan odam. Yopiq kanalga zayafka (`chat_join_request`), kanal/guruh
update'lari va `my_chat_member` foydalanuvchi yaratmaydi: bunday odamga bot
yoza olmaydi va u statistikaga kirmasligi kerak.

`/start ref<id>` payloadi ham shu yerda o'qiladi — obuna va telefon
tekshiruvidan oldin ishlagani uchun taklif hech qachon yo'qolmaydi.
"""

import logging
from typing import Any, Awaitable, Callable, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, User

from db.queries import get_or_create_user
from utils.private_link import notify_referrer
from utils.referral import parse_ref_payload

logger = logging.getLogger(__name__)


def _private_event(update: TelegramObject) -> bool:
    """Update botning shaxsiy chatidagi xabar yoki tugma bosishmi."""
    message = getattr(update, "message", None)
    if message is not None:
        return message.chat.type == "private"
    callback = getattr(update, "callback_query", None)
    if callback is not None and callback.message is not None:
        return callback.message.chat.type == "private"
    return False


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
        if tg_user and not tg_user.is_bot and _private_event(event):
            db_user, referrer_id = await get_or_create_user(
                tg_user.id,
                tg_user.full_name,
                tg_user.username,
                _referrer_id(event),
            )
            data["db_user"] = db_user
            if referrer_id is not None:
                await _notify_referrer(data.get("bot"), referrer_id, tg_user.full_name)
        return await handler(event, data)


async def _notify_referrer(bot: Optional[Bot], referrer_id: int, new_user_name: str) -> None:
    """Taklif qilganga tabrik (+ shart bajarilsa yopiq kanal havolasi).

    Bu yerdagi har qanday xato yangi kelgan odamning /start iga xalaqit bermasin.
    """
    if bot is None:
        return
    try:
        await notify_referrer(bot, referrer_id, new_user_name)
    except Exception:  # noqa: BLE001
        logger.exception("Taklif qilganga xabar yuborishda xato (%s)", referrer_id)
