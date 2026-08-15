"""Taklif (referal) tizimi: havola, `/start` payload va matn shabloni.

Havola: `https://t.me/<bot>?start=ref<tg_id>`
Payload middlewarada o'qiladi (obuna tekshiruvidan oldin), shuning uchun
foydalanuvchi kanalga obuna bo'lmagan bo'lsa ham taklif yo'qolmaydi.
"""

from html import escape
from typing import Optional
from urllib.parse import quote

from aiogram import Bot

#: `/start` payload prefiksi — `ref123456789`
REF_PREFIX = "ref"

#: Admin matnida ishlatishi mumkin bo'lgan o'rinbosarlar
PLACEHOLDERS = ("{title}", "{need}", "{count}", "{left}", "{link}")

SHARE_TEXT = "Bu botga qo'shiling 👇"

#: bot username har safar so'ralmasin
_username: Optional[str] = None


def parse_ref_payload(payload: Optional[str]) -> Optional[int]:
    """`ref123` -> 123. Boshqa payload yoki noto'g'ri format -> None."""
    if not payload or not payload.startswith(REF_PREFIX):
        return None
    digits = payload[len(REF_PREFIX) :]
    return int(digits) if digits.isdigit() else None


async def bot_username(bot: Bot) -> str:
    global _username
    if _username is None:
        me = await bot.get_me()
        _username = me.username or ""
    return _username


async def ref_link(bot: Bot, tg_id: int) -> str:
    return f"https://t.me/{await bot_username(bot)}?start={REF_PREFIX}{tg_id}"


def share_url(link: str, text: str = SHARE_TEXT) -> str:
    """Telegramning 'ulashish' oynasini ochadigan havola."""
    return f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(text, safe='')}"


def render_ref_text(template: str, *, title: str, need: int, count: int, link: str) -> str:
    """Shablondagi o'rinbosarlarni to'ldiradi.

    `str.format()` ishlatilmaydi — admin matnida tasodifiy `{` bo'lsa xato bermasin.
    Havola matn ichida bo'lmasa, oxiriga qo'shib qo'yiladi (aks holda foydalanuvchi
    havolani umuman ko'rmay qoladi).
    """
    values = {
        "{title}": escape(title),
        "{need}": str(need),
        "{count}": str(count),
        "{left}": str(max(need - count, 0)),
        "{link}": link,
    }
    text = template
    for key, value in values.items():
        text = text.replace(key, value)
    if "{link}" not in template:
        text += f"\n\n👇 Sizning havolangiz:\n{link}"
    return text
