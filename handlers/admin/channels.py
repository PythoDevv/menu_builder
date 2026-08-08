from html import escape

from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, MessageOriginChannel, MessageOriginChat

from db.queries import add_channel, delete_channel, get_channel, get_channels, toggle_channel
from handlers.admin.common import admin_router, edit_or_send
from handlers.admin.states import ChannelSG
from keyboards.admin_kb import (
    cancel_kb,
    channel_delete_kb,
    channel_one_kb,
    channel_type_kb,
    channels_kb,
)
from utils.subscription import clear_cache

router = admin_router()

LIST_TEXT = (
    "📢 <b>Kanallar</b>\n\n"
    "Foydalanuvchi botdan foydalanishi uchun shu kanallarga obuna bo'lishi kerak.\n"
    "🟢 — faol, 🔴 — o'chirilgan, 📢 — ochiq, 🔒 — yopiq"
)

ADD_TEXT = (
    "➕ <b>Kanal qo'shish</b>\n\n"
    "Kanaldan istalgan postni shu yerga <b>forward</b> qiling,\n"
    "yoki <code>@username</code> / <code>-1001234567890</code> ko'rinishida yuboring.\n\n"
    "⚠️ Bot o'sha kanalda <b>admin</b> bo'lishi shart."
)


async def _show_list(callback: CallbackQuery) -> None:
    channels = await get_channels()
    await edit_or_send(callback, LIST_TEXT, channels_kb(channels))


@router.callback_query(F.data == "ch:list")
async def cb_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_list(callback)
    await callback.answer()


async def _show_one(callback: CallbackQuery, channel_id: int) -> None:
    ch = await get_channel(channel_id)
    if ch is None:
        await _show_list(callback)
        return
    text = (
        f"{'🔒 Yopiq' if ch.is_private else '📢 Ochiq'} kanal\n\n"
        f"<b>{escape(ch.title)}</b>\n"
        f"ID: <code>{ch.chat_id}</code>\n"
        f"Username: {('@' + ch.username) if ch.username else '—'}\n"
        f"Havola: {ch.invite_link or '—'}\n"
        f"Holat: {'🟢 faol' if ch.is_active else '🔴 o‘chirilgan'}"
    )
    await edit_or_send(callback, text, channel_one_kb(ch))


@router.callback_query(F.data.startswith("ch:one:"))
async def cb_one(callback: CallbackQuery) -> None:
    await _show_one(callback, int(callback.data.split(":")[2]))
    await callback.answer()


@router.callback_query(F.data.startswith("ch:tog:"))
async def cb_toggle(callback: CallbackQuery) -> None:
    channel_id = int(callback.data.split(":")[2])
    await toggle_channel(channel_id)
    clear_cache()
    await callback.answer("✅ O'zgartirildi")
    await _show_one(callback, channel_id)


@router.callback_query(F.data.startswith("ch:del:"))
async def cb_delete_ask(callback: CallbackQuery) -> None:
    channel_id = int(callback.data.split(":")[2])
    await edit_or_send(
        callback, "🗑 Kanal ro'yxatdan o'chirilsinmi?", channel_delete_kb(channel_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ch:delok:"))
async def cb_delete(callback: CallbackQuery) -> None:
    await delete_channel(int(callback.data.split(":")[2]))
    clear_cache()
    await callback.answer("🗑 O'chirildi")
    await _show_list(callback)


# ------------------------------------------------------------------- qo'shish
@router.callback_query(F.data == "ch:add")
async def cb_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ChannelSG.waiting_chat)
    await edit_or_send(callback, ADD_TEXT, cancel_kb())
    await callback.answer()


def _parse_target(message: Message):
    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        return origin.chat.id
    if isinstance(origin, MessageOriginChat):
        return origin.sender_chat.id

    text = (message.text or "").strip()
    if not text:
        return None
    if "t.me/" in text:
        text = "@" + text.rstrip("/").rsplit("/", 1)[-1]
    if text.startswith("@"):
        return text
    if text.lstrip("-").isdigit():
        return int(text)
    return None


@router.message(ChannelSG.waiting_chat)
async def add_channel_step(message: Message, state: FSMContext) -> None:
    target = _parse_target(message)
    if target is None:
        await message.answer(
            "❗️ Tushunarsiz. Kanaldan post forward qiling yoki @username yuboring.",
            reply_markup=cancel_kb(),
        )
        return

    try:
        chat = await message.bot.get_chat(target)
    except TelegramAPIError:
        await message.answer(
            "❗️ Kanal topilmadi. Bot kanalda admin ekanligiga ishonch hosil qiling.",
            reply_markup=cancel_kb(),
        )
        return

    try:
        me = await message.bot.get_chat_member(chat.id, message.bot.id)
        is_admin = me.status in ("administrator", "creator")
    except TelegramAPIError:
        is_admin = False

    if not is_admin:
        await message.answer(
            "❗️ Bot bu kanalda admin emas. Avval admin qiling, so'ng qayta urinib ko'ring.",
            reply_markup=cancel_kb(),
        )
        return

    await state.update_data(
        chat_id=chat.id,
        title=chat.title or str(chat.id),
        username=chat.username,
        invite_link=chat.invite_link,
    )
    await state.set_state(ChannelSG.waiting_type)
    await message.answer(
        f"✅ <b>{escape(chat.title or str(chat.id))}</b> topildi.\n\nKanal turini tanlang:",
        reply_markup=channel_type_kb(),
    )


@router.callback_query(ChannelSG.waiting_type, F.data.startswith("ch:type:"))
async def add_channel_type(callback: CallbackQuery, state: FSMContext) -> None:
    is_private = callback.data.split(":")[2] == "private"
    data = await state.get_data()
    chat_id = data["chat_id"]
    username = data.get("username")
    invite_link = data.get("invite_link")

    if is_private or not username:
        try:
            link = await callback.bot.create_chat_invite_link(
                chat_id,
                name="Bot obuna",
                creates_join_request=is_private,
            )
            invite_link = link.invite_link
        except TelegramAPIError:
            pass  # eski havoladan foydalanamiz

    if not username and not invite_link:
        await callback.answer(
            "❗️ Havola olinmadi. Botga 'Invite Users via Link' huquqini bering.",
            show_alert=True,
        )
        return

    await add_channel(
        chat_id=chat_id,
        title=data["title"],
        username=username,
        invite_link=invite_link,
        is_private=is_private,
    )
    clear_cache()
    await state.clear()
    await callback.answer("✅ Kanal qo'shildi")
    await _show_list(callback)
