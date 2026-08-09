"""Admin panel klaviaturalari — hammasi reply (pastdagi) tugmalar.

Reply tugmada callback_data bo'lmagani uchun tugma matni orqali ishlaymiz.
Ro'yxatlar (kanal, menyu, admin, kontent) raqamlanadi: matn -> id moslik
FSM ma'lumotida saqlanadi (handlers/admin/common.py).
"""

from typing import Optional, Sequence

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from db.models import Admin, Channel, Content, MenuItem
from utils.content import content_label

# ------------------------------------------------------------------ umumiy tugmalar
BTN_HOME = "🏠 Admin panel"
BTN_BACK = "⬅️ Orqaga"
BTN_CANCEL = "❌ Bekor qilish"
BTN_EXIT = "🚪 Chiqish"
BTN_YES_DELETE = "✅ Ha, o'chirilsin"
BTN_NO = "⬅️ Yo'q"
BTN_DELETE = "🗑 O'chirish"
BTN_VIEW = "👁 Ko'rish"
BTN_ON = "🟢 Yoqish"
BTN_OFF = "🔴 O'chirish"

# ------------------------------------------------------------------- bosh sahifa
BTN_CHANNELS = "📢 Kanallar"
BTN_MENU = "🗂 Menyu tugmalari"
BTN_START_MSG = "✏️ Start xabar"
BTN_SUB_MSG = "📌 Obuna xabari"
BTN_PHONE = "☎️ Telefon so'rash"
BTN_BROADCAST = "📨 Xabar yuborish"
BTN_EXCEL = "📊 Excel"
BTN_STATS = "👥 Statistika"
BTN_ADMINS = "👮 Adminlar"

# ---------------------------------------------------------------------- kanallar
BTN_CH_ADD = "➕ Kanal qo'shish"
BTN_CH_LIST = "⬅️ Kanallar"
BTN_CH_ENABLE = "🟢 Faollashtirish"
BTN_CH_DISABLE = "🔴 To'xtatish"
BTN_CH_PUBLIC = "📢 Ochiq kanal"
BTN_CH_PRIVATE = "🔒 Yopiq (qo'shilish so'rovi)"

# ------------------------------------------------------------------------- menyu
BTN_MN_ADD = "➕ Tugma qo'shish"
BTN_MN_RENAME = "✏️ Nomi"
BTN_MN_SHOW = "👁 Ko'rsatish"
BTN_MN_HIDE = "🚫 Yashirish"
BTN_MN_UP = "⬆️ Yuqoriga"
BTN_MN_DOWN = "⬇️ Pastga"
BTN_CONTENT = "📎 Kontent"  # yoniga soni qo'shiladi: "📎 Kontent (3)"
BTN_CNT_ADD = "➕ Kontent qo'shish"
BTN_CNT_DONE = "✅ Tugatish"

# ------------------------------------------------------- start / obuna xabari
BTN_ST_EDIT = "✏️ O'zgartirish"
BTN_ST_ADD = "➕ Qo'shish"
BTN_SUB_RESET = "♻️ Standartga qaytarish"

# ---------------------------------------------------------------------- broadcast
BTN_BC_SEND = "✅ Yuborish"

# -------------------------------------------------------------------------- excel
BTN_XL_GET = "📥 Faylni olish"
BTN_XL_REFRESH = "🔄 Yangilash"

# ------------------------------------------------------------------------ adminlar
BTN_AD_ADD = "➕ Admin qo'shish"
BTN_AD_LIST = "⬅️ Adminlar"
BTN_AD_DELETE = "🗑 Adminlikdan olish"
BTN_AD_YES = "✅ Ha, olib tashlansin"


def _kb(rows: Sequence[Sequence[str]], placeholder: str = "Tugmani tanlang") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
        input_field_placeholder=placeholder,
    )


def _list_rows(labels: Sequence[str]) -> list[list[str]]:
    return [[label] for label in labels]


# ------------------------------------------------------------------- bosh sahifa
def admin_home_kb() -> ReplyKeyboardMarkup:
    return _kb(
        [
            [BTN_CHANNELS, BTN_MENU],
            [BTN_START_MSG, BTN_SUB_MSG],
            [BTN_PHONE, BTN_BROADCAST],
            [BTN_EXCEL, BTN_STATS],
            [BTN_ADMINS],
            [BTN_EXIT],
        ],
        "Bo'limni tanlang",
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return _kb([[BTN_CANCEL]], "Yuboring yoki bekor qiling")


def confirm_delete_kb(no_button: str = BTN_NO) -> ReplyKeyboardMarkup:
    return _kb([[BTN_YES_DELETE], [no_button]], "Tasdiqlang")


# ---------------------------------------------------------------------- ADMINLAR
def admin_label(admin: Admin, index: int) -> str:
    name = admin.full_name or (f"@{admin.username}" if admin.username else str(admin.tg_id))
    return f"{index}. 👤 {name}"


def super_admin_label(tg_id: int) -> str:
    return f"⭐ {tg_id}"


def admins_kb(labels: Sequence[str]) -> ReplyKeyboardMarkup:
    return _kb(_list_rows(labels) + [[BTN_AD_ADD], [BTN_HOME]])


def admin_one_kb() -> ReplyKeyboardMarkup:
    return _kb([[BTN_AD_DELETE], [BTN_AD_LIST]])


def admin_delete_kb() -> ReplyKeyboardMarkup:
    return _kb([[BTN_AD_YES], [BTN_NO]], "Tasdiqlang")


# ---------------------------------------------------------------------- KANALLAR
def channel_label(ch: Channel, index: int) -> str:
    mark = "🟢" if ch.is_active else "🔴"
    kind = "🔒" if ch.is_private else "📢"
    return f"{index}. {mark} {kind} {ch.title}"


def channels_kb(labels: Sequence[str]) -> ReplyKeyboardMarkup:
    return _kb(_list_rows(labels) + [[BTN_CH_ADD], [BTN_HOME]])


def channel_one_kb(ch: Channel) -> ReplyKeyboardMarkup:
    toggle = BTN_CH_DISABLE if ch.is_active else BTN_CH_ENABLE
    return _kb([[toggle, BTN_DELETE], [BTN_CH_LIST]])


def channel_type_kb() -> ReplyKeyboardMarkup:
    return _kb([[BTN_CH_PUBLIC], [BTN_CH_PRIVATE], [BTN_CANCEL]], "Turini tanlang")


# Bot kanalga admin qilinganda o'sha adminga tushadigan so'rov — inline,
# chunki u admin panelning istalgan ekranida (yoki umuman tashqarisida) keladi
# va reply klaviaturani buzmasligi kerak.
CB_NEW_CH_ADD = "newch:add"
CB_NEW_CH_SKIP = "newch:skip"


def new_channel_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, qo'shilsin", callback_data=f"{CB_NEW_CH_ADD}:{chat_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Yo'q", callback_data=f"{CB_NEW_CH_SKIP}:{chat_id}"
                ),
            ]
        ]
    )


# ------------------------------------------------------------------------- MENYU
def menu_item_label(item: MenuItem, index: int) -> str:
    mark = "" if item.is_active else "🚫 "
    return f"{index}. {mark}{item.title}"


def content_button(count: int) -> str:
    return f"{BTN_CONTENT} ({count})"


def menu_node_kb(
    labels: Sequence[str], item: Optional[MenuItem], content_count: int
) -> ReplyKeyboardMarkup:
    rows = _list_rows(labels)
    rows.append([BTN_MN_ADD])
    if item is None:
        rows.append([BTN_HOME])
    else:
        rows.append([content_button(content_count)])
        rows.append([BTN_MN_RENAME, BTN_MN_HIDE if item.is_active else BTN_MN_SHOW])
        rows.append([BTN_MN_UP, BTN_MN_DOWN, BTN_DELETE])
        rows.append([BTN_BACK, BTN_HOME])
    return _kb(rows)


def contents_kb(labels: Sequence[str]) -> ReplyKeyboardMarkup:
    rows = _list_rows(labels)
    rows.append([BTN_CNT_ADD])
    if labels:
        rows.append([BTN_VIEW])
    rows.append([BTN_BACK])
    return _kb(rows)


def content_item_label(content: Content, index: int) -> str:
    return f"🗑 {content_label(content, index)}"


def content_add_kb() -> ReplyKeyboardMarkup:
    return _kb([[BTN_CNT_DONE]], "Kontentni yuboring")


# -------------------------------------------------------------------- START XABAR
def start_msg_kb(exists: bool) -> ReplyKeyboardMarkup:
    rows = [[BTN_ST_EDIT if exists else BTN_ST_ADD]]
    if exists:
        rows.append([BTN_VIEW, BTN_DELETE])
    rows.append([BTN_HOME])
    return _kb(rows)


# ------------------------------------------------------------------ OBUNA XABARI
def sub_msg_kb(custom: bool) -> ReplyKeyboardMarkup:
    """custom — admin o'z xabarini qo'yganmi (yo'q bo'lsa standart ishlaydi)."""
    rows = [[BTN_ST_EDIT if custom else BTN_ST_ADD], [BTN_VIEW]]
    if custom:
        rows.append([BTN_SUB_RESET])
    rows.append([BTN_HOME])
    return _kb(rows)


# ------------------------------------------------------------------------ TELEFON
def phone_settings_kb(enabled: bool) -> ReplyKeyboardMarkup:
    return _kb([[BTN_OFF if enabled else BTN_ON], [BTN_HOME]])


# ---------------------------------------------------------------------- BROADCAST
def broadcast_confirm_kb() -> ReplyKeyboardMarkup:
    return _kb([[BTN_BC_SEND], [BTN_CANCEL]], "Tasdiqlang")


# -------------------------------------------------------------------------- EXCEL
def excel_kb() -> ReplyKeyboardMarkup:
    return _kb([[BTN_XL_GET, BTN_XL_REFRESH], [BTN_HOME]])
