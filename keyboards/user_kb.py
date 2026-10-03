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
from db.queries import DEFAULT_MY_POINTS_TEXT, DEFAULT_SUB_CHECK_TEXT
from utils.referral import share_url

BTN_BACK = "⬅️ Orqaga"
BTN_HOME = "🏠 Bosh menyu"
BTN_CHECK_SUB = DEFAULT_SUB_CHECK_TEXT
BTN_PHONE = "📱 Raqamni yuborish"
BTN_SHARE = "📤 Do'stlarga yuborish"
BTN_MY_POINTS = DEFAULT_MY_POINTS_TEXT

CB_CHECK_SUB = "check_sub"

Keyboard = Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]


def _menu_button(item: MenuItem) -> KeyboardButton:
    return KeyboardButton(
        text=item.title,
        style=item.button_style,
        icon_custom_emoji_id=item.icon_custom_emoji_id,
    )


def _item_row_size(item: MenuItem) -> int:
    """Eski/noto'g'ri qiymatni xavfsiz tarzda 1 talik deb oladi."""
    value = getattr(item, "row_size", 1)
    return value if value in {1, 2, 3, 4} else 1


def _rows(items: Sequence[MenuItem]) -> list[list[KeyboardButton]]:
    """Ketma-ket, bir xil o'lchamli tugmalarni qatorlarga guruhlaydi."""
    rows: list[list[MenuItem]] = []
    pending: list[MenuItem] = []
    pending_size: Optional[int] = None

    for item in items:
        row_size = _item_row_size(item)
        if pending and row_size != pending_size:
            rows.append(pending)
            pending = []
        pending_size = row_size
        pending.append(item)
        if len(pending) == row_size:
            rows.append(pending)
            pending = []
            pending_size = None

    if pending:
        rows.append(pending)
    return [[_menu_button(item) for item in row] for row in rows]


def menu_kb(
    children: list[MenuItem],
    is_root: bool,
    my_points_enabled: bool = True,
    my_points_text: str = BTN_MY_POINTS,
    my_points_style: Optional[str] = None,
    my_points_icon_custom_emoji_id: Optional[str] = None,
) -> Keyboard:
    """Menyu tugmalari. Ildizda 'Orqaga' kerak emas, 'Ballarim' esa faqat ildizda bor."""
    rows = _rows(children)
    if is_root:
        if my_points_enabled:
            rows.append(
                [
                    KeyboardButton(
                        text=my_points_text,
                        style=my_points_style,
                        icon_custom_emoji_id=my_points_icon_custom_emoji_id,
                    )
                ]
            )
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


def subscribe_kb(
    channels: list[Channel],
    check_text: str = BTN_CHECK_SUB,
    check_icon_custom_emoji_id: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Kanal havolalari + tekshirish tugmasi (inline)."""
    rows = []
    for ch in channels:
        url = channel_url(ch)
        if not url:
            continue
        prefix = "🔒" if ch.is_private else "📢"
        icon_custom_emoji_id = getattr(ch, "icon_custom_emoji_id", None)
        text = ch.title if icon_custom_emoji_id else f"{prefix} {ch.title}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    url=url,
                    icon_custom_emoji_id=icon_custom_emoji_id,
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=check_text,
                callback_data=CB_CHECK_SUB,
                icon_custom_emoji_id=check_icon_custom_emoji_id,
            )
        ]
    )
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
