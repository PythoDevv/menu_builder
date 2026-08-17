"""Foydalanuvchi menyusi — reply tugmalar orqali navigatsiya.

Reply tugmada callback_data yo'q, shuning uchun "hozir qaysi bo'limdaman"
degan ma'lumot FSM ma'lumotida (node_id) saqlanadi, bosilgan tugma esa
matni bo'yicha joriy bo'limning ichki tugmalari orasidan qidiriladi.
"""

from html import escape
from typing import Optional

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import LinkPreviewOptions, Message

from db.models import MenuItem
from db.queries import get_contents, get_item, get_items, get_ref_text, get_referral_count
from keyboards.user_kb import BTN_BACK, BTN_HOME, BTN_MY_POINTS, Keyboard, menu_kb, share_kb
from utils.admins import is_admin
from utils.content import send_content
from utils.referral import ref_link, render_ref_text
from utils.texts import DEFAULT_REF_TEXT

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


async def is_locked(message: Message, item: MenuItem) -> bool:
    """Taklif sharti bajarilmagan bo'lsa — shart matnini yuboradi va True qaytaradi.

    Adminlar uchun shart tekshirilmaydi (o'z botini sinab ko'rishi uchun).
    """
    need = item.required_referrals or 0
    user_id = message.from_user.id
    if need <= 0 or is_admin(user_id):
        return False

    count = await get_referral_count(user_id)
    if count >= need:
        return False

    link = await ref_link(message.bot, user_id)
    template = await get_ref_text() or DEFAULT_REF_TEXT
    await message.answer(
        render_ref_text(template, title=item.title, need=need, count=count, link=link),
        reply_markup=share_kb(link),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    return True


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


@router.message(F.text == BTN_MY_POINTS)
async def my_points(message: Message) -> None:
    """Doimiy 'Ballarim' tugmasi — shartli tugma bosilishini kutmasdan ham ko'rinadi."""
    user_id = message.from_user.id
    count = await get_referral_count(user_id)
    link = await ref_link(message.bot, user_id)
    await message.answer(
        "🏆 <b>Ballaringiz</b>\n\n"
        f"Siz taklif qilgan odamlar soni: <b>{count}</b> ta\n\n"
        "Do'stlaringizni shu havola orqali taklif qiling:\n"
        f"{link}",
        reply_markup=share_kb(link),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


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

    # taklif sharti — bo'lim ham, kontent ham shu tekshiruvdan keyin ochiladi
    if await is_locked(message, target):
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
