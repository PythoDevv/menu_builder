from html import escape

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.queries import (
    delete_start_message,
    delete_sub_message,
    get_channels,
    get_items,
    get_menu_columns,
    get_start_message,
    get_sub_message,
    is_phone_required,
    set_menu_columns,
    set_start_message,
    set_sub_message,
    toggle_phone_required,
)
from handlers.admin.common import NOT_COMMAND, admin_router
from handlers.admin.states import LayoutSG, PanelSG, PhoneSG, StartSG, SubSG
from keyboards.admin_kb import (
    BTN_DELETE,
    BTN_LAYOUT,
    BTN_LT_ONE,
    BTN_LT_TWO,
    BTN_NO,
    BTN_OFF,
    BTN_ON,
    BTN_PHONE,
    BTN_ST_ADD,
    BTN_ST_EDIT,
    BTN_START_MSG,
    BTN_SUB_MSG,
    BTN_SUB_RESET,
    BTN_VIEW,
    BTN_YES_DELETE,
    cancel_kb,
    confirm_delete_kb,
    layout_kb,
    phone_settings_kb,
    start_msg_kb,
    sub_msg_kb,
)
from keyboards.user_kb import SHORT_TITLE, menu_kb, subscribe_kb, title_width
from utils.content import TYPE_LABELS, extract_content, send_raw_content
from utils.texts import DEFAULT_SUB_MESSAGE

router = admin_router()

EDIT_TEXT = (
    "✏️ <b>Start xabar</b>\n\n"
    "Yangi start xabarni yuboring — matn, rasm, video yoki fayl.\n"
    "Formatlash o'zgarmasdan saqlanadi."
)


# -------------------------------------------------------------------- START XABAR
async def show_start(message: Message, state: FSMContext) -> None:
    data = await get_start_message()
    if data:
        text = (
            "✏️ <b>Start xabar</b>\n\n"
            f"Turi: {TYPE_LABELS.get(data['type'], data['type'])}\n"
            "Foydalanuvchi /start bosganda shu xabar ko'rsatiladi."
        )
    else:
        text = (
            "✏️ <b>Start xabar</b>\n\n"
            "Hozircha qo'yilmagan — foydalanuvchiga faqat menyu tugmalari ko'rsatiladi."
        )
    await state.set_state(StartSG.show)
    await message.answer(text, reply_markup=start_msg_kb(bool(data)))


@router.message(PanelSG.home, F.text == BTN_START_MSG)
async def open_start(message: Message, state: FSMContext) -> None:
    await show_start(message, state)


@router.message(StartSG.show, F.text.in_({BTN_ST_EDIT, BTN_ST_ADD}))
async def ask_start(message: Message, state: FSMContext) -> None:
    await state.set_state(StartSG.waiting_message)
    await message.answer(EDIT_TEXT, reply_markup=cancel_kb())


@router.message(StartSG.show, F.text == BTN_VIEW)
async def preview(message: Message, state: FSMContext) -> None:
    data = await get_start_message()
    if not data:
        await message.answer("❗️ Start xabar yo'q")
        return
    await send_raw_content(message.bot, message.chat.id, data)
    await show_start(message, state)


@router.message(StartSG.show, F.text == BTN_DELETE)
async def delete_ask(message: Message, state: FSMContext) -> None:
    await state.set_state(StartSG.confirm_delete)
    await message.answer("🗑 Start xabar o'chirilsinmi?", reply_markup=confirm_delete_kb())


@router.message(StartSG.confirm_delete, F.text == BTN_YES_DELETE)
async def delete_ok(message: Message, state: FSMContext) -> None:
    await delete_start_message()
    await message.answer("🗑 O'chirildi")
    await show_start(message, state)


@router.message(StartSG.confirm_delete, F.text == BTN_NO)
async def delete_no(message: Message, state: FSMContext) -> None:
    await show_start(message, state)


@router.message(StartSG.waiting_message, NOT_COMMAND)
async def save_start(message: Message, state: FSMContext) -> None:
    data = extract_content(message)
    if data is None:
        await message.answer(
            "❗️ Bu turdagi xabar qo'llab-quvvatlanmaydi.", reply_markup=cancel_kb()
        )
        return
    await set_start_message(data["type"], data["file_id"], data["text_html"])
    await message.answer("✅ Start xabar saqlandi")
    await show_start(message, state)


# ------------------------------------------------------------------ OBUNA XABARI
SUB_EDIT_TEXT = (
    "📌 <b>Obuna xabari</b>\n\n"
    "Yangi xabarni yuboring — matn, rasm, video, fayl...\n"
    "Rasm/videoga izoh (caption) yozsangiz, u ham saqlanadi.\n"
    "Formatlash (qalin, kursiv, havola) o'zgarmasdan saqlanadi.\n\n"
    "⚠️ Kanal tugmalari va <b>✅ Tekshirish</b> xabar ostiga avtomatik qo'shiladi — "
    "ularni o'zingiz yozishingiz shart emas."
)


async def show_sub(message: Message, state: FSMContext) -> None:
    data = await get_sub_message()
    if data:
        text = (
            "📌 <b>Obuna xabari</b>\n\n"
            f"Turi: {TYPE_LABELS.get(data['type'], data['type'])}\n"
            "Holat: <b>admin o'rnatgan</b>\n\n"
            "Majburiy obuna talab qilinganda shu xabar ko'rsatiladi."
        )
    else:
        text = (
            "📌 <b>Obuna xabari</b>\n\n"
            "Holat: <b>standart matn</b>\n\n"
            "Majburiy obuna talab qilinganda ko'rsatiladigan xabar.\n"
            "O'zingizning matningiz yoki rasm/videoli postni qo'yishingiz mumkin."
        )
    await state.set_state(SubSG.show)
    await message.answer(text, reply_markup=sub_msg_kb(bool(data)))


@router.message(PanelSG.home, F.text == BTN_SUB_MSG)
async def open_sub(message: Message, state: FSMContext) -> None:
    await show_sub(message, state)


@router.message(SubSG.show, F.text.in_({BTN_ST_EDIT, BTN_ST_ADD}))
async def ask_sub(message: Message, state: FSMContext) -> None:
    await state.set_state(SubSG.waiting_message)
    await message.answer(SUB_EDIT_TEXT, reply_markup=cancel_kb())


@router.message(SubSG.show, F.text == BTN_VIEW)
async def preview_sub(message: Message, state: FSMContext) -> None:
    data = await get_sub_message() or DEFAULT_SUB_MESSAGE
    channels = await get_channels(active_only=True)
    await message.answer("👇 Foydalanuvchi shu ko'rinishda ko'radi:")
    await send_raw_content(
        message.bot, message.chat.id, data, reply_markup=subscribe_kb(channels)
    )
    if not channels:
        await message.answer("ℹ️ Hozircha faol kanal yo'q — tugmalar bo'sh ko'rinadi.")
    await show_sub(message, state)


@router.message(SubSG.show, F.text == BTN_SUB_RESET)
async def reset_ask(message: Message, state: FSMContext) -> None:
    await state.set_state(SubSG.confirm_reset)
    await message.answer(
        "♻️ Obuna xabari standart matnga qaytarilsinmi?",
        reply_markup=confirm_delete_kb(),
    )


@router.message(SubSG.confirm_reset, F.text == BTN_YES_DELETE)
async def reset_ok(message: Message, state: FSMContext) -> None:
    await delete_sub_message()
    await message.answer("♻️ Standart matnga qaytarildi")
    await show_sub(message, state)


@router.message(SubSG.confirm_reset, F.text == BTN_NO)
async def reset_no(message: Message, state: FSMContext) -> None:
    await show_sub(message, state)


@router.message(SubSG.waiting_message, NOT_COMMAND)
async def save_sub(message: Message, state: FSMContext) -> None:
    data = extract_content(message)
    if data is None:
        await message.answer(
            "❗️ Bu turdagi xabar qo'llab-quvvatlanmaydi.", reply_markup=cancel_kb()
        )
        return
    await set_sub_message(data["type"], data["file_id"], data["text_html"])
    await message.answer("✅ Obuna xabari saqlandi")
    await show_sub(message, state)


# ------------------------------------------------------------------ telefon on/off
async def show_phone(message: Message, state: FSMContext, enabled: bool) -> None:
    hint = (
        "Foydalanuvchidan telefon raqami so'raladi.\n"
        "Bir marta yuborgan odamdan qayta so'ralmaydi."
        if enabled
        else "Raqam so'ralmaydi."
    )
    await state.set_state(PhoneSG.show)
    await message.answer(
        "☎️ <b>Telefon so'rash</b>\n\n"
        f"Holat: <b>{'🟢 YOQILGAN' if enabled else '🔴 O‘CHIRILGAN'}</b>\n\n{hint}",
        reply_markup=phone_settings_kb(enabled),
    )


@router.message(PanelSG.home, F.text == BTN_PHONE)
async def open_phone(message: Message, state: FSMContext) -> None:
    await show_phone(message, state, await is_phone_required())


@router.message(PhoneSG.show, F.text.in_({BTN_ON, BTN_OFF}))
async def toggle_phone(message: Message, state: FSMContext) -> None:
    enabled = await toggle_phone_required()
    await message.answer("✅ O'zgartirildi")
    await show_phone(message, state, enabled)


# ------------------------------------------------------------- menyu ko'rinishi
async def show_layout(message: Message, state: FSMContext, columns: int) -> None:
    if columns == 2:
        hint = (
            "Qisqa nomli tugmalar bir qatorga <b>ikkitadan</b> joylashadi.\n"
            f"Nomi uzun bo'lsa (taxminan {SHORT_TITLE} belgidan katta) — "
            "o'sha tugma qatorni <b>o'zi egallaydi</b>, matni kesilib qolmaydi."
        )
    else:
        hint = "Har bir tugma alohida qatorda, butun kenglikda chiqadi."

    await state.set_state(LayoutSG.show)
    await message.answer(
        "🧩 <b>Menyu ko'rinishi</b>\n\n"
        f"Holat: <b>{'2️⃣ ikkitadan' if columns == 2 else '1️⃣ bittadan'}</b>\n\n"
        f"{hint}\n\n"
        "Bu sozlama foydalanuvchi ko'radigan menyuga tegishli.",
        reply_markup=layout_kb(),
    )


@router.message(PanelSG.home, F.text == BTN_LAYOUT)
async def open_layout(message: Message, state: FSMContext) -> None:
    await show_layout(message, state, await get_menu_columns())


@router.message(LayoutSG.show, F.text.in_({BTN_LT_ONE, BTN_LT_TWO}))
async def choose_layout(message: Message, state: FSMContext) -> None:
    columns = await set_menu_columns(1 if message.text == BTN_LT_ONE else 2)
    await message.answer("✅ Saqlandi")
    await show_layout(message, state, columns)


@router.message(LayoutSG.show, F.text == BTN_VIEW)
async def preview_layout(message: Message, state: FSMContext) -> None:
    """Asosiy menyuni haqiqiy klaviatura sifatida ko'rsatadi."""
    columns = await get_menu_columns()
    items = await get_items(None, active_only=True)
    if not items:
        await message.answer("❗️ Asosiy menyuda faol tugma yo'q")
        return

    long_titles = [i.title for i in items if title_width(i.title) > SHORT_TITLE]
    note = (
        "\n\nℹ️ Nomi uzunligi uchun alohida qator olganlar: "
        + ", ".join(f"<b>{escape(t)}</b>" for t in long_titles)
        if columns == 2 and long_titles
        else ""
    )
    await message.answer(
        f"👇 Foydalanuvchi asosiy menyuni shunday ko'radi:{note}\n\n"
        "Istalgan tugmani bossangiz sozlamaga qaytasiz.",
        reply_markup=menu_kb(items, is_root=True, columns=columns),
    )


@router.message(LayoutSG.show, NOT_COMMAND)
async def back_from_preview(message: Message, state: FSMContext) -> None:
    """Namunadagi tugma bosilsa — sozlama ekraniga qaytamiz."""
    await show_layout(message, state, await get_menu_columns())
