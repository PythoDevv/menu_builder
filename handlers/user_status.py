"""Foydalanuvchi botni bloklasa / blokdan chiqarsa — holatini darhol yangilaymiz.

Telegram buni shaxsiy chatdagi `my_chat_member` update orqali xabar qiladi.
Shu tufayli "Faol" / "Bloklaganlar" soni keyingi rassilkani kutmay to'g'ri turadi.
Bu update foydalanuvchi yaratmaydi — faqat bazada borini yangilaydi.
"""

import logging

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated

from db.queries import set_user_inactive, set_user_reachable
from utils.user_status import BLOCKED

router = Router()
logger = logging.getLogger(__name__)


@router.my_chat_member(F.chat.type == "private")
async def on_private_status(event: ChatMemberUpdated) -> None:
    status = event.new_chat_member.status
    user_id = event.from_user.id
    if status == ChatMemberStatus.KICKED:
        await set_user_inactive(user_id, BLOCKED)
        logger.info("Botni blokladi: %s", user_id)
    elif status == ChatMemberStatus.MEMBER:
        await set_user_reachable(user_id)
        logger.info("Blokdan chiqardi: %s", user_id)
