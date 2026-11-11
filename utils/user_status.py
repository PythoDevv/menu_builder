"""Foydalanuvchiga xabar nega yetib bormasligini Telegram xatosidan aniqlash.

Telegram `403 Forbidden` ni uch xil holatda qaytaradi, matni bilan ajratiladi:

* ``bot was blocked by the user``               -> botni bloklagan
* ``user is deactivated``                       -> akkaunt o'chirilgan
* ``bot can't initiate conversation with a user`` -> botda /start bosmagan

``not_started`` — botni hech qachon ochmagan odam (masalan, faqat yopiq kanalga
zayafka tashlagan). Ular foydalanuvchi hisoblanmaydi va statistikaga kirmaydi.
"""

from typing import Optional

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

BLOCKED = "blocked"
DEACTIVATED = "deactivated"
NOT_STARTED = "not_started"


def inactive_reason(exc: Exception) -> Optional[str]:
    """Xato foydalanuvchiga yozib bo'lmasligini bildirsa — sababini qaytaradi.

    Vaqtinchalik / boshqa xatolar uchun ``None`` (foydalanuvchi holati o'zgarmaydi).
    """
    text = str(exc).lower()
    if isinstance(exc, TelegramForbiddenError):
        if "deactivated" in text:
            return DEACTIVATED
        if "can't initiate" in text or "can not initiate" in text:
            return NOT_STARTED
        return BLOCKED
    if isinstance(exc, TelegramBadRequest) and "chat not found" in text:
        return NOT_STARTED
    return None
