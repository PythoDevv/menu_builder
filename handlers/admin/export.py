from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from config import EXPORT_FILE, EXPORT_HOUR, EXPORT_MINUTE
from db.queries import TZ
from handlers.admin.common import admin_router, edit_or_send
from keyboards.admin_kb import excel_kb
from utils.excel import build_excel

router = admin_router()


async def _show(callback: CallbackQuery) -> None:
    if EXPORT_FILE.exists():
        mtime = datetime.fromtimestamp(EXPORT_FILE.stat().st_mtime, TZ)
        info = f"Oxirgi yangilanish: <b>{mtime:%Y-%m-%d %H:%M}</b>"
    else:
        info = "Fayl hali yaratilmagan."
    text = (
        "📊 <b>Excel</b>\n\n"
        f"{info}\n"
        f"Har kuni <b>{EXPORT_HOUR:02d}:{EXPORT_MINUTE:02d}</b> da avtomatik yangilanadi."
    )
    await edit_or_send(callback, text, excel_kb())


@router.callback_query(F.data == "xl:menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show(callback)
    await callback.answer()


@router.callback_query(F.data == "xl:get")
async def cb_get(callback: CallbackQuery) -> None:
    await callback.answer("📥 Tayyorlanmoqda...")
    if not EXPORT_FILE.exists():
        await build_excel()
    await callback.bot.send_document(
        callback.message.chat.id,
        FSInputFile(EXPORT_FILE, filename="users.xlsx"),
        caption="📊 Foydalanuvchilar ro'yxati",
    )


@router.callback_query(F.data == "xl:refresh")
async def cb_refresh(callback: CallbackQuery) -> None:
    await callback.answer("🔄 Yangilanmoqda...")
    await build_excel()
    await callback.bot.send_document(
        callback.message.chat.id,
        FSInputFile(EXPORT_FILE, filename="users.xlsx"),
        caption="✅ Excel yangilandi",
    )
    await _show(callback)
