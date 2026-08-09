"""Bot kanalga admin qilinganda — o'sha adminning o'ziga tasdiq so'rovi.

Telegram bot kanalda admin bo'lganini `my_chat_member` orqali xabar qiladi.
Bildirishnoma **faqat botni admin qilgan odamga** boradi va u ham botning
tasdiqlangan admini bo'lsagina. Boshqa adminlarga hech narsa yuborilmaydi —
kim qo'shgan bo'lsa, o'sha hal qiladi.

Tasdiqlansa kanal turi avtomatik aniqlanadi: username bor -> 📢 ochiq,
yo'q -> 🔒 yopiq (qo'shilish so'rovli havola ochiladi).
"""

import logging
from contextlib import suppress
from html import escape
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, ChatMemberUpdated

from db.queries import add_channel, get_channel_by_chat_id
from keyboards.admin_kb import CB_NEW_CH_ADD, CB_NEW_CH_SKIP, new_channel_kb
from utils.admins import is_admin
from utils.channels import (
    ADMIN_STATUSES,
    detect_private,
    is_bot_admin,
    resolve_invite_link,
)
from utils.subscription import clear_cache

router = Router()
logger = logging.getLogger(__name__)

NOT_ADMIN = "❗️ Sizda ruxsat yo'q"


def _kind(is_private: bool) -> str:
    return "🔒 Yopiq (qo'shilish so'rovi)" if is_private else "📢 Ochiq"


@router.my_chat_member(F.chat.type == "channel")
async def on_bot_promoted(event: ChatMemberUpdated, bot: Bot) -> None:
    # faqat "admin emas edi -> admin bo'ldi" holati. Huquqlari o'zgarganda
    # (admin -> admin) qayta so'ramaymiz.
    if event.old_chat_member.status in ADMIN_STATUSES:
        return
    if event.new_chat_member.status not in ADMIN_STATUSES:
        return

    actor = event.from_user
    if actor is None or not is_admin(actor.id):
        logger.info(
            "Kanalga admin qilindi (%s), lekin %s botning admini emas — so'ralmadi",
            event.chat.id,
            actor.id if actor else "?",
        )
        return

    if await get_channel_by_chat_id(event.chat.id) is not None:
        logger.info("Kanal allaqachon ro'yxatda: %s", event.chat.id)
        return

    title = event.chat.title or str(event.chat.id)
    is_private = detect_private(event.chat)
    with suppress(TelegramAPIError):
        await bot.send_message(
            actor.id,
            "🆕 <b>Yangi kanal</b>\n\n"
            f"Bot <b>{escape(title)}</b> kanalida admin qilindi.\n"
            f"Turi: {_kind(is_private)}\n"
            f"ID: <code>{event.chat.id}</code>\n\n"
            "Majburiy obuna ro'yxatiga qo'shilsinmi?",
            reply_markup=new_channel_kb(event.chat.id),
        )


def _chat_id(data: Optional[str]) -> Optional[int]:
    raw = (data or "").rsplit(":", 1)[-1]
    return int(raw) if raw.lstrip("-").isdigit() else None


async def _finish(callback: CallbackQuery, bot: Bot, text: str) -> None:
    """Tugmalarni olib tashlab, natijani xabarning o'ziga yozadi.

    `callback.message` eskirgan bo'lsa `InaccessibleMessage` keladi — unda
    `edit_text` yo'q, shuning uchun bot orqali tahrirlaymiz.
    """
    if callback.message is None:
        return
    with suppress(TelegramAPIError):
        await bot.edit_message_text(
            text,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )


@router.callback_query(F.data.startswith(CB_NEW_CH_ADD + ":"))
async def confirm_add(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(NOT_ADMIN, show_alert=True)
        return

    chat_id = _chat_id(callback.data)
    if chat_id is None:
        await callback.answer()
        return

    try:
        chat = await bot.get_chat(chat_id)
    except TelegramAPIError:
        await callback.answer("❗️ Kanal topilmadi", show_alert=True)
        await _finish(callback, bot, "❗️ Kanal topilmadi — u o'chirilgan bo'lishi mumkin.")
        return

    if not await is_bot_admin(bot, chat_id):
        await callback.answer("❗️ Bot bu kanalda admin emas", show_alert=True)
        await _finish(
            callback,
            bot,
            "❗️ Bot bu kanalda endi admin emas. Admin qilib, qaytadan urinib ko'ring.",
        )
        return

    is_private = detect_private(chat)
    invite_link = await resolve_invite_link(
        bot, chat_id, chat.username, chat.invite_link, is_private
    )
    if not chat.username and not invite_link:
        await callback.answer("❗️ Havola olinmadi", show_alert=True)
        await _finish(
            callback,
            bot,
            "❗️ Havola olinmadi. Botga <b>'Invite Users via Link'</b> huquqini bering "
            "va qaytadan urinib ko'ring.",
        )
        return

    title = chat.title or str(chat_id)
    await add_channel(
        chat_id=chat_id,
        title=title,
        username=chat.username,
        invite_link=invite_link,
        is_private=is_private,
    )
    clear_cache()
    logger.info("Kanal qo'shildi: %s (%s), admin: %s", title, chat_id, callback.from_user.id)

    await callback.answer("✅ Qo'shildi")
    await _finish(
        callback,
        bot,
        f"✅ <b>{escape(title)}</b> majburiy obuna ro'yxatiga qo'shildi.\n"
        f"Turi: {_kind(is_private)}\n\n"
        "<i>Sozlash uchun: /admin → 📢 Kanallar</i>",
    )


@router.callback_query(F.data.startswith(CB_NEW_CH_SKIP + ":"))
async def skip_add(callback: CallbackQuery, bot: Bot) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(NOT_ADMIN, show_alert=True)
        return
    await callback.answer("❌ Bekor qilindi")
    await _finish(
        callback,
        bot,
        "❌ Kanal qo'shilmadi.\n\n"
        "<i>Keyinroq qo'shmoqchi bo'lsangiz: /admin → 📢 Kanallar → ➕ Kanal qo'shish</i>",
    )
