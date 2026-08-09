"""Foydalanuvchi menyusi — reply tugmalar orqali navigatsiya.

Reply tugmada callback_data yo'q, shuning uchun "hozir qaysi bo'limdaman"
degan ma'lumot FSM ma'lumotida (node_id) saqlanadi, bosilgan tugma esa
matni bo'yicha joriy bo'limning ichki tugmalari orasidan qidiriladi.
"""

from html import escape
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.models import MenuItem
from db.queries import get_contents, get_item, get_items
from keyboards.user_kb import BTN_BACK, BTN_HOME, Keyboard, menu_kb
from utils.content import send_content

router = Router()

#: FSM kaliti — foydalanuvchi turgan bo'lim (None -> asosiy menyu)
KEY_NODE = "node_id"

MENU_TEXT = "🏠 Asosiy menyu"
EMPTY_TEXT = "⚠️ Hozircha menyu bo'sh. Keyinroq urinib ko'ring."
NO_DATA_TEXT = "ℹ️ Bu bo'limda hozircha ma'lumot yo'q."
PICK_TEXT = "👇 Pastdagi tugmalardan birini tanlang."


async def current_node_id(state: FSMContext) -> Optional[int]:
    """Joriy bo'lim. O'chirilgan bo'lsa asosiy menyuga qaytadi."""
    data = await state.get_data()
    node_id = data.get(KEY_NODE)
    if node_id is not None and await get_item(node_id) is None:
        node_id = None
        await state.update_data({KEY_NODE: None})
    return node_id


async def node_kb(node_id: Optional[int]) -> Keyboard:
    children = await get_items(node_id, active_only=True)
    return menu_kb(children, is_root=node_id is None)


async def _send_contents(message: Message, item_id: int, kb: Keyboard) -> None:
    """Kontentlarni yuboradi; klaviatura oxirgi xabarga ilinadi."""
    contents = await get_contents(item_id)
    last = len(contents) - 1
    for i, content in enumerate(contents):
        await send_content(
            message.bot,
            message.chat.id,
            content,
            reply_markup=kb if i == last else None,
        )


async def open_node(message: Message, state: FSMContext, node_id: Optional[int]) -> None:
    """Bo'lim ichiga kiradi: kontentini yuboradi va ichki tugmalarini ko'rsatadi."""
    await state.update_data({KEY_NODE: node_id})
    children = await get_items(node_id, active_only=True)
    kb = menu_kb(children, is_root=node_id is None)

    if node_id is not None and await get_contents(node_id):
        await _send_contents(message, node_id, kb)
        return

    item = await get_item(node_id) if node_id is not None else None
    if item is None:
        text = MENU_TEXT if children else EMPTY_TEXT
    else:
        text = f"<b>{escape(item.title)}</b>"
    await message.answer(text, reply_markup=kb)


async def _find_child(parent_id: Optional[int], title: str) -> Optional[MenuItem]:
    for item in await get_items(parent_id, active_only=True):
        if item.title == title:
            return item
    return None


@router.message(F.text == BTN_HOME)
async def go_home(message: Message, state: FSMContext) -> None:
    await open_node(message, state, None)


@router.message(F.text == BTN_BACK)
async def go_back(message: Message, state: FSMContext) -> None:
    node_id = await current_node_id(state)
    parent_id = None
    if node_id is not None:
        item = await get_item(node_id)
        parent_id = item.parent_id if item else None
    await open_node(message, state, parent_id)


@router.message(F.text)
async def navigate(message: Message, state: FSMContext) -> None:
    node_id = await current_node_id(state)
    title = message.text

    target = await _find_child(node_id, title)
    if target is None and node_id is not None:
        # eski klaviatura yoki bot qayta ishga tushgan — ildizdan ham qidiramiz
        target = await _find_child(None, title)
        if target is not None:
            node_id = None
            await state.update_data({KEY_NODE: None})

    if target is None:
        await message.answer(PICK_TEXT, reply_markup=await node_kb(node_id))
        return

    if await get_items(target.id, active_only=True):
        await open_node(message, state, target.id)
        return

    # ichki tugmasi yo'q — kontentni yuboramiz, klaviatura o'z joyida qoladi
    if await get_contents(target.id):
        await _send_contents(message, target.id, await node_kb(node_id))
    else:
        await message.answer(NO_DATA_TEXT, reply_markup=await node_kb(node_id))


@router.message()
async def other(message: Message, state: FSMContext) -> None:
    node_id = await current_node_id(state)
    await message.answer(PICK_TEXT, reply_markup=await node_kb(node_id))
