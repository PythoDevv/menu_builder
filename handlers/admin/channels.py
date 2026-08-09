from html import escape
from typing import Optional

from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, MessageOriginChannel, MessageOriginChat

from db.queries import add_channel, delete_channel, get_channel, get_channels, toggle_channel
from handlers.admin.common import (
    KEY_ITEM,
    NOT_COMMAND,
    PICK_TEXT,
    admin_router,
    pick_label,
    save_labels,
)
from handlers.admin.states import ChannelSG, PanelSG
from keyboards.admin_kb import (
    BTN_CH_ADD,
    BTN_CH_DISABLE,
    BTN_CH_ENABLE,
    BTN_CH_LIST,
    BTN_CH_PRIVATE,
    BTN_CH_PUBLIC,
    BTN_CHANNELS,
    BTN_DELETE,
    BTN_NO,
    BTN_YES_DELETE,
    cancel_kb,
    channel_label,
    channel_one_kb,
    channel_type_kb,
    channels_kb,
    confirm_delete_kb,
)
from utils.subscription import clear_cache

router = admin_router()

LIST_TEXT = (
    "📢 <b>Kanallar</b>\n\n"
    "Foydalanuvchi botdan foydalanishi uchun shu kanallarga obuna bo'lishi kerak.\n"
    "🟢 — faol, 🔴 — o'chirilgan, 📢 — ochiq, 🔒 — yopiq\n\n"
    "<i>Kanal ustiga bosing — sozlamalari ochiladi.</i>"
)

ADD_TEXT = (
    "➕ <b>Kanal qo'shish</b>\n\n"
    "Kanaldan istalgan postni shu yerga <b>forward</b> qiling,\n"
    "yoki <code>@username</code> / <code>-1001234567890</code> ko'rinishida yuboring.\n\n"
    "⚠️ Bot o'sha kanalda <b>admin</b> bo'lishi shart."
)


async def show_list(message: Message, state: FSMContext) -> None:
    channels = await get_channels()
    labels = {channel_label(ch, i): ch.id for i, ch in enumerate(channels, start=1)}
    await state.set_state(ChannelSG.browse)
    await save_labels(state, labels)
    text = LIST_TEXT if channels else "📢 <b>Kanallar</b>\n\nHozircha kanal qo'shilmagan."
    await message.answer(text, reply_markup=channels_kb(list(labels)))


async def show_one(message: Message, state: FSMContext, channel_id: Optional[int]) -> None:
    ch = await get_channel(channel_id) if channel_id is not None else None
    if ch is None:
        await show_list(message, state)
        return
    await state.set_state(ChannelSG.one)
    await state.update_data({KEY_ITEM: ch.id})
    await message.answer(
        f"{'🔒 Yopiq' if ch.is_private else '📢 Ochiq'} kanal\n\n"
        f"<b>{escape(ch.title)}</b>\n"
        f"ID: <code>{ch.chat_id}</code>\n"
        f"Username: {('@' + ch.username) if ch.username else '—'}\n"
        f"Havola: {ch.invite_link or '—'}\n"
        f"Holat: {'🟢 faol' if ch.is_active else '🔴 o‘chirilgan'}",
        reply_markup=channel_one_kb(ch),
    )


@router.message(PanelSG.home, F.text == BTN_CHANNELS)
async def open_list(message: Message, state: FSMContext) -> None:
    await show_list(message, state)


# ------------------------------------------------------------------------ ro'yxat
@router.message(ChannelSG.browse, F.text == BTN_CH_ADD)
async def ask_channel(message: Message, state: FSMContext) -> None:
    await state.set_state(ChannelSG.waiting_chat)
    await message.answer(ADD_TEXT, reply_markup=cancel_kb())


@router.message(ChannelSG.browse)
async def pick_channel(message: Message, state: FSMContext) -> None:
    channel_id = await pick_label(state, message.text)
    if channel_id is None:
        await message.answer(PICK_TEXT)
        return
    await show_one(message, state, channel_id)


# -------------------------------------------------------------------- bitta kanal
@router.message(ChannelSG.one, F.text.in_({BTN_CH_ENABLE, BTN_CH_DISABLE}))
async def toggle(message: Message, state: FSMContext) -> None:
    channel_id = (await state.get_data()).get(KEY_ITEM)
    if channel_id is not None:
        await toggle_channel(channel_id)
        clear_cache()
        await message.answer("✅ O'zgartirildi")
    await show_one(message, state, channel_id)


@router.message(ChannelSG.one, F.text == BTN_DELETE)
async def delete_ask(message: Message, state: FSMContext) -> None:
    await state.set_state(ChannelSG.confirm_delete)
    await message.answer("🗑 Kanal ro'yxatdan o'chirilsinmi?", reply_markup=confirm_delete_kb())


@router.message(ChannelSG.one, F.text == BTN_CH_LIST)
async def back_to_list(message: Message, state: FSMContext) -> None:
    await show_list(message, state)


@router.message(ChannelSG.confirm_delete, F.text == BTN_YES_DELETE)
async def delete_ok(message: Message, state: FSMContext) -> None:
    channel_id = (await state.get_data()).get(KEY_ITEM)
    if channel_id is not None:
        await delete_channel(channel_id)
        clear_cache()
        await message.answer("🗑 O'chirildi")
    await show_list(message, state)


@router.message(ChannelSG.confirm_delete, F.text == BTN_NO)
async def delete_no(message: Message, state: FSMContext) -> None:
    await show_one(message, state, (await state.get_data()).get(KEY_ITEM))


# ------------------------------------------------------------------------ qo'shish
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


@router.message(ChannelSG.waiting_chat, NOT_COMMAND)
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


@router.message(ChannelSG.waiting_type, F.text.in_({BTN_CH_PUBLIC, BTN_CH_PRIVATE}))
async def add_channel_type(message: Message, state: FSMContext) -> None:
    is_private = message.text == BTN_CH_PRIVATE
    data = await state.get_data()
    chat_id = data["chat_id"]
    username = data.get("username")
    invite_link = data.get("invite_link")

    if is_private or not username:
        try:
            link = await message.bot.create_chat_invite_link(
                chat_id,
                name="Bot obuna",
                creates_join_request=is_private,
            )
            invite_link = link.invite_link
        except TelegramAPIError:
            pass  # eski havoladan foydalanamiz

    if not username and not invite_link:
        await message.answer(
            "❗️ Havola olinmadi. Botga 'Invite Users via Link' huquqini bering.",
            reply_markup=channel_type_kb(),
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
    await message.answer("✅ Kanal qo'shildi")
    await show_list(message, state)
