import asyncio
import logging

from aiogram import Bot, F
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import BROADCAST_DELAY
from db.queries import get_active_user_ids, set_user_active
from handlers.admin.common import NOT_COMMAND, admin_router, show_home
from handlers.admin.states import BroadcastSG, PanelSG
from keyboards.admin_kb import (
    BTN_BC_SEND,
    BTN_BROADCAST,
    broadcast_confirm_kb,
    cancel_kb,
)

router = admin_router()
logger = logging.getLogger(__name__)

ASK_TEXT = (
    "📨 <b>Hammaga xabar</b>\n\n"
    "Yubormoqchi bo'lgan xabaringizni shu yerga tashlang.\n"
    "Matn, rasm, video, fayl — hammasi bo'ladi."
)


@router.message(PanelSG.home, F.text == BTN_BROADCAST)
async def ask_message(message: Message, state: FSMContext) -> None:
    await state.set_state(BroadcastSG.waiting_message)
    await message.answer(ASK_TEXT, reply_markup=cancel_kb())


@router.message(BroadcastSG.waiting_message, NOT_COMMAND)
async def got_message(message: Message, state: FSMContext) -> None:
    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(BroadcastSG.confirm)
    total = len(await get_active_user_ids())
    await message.answer(
        f"👆 Shu xabar <b>{total}</b> ta foydalanuvchiga yuboriladi.\n\nTasdiqlaysizmi?",
        reply_markup=broadcast_confirm_kb(),
    )


async def _send_one(bot: Bot, user_id: int, from_chat_id: int, message_id: int) -> str:
    """Natija: 'sent' | 'blocked' | 'failed'."""
    try:
        await bot.copy_message(user_id, from_chat_id, message_id)
        return "sent"
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await bot.copy_message(user_id, from_chat_id, message_id)
            return "sent"
        except TelegramAPIError:
            return "failed"
    except TelegramForbiddenError:
        return "blocked"
    except TelegramBadRequest as e:
        return "blocked" if "chat not found" in str(e).lower() else "failed"
    except TelegramAPIError:
        return "failed"


@router.message(BroadcastSG.confirm, F.text == BTN_BC_SEND)
async def send_all(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    if not from_chat_id or not message_id:
        await show_home(message, state, "❗️ Xabar topilmadi, qaytadan boshlang.")
        return

    users = await get_active_user_ids()
    status = await message.answer(f"📨 Yuborilmoqda... 0/{len(users)}")

    sent = blocked = failed = 0
    for i, user_id in enumerate(users, start=1):
        result = await _send_one(message.bot, user_id, from_chat_id, message_id)
        if result == "sent":
            sent += 1
        elif result == "blocked":
            blocked += 1
            await set_user_active(user_id, False)
        else:
            failed += 1

        if i % 30 == 0:
            try:
                await status.edit_text(f"📨 Yuborilmoqda... {i}/{len(users)}")
            except TelegramAPIError:
                pass
        await asyncio.sleep(BROADCAST_DELAY)

    logger.info("Broadcast: sent=%s blocked=%s failed=%s", sent, blocked, failed)
    await show_home(
        message,
        state,
        "✅ <b>Yuborish tugadi</b>\n\n"
        f"Yuborildi: <b>{sent}</b>\n"
        f"Bloklaganlar: <b>{blocked}</b>\n"
        f"Xatolik: <b>{failed}</b>\n"
        f"Jami: <b>{len(users)}</b>",
    )
