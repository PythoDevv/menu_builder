"""Adminlarni panel orqali qo'shish/o'chirish. Qo'shish telegram ID raqami orqali."""

from html import escape
from typing import Optional

from aiogram import Bot, F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, MessageOriginUser

from config import ADMINS as SUPER_ADMINS
from db.queries import TZ, add_admin, delete_admin, get_admin, get_admins, get_user
from handlers.admin.common import (
    KEY_ITEM,
    NOT_COMMAND,
    PICK_TEXT,
    admin_router,
    pick_label,
    save_labels,
)
from handlers.admin.states import AdminSG, PanelSG
from keyboards.admin_kb import (
    BTN_AD_ADD,
    BTN_AD_DELETE,
    BTN_AD_LIST,
    BTN_AD_YES,
    BTN_ADMINS,
    BTN_NO,
    admin_delete_kb,
    admin_label,
    admin_one_kb,
    admins_kb,
    cancel_kb,
    super_admin_label,
)
from utils.admins import is_admin, is_super_admin, refresh_admins
from utils.commands import reset_commands, set_admin_commands

router = admin_router()

LIST_TEXT = (
    "👮 <b>Adminlar</b>\n\n"
    "⭐ — <code>.env</code> dagi asosiy admin (paneldan o'chirilmaydi)\n"
    "👤 — panel orqali qo'shilgan admin"
)

SUPER_TEXT = (
    "⭐ Bu admin <code>.env</code> faylida yozilgan. Uni o'chirish uchun serverdagi "
    "<code>.env</code> faylini tahrirlab, botni qayta ishga tushiring."
)

ADD_TEXT = (
    "➕ <b>Admin qo'shish</b>\n\n"
    "Yangi adminning <b>telegram ID</b> raqamini yuboring.\n"
    "Masalan: <code>123456789</code>\n\n"
    "ID ni <a href=\"https://t.me/userinfobot\">@userinfobot</a> dan olish mumkin.\n"
    "Yoki o'sha odamning xabarini shu yerga <b>forward</b> qiling."
)


async def show_list(message: Message, state: FSMContext) -> None:
    admins = await get_admins()
    # super adminlar -1 bilan belgilanadi: bosilganda faqat izoh chiqadi
    labels: dict[str, int] = {super_admin_label(tg_id): -1 for tg_id in SUPER_ADMINS}
    labels.update({admin_label(a, i): a.id for i, a in enumerate(admins, start=1)})
    await state.set_state(AdminSG.browse)
    await save_labels(state, labels)
    await message.answer(LIST_TEXT, reply_markup=admins_kb(list(labels)))


async def show_one(message: Message, state: FSMContext, admin_id: Optional[int]) -> None:
    admin = await get_admin(admin_id) if admin_id is not None else None
    if admin is None:
        await show_list(message, state)
        return
    created = (
        admin.created_at.astimezone(TZ).strftime("%d.%m.%Y %H:%M") if admin.created_at else "—"
    )
    await state.set_state(AdminSG.one)
    await state.update_data({KEY_ITEM: admin.id})
    await message.answer(
        "👤 <b>Admin</b>\n\n"
        f"Ismi: <b>{escape(admin.full_name) or '—'}</b>\n"
        f"Username: {('@' + admin.username) if admin.username else '—'}\n"
        f"ID: <code>{admin.tg_id}</code>\n"
        f"Qo'shgan: <code>{admin.added_by or '—'}</code>\n"
        f"Sana: {created}",
        reply_markup=admin_one_kb(),
    )


@router.message(PanelSG.home, F.text == BTN_ADMINS)
async def open_list(message: Message, state: FSMContext) -> None:
    await show_list(message, state)


@router.message(AdminSG.browse, F.text == BTN_AD_ADD)
async def ask_id(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminSG.waiting_id)
    await message.answer(ADD_TEXT, reply_markup=cancel_kb())


@router.message(AdminSG.browse)
async def pick_admin(message: Message, state: FSMContext) -> None:
    admin_id = await pick_label(state, message.text)
    if admin_id is None:
        await message.answer(PICK_TEXT)
        return
    if admin_id < 0:
        await message.answer(SUPER_TEXT)
        return
    await show_one(message, state, admin_id)


# ------------------------------------------------------------------- bitta admin
@router.message(AdminSG.one, F.text == BTN_AD_DELETE)
async def delete_ask(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminSG.confirm_delete)
    await message.answer("🗑 Bu odam adminlikdan olinsinmi?", reply_markup=admin_delete_kb())


@router.message(AdminSG.one, F.text == BTN_AD_LIST)
async def back_to_list(message: Message, state: FSMContext) -> None:
    await show_list(message, state)


@router.message(AdminSG.confirm_delete, F.text == BTN_AD_YES)
async def delete_ok(message: Message, state: FSMContext) -> None:
    admin_id = (await state.get_data()).get(KEY_ITEM)
    if admin_id is not None:
        tg_id = await delete_admin(admin_id)
        await refresh_admins()
        if tg_id is not None and not is_admin(tg_id):
            await reset_commands(message.bot, tg_id)
        await message.answer("🗑 Adminlikdan olindi")
    await show_list(message, state)


@router.message(AdminSG.confirm_delete, F.text == BTN_NO)
async def delete_no(message: Message, state: FSMContext) -> None:
    await show_one(message, state, (await state.get_data()).get(KEY_ITEM))


# ------------------------------------------------------------------- qo'shish
def _parse_tg_id(message: Message) -> Optional[int]:
    # forward yopiq profilda kelmaydi — o'shanda ID raqam kerak
    if isinstance(message.forward_origin, MessageOriginUser):
        return message.forward_origin.sender_user.id
    text = (message.text or "").strip()
    if text.isdigit():
        return int(text)
    return None


async def _fetch_profile(bot: Bot, tg_id: int) -> tuple[str, Optional[str]]:
    """Ismni avval bazadan, bo'lmasa Telegramdan oladi."""
    user = await get_user(tg_id)
    if user is not None:
        return user.full_name, user.username
    try:
        chat = await bot.get_chat(tg_id)
    except TelegramAPIError:
        return "", None
    return chat.full_name or "", chat.username


@router.message(AdminSG.waiting_id, NOT_COMMAND)
async def add_admin_step(message: Message, state: FSMContext) -> None:
    tg_id = _parse_tg_id(message)
    if tg_id is None:
        await message.answer(
            "❗️ Faqat raqam yuboring (masalan <code>123456789</code>) "
            "yoki o'sha odamning xabarini forward qiling.",
            reply_markup=cancel_kb(),
        )
        return

    if is_super_admin(tg_id):
        await message.answer(
            "⭐ Bu odam allaqachon <code>.env</code> dagi asosiy admin.",
            reply_markup=cancel_kb(),
        )
        return
    if is_admin(tg_id):
        await message.answer("ℹ️ Bu odam allaqachon admin.", reply_markup=cancel_kb())
        return

    full_name, username = await _fetch_profile(message.bot, tg_id)
    _, created = await add_admin(
        tg_id=tg_id,
        full_name=full_name,
        username=username,
        added_by=message.from_user.id,
    )
    await refresh_admins()

    if created:
        await set_admin_commands(message.bot, tg_id)
        label = full_name or (f"@{username}" if username else str(tg_id))
        await message.answer(f"✅ <b>{escape(label)}</b> admin qilib qo'shildi.")
        try:
            await message.bot.send_message(
                tg_id,
                "👑 Sizga admin huquqi berildi.\n\nPanelni ochish uchun /admin",
            )
        except TelegramAPIError:
            await message.answer(
                "⚠️ Unga xabar yuborilmadi — u avval botga /start bermagan bo'lishi mumkin."
            )
    else:
        await message.answer("ℹ️ Bu odam allaqachon admin.")

    await show_list(message, state)
