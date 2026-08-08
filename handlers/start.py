from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from db.queries import get_items, get_start_message, set_phone
from keyboards.user_kb import nav_kb, phone_kb
from utils.content import send_raw_content

router = Router()

EMPTY_TEXT = "⚠️ Hozircha menyu bo'sh. Keyinroq urinib ko'ring."
MENU_TEXT = "🏠 Asosiy menyu"


async def send_start_screen(bot: Bot, chat_id: int) -> None:
    """Start xabar (agar bor bo'lsa) + asosiy menyu tugmalari."""
    start_msg = await get_start_message()
    items = await get_items(None, active_only=True)
    kb = nav_kb(items, back_to=None) if items else None

    if start_msg:
        await send_raw_content(bot, chat_id, start_msg, reply_markup=kb)
        if not items:
            await bot.send_message(chat_id, EMPTY_TEXT)
    else:
        await bot.send_message(chat_id, MENU_TEXT if items else EMPTY_TEXT, reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_start_screen(message.bot, message.chat.id)


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery) -> None:
    # bu yergacha yetib kelgan bo'lsa — obuna tekshiruvidan o'tgan
    await callback.answer("✅ Rahmat!")
    with suppress(TelegramBadRequest):
        await callback.message.delete()
    await send_start_screen(callback.bot, callback.message.chat.id)


@router.message(F.contact)
async def get_contact(message: Message) -> None:
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
    await send_start_screen(message.bot, message.chat.id)
