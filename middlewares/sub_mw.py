"""Obuna va telefon tekshiruvi (outer middleware).

Obuna ekrani — inline: kanal havolalari tugmalarda, ostida '✅ Tekshirish'.
Xabarning o'zi (matn / rasm / video ...) admin paneldan sozlanadi, qo'yilmagan
bo'lsa `utils.texts.DEFAULT_SUB_MESSAGE` ishlatiladi.
"""

from contextlib import suppress
from typing import Any, Awaitable, Callable, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, TelegramObject

from db.models import Channel
from db.queries import get_sub_message, is_phone_required
from keyboards.user_kb import phone_kb, subscribe_kb
from utils.admins import is_admin
from utils.content import send_raw_content
from utils.subscription import check_subscription
from utils.texts import DEFAULT_SUB_MESSAGE

PHONE_TEXT = (
    "📱 Davom etish uchun telefon raqamingizni yuboring.\n\n"
    "Pastdagi <b>📱 Raqamni yuborish</b> tugmasini bosing."
)
NOT_SUBSCRIBED = "❗️ Siz hali barcha kanallarga qo'shilmadingiz"
PHONE_ALERT = "📱 Avval telefon raqamingizni yuboring"


def _chat_id(event: TelegramObject) -> Optional[int]:
    if isinstance(event, Message):
        return event.chat.id
    if isinstance(event, CallbackQuery):
        return event.message.chat.id if event.message else event.from_user.id
    return None


def _skip(event: TelegramObject) -> bool:
    """Tekshiruv faqat shaxsiy chatdagi oddiy foydalanuvchi uchun."""
    if isinstance(event, Message):
        chat_type = event.chat.type
    elif isinstance(event, CallbackQuery):
        chat_type = event.message.chat.type if event.message else "private"
    else:
        return True
    if chat_type != "private":
        return True
    user = event.from_user
    return user is None or is_admin(user.id)


async def send_sub_prompt(bot: Bot, chat_id: int, missing: list[Channel]) -> None:
    data = await get_sub_message() or DEFAULT_SUB_MESSAGE
    await send_raw_content(bot, chat_id, data, reply_markup=subscribe_kb(missing))


def _shown_channels(event: CallbackQuery) -> int:
    """Bosilgan xabarda nechta kanal tugmasi turganini sanaydi."""
    markup = getattr(event.message, "reply_markup", None)
    if markup is None:
        return -1
    return sum(1 for row in markup.inline_keyboard for btn in row if btn.url)


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if _skip(event):
            return await handler(event, data)

        bot: Bot = data["bot"]
        missing = await check_subscription(bot, event.from_user.id)
        if not missing:
            return await handler(event, data)

        chat_id = _chat_id(event)
        if isinstance(event, CallbackQuery):
            await event.answer(NOT_SUBSCRIBED, show_alert=True)
            # ro'yxat o'zgarmagan bo'lsa xabarni qayta yubormaymiz
            if _shown_channels(event) == len(missing):
                return None
            if event.message:
                with suppress(TelegramBadRequest):
                    await event.message.delete()

        if chat_id is not None:
            await send_sub_prompt(bot, chat_id, missing)
        return None


class PhoneMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if _skip(event):
            return await handler(event, data)
        # kontakt xabarining o'zi o'tib ketishi kerak
        if isinstance(event, Message) and event.contact:
            return await handler(event, data)

        db_user = data.get("db_user")
        if db_user is not None and db_user.phone:
            return await handler(event, data)
        if not await is_phone_required():
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer(PHONE_ALERT, show_alert=True)

        bot: Bot = data["bot"]
        chat_id = _chat_id(event)
        if chat_id is not None:
            await bot.send_message(chat_id, PHONE_TEXT, reply_markup=phone_kb())
        return None
