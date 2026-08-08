import asyncio
import logging

from aiogram import Bot, F
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import BROADCAST_DELAY
from db.queries import get_active_user_ids, set_user_active
from handlers.admin.common import admin_router, edit_or_send
from handlers.admin.states import BroadcastSG
from keyboards.admin_kb import admin_home_kb, broadcast_confirm_kb, cancel_kb

router = admin_router()
logger = logging.getLogger(__name__)

ASK_TEXT = (
    "📨 <b>Hammaga xabar</b>\n\n"
    "Yubormoqchi bo'lgan xabaringizni shu yerga tashlang.\n"
    "Matn, rasm, video, fayl — hammasi bo'ladi."
)


@router.callback_query(F.data == "adm:send")
async def cb_send(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastSG.waiting_message)
    await edit_or_send(callback, ASK_TEXT, cancel_kb())
    await callback.answer()


@router.message(BroadcastSG.waiting_message, ~CommandStart())
async def got_message(message: Message, state: FSMContext) -> None:
    await state.update_data(from_chat_id=message.chat.id, message_id=message.message_id)
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


@router.callback_query(F.data == "bc:go")
async def cb_go(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()

    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    if not from_chat_id or not message_id:
        await callback.answer("❗️ Xabar topilmadi, qaytadan boshlang", show_alert=True)
        return

    users = await get_active_user_ids()
    await callback.answer()
    status = await callback.message.answer(f"📨 Yuborilmoqda... 0/{len(users)}")

    sent = blocked = failed = 0
    for i, user_id in enumerate(users, start=1):
        result = await _send_one(callback.bot, user_id, from_chat_id, message_id)
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

    report = (
        "✅ <b>Yuborish tugadi</b>\n\n"
        f"Yuborildi: <b>{sent}</b>\n"
        f"Bloklaganlar: <b>{blocked}</b>\n"
        f"Xatolik: <b>{failed}</b>\n"
        f"Jami: <b>{len(users)}</b>"
    )
    try:
        await status.edit_text(report, reply_markup=admin_home_kb())
    except TelegramAPIError:
        await callback.message.answer(report, reply_markup=admin_home_kb())
    logger.info("Broadcast: sent=%s blocked=%s failed=%s", sent, blocked, failed)
