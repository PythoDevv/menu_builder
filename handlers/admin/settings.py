from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db.queries import (
    delete_start_message,
    get_start_message,
    is_phone_required,
    set_start_message,
    toggle_phone_required,
)
from handlers.admin.common import admin_router, edit_or_send
from handlers.admin.states import StartSG
from keyboards.admin_kb import (
    admin_home_kb,
    cancel_kb,
    phone_settings_kb,
    start_delete_kb,
    start_msg_kb,
)
from utils.content import TYPE_LABELS, extract_content, send_raw_content

router = admin_router()

EDIT_TEXT = (
    "✏️ <b>Start xabar</b>\n\n"
    "Yangi start xabarni yuboring — matn, rasm, video yoki fayl.\n"
    "Formatlash o'zgarmasdan saqlanadi."
)


async def _show_start(callback: CallbackQuery) -> None:
    data = await get_start_message()
    if data:
        label = TYPE_LABELS.get(data["type"], data["type"])
        text = (
            "✏️ <b>Start xabar</b>\n\n"
            f"Turi: {label}\n"
            "Foydalanuvchi /start bosganda shu xabar ko'rsatiladi."
        )
    else:
        text = (
            "✏️ <b>Start xabar</b>\n\n"
            "Hozircha qo'yilmagan — foydalanuvchiga faqat menyu tugmalari ko'rsatiladi."
        )
    await edit_or_send(callback, text, start_msg_kb(bool(data)))


@router.callback_query(F.data == "st:show")
async def cb_show(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_start(callback)
    await callback.answer()


@router.callback_query(F.data == "st:prev")
async def cb_preview(callback: CallbackQuery) -> None:
    data = await get_start_message()
    if not data:
        await callback.answer("Start xabar yo'q", show_alert=True)
        return
    await callback.answer("👁 Yuborilmoqda...")
    await send_raw_content(callback.bot, callback.message.chat.id, data)


@router.callback_query(F.data == "st:edit")
async def cb_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(StartSG.waiting_message)
    await edit_or_send(callback, EDIT_TEXT, cancel_kb())
    await callback.answer()


@router.message(StartSG.waiting_message)
async def save_start(message: Message, state: FSMContext) -> None:
    data = extract_content(message)
    if data is None:
        await message.answer("❗️ Bu turdagi xabar qo'llab-quvvatlanmaydi.", reply_markup=cancel_kb())
        return
    await set_start_message(data["type"], data["file_id"], data["text_html"])
    await state.clear()
    await message.answer("✅ Start xabar saqlandi", reply_markup=admin_home_kb())


@router.callback_query(F.data == "st:del")
async def cb_delete_ask(callback: CallbackQuery) -> None:
    await edit_or_send(callback, "🗑 Start xabar o'chirilsinmi?", start_delete_kb())
    await callback.answer()


@router.callback_query(F.data == "st:delok")
async def cb_delete(callback: CallbackQuery) -> None:
    await delete_start_message()
    await callback.answer("🗑 O'chirildi")
    await _show_start(callback)


# ------------------------------------------------------------------- telefon on/off
async def _show_phone(callback: CallbackQuery, enabled: bool) -> None:
    state_text = "🟢 YOQILGAN" if enabled else "🔴 O'CHIRILGAN"
    hint = (
        "Foydalanuvchidan telefon raqami so'raladi.\n"
        "Bir marta yuborgan odamdan qayta so'ralmaydi."
        if enabled
        else "Raqam so'ralmaydi."
    )
    text = f"☎️ <b>Telefon so'rash</b>\n\nHolat: <b>{state_text}</b>\n\n{hint}"
    await edit_or_send(callback, text, phone_settings_kb(enabled))


@router.callback_query(F.data == "adm:phone")
async def cb_phone(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_phone(callback, await is_phone_required())
    await callback.answer()


@router.callback_query(F.data == "adm:phone:tog")
async def cb_phone_toggle(callback: CallbackQuery) -> None:
    enabled = await toggle_phone_required()
    await callback.answer("✅ O'zgartirildi")
    await _show_phone(callback, enabled)
