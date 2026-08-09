"""Foydalanuvchi tomonidagi klaviaturalar.

Menyu — reply (pastdagi) tugmalar.
Majburiy obuna — inline: reply tugmaga kanal havolasini (URL) qo'yib bo'lmaydi.
"""

from typing import Sequence, Union

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from db.models import Channel, MenuItem

BTN_BACK = "⬅️ Orqaga"
BTN_HOME = "🏠 Bosh menyu"
BTN_CHECK_SUB = "✅ Tekshirish"
BTN_PHONE = "📱 Raqamni yuborish"

CB_CHECK_SUB = "check_sub"

# Shu belgidan qisqa nomlar bir qatorga ikkitadan joylashtiriladi
SHORT_TITLE = 18

Keyboard = Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]


def _rows(titles: Sequence[str]) -> list[list[KeyboardButton]]:
    per_row = 2 if titles and all(len(t) <= SHORT_TITLE for t in titles) else 1
    return [
        [KeyboardButton(text=t) for t in titles[i : i + per_row]]
        for i in range(0, len(titles), per_row)
    ]


def menu_kb(children: list[MenuItem], is_root: bool) -> Keyboard:
    """Menyu tugmalari. Ildizda 'Orqaga' kerak emas."""
    rows = _rows([c.title for c in children])
    if not is_root:
        rows.append([KeyboardButton(text=BTN_BACK), KeyboardButton(text=BTN_HOME)])
    if not rows:
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Tugmani tanlang",
    )


def channel_url(ch: Channel) -> str:
    """Yopiq kanalda zayafkali havola, ochiq kanalda @username afzal."""
    public = f"https://t.me/{ch.username}" if ch.username else None
    return (ch.invite_link or public) if ch.is_private else (public or ch.invite_link)


def subscribe_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    """Kanal havolalari + tekshirish tugmasi (inline)."""
    rows = []
    for ch in channels:
        url = channel_url(ch)
        if not url:
            continue
        prefix = "🔒" if ch.is_private else "📢"
        rows.append([InlineKeyboardButton(text=f"{prefix} {ch.title}", url=url)])
    rows.append([InlineKeyboardButton(text=BTN_CHECK_SUB, callback_data=CB_CHECK_SUB)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_PHONE, request_contact=True)]],
        resize_keyboard=True,
        input_field_placeholder="Raqamni tugma orqali yuboring",
    )
