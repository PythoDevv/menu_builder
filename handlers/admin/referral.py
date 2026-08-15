"""Taklif sharti bajarilmaganda foydalanuvchiga chiqadigan matn.

Matn faqat matn (HTML) bo'ladi — ichida o'rinbosarlar ({need}, {link} ...)
ishlatilgani uchun rasm/video qabul qilinmaydi. Qo'yilmagan bo'lsa
`utils.texts.DEFAULT_REF_TEXT` ishlatiladi.
"""

from html import escape

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import LinkPreviewOptions, Message

from db.queries import delete_ref_text, get_ref_text, set_ref_text
from handlers.admin.common import NOT_COMMAND, admin_router
from handlers.admin.states import PanelSG, RefTextSG
from keyboards.admin_kb import (
    BTN_NO,
    BTN_REF_RESET,
    BTN_REF_TEXT,
    BTN_ST_ADD,
    BTN_ST_EDIT,
    BTN_VIEW,
    BTN_YES_DELETE,
    cancel_kb,
    confirm_delete_kb,
    ref_text_kb,
)
from keyboards.user_kb import share_kb
from utils.referral import PLACEHOLDERS, ref_link, render_ref_text
from utils.texts import DEFAULT_REF_TEXT

router = admin_router()

TEXT_LIMIT = 3000

PLACEHOLDER_HELP = (
    "Matn ichida shu belgilarni ishlatishingiz mumkin:\n"
    "<code>{title}</code> — tugma nomi\n"
    "<code>{need}</code> — kerakli taklif soni\n"
    "<code>{count}</code> — foydalanuvchi taklif qilgan son\n"
    "<code>{left}</code> — yana nechta kerak\n"
    "<code>{link}</code> — foydalanuvchining shaxsiy havolasi"
)

EDIT_TEXT = (
    "✍️ <b>Taklif matni</b>\n\n"
    "Yangi matnni yuboring (faqat matn).\n"
    "Formatlash (qalin, kursiv, havola) o'zgarmasdan saqlanadi.\n\n"
    f"{PLACEHOLDER_HELP}\n\n"
    "⚠️ <b>📤 Do'stlarga yuborish</b> tugmasi xabar ostiga avtomatik qo'shiladi."
)

#: Ko'rish (preview) uchun namunaviy qiymatlar
SAMPLE_TITLE = "Yopiq bo'lim"
SAMPLE_NEED = 5
SAMPLE_COUNT = 1


async def show(message: Message, state: FSMContext) -> None:
    custom = await get_ref_text()
    status = "<b>admin o'rnatgan</b>" if custom else "<b>standart matn</b>"
    await state.set_state(RefTextSG.show)
    await message.answer(
        "✍️ <b>Taklif matni</b>\n\n"
        f"Holat: {status}\n\n"
        "Taklif sharti qo'yilgan tugma bosilganda, shart bajarilmagan bo'lsa "
        "foydalanuvchiga shu matn chiqadi.\n\n"
        f"{PLACEHOLDER_HELP}",
        reply_markup=ref_text_kb(bool(custom)),
    )


@router.message(PanelSG.home, F.text == BTN_REF_TEXT)
async def open_ref_text(message: Message, state: FSMContext) -> None:
    await show(message, state)


@router.message(RefTextSG.show, F.text.in_({BTN_ST_EDIT, BTN_ST_ADD}))
async def ask_text(message: Message, state: FSMContext) -> None:
    await state.set_state(RefTextSG.waiting_text)
    current = await get_ref_text() or DEFAULT_REF_TEXT
    await message.answer(EDIT_TEXT, reply_markup=cancel_kb())
    await message.answer(
        "👇 Hozirgi matn (nusxa olib, tahrirlashingiz mumkin):\n\n"
        f"<code>{escape(current)}</code>",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.message(RefTextSG.show, F.text == BTN_VIEW)
async def preview(message: Message, state: FSMContext) -> None:
    template = await get_ref_text() or DEFAULT_REF_TEXT
    link = await ref_link(message.bot, message.from_user.id)
    await message.answer("👇 Foydalanuvchi shu ko'rinishda ko'radi:")
    await message.answer(
        render_ref_text(
            template,
            title=SAMPLE_TITLE,
            need=SAMPLE_NEED,
            count=SAMPLE_COUNT,
            link=link,
        ),
        reply_markup=share_kb(link),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
    await show(message, state)


@router.message(RefTextSG.show, F.text == BTN_REF_RESET)
async def reset_ask(message: Message, state: FSMContext) -> None:
    await state.set_state(RefTextSG.confirm_reset)
    await message.answer(
        "♻️ Taklif matni standartga qaytarilsinmi?", reply_markup=confirm_delete_kb()
    )


@router.message(RefTextSG.confirm_reset, F.text == BTN_YES_DELETE)
async def reset_ok(message: Message, state: FSMContext) -> None:
    await delete_ref_text()
    await message.answer("♻️ Standart matnga qaytarildi")
    await show(message, state)


@router.message(RefTextSG.confirm_reset, F.text == BTN_NO)
async def reset_no(message: Message, state: FSMContext) -> None:
    await show(message, state)


@router.message(RefTextSG.waiting_text, NOT_COMMAND)
async def save_text(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(
            "❗️ Faqat matn yuboring — bu bo'limda rasm/video ishlatilmaydi.",
            reply_markup=cancel_kb(),
        )
        return
    if len(message.text) > TEXT_LIMIT:
        await message.answer(
            f"❗️ Matn juda uzun ({len(message.text)} belgi). "
            f"{TEXT_LIMIT} belgidan oshmasin.",
            reply_markup=cancel_kb(),
        )
        return

    await set_ref_text(message.html_text)
    missing = [p for p in PLACEHOLDERS if p not in message.text]
    await message.answer("✅ Taklif matni saqlandi")
    if "{link}" in missing:
        await message.answer(
            "ℹ️ Matnda <code>{link}</code> yo'q — havola xabar oxiriga "
            "avtomatik qo'shib yuboriladi."
        )
    await show(message, state)
