from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db.queries import get_stats
from handlers.admin.common import HOME_TEXT, admin_router, edit_or_send, show_home
from keyboards.admin_kb import admin_home_kb

router = admin_router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HOME_TEXT, reply_markup=admin_home_kb())


@router.callback_query(F.data == "adm:home")
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_home(callback)
    await callback.answer()


@router.callback_query(F.data == "adm:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show_home(callback)
    await callback.answer("❌ Bekor qilindi")


@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery) -> None:
    s = await get_stats()
    text = (
        "👥 <b>Statistika</b>\n\n"
        f"Jami: <b>{s['total']}</b> ta\n"
        f"Faol: <b>{s['active']}</b> ta\n"
        f"Bloklaganlar: <b>{s['total'] - s['active']}</b> ta\n"
        f"Raqam qoldirgan: <b>{s['with_phone']}</b> ta\n\n"
        f"Bugun qo'shilgan: <b>{s['today']}</b> ta\n"
        f"7 kunda: <b>{s['week']}</b> ta"
    )
    await edit_or_send(callback, text, admin_home_kb())
    await callback.answer()
