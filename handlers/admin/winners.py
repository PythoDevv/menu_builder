"""G'oliblar hisoboti va Telegram ID bo'yicha shaxsiy xabar yuborish."""

from html import escape

from aiogram import F
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.models import User
from db.queries import (
    MAX_WINNERS_LIMIT,
    get_referral_count,
    get_top_referrers,
    get_user,
    get_winners_limit,
    set_user_active,
    set_winners_limit,
)
from handlers.admin.common import KEY_ITEM, NOT_COMMAND, admin_router
from handlers.admin.states import PanelSG, WinnersSG
from handlers.admin.superadmin import ask_points_reset
from keyboards.admin_kb import (
    BTN_BC_SEND,
    BTN_DIRECT_MESSAGE,
    BTN_WINNERS,
    BTN_WINNERS_BACK,
    BTN_WINNERS_COUNT,
    BTN_WINNERS_RESET,
    BTN_WINNERS_VIEW,
    cancel_kb,
    winner_send_confirm_kb,
    winners_kb,
)
from utils.admins import is_super_admin

router = admin_router()


def render_winners_report(rows: list[tuple[User, int]]) -> str:
    """Barcha so'ralgan maydonlarni bitta ixcham Telegram xabariga joylaydi."""
    if not rows:
        return "🏆 <b>G'oliblar</b>\n\nHozircha ball to'plagan foydalanuvchi yo'q."

    lines = [f"🏆 <b>G'oliblar — TOP {len(rows)}</b>", ""]
    for index, (user, count) in enumerate(rows, start=1):
        name = " ".join((user.full_name or "—").split())
        if len(name) > 48:
            name = name[:47] + "…"
        username = f"@{escape(user.username)}" if user.username else "—"
        lines.append(
            f"{index}. Ismi: <b>{escape(name)}</b> | "
            f"Username: {username} | "
            f"TG ID: <code>{user.tg_id}</code> | "
            f"Ball: <b>{count}</b>"
        )
    return "\n".join(lines)


async def show_winners(message: Message, state: FSMContext) -> None:
    limit = await get_winners_limit()
    await state.set_state(WinnersSG.show)
    can_reset_points = (
        message.from_user is not None and is_super_admin(message.from_user.id)
    )
    await message.answer(
        "🏆 <b>G'oliblar boshqaruvi</b>\n\n"
        f"Bitta xabarda ko'rsatiladigan g'oliblar: <b>{limit}</b> ta.\n\n"
        "📋 Hisobotda har bir g'olibning ismi, username'i, Telegram ID si va "
        "to'plagan balli chiqadi.\n"
        "✉️ ID bo'yicha xabar orqali botdagi istalgan odamga alohida xabar "
        "yuborish mumkin.",
        reply_markup=winners_kb(can_reset_points),
    )


def _user_info(user: User, count: int) -> str:
    username = f"@{escape(user.username)}" if user.username else "—"
    return (
        f"Ismi: <b>{escape(user.full_name) or '—'}</b>\n"
        f"Username: {username}\n"
        f"Telegram ID: <code>{user.tg_id}</code>\n"
        f"To'plagan balli: <b>{count}</b> ta"
    )


@router.message(PanelSG.home, F.text == BTN_WINNERS)
async def open_winners(message: Message, state: FSMContext) -> None:
    await show_winners(message, state)


@router.message(WinnersSG.show, F.text == BTN_WINNERS_VIEW)
async def view_winners(message: Message, state: FSMContext) -> None:
    limit = await get_winners_limit()
    top = await get_top_referrers(limit)
    can_reset_points = (
        message.from_user is not None and is_super_admin(message.from_user.id)
    )
    await message.answer(
        render_winners_report(top), reply_markup=winners_kb(can_reset_points)
    )


@router.message(WinnersSG.show, F.text == BTN_WINNERS_RESET)
async def reset_all_points_from_winners(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_super_admin(message.from_user.id):
        await message.answer("❌ Bu amal faqat superadmin uchun.")
        return
    await ask_points_reset(message, state)


@router.message(WinnersSG.show, F.text == BTN_WINNERS_COUNT)
async def ask_winners_count(message: Message, state: FSMContext) -> None:
    current = await get_winners_limit()
    await state.set_state(WinnersSG.waiting_limit)
    await message.answer(
        "🔢 <b>G'oliblar soni</b>\n\n"
        f"Hozir: <b>{current}</b> ta.\n"
        f"Bitta xabarga chiqarish uchun 1 dan {MAX_WINNERS_LIMIT} gacha son yuboring.",
        reply_markup=cancel_kb(),
    )


@router.message(WinnersSG.waiting_limit, NOT_COMMAND)
async def save_winners_count(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        limit = int(raw)
    except ValueError:
        limit = 0
    if not 1 <= limit <= MAX_WINNERS_LIMIT:
        await message.answer(
            f"❗️ 1 dan {MAX_WINNERS_LIMIT} gacha butun son yuboring.",
            reply_markup=cancel_kb(),
        )
        return
    await set_winners_limit(limit)
    await message.answer(f"✅ G'oliblar soni <b>{limit}</b> ta qilib saqlandi.")
    await show_winners(message, state)


@router.message(WinnersSG.show, F.text == BTN_DIRECT_MESSAGE)
async def ask_target_id(message: Message, state: FSMContext) -> None:
    await state.set_state(WinnersSG.waiting_id)
    await message.answer(
        "✉️ <b>ID bo'yicha xabar</b>\n\n"
        "Xabar yuboriladigan foydalanuvchining Telegram ID raqamini kiriting.\n"
        "Masalan: <code>123456789</code>",
        reply_markup=cancel_kb(),
    )


@router.message(WinnersSG.waiting_id, NOT_COMMAND)
async def receive_target_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(
            "❗️ Telegram ID faqat raqamlardan iborat bo'lishi kerak.",
            reply_markup=cancel_kb(),
        )
        return

    tg_id = int(raw)
    user = await get_user(tg_id)
    if user is None:
        await message.answer(
            "❗️ Bunday ID li foydalanuvchi bot bazasida topilmadi.",
            reply_markup=cancel_kb(),
        )
        return

    count = await get_referral_count(tg_id)
    await state.update_data({KEY_ITEM: tg_id})
    await state.set_state(WinnersSG.waiting_message)
    await message.answer(
        "👤 <b>Qabul qiluvchi topildi</b>\n\n"
        f"{_user_info(user, count)}\n\n"
        "Endi shu odamga yuboriladigan xabarni jo'nating. Matn, rasm, video yoki "
        "fayl yuborish mumkin.",
        reply_markup=cancel_kb(),
    )


@router.message(WinnersSG.waiting_message, NOT_COMMAND)
async def got_direct_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tg_id = data.get(KEY_ITEM)
    user = await get_user(tg_id) if tg_id is not None else None
    if user is None:
        await message.answer("❗️ Qabul qiluvchi topilmadi. ID ni qaytadan kiriting.")
        await show_winners(message, state)
        return

    await state.update_data(
        winner_message_chat_id=message.chat.id,
        winner_message_id=message.message_id,
    )
    await state.set_state(WinnersSG.confirm_send)
    await message.answer(
        "👆 Shu xabar quyidagi odamga yuborilsinmi?\n\n"
        f"{_user_info(user, await get_referral_count(user.tg_id))}",
        reply_markup=winner_send_confirm_kb(),
    )


@router.message(WinnersSG.confirm_send, F.text == BTN_WINNERS_BACK)
async def cancel_direct_message(message: Message, state: FSMContext) -> None:
    await show_winners(message, state)


@router.message(WinnersSG.confirm_send, F.text == BTN_BC_SEND)
async def send_direct_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tg_id = data.get(KEY_ITEM)
    from_chat_id = data.get("winner_message_chat_id")
    message_id = data.get("winner_message_id")
    if not all((tg_id, from_chat_id, message_id)):
        await message.answer("❗️ Qabul qiluvchi yoki xabar ma'lumoti topilmadi.")
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
        await message.answer(
            f"✅ Xabar faqat <code>{tg_id}</code> ID li odamga yuborildi."
        )
    await show_winners(message, state)
