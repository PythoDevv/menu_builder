"""Kanalni ro'yxatga olishdagi umumiy qadamlar.

Ikki joyda kerak bo'ladi: paneldan qo'lda qo'shishda (`handlers/admin/channels.py`)
va bot kanalga admin qilinganda avtomatik so'raladigan tasdiqda
(`handlers/admin/channel_events.py`).
"""

from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Chat

#: Bot kanalda "admin" hisoblanadigan holatlar
ADMIN_STATUSES = ("administrator", "creator")


async def is_bot_admin(bot: Bot, chat_id: int) -> bool:
    try:
        me = await bot.get_chat_member(chat_id, bot.id)
    except TelegramAPIError:
        return False
    return me.status in ADMIN_STATUSES


def detect_private(chat: Chat) -> bool:
    """Kanal turi: username bo'lsa ochiq, bo'lmasa yopiq (qo'shilish so'rovli)."""
    return not chat.username


async def resolve_invite_link(
    bot: Bot,
    chat_id: int,
    username: Optional[str],
    invite_link: Optional[str],
    is_private: bool,
) -> Optional[str]:
    """Kerak bo'lsa botning o'z havolasini ochadi.

    Ochiq kanalda username yetarli, lekin u yo'q bo'lsa ham havola kerak.
    Yopiq kanalda havola `creates_join_request=True` bilan ochiladi.
    """
    if is_private or not username:
        try:
            link = await bot.create_chat_invite_link(
                chat_id,
                name="Bot obuna",
                creates_join_request=is_private,
            )
            return link.invite_link
        except TelegramAPIError:
            pass  # huquq yo'q -> eski havoladan foydalanamiz
    return invite_link
