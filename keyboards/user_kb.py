"""Foydalanuvchi tomonidagi klaviaturalar.

Menyu — reply (pastdagi) tugmalar.
Majburiy obuna — inline: reply tugmaga kanal havolasini (URL) qo'yib bo'lmaydi.
"""

from typing import Optional, Sequence, Union

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from db.models import Channel, MenuItem
from db.queries import DEFAULT_MY_POINTS_TEXT
from utils.referral import share_url

BTN_BACK = "⬅️ Orqaga"
BTN_HOME = "🏠 Bosh menyu"
BTN_CHECK_SUB = "✅ Tekshirish"
BTN_PHONE = "📱 Raqamni yuborish"
BTN_SHARE = "📤 Do'stlarga yuborish"
BTN_MY_POINTS = DEFAULT_MY_POINTS_TEXT

CB_CHECK_SUB = "check_sub"

#: Menyu ustunlari soni (admin paneldan boshqariladi)
COLUMNS_ONE = 1
COLUMNS_TWO = 2
DEFAULT_COLUMNS = COLUMNS_TWO

Keyboard = Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]


def _menu_button(item: MenuItem) -> KeyboardButton:
    return KeyboardButton(text=item.title, style=item.button_style)


def _rows(items: Sequence[MenuItem], columns: int) -> list[list[KeyboardButton]]:
    """Tanlangan ustun soniga ko'ra tugmalarni qatorlarga joylaydi."""
    rows: list[list[MenuItem]] = []
    pending: Optional[MenuItem] = None

    for item in items:
        if columns < COLUMNS_TWO:
            if pending is not None:
                rows.append([pending])
                pending = None
            rows.append([item])
        elif pending is None:
            pending = item
        else:
            rows.append([pending, item])
            pending = None

    if pending is not None:
        rows.append([pending])
    return [[_menu_button(item) for item in row] for row in rows]


def menu_kb(
    children: list[MenuItem],
    is_root: bool,
    columns: int = DEFAULT_COLUMNS,
    my_points_enabled: bool = True,
    my_points_text: str = BTN_MY_POINTS,
    my_points_style: Optional[str] = None,
) -> Keyboard:
    """Menyu tugmalari. Ildizda 'Orqaga' kerak emas, 'Ballarim' esa faqat ildizda bor."""
    rows = _rows(children, columns)
    if is_root:
        if my_points_enabled:
            rows.append([KeyboardButton(text=my_points_text, style=my_points_style)])
    else:
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


def share_kb(link: str) -> InlineKeyboardMarkup:
    """Taklif havolasini ulashish — inline, chunki reply tugmaga URL qo'yilmaydi.

    Menyu klaviaturasi joyida qoladi: xabar inline tugma bilan yuboriladi.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_SHARE, url=share_url(link))]]
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_PHONE, request_contact=True)]],
        resize_keyboard=True,
        input_field_placeholder="Raqamni tugma orqali yuboring",
    )
