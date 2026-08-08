from html import escape
from typing import Optional

from aiogram import Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from db.queries import (
    add_content,
    add_item,
    count_contents,
    delete_content,
    delete_item,
    get_content,
    get_contents,
    get_item,
    get_item_path,
    get_items,
    move_item,
    rename_item,
    toggle_item,
)
from handlers.admin.common import admin_router, edit_or_send
from handlers.admin.states import MenuSG
from keyboards.admin_kb import (
    cancel_kb,
    content_add_done_kb,
    contents_kb,
    menu_delete_kb,
    menu_node_kb,
)
from utils.content import extract_content, send_content

router = admin_router()

TITLE_LIMIT = 60

ADD_CONTENT_TEXT = (
    "📎 <b>Kontent qo'shish</b>\n\n"
    "Kerakli kontentni shu yerga yuboring — matn, rasm, video, fayl, audio...\n"
    "Nechta bo'lsa ham ketma-ket yuborishingiz mumkin.\n\n"
    "Formatlash (qalin, kursiv, havola) o'zgarmasdan saqlanadi.\n"
    "Tugatgach <b>✅ Tugatish</b> tugmasini bosing."
)


def _parse_node(raw: str) -> Optional[int]:
    return None if raw == "root" else int(raw)


async def _build_node(item_id: Optional[int]) -> tuple[str, InlineKeyboardMarkup]:
    item = await get_item(item_id) if item_id is not None else None
    parent_for_children = item.id if item else None
    children = await get_items(parent_for_children)
    content_count = await count_contents(item.id) if item else 0

    path = await get_item_path(item.id) if item else []
    crumb = " › ".join(escape(p.title) for p in path)
    lines = ["🗂 <b>Menyu tugmalari</b>", "", "🏠 Bosh menyu" + (f" › {crumb}" if crumb else "")]

    if item:
        state = "👁 ko'rinadi" if item.is_active else "🚫 yashirin"
        lines.append("")
        lines.append(f"📎 Kontent: <b>{content_count}</b> ta")
        lines.append(f"Holat: {state}")

    lines.append("")
    lines.append(f"Ichki tugmalar: <b>{len(children)}</b> ta")
    lines.append("<i>Tugma ustiga bosing — ichiga kirasiz.</i>")

    return "\n".join(lines), menu_node_kb(item, children, content_count)


async def _open_node(callback: CallbackQuery, item_id: Optional[int]) -> None:
    text, kb = await _build_node(item_id)
    await edit_or_send(callback, text, kb)


async def _send_node(bot: Bot, chat_id: int, item_id: Optional[int]) -> None:
    text, kb = await _build_node(item_id)
    await bot.send_message(chat_id, text, reply_markup=kb)


# ------------------------------------------------------------------------ ochish
@router.callback_query(F.data.startswith("mn:open:"))
async def cb_open(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    item_id = _parse_node(callback.data.split(":")[2])
    if item_id is not None and await get_item(item_id) is None:
        await callback.answer("Bu tugma o'chirilgan", show_alert=True)
        await _open_node(callback, None)
        return
    await _open_node(callback, item_id)
    await callback.answer()


# ----------------------------------------------------------------- tugma qo'shish
@router.callback_query(F.data.startswith("mn:add:"))
async def cb_add(callback: CallbackQuery, state: FSMContext) -> None:
    parent_id = _parse_node(callback.data.split(":")[2])
    await state.set_state(MenuSG.waiting_title)
    await state.update_data(parent_id=parent_id)
    await edit_or_send(
        callback,
        f"➕ Yangi tugma nomini yuboring (max {TITLE_LIMIT} belgi):",
        cancel_kb(),
    )
    await callback.answer()


@router.message(MenuSG.waiting_title)
async def add_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > TITLE_LIMIT:
        await message.answer(
            f"❗️ Nom bo'sh bo'lmasin va {TITLE_LIMIT} belgidan oshmasin.",
            reply_markup=cancel_kb(),
        )
        return
    data = await state.get_data()
    parent_id = data.get("parent_id")
    await add_item(parent_id, title)
    await state.clear()
    await message.answer("✅ Tugma qo'shildi")
    await _send_node(message.bot, message.chat.id, parent_id)


# ------------------------------------------------------------------ nomni o'zgart
@router.callback_query(F.data.startswith("mn:ren:"))
async def cb_rename(callback: CallbackQuery, state: FSMContext) -> None:
    item_id = int(callback.data.split(":")[2])
    await state.set_state(MenuSG.waiting_rename)
    await state.update_data(item_id=item_id)
    await edit_or_send(callback, "✏️ Yangi nomni yuboring:", cancel_kb())
    await callback.answer()


@router.message(MenuSG.waiting_rename)
async def rename_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > TITLE_LIMIT:
        await message.answer(
            f"❗️ Nom bo'sh bo'lmasin va {TITLE_LIMIT} belgidan oshmasin.",
            reply_markup=cancel_kb(),
        )
        return
    data = await state.get_data()
    item_id = data["item_id"]
    await rename_item(item_id, title)
    await state.clear()
    await message.answer("✅ Nom o'zgartirildi")
    await _send_node(message.bot, message.chat.id, item_id)


# ------------------------------------------------------------- yashirish / tartib
@router.callback_query(F.data.startswith("mn:tog:"))
async def cb_toggle(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[2])
    await toggle_item(item_id)
    await callback.answer("✅ O'zgartirildi")
    await _open_node(callback, item_id)


@router.callback_query(F.data.startswith("mn:up:"))
async def cb_up(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[2])
    await move_item(item_id, -1)
    await callback.answer("⬆️")
    await _open_node(callback, item_id)


@router.callback_query(F.data.startswith("mn:down:"))
async def cb_down(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[2])
    await move_item(item_id, +1)
    await callback.answer("⬇️")
    await _open_node(callback, item_id)


# ---------------------------------------------------------------------- o'chirish
@router.callback_query(F.data.startswith("mn:del:"))
async def cb_delete_ask(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[2])
    item = await get_item(item_id)
    if item is None:
        await callback.answer("Topilmadi", show_alert=True)
        return
    await edit_or_send(
        callback,
        f"🗑 <b>{escape(item.title)}</b> o'chirilsinmi?\n\n"
        "⚠️ Ichidagi barcha tugmalar va kontentlar ham o'chadi.",
        menu_delete_kb(item_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mn:delok:"))
async def cb_delete(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[2])
    item = await get_item(item_id)
    parent_id = item.parent_id if item else None
    await delete_item(item_id)
    await callback.answer("🗑 O'chirildi")
    await _open_node(callback, parent_id)


# ----------------------------------------------------------------------- KONTENT
async def _show_contents(callback: CallbackQuery, item_id: int) -> None:
    item = await get_item(item_id)
    if item is None:
        await _open_node(callback, None)
        return
    contents = await get_contents(item_id)
    text = (
        f"📎 <b>{escape(item.title)}</b> — kontentlar\n\n"
        + (
            "Ro'yxatdagi tugmani bossangiz — o'chadi."
            if contents
            else "Hozircha kontent yo'q."
        )
    )
    await edit_or_send(callback, text, contents_kb(item_id, contents))


@router.callback_query(F.data.startswith("mn:cnt:"))
async def cb_contents(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_contents(callback, int(callback.data.split(":")[2]))
    await callback.answer()


@router.callback_query(F.data.startswith("mn:cadd:"))
async def cb_content_add(callback: CallbackQuery, state: FSMContext) -> None:
    item_id = int(callback.data.split(":")[2])
    await state.set_state(MenuSG.waiting_content)
    await state.update_data(item_id=item_id)
    await edit_or_send(callback, ADD_CONTENT_TEXT, content_add_done_kb(item_id))
    await callback.answer()


@router.message(MenuSG.waiting_content)
async def content_received(message: Message, state: FSMContext) -> None:
    data = extract_content(message)
    if data is None:
        await message.answer("❗️ Bu turdagi kontent qo'llab-quvvatlanmaydi.")
        return
    item_id = (await state.get_data())["item_id"]
    await add_content(item_id, data["type"], data["file_id"], data["text_html"])
    total = await count_contents(item_id)
    await message.answer(
        f"✅ Saqlandi. Jami: <b>{total}</b> ta.\nYana yuborishingiz mumkin.",
        reply_markup=content_add_done_kb(item_id),
    )


@router.callback_query(F.data.startswith("mn:cdel:"))
async def cb_content_delete(callback: CallbackQuery) -> None:
    content_id = int(callback.data.split(":")[2])
    content = await get_content(content_id)
    if content is None:
        await callback.answer("Topilmadi", show_alert=True)
        return
    item_id = content.menu_item_id
    await delete_content(content_id)
    await callback.answer("🗑 O'chirildi")
    await _show_contents(callback, item_id)


@router.callback_query(F.data.startswith("mn:cprev:"))
async def cb_content_preview(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[2])
    contents = await get_contents(item_id)
    if not contents:
        await callback.answer("Kontent yo'q", show_alert=True)
        return
    await callback.answer("👁 Yuborilmoqda...")
    await callback.bot.send_message(
        callback.message.chat.id, "👇 Foydalanuvchi shu ko'rinishda ko'radi:"
    )
    for content in contents:
        await send_content(callback.bot, callback.message.chat.id, content)
    await _send_node(callback.bot, callback.message.chat.id, item_id)
