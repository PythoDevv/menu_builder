"""Foydalanuvchi tomonidagi klaviaturalar.

Menyu — reply (pastdagi) tugmalar.
Majburiy obuna — inline: reply tugmaga kanal havolasini (URL) qo'yib bo'lmaydi.
"""

from typing import Union

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

Keyboard = Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]


def _menu_rows(children: list[MenuItem]) -> list[list[KeyboardButton]]:
    """Faqat ketma-ket kelgan ikkita 2-lik tugmani bir qatorga joylaydi."""
    rows: list[list[KeyboardButton]] = []
    index = 0
    while index < len(children):
        item = children[index]
        row = [KeyboardButton(text=item.title)]
        next_item = children[index + 1] if index + 1 < len(children) else None
        if (
            item.buttons_per_row == 2
            and next_item is not None
            and next_item.buttons_per_row == 2
        ):
            row.append(KeyboardButton(text=next_item.title))
            index += 1
        rows.append(row)
        index += 1
    return rows


def menu_kb(children: list[MenuItem], is_root: bool) -> Keyboard:
    """Menyu tugmalari. Ildizda 'Orqaga' kerak emas."""
    rows = _menu_rows(children)
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
