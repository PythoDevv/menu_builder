from html import escape
from typing import Optional

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.queries import (
    add_content,
    add_item,
    count_contents,
    delete_content,
    delete_item,
    get_contents,
    get_item,
    get_item_path,
    get_items,
    move_item,
    rename_item,
    toggle_item,
)
from handlers.admin.common import (
    KEY_NODE,
    NOT_COMMAND,
    PICK_TEXT,
    admin_router,
    pick_label,
    save_labels,
)
from handlers.admin.states import MenuSG, PanelSG
from keyboards.admin_kb import (
    BTN_BACK,
    BTN_CNT_ADD,
    BTN_CNT_DONE,
    BTN_CONTENT,
    BTN_DELETE,
    BTN_MENU,
    BTN_MN_ADD,
    BTN_MN_DOWN,
    BTN_MN_HIDE,
    BTN_MN_RENAME,
    BTN_MN_SHOW,
    BTN_MN_UP,
    BTN_NO,
    BTN_VIEW,
    BTN_YES_DELETE,
    cancel_kb,
    confirm_delete_kb,
    content_add_kb,
    content_item_label,
    contents_kb,
    menu_item_label,
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


async def _node_id(state: FSMContext) -> Optional[int]:
    return (await state.get_data()).get(KEY_NODE)


# --------------------------------------------------------------------- ekranlar
async def show_node(message: Message, state: FSMContext, node_id: Optional[int]) -> None:
    item = await get_item(node_id) if node_id is not None else None
    if item is None:
        node_id = None

    children = await get_items(node_id)
    content_count = await count_contents(node_id) if node_id is not None else 0
    labels = {menu_item_label(c, i): c.id for i, c in enumerate(children, start=1)}

    path = await get_item_path(item.id) if item else []
    crumb = " › ".join(escape(p.title) for p in path)
    lines = ["🗂 <b>Menyu tugmalari</b>", "", "🏠 Bosh menyu" + (f" › {crumb}" if crumb else "")]
    if item:
        lines.append("")
        lines.append(f"📎 Kontent: <b>{content_count}</b> ta")
        lines.append(f"Holat: {'👁 ko‘rinadi' if item.is_active else '🚫 yashirin'}")
    lines.append("")
    lines.append(f"Ichki tugmalar: <b>{len(children)}</b> ta")
    lines.append("<i>Tugma ustiga bosing — ichiga kirasiz.</i>")

    await state.set_state(MenuSG.node)
    await state.update_data({KEY_NODE: node_id})
    await save_labels(state, labels)
    await message.answer(
        "\n".join(lines), reply_markup=menu_node_kb(list(labels), item, content_count)
    )


async def show_contents(message: Message, state: FSMContext, item_id: Optional[int]) -> None:
    item = await get_item(item_id) if item_id is not None else None
    if item is None:
        await show_node(message, state, None)
        return

    contents = await get_contents(item_id)
    labels = {content_item_label(c, i): c.id for i, c in enumerate(contents, start=1)}
    await state.set_state(MenuSG.contents)
    await state.update_data({KEY_NODE: item_id})
    await save_labels(state, labels)
    await message.answer(
        f"📎 <b>{escape(item.title)}</b> — kontentlar\n\n"
        + (
            "Ro'yxatdagi tugmani bossangiz — o'chadi."
            if contents
            else "Hozircha kontent yo'q."
        ),
        reply_markup=contents_kb(list(labels)),
    )


@router.message(PanelSG.home, F.text == BTN_MENU)
async def open_root(message: Message, state: FSMContext) -> None:
    await show_node(message, state, None)


# ----------------------------------------------------------------- tugma qo'shish
@router.message(MenuSG.node, F.text == BTN_MN_ADD)
async def ask_title(message: Message, state: FSMContext) -> None:
    await state.set_state(MenuSG.waiting_title)
    await message.answer(
        f"➕ Yangi tugma nomini yuboring (max {TITLE_LIMIT} belgi):",
        reply_markup=cancel_kb(),
    )


@router.message(MenuSG.waiting_title, NOT_COMMAND)
async def add_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > TITLE_LIMIT:
        await message.answer(
            f"❗️ Nom bo'sh bo'lmasin va {TITLE_LIMIT} belgidan oshmasin.",
            reply_markup=cancel_kb(),
        )
        return
    parent_id = await _node_id(state)
    await add_item(parent_id, title)
    await message.answer("✅ Tugma qo'shildi")
    await show_node(message, state, parent_id)


# ------------------------------------------------------------------ nomni o'zgart
@router.message(MenuSG.node, F.text == BTN_MN_RENAME)
async def ask_rename(message: Message, state: FSMContext) -> None:
    if await _node_id(state) is None:
        await show_node(message, state, None)
        return
    await state.set_state(MenuSG.waiting_rename)
    await message.answer("✏️ Yangi nomni yuboring:", reply_markup=cancel_kb())


@router.message(MenuSG.waiting_rename, NOT_COMMAND)
async def rename(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > TITLE_LIMIT:
        await message.answer(
            f"❗️ Nom bo'sh bo'lmasin va {TITLE_LIMIT} belgidan oshmasin.",
            reply_markup=cancel_kb(),
        )
        return
    item_id = await _node_id(state)
    if item_id is not None:
        await rename_item(item_id, title)
        await message.answer("✅ Nom o'zgartirildi")
    await show_node(message, state, item_id)


# ------------------------------------------------------------- yashirish / tartib
@router.message(MenuSG.node, F.text.in_({BTN_MN_HIDE, BTN_MN_SHOW}))
async def toggle(message: Message, state: FSMContext) -> None:
    item_id = await _node_id(state)
    if item_id is not None:
        await toggle_item(item_id)
        await message.answer("✅ O'zgartirildi")
    await show_node(message, state, item_id)


@router.message(MenuSG.node, F.text.in_({BTN_MN_UP, BTN_MN_DOWN}))
async def move(message: Message, state: FSMContext) -> None:
    item_id = await _node_id(state)
    if item_id is not None:
        await move_item(item_id, -1 if message.text == BTN_MN_UP else +1)
        await message.answer("✅ Tartib o'zgartirildi")
    await show_node(message, state, item_id)


# ---------------------------------------------------------------------- o'chirish
@router.message(MenuSG.node, F.text == BTN_DELETE)
async def delete_ask(message: Message, state: FSMContext) -> None:
    item_id = await _node_id(state)
    item = await get_item(item_id) if item_id is not None else None
    if item is None:
        await show_node(message, state, None)
        return
    await state.set_state(MenuSG.confirm_delete)
    await message.answer(
        f"🗑 <b>{escape(item.title)}</b> o'chirilsinmi?\n\n"
        "⚠️ Ichidagi barcha tugmalar va kontentlar ham o'chadi.",
        reply_markup=confirm_delete_kb(),
    )


@router.message(MenuSG.confirm_delete, F.text == BTN_YES_DELETE)
async def delete_ok(message: Message, state: FSMContext) -> None:
    item_id = await _node_id(state)
    item = await get_item(item_id) if item_id is not None else None
    parent_id = item.parent_id if item else None
    if item_id is not None:
        await delete_item(item_id)
        await message.answer("🗑 O'chirildi")
    await show_node(message, state, parent_id)


@router.message(MenuSG.confirm_delete, F.text == BTN_NO)
async def delete_no(message: Message, state: FSMContext) -> None:
    await show_node(message, state, await _node_id(state))


# ------------------------------------------------------------------------- orqaga
@router.message(MenuSG.node, F.text == BTN_BACK)
async def go_up(message: Message, state: FSMContext) -> None:
    item_id = await _node_id(state)
    item = await get_item(item_id) if item_id is not None else None
    await show_node(message, state, item.parent_id if item else None)


@router.message(MenuSG.node, F.text.startswith(BTN_CONTENT))
async def open_contents(message: Message, state: FSMContext) -> None:
    item_id = await _node_id(state)
    if item_id is None:
        await show_node(message, state, None)
        return
    await show_contents(message, state, item_id)


@router.message(MenuSG.node)
async def pick_child(message: Message, state: FSMContext) -> None:
    child_id = await pick_label(state, message.text)
    if child_id is None:
        await message.answer(PICK_TEXT)
        return
    await show_node(message, state, child_id)


# ------------------------------------------------------------------------ KONTENT
@router.message(MenuSG.contents, F.text == BTN_CNT_ADD)
async def ask_content(message: Message, state: FSMContext) -> None:
    await state.set_state(MenuSG.waiting_content)
    await message.answer(ADD_CONTENT_TEXT, reply_markup=content_add_kb())


@router.message(MenuSG.contents, F.text == BTN_VIEW)
async def preview(message: Message, state: FSMContext) -> None:
    item_id = await _node_id(state)
    contents = await get_contents(item_id) if item_id is not None else []
    if not contents:
        await message.answer("❗️ Kontent yo'q")
        return
    await message.answer("👇 Foydalanuvchi shu ko'rinishda ko'radi:")
    for content in contents:
        await send_content(message.bot, message.chat.id, content)
    await show_contents(message, state, item_id)


@router.message(MenuSG.contents, F.text == BTN_BACK)
async def contents_back(message: Message, state: FSMContext) -> None:
    await show_node(message, state, await _node_id(state))


@router.message(MenuSG.contents)
async def delete_content_btn(message: Message, state: FSMContext) -> None:
    content_id = await pick_label(state, message.text)
    if content_id is None:
        await message.answer(PICK_TEXT)
        return
    item_id = await _node_id(state)
    await delete_content(content_id)
    await message.answer("🗑 O'chirildi")
    await show_contents(message, state, item_id)


@router.message(MenuSG.waiting_content, F.text == BTN_CNT_DONE)
async def content_done(message: Message, state: FSMContext) -> None:
    await show_contents(message, state, await _node_id(state))


@router.message(MenuSG.waiting_content, NOT_COMMAND)
async def content_received(message: Message, state: FSMContext) -> None:
    data = extract_content(message)
    if data is None:
        await message.answer("❗️ Bu turdagi kontent qo'llab-quvvatlanmaydi.")
        return
    item_id = await _node_id(state)
    if item_id is None:
        await show_node(message, state, None)
        return
    await add_content(item_id, data["type"], data["file_id"], data["text_html"])
    total = await count_contents(item_id)
    await message.answer(
        f"✅ Saqlandi. Jami: <b>{total}</b> ta.\nYana yuborishingiz mumkin.",
        reply_markup=content_add_kb(),
    )
