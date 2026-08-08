from typing import Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models import Channel, Content, MenuItem
from utils.content import content_label


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


BACK_HOME = [_btn("⬅️ Admin panel", "adm:home")]
CANCEL_ROW = [_btn("❌ Bekor qilish", "adm:cancel")]


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[CANCEL_ROW])


def admin_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📢 Kanallar", "ch:list"), _btn("🗂 Menyu tugmalari", "mn:open:root")],
            [_btn("✏️ Start xabar", "st:show"), _btn("☎️ Telefon so'rash", "adm:phone")],
            [_btn("📨 Xabar yuborish", "adm:send"), _btn("📊 Excel", "xl:menu")],
            [_btn("👥 Statistika", "adm:stats")],
        ]
    )


# ---------------------------------------------------------------------- KANALLAR
def channels_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        mark = "🟢" if ch.is_active else "🔴"
        kind = "🔒" if ch.is_private else "📢"
        rows.append([_btn(f"{mark} {kind} {ch.title}", f"ch:one:{ch.id}")])
    rows.append([_btn("➕ Kanal qo'shish", "ch:add")])
    rows.append(BACK_HOME)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def channel_one_kb(ch: Channel) -> InlineKeyboardMarkup:
    toggle = "🔴 O'chirish" if ch.is_active else "🟢 Yoqish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(toggle, f"ch:tog:{ch.id}"), _btn("🗑 O'chirish", f"ch:del:{ch.id}")],
            [_btn("⬅️ Kanallar", "ch:list")],
        ]
    )


def channel_delete_kb(channel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✅ Ha, o'chirilsin", f"ch:delok:{channel_id}")],
            [_btn("⬅️ Yo'q", f"ch:one:{channel_id}")],
        ]
    )


def channel_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📢 Ochiq kanal", "ch:type:public")],
            [_btn("🔒 Yopiq (qo'shilish so'rovi)", "ch:type:private")],
            CANCEL_ROW,
        ]
    )


# ------------------------------------------------------------------------- MENYU
def menu_node_kb(
    item: Optional[MenuItem], children: list[MenuItem], content_count: int
) -> InlineKeyboardMarkup:
    node_id = "root" if item is None else str(item.id)
    rows = []
    for child in children:
        mark = "" if child.is_active else "🚫 "
        rows.append([_btn(f"{mark}{child.title}", f"mn:open:{child.id}")])

    rows.append([_btn("➕ Tugma qo'shish", f"mn:add:{node_id}")])

    if item is not None:
        rows.append([_btn(f"📎 Kontent ({content_count})", f"mn:cnt:{item.id}")])
        toggle = "🚫 Yashirish" if item.is_active else "👁 Ko'rsatish"
        rows.append([_btn("✏️ Nomi", f"mn:ren:{item.id}"), _btn(toggle, f"mn:tog:{item.id}")])
        rows.append(
            [
                _btn("⬆️", f"mn:up:{item.id}"),
                _btn("⬇️", f"mn:down:{item.id}"),
                _btn("🗑 O'chirish", f"mn:del:{item.id}"),
            ]
        )
        back = "root" if item.parent_id is None else str(item.parent_id)
        rows.append([_btn("⬅️ Orqaga", f"mn:open:{back}")])
    else:
        rows.append(BACK_HOME)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def menu_delete_kb(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✅ Ha, o'chirilsin", f"mn:delok:{item_id}")],
            [_btn("⬅️ Yo'q", f"mn:open:{item_id}")],
        ]
    )


def contents_kb(item_id: int, contents: list[Content]) -> InlineKeyboardMarkup:
    rows = []
    for i, c in enumerate(contents, start=1):
        rows.append([_btn(f"🗑 {content_label(c, i)}", f"mn:cdel:{c.id}")])
    rows.append([_btn("➕ Kontent qo'shish", f"mn:cadd:{item_id}")])
    if contents:
        rows.append([_btn("👁 Ko'rish", f"mn:cprev:{item_id}")])
    rows.append([_btn("⬅️ Orqaga", f"mn:open:{item_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def content_add_done_kb(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn("✅ Tugatish", f"mn:cnt:{item_id}")]]
    )


# -------------------------------------------------------------------- START XABAR
def start_msg_kb(exists: bool) -> InlineKeyboardMarkup:
    rows = [[_btn("✏️ O'zgartirish" if exists else "➕ Qo'shish", "st:edit")]]
    if exists:
        rows.append([_btn("🗑 O'chirish", "st:del")])
    rows.append(BACK_HOME)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_delete_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✅ Ha, o'chirilsin", "st:delok")],
            [_btn("⬅️ Yo'q", "st:show")],
        ]
    )


# ---------------------------------------------------------------------- BROADCAST
def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✅ Yuborish", "bc:go")],
            CANCEL_ROW,
        ]
    )


# -------------------------------------------------------------------------- EXCEL
def excel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📥 Faylni olish", "xl:get")],
            [_btn("🔄 Yangilash", "xl:refresh")],
            BACK_HOME,
        ]
    )
