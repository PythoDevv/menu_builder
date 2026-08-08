"""Obuna va telefon tekshiruvi. Ikkalasi ham outer middleware sifatida ishlaydi."""

from contextlib import suppress
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, TelegramObject

from db.queries import is_phone_required
from keyboards.user_kb import phone_kb, subscribe_kb
from utils.admins import is_admin
from utils.subscription import check_subscription

SUB_TEXT = (
    "👋 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling.\n\n"
    "So'ng <b>✅ Tekshirish</b> tugmasini bosing."
)
PHONE_TEXT = (
    "📱 Davom etish uchun telefon raqamingizni yuboring.\n\n"
    "Pastdagi <b>📱 Raqamni yuborish</b> tugmasini bosing."
)


def _private_chat(event: TelegramObject) -> bool:
    if isinstance(event, Message):
        return event.chat.type == "private"
    if isinstance(event, CallbackQuery) and event.message:
        return event.message.chat.type == "private"
    return False


async def _reply(event: TelegramObject, bot: Bot, text: str, kb: InlineKeyboardMarkup) -> None:
    """Callback bo'lsa xabarni tahrirlashga urinadi, bo'lmasa yangisini yuboradi."""
    if isinstance(event, CallbackQuery) and event.message:
        try:
            await event.message.edit_text(text, reply_markup=kb)
            return
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return  # xabar allaqachon shunday — hech narsa qilmaymiz
        with suppress(TelegramBadRequest):
            await event.message.delete()
        await bot.send_message(event.message.chat.id, text, reply_markup=kb)
    elif isinstance(event, Message):
        await event.answer(text, reply_markup=kb)


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        bot: Bot = data["bot"]

        if user is None or is_admin(user.id) or not _private_chat(event):
            return await handler(event, data)

        missing = await check_subscription(bot, user.id)
        if not missing:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer("❗️ Siz hali barcha kanallarga qo'shilmadingiz", show_alert=True)
        await _reply(event, bot, SUB_TEXT, subscribe_kb(missing))
        return None


class PhoneMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        db_user = data.get("db_user")

        if user is None or is_admin(user.id) or not _private_chat(event):
            return await handler(event, data)
        # kontakt xabarining o'zi o'tib ketishi kerak
        if isinstance(event, Message) and event.contact:
            return await handler(event, data)
        if db_user is not None and db_user.phone:
            return await handler(event, data)
        if not await is_phone_required():
            return await handler(event, data)

        bot: Bot = data["bot"]
        if isinstance(event, CallbackQuery):
            await event.answer("📱 Avval telefon raqamingizni yuboring", show_alert=True)
            chat_id = event.message.chat.id if event.message else user.id
        else:
            chat_id = event.chat.id
        await bot.send_message(chat_id, PHONE_TEXT, reply_markup=phone_kb())
        return None
