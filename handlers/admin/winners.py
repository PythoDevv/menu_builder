"""Reytingdagi g'oliblar ma'lumoti va tanlangan odamga shaxsiy xabar."""

from html import escape

from aiogram import F
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.queries import get_referral_count, get_top_referrers, get_user, set_user_active
from handlers.admin.common import (
    KEY_ITEM,
    NOT_COMMAND,
    PICK_TEXT,
    admin_router,
    pick_label,
    save_labels,
)
from handlers.admin.states import PanelSG, WinnersSG
from keyboards.admin_kb import (
    BTN_BC_SEND,
    BTN_WINNER_MESSAGE,
    BTN_WINNERS,
    BTN_WINNERS_LIST,
    cancel_kb,
    winner_one_kb,
    winner_send_confirm_kb,
    winners_kb,
)

router = admin_router()
WINNERS_LIMIT = 50


def _winner_label(index: int, name: str, count: int) -> str:
    clean_name = " ".join(name.split())
    if len(clean_name) > 32:
        clean_name = clean_name[:31] + "…"
    return f"{index}. 🏆 {clean_name} — {count} ball"


async def show_winners(message: Message, state: FSMContext) -> None:
    top = await get_top_referrers(WINNERS_LIMIT)
    labels: dict[str, int] = {}
    for index, (user, count) in enumerate(top, start=1):
        name = user.full_name or (f"@{user.username}" if user.username else str(user.tg_id))
        labels[_winner_label(index, name, count)] = user.tg_id

    await state.set_state(WinnersSG.browse)
    await save_labels(state, labels)
    text = (
        "🏆 <b>G'oliblar</b>\n\n"
        "G'olib ustiga bosing — to'liq ma'lumoti ochiladi va aynan o'sha "
        "odamga shaxsiy xabar yuborishingiz mumkin."
        if labels
        else "🏆 <b>G'oliblar</b>\n\nHozircha ball to'plagan foydalanuvchi yo'q."
    )
    await message.answer(text, reply_markup=winners_kb(list(labels)))


async def show_winner(message: Message, state: FSMContext, tg_id: int | None) -> None:
    user = await get_user(tg_id) if tg_id is not None else None
    if user is None:
        await show_winners(message, state)
        return

    count = await get_referral_count(user.tg_id)
    username = f"@{escape(user.username)}" if user.username else "—"
    await state.set_state(WinnersSG.one)
    await state.update_data({KEY_ITEM: user.tg_id})
    await message.answer(
        "🏆 <b>G'olib ma'lumoti</b>\n\n"
        f"Ismi: <b>{escape(user.full_name) or '—'}</b>\n"
        f"Username: {username}\n"
        f"Telegram ID: <code>{user.tg_id}</code>\n"
        f"Telefon: <code>{escape(user.phone) if user.phone else '—'}</code>\n"
        f"Holati: <b>{'faol' if user.is_active else 'botni bloklagan'}</b>\n"
        f"Ballari: <b>{count}</b> ta",
        reply_markup=winner_one_kb(),
    )


@router.message(PanelSG.home, F.text == BTN_WINNERS)
async def open_winners(message: Message, state: FSMContext) -> None:
    await show_winners(message, state)


@router.message(WinnersSG.browse)
async def pick_winner(message: Message, state: FSMContext) -> None:
    tg_id = await pick_label(state, message.text)
    if tg_id is None:
        await message.answer(PICK_TEXT)
        return
    await show_winner(message, state, tg_id)


@router.message(WinnersSG.one, F.text == BTN_WINNERS_LIST)
async def back_to_winners(message: Message, state: FSMContext) -> None:
    await show_winners(message, state)


@router.message(WinnersSG.one, F.text == BTN_WINNER_MESSAGE)
async def ask_winner_message(message: Message, state: FSMContext) -> None:
    await state.set_state(WinnersSG.waiting_message)
    await message.answer(
        "✉️ G'olibga yuboriladigan xabarni jo'nating. Matn, rasm, video yoki "
        "fayl yuborish mumkin.",
        reply_markup=cancel_kb(),
    )


@router.message(WinnersSG.waiting_message, NOT_COMMAND)
async def got_winner_message(message: Message, state: FSMContext) -> None:
    await state.update_data(
        winner_message_chat_id=message.chat.id,
        winner_message_id=message.message_id,
    )
    await state.set_state(WinnersSG.confirm_send)
    await message.answer(
        "👆 Shu xabar faqat tanlangan g'olibga yuborilsinmi?",
        reply_markup=winner_send_confirm_kb(),
    )


@router.message(WinnersSG.confirm_send, F.text == BTN_BC_SEND)
async def send_winner_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tg_id = data.get(KEY_ITEM)
    from_chat_id = data.get("winner_message_chat_id")
    message_id = data.get("winner_message_id")
    if not all((tg_id, from_chat_id, message_id)):
        await message.answer("❗️ G'olib yoki xabar ma'lumoti topilmadi.")
        await show_winners(message, state)
        return

    try:
        await message.bot.copy_message(tg_id, from_chat_id, message_id)
    except TelegramForbiddenError:
        await set_user_active(tg_id, False)
        await message.answer("❌ Xabar yuborilmadi: foydalanuvchi botni bloklagan.")
    except TelegramBadRequest as exc:
        await message.answer(f"❌ Telegram xatosi: {escape(str(exc))}")
    except TelegramAPIError as exc:
        await message.answer(f"❌ Xabar yuborilmadi: {escape(str(exc))}")
    else:
        await message.answer("✅ Xabar aynan shu g'olibga yuborildi.")
    await show_winner(message, state, tg_id)
