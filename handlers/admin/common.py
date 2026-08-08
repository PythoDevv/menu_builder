from contextlib import suppress
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from config import ADMINS
from keyboards.admin_kb import admin_home_kb

HOME_TEXT = "👑 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:"


def admin_router() -> Router:
    """Faqat adminlar uchun router."""
    router = Router()
    router.message.filter(F.from_user.id.in_(ADMINS))
    router.callback_query.filter(F.from_user.id.in_(ADMINS))
    return router


async def edit_or_send(
    callback: CallbackQuery, text: str, kb: Optional[InlineKeyboardMarkup] = None
) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=kb)
        return
    except TelegramBadRequest as e:
        if "not modified" in str(e):
            return
    with suppress(TelegramBadRequest):
        await callback.message.delete()
    await callback.bot.send_message(callback.message.chat.id, text, reply_markup=kb)


async def show_home(callback: CallbackQuery) -> None:
    await edit_or_send(callback, HOME_TEXT, admin_home_kb())
