"""🔐 Yopiq kanal linki — N ta odam taklif qilganga shaxsiy, bir martalik havola.

Admin shu yerdan sozlaydi:
  * kanal — bot u yerda admin va "Foydalanuvchilarni taklif qilish" huquqi bor;
  * kerakli takliflar soni;
  * havola bilan boradigan post (`{link}`, `{count}`, `{need}`);
  * har bir yangi taklifda boradigan tabrik (`{name}`, `{count}`, `{need}`, `{left}`).

Havolani berish mantig'i `utils/private_link.py` da.
"""

from html import escape

from aiogram import F
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import LinkPreviewOptions, Message

from db.queries import (
    count_private_link_grants,
    delete_private_link_button,
    delete_private_link_post,
    delete_ref_notify_text,
    get_private_link_settings,
    get_ref_notify_text,
    get_referral_counts,
    set_private_link_button,
    set_private_link_channel,
    set_private_link_enabled,
    set_private_link_need,
    set_private_link_post,
    set_ref_notify_text,
)
from handlers.admin.common import NOT_COMMAND, admin_router
from handlers.admin.states import PanelSG, PrivateLinkSG
from keyboards.admin_kb import (
    BTN_NO,
    BTN_OFF,
    BTN_ON,
    BTN_PL_BUTTON,
    BTN_PL_BUTTON_RESET,
    BTN_PL_CHANNEL,
    BTN_PL_NEED,
    BTN_PL_NOTIFY,
    BTN_PL_NOTIFY_RESET,
    BTN_PL_NOTIFY_VIEW,
    BTN_PL_POST,
    BTN_PL_POST_RESET,
    BTN_PL_POST_VIEW,
    BTN_PRIVATE_LINK,
    BTN_YES_DELETE,
    cancel_kb,
    confirm_delete_kb,
    private_link_kb,
)
from utils.channels import can_bot_invite, parse_chat_target
from utils.content import extract_button_text_and_icon
from utils.private_link import BTN_JOIN, goal_active, join_kb, render_notify_text, send_post
from utils.texts import DEFAULT_REF_NOTIFY_TEXT

router = admin_router()

NEED_LIMIT = 10_000
TEXT_LIMIT = 3000
#: Telegram izoh limiti 1024; `{link}` o'rniga uzunroq havola qo'yiladi
CAPTION_LIMIT = 900
POST_MEDIA = ("photo", "video", "animation", "document")

#: Ko'rish (preview) uchun namunaviy qiymatlar
SAMPLE_LINK = "https://t.me/+namuna_havola"
SAMPLE_NAME = "Ali Valiyev"
SAMPLE_NEED = 5

NO_RIGHTS_TEXT = (
    "❗️ Bot bu kanalda admin emas yoki unda <b>“Foydalanuvchilarni taklif qilish”</b> "
    "(Invite users via link) huquqi yo'q.\n\n"
    "Botni kanalga shu huquq bilan admin qiling va qayta urinib ko'ring."
)

CHANNEL_TEXT = (
    "📢 <b>Kanalni belgilash</b>\n\n"
    "Havola beriladigan yopiq kanaldan istalgan postni shu yerga <b>forward</b> "
    "qiling, yoki <code>-1001234567890</code> / <code>@username</code> yuboring.\n\n"
    "⚠️ Bot o'sha kanalda <b>admin</b> bo'lishi va "
    "<b>“Foydalanuvchilarni taklif qilish”</b> huquqiga ega bo'lishi shart."
)

POST_HELP = (
    "<code>{link}</code> — foydalanuvchining shaxsiy havolasi\n"
    "<code>{count}</code> — u taklif qilgan odamlar soni\n"
    "<code>{need}</code> — kerakli takliflar soni"
)

POST_TEXT = (
    "📝 <b>Link posti</b>\n\n"
    "Taklif sharti bajarilganda foydalanuvchiga boradigan postni yuboring: "
    "matn yoki rasm / video / GIF / fayl (izohi bilan). Qalin, kursiv va premium "
    "emojilar saqlanadi.\n\n"
    f"{POST_HELP}\n\n"
    "Masalan: <code>Tabriklaymiz! Mana sizning havolangiz: {link}</code>\n\n"
    "ℹ️ Post ostiga <b>🔐 Kanalga kirish</b> tugmasi avtomatik qo'shiladi."
)

BUTTON_LIMIT = 64
BUTTON_TEXT = (
    "🔘 <b>Kirish tugmasi matni</b>\n\n"
    "Havolali post ostidagi tugma uchun yangi matn yuboring.\n"
    f"Standart: <b>{BTN_JOIN}</b>\n\n"
    "Premium emoji ishlatsangiz, uni matn bilan birga yuboring — birinchi premium "
    "emoji tugma ikonkasiga aylanadi.\n\n"
    f"Maksimum: {BUTTON_LIMIT} ta belgi."
)

NOTIFY_HELP = (
    "<code>{name}</code> — yangi qo'shilgan odamning ismi\n"
    "<code>{count}</code> — jami ballari (takliflari)\n"
    "<code>{need}</code> — yopiq kanal uchun kerakli son\n"
    "<code>{left}</code> — yana nechta qoldi\n\n"
    "ℹ️ <code>{need}</code> yoki <code>{left}</code> bor qator faqat bo'lim yoqilgan "
    "va odam havolani hali olmagan bo'lsa chiqadi."
)

NOTIFY_TEXT = (
    "🎉 <b>Tabrik xabari</b>\n\n"
    "Kimdir havola orqali botga qo'shilganda, taklif qilgan odamga shu xabar "
    "boradi. Yangi matnni yuboring (faqat matn, Telegram formatlashi bilan).\n\n"
    f"{NOTIFY_HELP}"
)

NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


# --------------------------------------------------------------------- bosh ekran
async def show(message: Message, state: FSMContext) -> None:
    settings = await get_private_link_settings()
    custom_notify = await get_ref_notify_text()
    chat_id = settings["chat_id"]
    need = settings["need"]

    status = "🟢 YOQILGAN" if settings["enabled"] else "🔴 O'CHIRILGAN"
    if chat_id:
        title = escape(settings["chat_title"] or str(chat_id))
        channel = f"<b>{title}</b> (<code>{chat_id}</code>)"
    else:
        channel = "— belgilanmagan"
    need_line = f"<b>{need} ta</b> taklif" if need else "— belgilanmagan"
    post = "admin o'rnatgan" if settings["post"] else "standart"
    button = escape(settings["button_text"] or BTN_JOIN)
    if not settings["button_text"]:
        button += " (standart)"
    elif settings["button_icon"]:
        button += " + premium emoji"
    notify = "admin o'rnatgan" if custom_notify else "standart"
    granted = await count_private_link_grants(chat_id) if chat_id else 0

    await state.set_state(PrivateLinkSG.show)
    await message.answer(
        "🔐 <b>Yopiq kanal linki</b>\n\n"
        f"Holat: <b>{status}</b>\n"
        f"Kanal: {channel}\n"
        f"Shart: {need_line}\n"
        f"Post: <b>{post}</b>\n"
        f"Kirish tugmasi: <b>{button}</b>\n"
        f"Tabrik xabari: <b>{notify}</b>\n"
        f"Havola olganlar: <b>{granted}</b> ta\n\n"
        "Foydalanuvchi shuncha odamni taklif qilganda bot unga shu kanalga "
        "<b>faqat o'zi uchun, bir martalik</b> havola yuboradi. Har bir yangi "
        "taklifda esa tabrik xabari boradi: necha ball olgani va yana nechta qolgani.",
        reply_markup=private_link_kb(
            bool(settings["enabled"]),
            bool(settings["post"]),
            bool(custom_notify),
            bool(settings["button_text"]),
        ),
    )


@router.message(PanelSG.home, F.text == BTN_PRIVATE_LINK)
async def open_section(message: Message, state: FSMContext) -> None:
    await show(message, state)


# ------------------------------------------------------------------ yoqish/o'chirish
@router.message(PrivateLinkSG.show, F.text.in_({BTN_ON, BTN_OFF}))
async def toggle(message: Message, state: FSMContext) -> None:
    settings = await get_private_link_settings()
    if settings["enabled"]:
        await set_private_link_enabled(False)
        await message.answer("🔴 O'chirildi. Yangi havolalar berilmaydi.")
        await show(message, state)
        return

    if not settings["chat_id"] or settings["need"] <= 0:
        await message.answer("❗️ Avval kanalni va takliflar sonini belgilang.")
        await show(message, state)
        return
    if not await can_bot_invite(message.bot, settings["chat_id"]):
        await message.answer(NO_RIGHTS_TEXT)
        await show(message, state)
        return

    await set_private_link_enabled(True)
    need = settings["need"]
    ready = sum(1 for count in (await get_referral_counts()).values() if count >= need)
    text = "🟢 Yoqildi."
    if ready:
        text += (
            f"\n\nℹ️ Shartni allaqachon bajarib bo'lganlar: <b>{ready}</b> ta. Ular "
            "havolani keyingi taklifida yoki <b>Ballarim</b> tugmasini bosganda oladi."
        )
    await message.answer(text)
    await show(message, state)


# ---------------------------------------------------------------------------- kanal
@router.message(PrivateLinkSG.show, F.text == BTN_PL_CHANNEL)
async def ask_channel(message: Message, state: FSMContext) -> None:
    await state.set_state(PrivateLinkSG.waiting_channel)
    await message.answer(CHANNEL_TEXT, reply_markup=cancel_kb())


@router.message(PrivateLinkSG.waiting_channel, NOT_COMMAND)
async def save_channel(message: Message, state: FSMContext) -> None:
    target = parse_chat_target(message)
    if target is None:
        await message.answer(
            "❗️ Tushunarsiz. Kanaldan post forward qiling yoki kanal ID sini yuboring.",
            reply_markup=cancel_kb(),
        )
        return
    try:
        chat = await message.bot.get_chat(target)
    except TelegramAPIError:
        await message.answer(
            "❗️ Kanal topilmadi. Bot kanalda admin ekanligiga ishonch hosil qiling.",
            reply_markup=cancel_kb(),
        )
        return
    if not await can_bot_invite(message.bot, chat.id):
        await message.answer(NO_RIGHTS_TEXT, reply_markup=cancel_kb())
        return

    title = chat.title or str(chat.id)
    await set_private_link_channel(chat.id, title)
    await message.answer(f"✅ Kanal saqlandi: <b>{escape(title)}</b>")
    await show(message, state)


# ------------------------------------------------------------------ takliflar soni
@router.message(PrivateLinkSG.show, F.text == BTN_PL_NEED)
async def ask_need(message: Message, state: FSMContext) -> None:
    settings = await get_private_link_settings()
    current = f"\n\nHozir: <b>{settings['need']} ta</b>" if settings["need"] else ""
    await state.set_state(PrivateLinkSG.waiting_need)
    await message.answer(
        "👥 Nechta odam taklif qilganda havola berilsin?\n"
        f"Raqam yuboring (1 — {NEED_LIMIT}).{current}",
        reply_markup=cancel_kb(),
    )


@router.message(PrivateLinkSG.waiting_need, NOT_COMMAND)
async def save_need(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= NEED_LIMIT:
        await message.answer(
            f"❗️ 1 dan {NEED_LIMIT} gacha bo'lgan raqam yuboring.",
            reply_markup=cancel_kb(),
        )
        return
    await set_private_link_need(int(raw))
    await message.answer(f"✅ Shart saqlandi: <b>{int(raw)} ta</b> taklif")
    await show(message, state)


# ----------------------------------------------------------------------------- post
def extract_post(message: Message) -> dict | None:
    """Matn yoki bitta media + izoh. Formatlash HTML ko'rinishida saqlanadi."""
    if message.text:
        return {"type": "text", "file_id": None, "text_html": message.html_text}
    for kind in POST_MEDIA:
        media = getattr(message, kind)
        if not media:
            continue
        file_id = media[-1].file_id if kind == "photo" else media.file_id
        text_html = message.html_text if message.caption else ""
        return {"type": kind, "file_id": file_id, "text_html": text_html}
    return None


async def _preview_post(message: Message, settings: dict) -> None:
    """`settings` — saqlangan yoki hali saqlanmagan (yangi post/tugma) sozlamalar."""
    need = settings["need"] or SAMPLE_NEED
    await message.answer("👇 Foydalanuvchi shu ko'rinishda ko'radi (havola namunaviy):")
    await send_post(
        message.bot, message.chat.id, settings, link=SAMPLE_LINK, count=need, need=need
    )


@router.message(PrivateLinkSG.show, F.text == BTN_PL_POST)
async def ask_post(message: Message, state: FSMContext) -> None:
    await state.set_state(PrivateLinkSG.waiting_post)
    await message.answer(POST_TEXT, reply_markup=cancel_kb())


@router.message(PrivateLinkSG.waiting_post, NOT_COMMAND)
async def save_post(message: Message, state: FSMContext) -> None:
    post = extract_post(message)
    if post is None:
        await message.answer(
            "❗️ Matn yoki rasm / video / GIF / fayl yuboring.", reply_markup=cancel_kb()
        )
        return
    raw = message.text or message.caption or ""
    limit = TEXT_LIMIT if post["type"] == "text" else CAPTION_LIMIT
    if len(raw) > limit:
        await message.answer(
            f"❗️ Matn juda uzun ({len(raw)} belgi). {limit} belgidan oshmasin.",
            reply_markup=cancel_kb(),
        )
        return

    settings = await get_private_link_settings()
    try:
        await _preview_post(message, {**settings, "post": post})
    except TelegramBadRequest:
        await message.answer(
            "❗️ Post <b>saqlanmadi</b>: Telegram uni qabul qilmadi (format yoki "
            "premium emoji). Qayta yuboring.",
            reply_markup=cancel_kb(),
        )
        return

    await set_private_link_post(post["type"], post["file_id"], post["text_html"])
    await message.answer("✅ Link posti saqlandi")
    if "{link}" not in post["text_html"]:
        await message.answer(
            "ℹ️ Matnda <code>{link}</code> yo'q — havola faqat "
            "<b>🔐 Kanalga kirish</b> tugmasida bo'ladi."
        )
    await show(message, state)


@router.message(PrivateLinkSG.show, F.text == BTN_PL_POST_VIEW)
async def view_post(message: Message, state: FSMContext) -> None:
    await _preview_post(message, await get_private_link_settings())
    await show(message, state)


@router.message(PrivateLinkSG.show, F.text == BTN_PL_POST_RESET)
async def ask_reset_post(message: Message, state: FSMContext) -> None:
    await state.set_state(PrivateLinkSG.confirm_post_reset)
    await message.answer(
        "♻️ Link posti standart matnga qaytarilsinmi?", reply_markup=confirm_delete_kb()
    )


@router.message(PrivateLinkSG.confirm_post_reset, F.text == BTN_YES_DELETE)
async def reset_post(message: Message, state: FSMContext) -> None:
    await delete_private_link_post()
    await message.answer("♻️ Standart postga qaytarildi")
    await show(message, state)


@router.message(PrivateLinkSG.confirm_post_reset, F.text == BTN_NO)
async def keep_post(message: Message, state: FSMContext) -> None:
    await show(message, state)


# ------------------------------------------------------------------- kirish tugmasi
@router.message(PrivateLinkSG.show, F.text == BTN_PL_BUTTON)
async def ask_button(message: Message, state: FSMContext) -> None:
    settings = await get_private_link_settings()
    await state.set_state(PrivateLinkSG.waiting_button)
    await message.answer(BUTTON_TEXT, reply_markup=cancel_kb())
    await message.answer(
        "👇 Hozirgi tugma:",
        reply_markup=join_kb(SAMPLE_LINK, settings["button_text"], settings["button_icon"]),
    )


@router.message(PrivateLinkSG.waiting_button, NOT_COMMAND)
async def save_button(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("❗️ Tugma uchun matn yuboring.", reply_markup=cancel_kb())
        return
    text, icon_custom_emoji_id = extract_button_text_and_icon(message)
    if not text or len(text) > BUTTON_LIMIT:
        await message.answer(
            f"❗️ Tugma matni bo'sh bo'lmasin va {BUTTON_LIMIT} ta belgidan oshmasin. "
            "Premium emoji yuborsangiz, yoniga matn ham yozing.",
            reply_markup=cancel_kb(),
        )
        return
    try:
        await message.answer(
            "👇 Tugma shunday ko'rinadi:",
            reply_markup=join_kb(SAMPLE_LINK, text, icon_custom_emoji_id),
        )
    except TelegramBadRequest:
        await message.answer(
            "❗️ Telegram premium emojini tugmada qabul qilmadi. Bot egasida "
            "Telegram Premium faol ekanini tekshiring yoki oddiy emoji yuboring.",
            reply_markup=cancel_kb(),
        )
        return

    await set_private_link_button(text, icon_custom_emoji_id)
    await message.answer("✅ Tugma matni saqlandi")
    await show(message, state)


@router.message(PrivateLinkSG.show, F.text == BTN_PL_BUTTON_RESET)
async def reset_button(message: Message, state: FSMContext) -> None:
    await delete_private_link_button()
    await message.answer(f"♻️ Standart tugmaga qaytarildi: <b>{BTN_JOIN}</b>")
    await show(message, state)


# --------------------------------------------------------------------- tabrik xabari
async def _preview_notify(message: Message, template: str) -> None:
    """Haqiqiy sozlamalar bilan: bo'lim o'chiq bo'lsa maqsad qatori ko'rinmaydi."""
    settings = await get_private_link_settings()
    need = settings["need"] or SAMPLE_NEED
    count = max(need - 2, 1)
    await message.answer("👇 Taklif qilgan odam shu ko'rinishda ko'radi:")
    await message.answer(
        render_notify_text(
            template,
            name=SAMPLE_NAME,
            count=count,
            need=need,
            has_goal=goal_active(settings) and count < need,
        ),
        link_preview_options=NO_PREVIEW,
    )


@router.message(PrivateLinkSG.show, F.text == BTN_PL_NOTIFY)
async def ask_notify(message: Message, state: FSMContext) -> None:
    await state.set_state(PrivateLinkSG.waiting_notify)
    await message.answer(NOTIFY_TEXT, reply_markup=cancel_kb())
    await _preview_notify(message, await get_ref_notify_text() or DEFAULT_REF_NOTIFY_TEXT)


@router.message(PrivateLinkSG.waiting_notify, NOT_COMMAND)
async def save_notify(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(
            "❗️ Faqat matn yuboring — bu xabarda rasm/video ishlatilmaydi.",
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

    template = message.html_text
    try:
        await _preview_notify(message, template)
    except TelegramBadRequest:
        await message.answer(
            "❗️ Matn <b>saqlanmadi</b>: Telegram uni qabul qilmadi. Qayta yuboring.",
            reply_markup=cancel_kb(),
        )
        return

    await set_ref_notify_text(template)
    await message.answer("✅ Tabrik xabari saqlandi")
    await show(message, state)


@router.message(PrivateLinkSG.show, F.text == BTN_PL_NOTIFY_VIEW)
async def view_notify(message: Message, state: FSMContext) -> None:
    await _preview_notify(message, await get_ref_notify_text() or DEFAULT_REF_NOTIFY_TEXT)
    await show(message, state)


@router.message(PrivateLinkSG.show, F.text == BTN_PL_NOTIFY_RESET)
async def ask_reset_notify(message: Message, state: FSMContext) -> None:
    await state.set_state(PrivateLinkSG.confirm_notify_reset)
    await message.answer(
        "♻️ Tabrik xabari standart matnga qaytarilsinmi?", reply_markup=confirm_delete_kb()
    )


@router.message(PrivateLinkSG.confirm_notify_reset, F.text == BTN_YES_DELETE)
async def reset_notify(message: Message, state: FSMContext) -> None:
    await delete_ref_notify_text()
    await message.answer("♻️ Standart matnga qaytarildi")
    await show(message, state)


@router.message(PrivateLinkSG.confirm_notify_reset, F.text == BTN_NO)
async def keep_notify(message: Message, state: FSMContext) -> None:
    await show(message, state)
