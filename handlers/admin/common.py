from contextlib import suppress
from typing import Optional

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, TelegramObject

from keyboards.admin_kb import admin_home_kb
from utils.admins import is_admin

HOME_TEXT = "👑 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:"


class IsAdmin(BaseFilter):
    """Ro'yxat xotirada (utils.admins), shuning uchun bazaga murojaat yo'q."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and is_admin(user.id)


def admin_router() -> Router:
    """Faqat adminlar uchun router."""
    router = Router()
    router.message.filter(IsAdmin())
    router.callback_query.filter(IsAdmin())
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
