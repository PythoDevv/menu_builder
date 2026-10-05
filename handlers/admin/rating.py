"""Asosiy menyudagi reyting tugmasi va top foydalanuvchilar posti sozlamalari."""

from html import escape

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import LinkPreviewOptions, Message

from db.queries import (
    delete_rating_message,
    get_items,
    get_my_points_settings,
    get_rating_settings,
    get_top_referrers,
    set_rating_enabled,
    set_rating_message,
    set_rating_row_size,
    set_rating_style,
    set_rating_text,
)
from handlers.admin.common import NOT_COMMAND, admin_router
from handlers.admin.states import PanelSG, RatingSG
from keyboards.admin_kb import (
    BUTTON_ROW_SIZE_OPTIONS,
    BUTTON_STYLE_OPTIONS,
    BTN_BACK,
    BTN_NO,
    BTN_OFF,
    BTN_ON,
    BTN_RATING,
    BTN_RATING_MESSAGE,
    BTN_RATING_MESSAGE_RESET,
    BTN_RATING_RENAME,
    BTN_RATING_ROW_SIZE,
    BTN_RATING_STYLE,
    BTN_VIEW,
    BTN_YES_DELETE,
    button_style_kb,
    button_style_label,
    cancel_kb,
    confirm_delete_kb,
    rating_settings_kb,
    row_size_kb,
    row_size_label,
)
from keyboards.user_kb import BTN_BACK as USER_BACK
from keyboards.user_kb import BTN_HOME as USER_HOME
from keyboards.user_kb import menu_kb
from utils.content import extract_button_text_and_icon
from utils.rating import MAX_RATING_USERS, rating_limits, render_rating_text
from utils.texts import DEFAULT_RATING_MESSAGE

router = admin_router()


async def _render_current(template: str) -> str:
    limits = rating_limits(template)
    top = await get_top_referrers(max(limits, default=10))
    return render_rating_text(template, top)


async def show_rating(message: Message, state: FSMContext) -> None:
    settings = await get_rating_settings()
    enabled = bool(settings["enabled"])
    custom_message = bool(settings["message"])
    icon_status = "✅ bor" if settings["icon_custom_emoji_id"] else "yo'q"
    await state.set_state(RatingSG.show)
    await message.answer(
        "🏅 <b>Reyting tugmasi</b>\n\n"
        f"Holat: <b>{'🟢 KO‘RINADI' if enabled else '🔴 YASHIRILGAN'}</b>\n"
        f"Matni: <b>{escape(str(settings['text']))}</b>\n"
        f"Premium emoji: <b>{icon_status}</b>\n"
        f"Rangi: <b>{button_style_label(settings['style'])}</b>\n"
        f"Joylashuvi: <b>{row_size_label(int(settings['row_size']))}</b>\n\n"
        f"Post: <b>{'admin o‘rnatgan' if custom_message else 'standart matn'}</b>",
        reply_markup=rating_settings_kb(enabled, custom_message),
    )


@router.message(PanelSG.home, F.text == BTN_RATING)
async def open_rating(message: Message, state: FSMContext) -> None:
    await show_rating(message, state)


@router.message(RatingSG.show, F.text.in_({BTN_ON, BTN_OFF}))
async def toggle_rating(message: Message, state: FSMContext) -> None:
    settings = await get_rating_settings()
    await set_rating_enabled(not bool(settings["enabled"]))
    await message.answer("✅ O'zgartirildi")
    await show_rating(message, state)


@router.message(RatingSG.show, F.text == BTN_RATING_RENAME)
async def ask_rating_text(message: Message, state: FSMContext) -> None:
    await state.set_state(RatingSG.waiting_text)
    await message.answer(
        "✏️ Yangi reyting tugmasi nomini yuboring.\n\n"
        "Premium custom emoji ishlatsangiz, uni nom bilan birga yuboring — "
        "birinchi premium emoji tugma ikonkasiga aylanadi.\n\n"
        "Maksimum: 64 ta belgi.",
        reply_markup=cancel_kb(),
    )


@router.message(RatingSG.waiting_text, NOT_COMMAND)
async def save_rating_text(message: Message, state: FSMContext) -> None:
    text, icon_custom_emoji_id = extract_button_text_and_icon(message)
    if not text or len(text) > 64:
        await message.answer(
            "❗️ Tugma nomi bo'sh bo'lmasin va 64 ta belgidan oshmasin.",
            reply_markup=cancel_kb(),
        )
        return
    if text in {USER_BACK, USER_HOME}:
        await message.answer(
            "❗️ Bu matn menyuning xizmat tugmasi uchun band.",
            reply_markup=cancel_kb(),
        )
        return
    root_items = await get_items(None)
    points = await get_my_points_settings()
    if any(item.title == text for item in root_items) or text == points["text"]:
        await message.answer(
            "❗️ Asosiy menyuda bunday nomli tugma bor. Boshqa nom yuboring.",
            reply_markup=cancel_kb(),
        )
        return

    settings = await get_rating_settings()
    try:
        await message.answer(
            "👇 Tugma shunday ko'rinadi:",
            reply_markup=menu_kb(
                [],
                is_root=True,
                my_points_enabled=bool(points["enabled"]),
                my_points_text=str(points["text"]),
                my_points_style=points["style"],
                my_points_icon_custom_emoji_id=points["icon_custom_emoji_id"],
                rating_enabled=True,
                rating_text=text,
                rating_style=settings["style"],
                rating_icon_custom_emoji_id=icon_custom_emoji_id,
                rating_row_size=int(settings["row_size"]),
            ),
        )
    except TelegramBadRequest:
        await message.answer(
            "❗️ Telegram premium emojini tugmada qabul qilmadi. Bot egasida "
            "Telegram Premium faol ekanini tekshiring yoki oddiy emoji yuboring.",
            reply_markup=cancel_kb(),
        )
        return
    await set_rating_text(text, icon_custom_emoji_id)
    await message.answer("✅ Reyting tugmasi matni saqlandi")
    await show_rating(message, state)


@router.message(RatingSG.show, F.text == BTN_RATING_MESSAGE)
async def ask_rating_message(message: Message, state: FSMContext) -> None:
    settings = await get_rating_settings()
    template = str(settings["message"] or DEFAULT_RATING_MESSAGE)
    await state.set_state(RatingSG.waiting_message)
    await message.answer(
        "📝 <b>Reyting posti</b>\n\n"
        "Yangi matnni Telegram formatida yuboring. Premium custom emoji, qalin, "
        "kursiv va havolalar saqlanadi.\n\n"
        "<code>{users-10}</code> — eng ko'p taklif qilgan 10 kishi. 10 o'rniga "
        f"1 dan {MAX_RATING_USERS} gacha son yozish mumkin.\n\n"
        "Kalitning tepasi va pastida avtomatik ravishda bittadan bo'sh qator qoladi.",
        reply_markup=cancel_kb(),
    )
    await message.answer("👇 Hozirgi ko'rinish:")
    await message.answer(
        await _render_current(template),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.message(RatingSG.waiting_message, NOT_COMMAND)
async def save_rating_message(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(
            "❗️ Matn yuboring. Premium emoji matn ichida bo'lishi kerak.",
            reply_markup=cancel_kb(),
        )
        return
    if len(message.text) > 2000:
        await message.answer("❗️ Matn 2000 ta belgidan oshmasin.", reply_markup=cancel_kb())
        return

    template = message.html_text
    if not rating_limits(template):
        await message.answer(
            "❗️ Matnda kamida bitta <code>{users-10}</code> ko'rinishidagi kalit "
            "bo'lishi shart.",
            reply_markup=cancel_kb(),
        )
        return

    rendered = await _render_current(template)
    try:
        await message.answer(
            rendered,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except TelegramBadRequest:
        await message.answer(
            "❗️ Post saqlanmadi. Matn juda uzun yoki format/premium emoji Telegram "
            "tomonidan qabul qilinmadi.",
            reply_markup=cancel_kb(),
        )
        return
    await set_rating_message(template)
    await message.answer("✅ Reyting posti saqlandi")
    await show_rating(message, state)


@router.message(RatingSG.show, F.text == BTN_VIEW)
async def preview_rating(message: Message, state: FSMContext) -> None:
    settings = await get_rating_settings()
    template = str(settings["message"] or DEFAULT_RATING_MESSAGE)
    await message.answer("👇 Foydalanuvchi shu ko'rinishda ko'radi:")
    await message.answer(
        await _render_current(template),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await show_rating(message, state)


@router.message(RatingSG.show, F.text == BTN_RATING_MESSAGE_RESET)
async def ask_reset_rating(message: Message, state: FSMContext) -> None:
    await state.set_state(RatingSG.confirm_message_reset)
    await message.answer(
        "♻️ Reyting posti standart matnga qaytarilsinmi?",
        reply_markup=confirm_delete_kb(),
    )
@router.message(RatingSG.confirm_message_reset, F.text == BTN_YES_DELETE)
async def reset_rating(message: Message, state: FSMContext) -> None:
    await delete_rating_message()
    await message.answer("♻️ Standart reyting postiga qaytarildi")
    await show_rating(message, state)


@router.message(RatingSG.confirm_message_reset, F.text == BTN_NO)
async def cancel_reset_rating(message: Message, state: FSMContext) -> None:
    await show_rating(message, state)


@router.message(RatingSG.show, F.text == BTN_RATING_STYLE)
async def ask_rating_style(message: Message, state: FSMContext) -> None:
    settings = await get_rating_settings()
    await state.set_state(RatingSG.style)
    await message.answer(
        "🎨 <b>Reyting tugmasi rangi</b>\n\n"
        f"Hozir: <b>{button_style_label(settings['style'])}</b>",
        reply_markup=button_style_kb(),
    )


@router.message(RatingSG.style, F.text.in_(set(BUTTON_STYLE_OPTIONS)))
async def save_rating_style(message: Message, state: FSMContext) -> None:
    style = BUTTON_STYLE_OPTIONS[message.text]
    await set_rating_style(style)
    await message.answer(f"✅ Tugma rangi: <b>{button_style_label(style)}</b>")
    await show_rating(message, state)


@router.message(RatingSG.style, F.text == BTN_BACK)
async def rating_style_back(message: Message, state: FSMContext) -> None:
    await show_rating(message, state)


@router.message(RatingSG.show, F.text == BTN_RATING_ROW_SIZE)
async def ask_rating_row_size(message: Message, state: FSMContext) -> None:
    settings = await get_rating_settings()
    await state.set_state(RatingSG.row_size)
    await message.answer(
        "🧩 <b>Reyting tugmasi joylashuvi</b>\n\n"
        f"Hozir: <b>{row_size_label(int(settings['row_size']))}</b>\n\n"
        "2 talik tanlansa Ballarim va Reyting odatda yonma-yon chiqadi. "
        "Ketma-ket turgan bir xil joylashuvli menyu tugmalari ham shu qatorni "
        "to'ldirishi mumkin.",
        reply_markup=row_size_kb(),
    )


@router.message(RatingSG.row_size, F.text.in_(set(BUTTON_ROW_SIZE_OPTIONS)))
async def save_rating_row_size(message: Message, state: FSMContext) -> None:
    row_size = BUTTON_ROW_SIZE_OPTIONS[message.text]
    await set_rating_row_size(row_size)
    await message.answer(f"✅ Joylashuvi: <b>{row_size_label(row_size)}</b>")
    await show_rating(message, state)


@router.message(RatingSG.row_size, F.text == BTN_BACK)
async def rating_row_size_back(message: Message, state: FSMContext) -> None:
    await show_rating(message, state)
