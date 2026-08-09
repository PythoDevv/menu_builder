from datetime import datetime

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from config import EXPORT_FILE, EXPORT_HOUR, EXPORT_MINUTE
from db.queries import TZ
from handlers.admin.common import admin_router
from handlers.admin.states import ExcelSG, PanelSG
from keyboards.admin_kb import BTN_EXCEL, BTN_XL_GET, BTN_XL_REFRESH, excel_kb
from utils.excel import build_excel

router = admin_router()


async def show(message: Message, state: FSMContext) -> None:
    if EXPORT_FILE.exists():
        mtime = datetime.fromtimestamp(EXPORT_FILE.stat().st_mtime, TZ)
        info = f"Oxirgi yangilanish: <b>{mtime:%Y-%m-%d %H:%M}</b>"
    else:
        info = "Fayl hali yaratilmagan."
    await state.set_state(ExcelSG.show)
    await message.answer(
        "📊 <b>Excel</b>\n\n"
        f"{info}\n"
        f"Har kuni <b>{EXPORT_HOUR:02d}:{EXPORT_MINUTE:02d}</b> da avtomatik yangilanadi.",
        reply_markup=excel_kb(),
    )


@router.message(PanelSG.home, F.text == BTN_EXCEL)
async def open_excel(message: Message, state: FSMContext) -> None:
    await show(message, state)


@router.message(ExcelSG.show, F.text == BTN_XL_GET)
async def get_file(message: Message, state: FSMContext) -> None:
    await message.answer("📥 Tayyorlanmoqda...")
    if not EXPORT_FILE.exists():
        await build_excel()
    await message.answer_document(
        FSInputFile(EXPORT_FILE, filename="users.xlsx"),
        caption="📊 Foydalanuvchilar ro'yxati",
        reply_markup=excel_kb(),
    )


@router.message(ExcelSG.show, F.text == BTN_XL_REFRESH)
async def refresh(message: Message, state: FSMContext) -> None:
    await message.answer("🔄 Yangilanmoqda...")
    await build_excel()
    await message.answer_document(
        FSInputFile(EXPORT_FILE, filename="users.xlsx"),
        caption="✅ Excel yangilandi",
    )
    await show(message, state)
