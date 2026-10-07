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
from db.queries import DEFAULT_MY_POINTS_TEXT, DEFAULT_RATING_TEXT, DEFAULT_SUB_CHECK_TEXT
from utils.referral import share_url

BTN_BACK = "⬅️ Orqaga"
BTN_HOME = "🏠 Bosh menyu"
BTN_CHECK_SUB = DEFAULT_SUB_CHECK_TEXT
BTN_PHONE = "📱 Raqamni yuborish"
BTN_SHARE = "📤 Do'stlarga yuborish"
BTN_MY_POINTS = DEFAULT_MY_POINTS_TEXT
BTN_RATING = DEFAULT_RATING_TEXT

CB_CHECK_SUB = "check_sub"

Keyboard = Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]


def _menu_button(item: MenuItem) -> KeyboardButton:
    return KeyboardButton(
        text=item.title,
        style=item.button_style,
        icon_custom_emoji_id=item.icon_custom_emoji_id,
    )


def _item_row_size(item: MenuItem) -> int:
    """Qiymat yo'q/noto'g'ri bo'lsa standart 2 talik ko'rinishni oladi."""
    value = getattr(item, "row_size", 2)
    return value if value in {1, 2, 3, 4} else 2


def _button_rows(
    buttons: Sequence[tuple[KeyboardButton, int]],
) -> list[list[KeyboardButton]]:
    """Ketma-ket, bir xil sig'imli tugmalarni qatorlarga guruhlaydi."""
    rows: list[list[KeyboardButton]] = []
    pending: list[KeyboardButton] = []
    pending_size: Optional[int] = None

    for button, row_size in buttons:
        if pending and row_size != pending_size:
            rows.append(pending)
            pending = []
        pending_size = row_size
        pending.append(button)
        if len(pending) == row_size:
            rows.append(pending)
            pending = []
            pending_size = None

    if pending:
        rows.append(pending)
    return rows


def _rows(items: Sequence[MenuItem]) -> list[list[KeyboardButton]]:
    return _button_rows(
        [(_menu_button(item), _item_row_size(item)) for item in items]
    )


def menu_kb(
    children: list[MenuItem],
    is_root: bool,
    my_points_enabled: bool = True,
    my_points_text: str = BTN_MY_POINTS,
    my_points_style: Optional[str] = None,
    my_points_icon_custom_emoji_id: Optional[str] = None,
    rating_enabled: bool = False,
    rating_text: str = BTN_RATING,
    rating_style: Optional[str] = None,
    rating_icon_custom_emoji_id: Optional[str] = None,
    rating_row_size: int = 2,
) -> Keyboard:
    """Menyu tugmalari va ildizdagi doimiy Ballarim/Reyting tugmalari."""
    if is_root:
        row_size = rating_row_size if rating_row_size in {1, 2, 3, 4} else 2
        button_specs = [
            (_menu_button(item), _item_row_size(item)) for item in children
        ]
        if my_points_enabled:
            button_specs.append(
                (
                    KeyboardButton(
                        text=my_points_text,
                        style=my_points_style,
                        icon_custom_emoji_id=my_points_icon_custom_emoji_id,
                    ),
                    row_size if rating_enabled else 1,
                )
            )
        if rating_enabled:
            button_specs.append(
                (
                    KeyboardButton(
                        text=rating_text,
                        style=rating_style,
                        icon_custom_emoji_id=rating_icon_custom_emoji_id,
                    ),
                    row_size,
                )
            )
        rows = _button_rows(button_specs)
    else:
        rows = _rows(children)
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
