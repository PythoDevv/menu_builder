"""Admin panelning bosh sahifasi va barcha ekranlarda ishlaydigan tugmalar."""

from html import escape

from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.queries import get_stats, get_top_referrers
from handlers.admin.common import (
    HOME_TEXT,
    NOT_COMMAND,
    PICK_TEXT,
    admin_router,
    show_home,
)
from handlers.admin.states import ALL_STATES, PanelSG
from handlers.start import send_start_screen
from keyboards.admin_kb import BTN_CANCEL, BTN_EXIT, BTN_HOME, BTN_STATS, admin_home_kb

#: Global tugmalar — routerlar orasida birinchi turadi
router = admin_router()

#: Tanilmagan xabar — admin routerlari orasida oxirgi turadi
fallback_router = admin_router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await show_home(message, state)


@router.message(StateFilter(*ALL_STATES), F.text == BTN_HOME)
async def btn_home(message: Message, state: FSMContext) -> None:
    await show_home(message, state)


@router.message(StateFilter(*ALL_STATES), F.text == BTN_CANCEL)
async def btn_cancel(message: Message, state: FSMContext) -> None:
    await show_home(message, state, "❌ Bekor qilindi.\n\n" + HOME_TEXT)


@router.message(StateFilter(*ALL_STATES), F.text == BTN_EXIT)
async def btn_exit(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🚪 Admin paneldan chiqdingiz.")
    await send_start_screen(message.bot, message.chat.id, state)


@router.message(PanelSG.home, F.text == BTN_STATS)
async def btn_stats(message: Message) -> None:
    s = await get_stats()
    lines = [
        "👥 <b>Statistika</b>",
        "",
        f"Jami: <b>{s['total']}</b> ta",
        f"Faol: <b>{s['active']}</b> ta",
        f"Bloklaganlar: <b>{s['total'] - s['active']}</b> ta",
        f"Raqam qoldirgan: <b>{s['with_phone']}</b> ta",
        "",
        f"🔗 Taklif orqali kelgan: <b>{s['referred']}</b> ta",
        f"👤 Odam taklif qilganlar: <b>{s['inviters']}</b> ta",
    ]

    top = await get_top_referrers()
    if top:
        lines.append("")
        lines.append("🏆 <b>Eng ko'p taklif qilganlar</b>")
        for i, (user, count) in enumerate(top, start=1):
            name = user.full_name or (f"@{user.username}" if user.username else str(user.tg_id))
            lines.append(f"{i}. {escape(name)} — <b>{count}</b> ta")

    await message.answer("\n".join(lines), reply_markup=admin_home_kb())


@fallback_router.message(StateFilter(*ALL_STATES), NOT_COMMAND)
async def unknown(message: Message) -> None:
    """Admin panelda tanilmagan xabar — oddiy menyuga tushib ketmasin."""
    await message.answer(PICK_TEXT)
