from typing import Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from db.models import Channel, MenuItem


def subscribe_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        if ch.username:
            url = f"https://t.me/{ch.username}"
        else:
            url = ch.invite_link
        if not url:
            continue
        prefix = "🔒" if ch.is_private else "📢"
        rows.append([InlineKeyboardButton(text=f"{prefix} {ch.title}", url=url)])
    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def nav_kb(children: list[MenuItem], back_to: Optional[str]) -> InlineKeyboardMarkup:
    """back_to: 'root' / '<parent_id>' / None (asosiy menyuda orqaga kerak emas)."""
    rows = [
        [InlineKeyboardButton(text=item.title, callback_data=f"nav:{item.id}")]
        for item in children
    ]
    if back_to is not None:
        bottom = [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"nav:{back_to}")]
        if back_to != "root":
            bottom.append(InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="nav:root"))
        rows.append(bottom)
    return InlineKeyboardMarkup(inline_keyboard=rows)
