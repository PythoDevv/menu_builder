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
from utils.referral import share_url

BTN_BACK = "⬅️ Orqaga"
BTN_HOME = "🏠 Bosh menyu"
BTN_CHECK_SUB = "✅ Tekshirish"
BTN_PHONE = "📱 Raqamni yuborish"
BTN_SHARE = "📤 Do'stlarga yuborish"
BTN_MY_POINTS = "🏆 Ballarim"

CB_CHECK_SUB = "check_sub"

# Shu kenglikkacha bo'lgan nomlar juftlanadi, uzunlari alohida qatorda qoladi.
# O'rta/katta nomlar uchun 2 ustunli menu ko'rinishini saqlab qolish uchun
# chegara biroz kengaytirildi; aks holda ko'p sarlavhalar bir qatorga sig'maydi.
SHORT_TITLE = 30

#: Menyu ustunlari soni (admin paneldan boshqariladi)
COLUMNS_ONE = 1
COLUMNS_TWO = 2
DEFAULT_COLUMNS = COLUMNS_TWO

Keyboard = Union[ReplyKeyboardMarkup, ReplyKeyboardRemove]


def title_width(text: str) -> int:
    """Taxminiy ko'rinish kengligi: emoji va belgilar ikki harf joyini egallaydi."""
    return sum(2 if ord(ch) > 0x2000 else 1 for ch in text)


def _rows(titles: Sequence[str], columns: int) -> list[list[KeyboardButton]]:
    """Qisqa nomlarni ikkitadan juftlaydi, uzunlarini yolg'iz qoldiradi.

    Tartib buzilmaydi: uzun nom uchragan joyda kutib turgan qisqa nom
    o'z qatoriga chiqariladi.
    """
    rows: list[list[str]] = []
    pending: Optional[str] = None

    for title in titles:
        if columns < COLUMNS_TWO or title_width(title) > SHORT_TITLE:
            if pending is not None:
                rows.append([pending])
                pending = None
            rows.append([title])
        elif pending is None:
            pending = title
        else:
            rows.append([pending, title])
            pending = None

    if pending is not None:
        rows.append([pending])
    return [[KeyboardButton(text=t) for t in row] for row in rows]


def menu_kb(
    children: list[MenuItem], is_root: bool, columns: int = DEFAULT_COLUMNS
) -> Keyboard:
    """Menyu tugmalari. Ildizda 'Orqaga' kerak emas, 'Ballarim' esa faqat ildizda bor."""
    rows = _rows([c.title for c in children], columns)
    if is_root:
        rows.append([KeyboardButton(text=BTN_MY_POINTS)])
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
