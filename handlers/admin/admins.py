"""Adminlarni panel orqali qo'shish/o'chirish. Qo'shish telegram ID raqami orqali."""

from html import escape
from typing import Optional

from aiogram import Bot, F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, MessageOriginUser

from config import ADMINS as SUPER_ADMINS
from db.queries import (
    TZ,
    add_admin,
    delete_admin,
    get_admin,
    get_admins,
    get_user,
)
from handlers.admin.common import admin_router, edit_or_send
from handlers.admin.states import AdminSG
from keyboards.admin_kb import admin_delete_kb, admin_one_kb, admins_kb, cancel_kb
from utils.admins import is_admin, is_super_admin, refresh_admins
from utils.commands import reset_commands, set_admin_commands

router = admin_router()

LIST_TEXT = (
    "👮 <b>Adminlar</b>\n\n"
    "⭐ — <code>.env</code> dagi asosiy admin (paneldan o'chirilmaydi)\n"
    "👤 — panel orqali qo'shilgan admin"
)

ADD_TEXT = (
    "➕ <b>Admin qo'shish</b>\n\n"
    "Yangi adminning <b>telegram ID</b> raqamini yuboring.\n"
    "Masalan: <code>123456789</code>\n\n"
    "ID ni <a href=\"https://t.me/userinfobot\">@userinfobot</a> dan olish mumkin.\n"
    "Yoki o'sha odamning xabarini shu yerga <b>forward</b> qiling."
)


async def _show_list(callback: CallbackQuery) -> None:
    admins = await get_admins()
    await edit_or_send(callback, LIST_TEXT, admins_kb(admins, SUPER_ADMINS))


@router.callback_query(F.data == "ad:list")
async def cb_list(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_list(callback)
    await callback.answer()


@router.callback_query(F.data == "ad:super")
async def cb_super(callback: CallbackQuery) -> None:
    await callback.answer(
        "⭐ Bu admin .env faylida yozilgan. Uni o'chirish uchun serverdagi "
        ".env faylini tahrirlab, botni qayta ishga tushiring.",
        show_alert=True,
    )


async def _show_one(callback: CallbackQuery, admin_id: int) -> None:
    admin = await get_admin(admin_id)
    if admin is None:
        await _show_list(callback)
        return
    created = admin.created_at.astimezone(TZ).strftime("%d.%m.%Y %H:%M") if admin.created_at else "—"
    text = (
        "👤 <b>Admin</b>\n\n"
        f"Ismi: <b>{escape(admin.full_name) or '—'}</b>\n"
        f"Username: {('@' + admin.username) if admin.username else '—'}\n"
        f"ID: <code>{admin.tg_id}</code>\n"
        f"Qo'shgan: <code>{admin.added_by or '—'}</code>\n"
        f"Sana: {created}"
    )
    await edit_or_send(callback, text, admin_one_kb(admin.id))


@router.callback_query(F.data.startswith("ad:one:"))
async def cb_one(callback: CallbackQuery) -> None:
    await _show_one(callback, int(callback.data.split(":")[2]))
    await callback.answer()


# ------------------------------------------------------------------- qo'shish
@router.callback_query(F.data == "ad:add")
async def cb_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminSG.waiting_id)
    await edit_or_send(callback, ADD_TEXT, cancel_kb())
    await callback.answer()


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


@router.message(AdminSG.waiting_id)
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
    admin, created = await add_admin(
        tg_id=tg_id,
        full_name=full_name,
        username=username,
        added_by=message.from_user.id,
    )
    await refresh_admins()
    await state.clear()

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

    admins = await get_admins()
    await message.answer(LIST_TEXT, reply_markup=admins_kb(admins, SUPER_ADMINS))


# ------------------------------------------------------------------- o'chirish
@router.callback_query(F.data.startswith("ad:del:"))
async def cb_delete_ask(callback: CallbackQuery) -> None:
    admin_id = int(callback.data.split(":")[2])
    await edit_or_send(
        callback, "🗑 Bu odam adminlikdan olinsinmi?", admin_delete_kb(admin_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ad:delok:"))
async def cb_delete(callback: CallbackQuery) -> None:
    tg_id = await delete_admin(int(callback.data.split(":")[2]))
    await refresh_admins()
    if tg_id is not None and not is_admin(tg_id):
        await reset_commands(callback.bot, tg_id)
    await callback.answer("🗑 Adminlikdan olindi")
    await _show_list(callback)
