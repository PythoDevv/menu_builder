from contextlib import suppress
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from db.queries import get_contents, get_item, get_items
from keyboards.user_kb import nav_kb
from utils.content import send_content

router = Router()

MENU_TEXT = "🏠 Asosiy menyu"
EMPTY_TEXT = "⚠️ Hozircha menyu bo'sh."


async def _render(callback: CallbackQuery, text: str, kb: InlineKeyboardMarkup) -> None:
    """Mavjud xabarni tahrirlaydi; bo'lmasa o'chirib yangisini yuboradi."""
    try:
        await callback.message.edit_text(text, reply_markup=kb)
        return
    except TelegramBadRequest as e:
        if "not modified" in str(e):
            return
    with suppress(TelegramBadRequest):
        await callback.message.delete()
    await callback.bot.send_message(callback.message.chat.id, text, reply_markup=kb)


@router.callback_query(F.data.startswith("nav:"))
async def navigate(callback: CallbackQuery) -> None:
    raw = callback.data.split(":", 1)[1]

    if raw == "root":
        item = None
        item_id = None
    else:
        item_id = int(raw)
        item = await get_item(item_id)
        if item is None or not item.is_active:
            await callback.answer("❗️ Bu bo'lim mavjud emas", show_alert=True)
            return

    children = await get_items(item_id, active_only=True)
    contents = await get_contents(item_id) if item_id is not None else []

    if item is None:
        back_to = None
        text = MENU_TEXT if children else EMPTY_TEXT
    else:
        back_to = "root" if item.parent_id is None else str(item.parent_id)
        text = f"<b>{escape(item.title)}</b>"

    kb = nav_kb(children, back_to)

    if contents:
        with suppress(TelegramBadRequest):
            await callback.message.delete()
        last = len(contents) - 1
        for i, content in enumerate(contents):
            await send_content(
                callback.bot,
                callback.message.chat.id,
                content,
                reply_markup=kb if i == last else None,
            )
    elif children or back_to is not None:
        await _render(callback, text, kb)
    else:
        await callback.answer("ℹ️ Bu bo'limda hozircha ma'lumot yo'q", show_alert=True)
        return

    await callback.answer()
