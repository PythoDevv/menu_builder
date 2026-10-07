"""Faqat `.env` dagi adminlar uchun xavfli DB amallari."""

import asyncio
from datetime import datetime
from html import escape
from pathlib import Path

from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import DUMPS_DIR
from db.base import close_db, init_db
from db.queries import TZ, reset_referral_points
from db_backup import BackupError, create_backup, list_backups, restore_backup
from handlers.admin.common import super_admin_router
from handlers.admin.states import SuperAdminSG
from keyboards.admin_kb import (
    BTN_CONFIRM_RESET,
    BTN_CONFIRM_RESTORE,
    BTN_DUMPS,
    BTN_POINTS_RESET,
    BTN_RESTORE,
    BTN_SUPER_ADMIN,
    dump_one_kb,
    dumps_kb,
    reset_points_confirm_kb,
    restore_confirm_kb,
    super_admin_kb,
)
from utils.admins import refresh_admins
from utils.excel import build_excel
from utils.maintenance import maintenance_mode
from utils.subscription import clear_cache

router = super_admin_router()

KEY_DUMP_NAMES = "super_dump_names"
KEY_DUMP_NAME = "super_dump_name"
_maintenance_lock = asyncio.Lock()


async def show_home(message: Message, state: FSMContext) -> None:
    await state.set_data({})
    await state.set_state(SuperAdminSG.home)
    await message.answer(
        "🔐 <b>Superadmin panel</b>\n\n"
        "Bu bo'lim faqat <code>.env</code> dagi ADMINS ro'yxatiga ko'rinadi.\n\n"
        "⚠️ Ballarni nolga tushirish va bazani restore qilishdan oldin bot "
        "avtomatik xavfsizlik dumpini yaratadi.",
        reply_markup=super_admin_kb(),
    )


def _dump_label(index: int, path: Path) -> str:
    size_mb = path.stat().st_size / (1024 * 1024)
    return f"{index}. 🗄 {path.name} ({size_mb:.2f} MB)"


async def show_dumps(message: Message, state: FSMContext) -> None:
    backups = list_backups()
    labels = [_dump_label(i, path) for i, path in enumerate(backups, start=1)]
    await state.set_state(SuperAdminSG.dumps)
    await state.update_data(
        {
            KEY_DUMP_NAMES: [path.name for path in backups],
            KEY_DUMP_NAME: None,
        }
    )
    await message.answer(
        "🗄 <b>Database dumplari</b>\n\n"
        + ("Eng yangi dump tepada. Tiklash uchun birini tanlang." if backups else "Dump topilmadi."),
        reply_markup=dumps_kb(labels),
    )


async def show_dump(message: Message, state: FSMContext, path: Path) -> None:
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, TZ)
    await state.set_state(SuperAdminSG.dumps)
    await state.update_data({KEY_DUMP_NAME: path.name})
    await message.answer(
        "🗄 <b>Tanlangan dump</b>\n\n"
        f"Fayl: <code>{escape(path.name)}</code>\n"
        f"Hajmi: <b>{stat.st_size / (1024 * 1024):.2f} MB</b>\n"
        f"Fayl vaqti: <b>{modified:%Y-%m-%d %H:%M:%S}</b>",
        reply_markup=dump_one_kb(),
    )


def _selected_dump(data: dict) -> Path | None:
    name = data.get(KEY_DUMP_NAME)
    if not isinstance(name, str):
        return None
    candidate = DUMPS_DIR / name
    return candidate if candidate in list_backups() else None


@router.message(Command("superadmin"))
async def cmd_superadmin(message: Message, state: FSMContext) -> None:
    await show_home(message, state)


@router.message(StateFilter(*SuperAdminSG.__all_states__), F.text == BTN_SUPER_ADMIN)
async def back_home(message: Message, state: FSMContext) -> None:
    await show_home(message, state)


@router.message(SuperAdminSG.home, F.text == BTN_DUMPS)
@router.message(SuperAdminSG.dumps, F.text == BTN_DUMPS)
@router.message(SuperAdminSG.restore_confirm, F.text == BTN_DUMPS)
async def open_dumps(message: Message, state: FSMContext) -> None:
    await show_dumps(message, state)


@router.message(SuperAdminSG.dumps, F.text == BTN_RESTORE)
async def ask_restore(message: Message, state: FSMContext) -> None:
    path = _selected_dump(await state.get_data())
    if path is None:
        await message.answer("❗️ Dump topilmadi yoki ro'yxat o'zgargan.")
        await show_dumps(message, state)
        return
    await state.set_state(SuperAdminSG.restore_confirm)
    await message.answer(
        "⚠️ <b>DIQQAT</b>\n\n"
        f"Joriy baza <code>{escape(path.name)}</code> holatiga qaytariladi. "
        "Avval joriy bazaning yana bitta xavfsizlik dumpi olinadi.\n\n"
        "Amal davomida botga xabar yubormang.",
        reply_markup=restore_confirm_kb(),
    )


@router.message(SuperAdminSG.dumps)
async def pick_dump(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    try:
        index = int(text.split(".", maxsplit=1)[0]) - 1
    except (ValueError, IndexError):
        await message.answer("❗️ Ro'yxatdagi dump tugmasini tanlang.")
        return
    names = (await state.get_data()).get(KEY_DUMP_NAMES) or []
    if not 0 <= index < len(names):
        await message.answer("❗️ Dump topilmadi. Ro'yxatni qayta oching.")
        return
    path = DUMPS_DIR / names[index]
    if path not in list_backups():
        await message.answer("❗️ Dump fayli endi mavjud emas.")
        await show_dumps(message, state)
        return
    await show_dump(message, state, path)


@router.message(SuperAdminSG.home, F.text == BTN_POINTS_RESET)
async def ask_points_reset(message: Message, state: FSMContext) -> None:
    await state.set_state(SuperAdminSG.reset_confirm)
    await message.answer(
        "⚠️ <b>Barcha ballar nolga tushiriladi</b>\n\n"
        "Barcha foydalanuvchilarning taklif bog'lanishlari tozalanadi. Amal oldidan "
        "to'liq database dump olinadi; kerak bo'lsa Dumplar bo'limidan qaytariladi.",
        reply_markup=reset_points_confirm_kb(),
    )


@router.message(SuperAdminSG.reset_confirm, F.text == BTN_CONFIRM_RESET)
async def reset_points(message: Message, state: FSMContext) -> None:
    if _maintenance_lock.locked():
        await message.answer("⏳ Boshqa database amali tugashini kuting.")
        return
    async with _maintenance_lock, maintenance_mode():
        status = await message.answer("⏳ Xavfsizlik dumpi olinmoqda...")
        try:
            backup = await asyncio.to_thread(create_backup, reason="pre_points_reset")
        except (BackupError, OSError) as exc:
            await status.edit_text(
                "❌ Ballarga tegilmadi. Dump yaratish bajarilmadi:\n"
                f"<code>{escape(str(exc))}</code>"
            )
            await show_home(message, state)
            return
        try:
            changed = await reset_referral_points()
        except Exception as exc:
            await status.edit_text(
                "❌ Dump olindi, lekin ballarni tozalash bajarilmadi:\n"
                f"<code>{escape(str(exc))}</code>\n\n"
                f"Dump: <code>{escape(backup.name)}</code>"
            )
            await show_home(message, state)
            return
        try:
            await build_excel()
        except Exception:
            # Excel yordamchi nusxa; DB resetining muvaffaqiyatiga ta'sir qilmaydi.
            pass
        await status.edit_text(
            "✅ Ballar nolga tushirildi.\n\n"
            f"Tozalangan takliflar: <b>{changed}</b> ta\n"
            f"Qaytarish dumpi: <code>{escape(backup.name)}</code>"
        )
    await show_home(message, state)


@router.message(SuperAdminSG.restore_confirm, F.text == BTN_CONFIRM_RESTORE)
async def restore_selected(message: Message, state: FSMContext) -> None:
    path = _selected_dump(await state.get_data())
    if path is None:
        await message.answer("❗️ Tanlangan dump topilmadi.")
        await show_dumps(message, state)
        return
    if _maintenance_lock.locked():
        await message.answer("⏳ Boshqa database amali tugashini kuting.")
        return

    async with _maintenance_lock, maintenance_mode():
        status = await message.answer("⏳ Joriy bazaning xavfsizlik dumpi olinmoqda...")
        try:
            safety = await asyncio.to_thread(create_backup, reason="pre_restore")
        except (BackupError, OSError) as exc:
            await status.edit_text(
                "❌ Restore boshlanmadi; joriy baza o'zgarmadi:\n"
                f"<code>{escape(str(exc))}</code>"
            )
            await show_home(message, state)
            return

        await status.edit_text(
            f"⏳ Xavfsizlik dumpi: <code>{escape(safety.name)}</code>\n"
            f"Tiklanmoqda: <code>{escape(path.name)}</code>"
        )
        await close_db()
        restore_error: Exception | None = None
        try:
            await asyncio.to_thread(restore_backup, path)
        except Exception as exc:  # qayta ulanish finally'da baribir bajarilishi shart
            restore_error = exc
        finally:
            try:
                await init_db()
                await refresh_admins()
                clear_cache()
            except Exception as reconnect_exc:
                restore_error = restore_error or reconnect_exc

        if restore_error is not None:
            await status.edit_text(
                "❌ Restore to'liq tugamadi. Bot bazaga qayta ulandi, xavfsizlik "
                f"dumpi: <code>{escape(safety.name)}</code>\n\n"
                f"Xato: <code>{escape(str(restore_error))}</code>"
            )
            await show_home(message, state)
            return

        try:
            await build_excel()
        except Exception:
            pass
        await status.edit_text(
            "✅ Database muvaffaqiyatli tiklandi.\n\n"
            f"Tiklangan dump: <code>{escape(path.name)}</code>\n"
            f"Restore oldi xavfsizlik dumpi: <code>{escape(safety.name)}</code>"
        )
    await show_home(message, state)
