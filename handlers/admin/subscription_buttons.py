"""Majburiy obuna postidagi kanalga bog'liq bo'lmagan URL tugmalar."""

from html import escape
from typing import Optional
from urllib.parse import urlsplit

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.queries import (
    add_subscription_button,
    delete_subscription_button,
    get_subscription_button,
    get_subscription_buttons,
)
from handlers.admin.common import (
    KEY_ITEM,
    NOT_COMMAND,
    PICK_TEXT,
    admin_router,
    pick_label,
    save_labels,
)
from handlers.admin.states import PanelSG, SubscriptionButtonSG
from keyboards.admin_kb import (
    BTN_DELETE,
    BTN_NO,
    BTN_SB_ADD,
    BTN_SB_LIST,
    BTN_SUB_BUTTONS,
    BTN_YES_DELETE,
    cancel_kb,
    confirm_delete_kb,
    subscription_button_label,
    subscription_button_one_kb,
    subscription_buttons_kb,
)

router = admin_router()

LIST_TEXT = (
    "🔗 <b>Obuna URL tugmalari</b>\n\n"
    "Bu tugmalar majburiy obuna xabarida kanal tugmalaridan keyin, "
    "<b>A'zo bo'ldim</b> tugmasidan oldin chiqadi.\n\n"
    "<i>Tugma ustiga bosing — ma'lumoti ochiladi.</i>"
)


def normalize_button_url(value: str) -> Optional[str]:
    """Telegram inline tugmasiga mos URL qaytaradi."""
    url = value.strip()
    if not url or len(url) > 2048 or any(char.isspace() for char in url):
        return None
    if url.startswith(("t.me/", "www.")):
        url = "https://" + url
    elif "://" not in url and "." in url:
        url = "https://" + url

    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    if parsed.scheme == "tg" and (parsed.netloc or parsed.path):
        return url
    return None


async def show_list(message: Message, state: FSMContext) -> None:
    buttons = await get_subscription_buttons()
    labels = {
        subscription_button_label(button, index): button.id
        for index, button in enumerate(buttons, start=1)
    }
    await state.set_state(SubscriptionButtonSG.browse)
    await save_labels(state, labels)
    text = LIST_TEXT if buttons else LIST_TEXT + "\n\nHozircha tugma qo'shilmagan."
    await message.answer(text, reply_markup=subscription_buttons_kb(list(labels)))


async def show_one(message: Message, state: FSMContext, button_id: Optional[int]) -> None:
    button = await get_subscription_button(button_id) if button_id is not None else None
    if button is None:
        await show_list(message, state)
        return
    await state.set_state(SubscriptionButtonSG.one)
    await state.update_data({KEY_ITEM: button.id})
    await message.answer(
        "🔗 <b>Obuna URL tugmasi</b>\n\n"
        f"Nomi: <b>{escape(button.title)}</b>\n"
        f"Link: {escape(button.url)}",
        reply_markup=subscription_button_one_kb(),
    )


@router.message(Command("tugma"))
@router.message(PanelSG.home, F.text == BTN_SUB_BUTTONS)
async def open_list(message: Message, state: FSMContext) -> None:
    await show_list(message, state)


@router.message(SubscriptionButtonSG.browse, F.text == BTN_SB_ADD)
async def ask_title(message: Message, state: FSMContext) -> None:
    await state.set_state(SubscriptionButtonSG.waiting_title)
    await message.answer(
        "✏️ Tugma nomini yuboring. Maksimum: 64 ta belgi.",
        reply_markup=cancel_kb(),
    )


@router.message(SubscriptionButtonSG.browse)
async def pick_button(message: Message, state: FSMContext) -> None:
    button_id = await pick_label(state, message.text)
    if button_id is None:
        await message.answer(PICK_TEXT)
        return
    await show_one(message, state, button_id)


@router.message(SubscriptionButtonSG.waiting_title, NOT_COMMAND)
async def save_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 64:
        await message.answer(
            "❗️ Tugma nomi 1–64 ta belgi bo'lishi kerak.",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(subscription_button_title=title)
    await state.set_state(SubscriptionButtonSG.waiting_url)
    await message.answer(
        "🔗 Tugma linkini yuboring.\n\n"
        "Masalan: <code>https://example.com</code> yoki <code>https://t.me/example</code>",
        reply_markup=cancel_kb(),
    )


@router.message(SubscriptionButtonSG.waiting_url, NOT_COMMAND)
async def save_url(message: Message, state: FSMContext) -> None:
    url = normalize_button_url(message.text or "")
    if url is None:
        await message.answer(
            "❗️ Link noto'g'ri. <code>https://...</code>, <code>http://...</code> "
            "yoki <code>tg://...</code> ko'rinishida yuboring.",
            reply_markup=cancel_kb(),
        )
        return
    title = (await state.get_data()).get("subscription_button_title")
    if not title:
        await show_list(message, state)
        return
    await add_subscription_button(title, url)
    await message.answer("✅ Tugma saqlandi")
    await show_list(message, state)


@router.message(SubscriptionButtonSG.one, F.text == BTN_DELETE)
async def delete_ask(message: Message, state: FSMContext) -> None:
    await state.set_state(SubscriptionButtonSG.confirm_delete)
    await message.answer("🗑 Tugma o'chirilsinmi?", reply_markup=confirm_delete_kb())


@router.message(SubscriptionButtonSG.one, F.text == BTN_SB_LIST)
async def back_to_list(message: Message, state: FSMContext) -> None:
    await show_list(message, state)


@router.message(SubscriptionButtonSG.confirm_delete, F.text == BTN_YES_DELETE)
async def delete_ok(message: Message, state: FSMContext) -> None:
    button_id = (await state.get_data()).get(KEY_ITEM)
    if button_id is not None:
        await delete_subscription_button(button_id)
        await message.answer("🗑 Tugma o'chirildi")
    await show_list(message, state)


@router.message(SubscriptionButtonSG.confirm_delete, F.text == BTN_NO)
async def delete_no(message: Message, state: FSMContext) -> None:
    await show_one(message, state, (await state.get_data()).get(KEY_ITEM))
