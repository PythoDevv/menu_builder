from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from db.queries import get_items, get_menu_columns, get_start_message, set_phone
from handlers.menu import EMPTY_TEXT, KEY_NODE, MENU_TEXT
from keyboards.user_kb import CB_CHECK_SUB, menu_kb, phone_kb
from utils.content import send_raw_content

router = Router()


async def send_start_screen(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """Start xabar (agar bor bo'lsa) + asosiy menyu tugmalari."""
    await state.set_state(None)
    await state.set_data({KEY_NODE: None})

    start_msg = await get_start_message()
    items = await get_items(None, active_only=True)
    kb = menu_kb(items, is_root=True, columns=await get_menu_columns())

    if start_msg:
        await send_raw_content(bot, chat_id, start_msg, reply_markup=kb)
        if not items:
            await bot.send_message(chat_id, EMPTY_TEXT)
    else:
        await bot.send_message(chat_id, MENU_TEXT if items else EMPTY_TEXT, reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await send_start_screen(message.bot, message.chat.id, state)


@router.callback_query(F.data == CB_CHECK_SUB)
async def check_sub(callback: CallbackQuery, state: FSMContext) -> None:
    # bu yergacha yetib kelgan bo'lsa — obuna tekshiruvidan o'tgan
    await callback.answer("✅ Rahmat!")
    chat_id = callback.message.chat.id if callback.message else callback.from_user.id
    if callback.message:
        with suppress(TelegramBadRequest):
            await callback.message.delete()
    await send_start_screen(callback.bot, chat_id, state)


@router.message(F.contact)
async def get_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(
            "❗️ Iltimos, o'zingizning raqamingizni tugma orqali yuboring.",
            reply_markup=phone_kb(),
        )
        return

    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await set_phone(message.from_user.id, phone)
    await message.answer("✅ Raqam saqlandi. Rahmat!", reply_markup=ReplyKeyboardRemove())
    await send_start_screen(message.bot, message.chat.id, state)
