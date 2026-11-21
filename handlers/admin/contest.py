"""🎁 Konkurs tugmasi — "Konkursda qatnashish" va shaxsiy havolali tarqatish posti.

Admin shu yerdan boshqaradi:
  * tugmani ko'rsatish / yashirish;
  * joylashuvi — asosiy menyuning eng tepasida (standart) yoki eng pastida;
  * nomi + premium emoji ikonka va rangi (oddiy menyu tugmalari kabi);
  * tarqatish posti — matn yoki rasm / video / GIF / fayl / stiker, premium
    emojilar bilan; `{link}` -> foydalanuvchining shaxsiy havolasi;
  * post ostidagi havola tugmasi — matni, premium emojisi va rangi.

Foydalanuvchi tomoni `handlers/menu.py` da, post yig'ish `utils/contest.py` da.
"""

from html import escape

from aiogram import F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from db.queries import (
    CONTEST_BOTTOM,
    CONTEST_TOP,
    DEFAULT_CONTEST_JOIN_TEXT,
    DEFAULT_CONTEST_STYLE,
    delete_contest_join_button,
    delete_contest_post,
    get_contest_settings,
    get_items,
    get_my_points_settings,
    get_rating_settings,
    set_contest_enabled,
    set_contest_join_button,
    set_contest_join_style,
    set_contest_position,
    set_contest_post,
    set_contest_style,
    set_contest_text,
)
from handlers.admin.common import NOT_COMMAND, admin_router
from handlers.admin.states import ContestSG, PanelSG
from keyboards.admin_kb import (
    BUTTON_STYLE_OPTIONS,
    BTN_BACK,
    BTN_CONTEST,
    BTN_CT_BOTTOM,
    BTN_CT_JOIN,
    BTN_CT_JOIN_RESET,
    BTN_CT_JOIN_STYLE,
    BTN_CT_POST,
    BTN_CT_POST_RESET,
    BTN_CT_RENAME,
    BTN_CT_STYLE,
    BTN_CT_TOP,
    BTN_NO,
    BTN_OFF,
    BTN_ON,
    BTN_VIEW,
    BTN_YES_DELETE,
    button_style_kb,
    button_style_label,
    cancel_kb,
    confirm_delete_kb,
    contest_position_label,
    contest_settings_kb,
)
from keyboards.user_kb import BTN_BACK as USER_BACK
from keyboards.user_kb import BTN_HOME as USER_HOME
from keyboards.user_kb import menu_kb
from utils.contest import NO_TEXT_TYPES, extract_contest_post, join_kb, send_contest_post
from utils.content import TYPE_LABELS, extract_button_text_and_icon
from utils.referral import ref_link

router = admin_router()

BUTTON_LIMIT = 64
TEXT_LIMIT = 3000
#: Telegram izoh limiti 1024; `{link}` o'rniga uzunroq havola qo'yiladi
CAPTION_LIMIT = 900

PREMIUM_REJECTED = (
    "❗️ Telegram premium emojini tugmada qabul qilmadi. Bot egasida "
    "Telegram Premium faol ekanini tekshiring yoki oddiy emoji yuboring."
)

RENAME_TEXT = (
    "✏️ <b>Konkurs tugmasi nomi</b>\n\n"
    "Yangi nomni yuboring. Premium custom emoji ishlatsangiz, uni nom bilan birga "
    "yuboring — birinchi premium emoji tugma ikonkasiga aylanadi.\n\n"
    f"Maksimum: {BUTTON_LIMIT} ta belgi."
)

POST_TEXT = (
    "📝 <b>Tarqatish posti</b>\n\n"
    "Foydalanuvchi <b>Konkursda qatnashish</b> tugmasini bosganda shu post keladi — "
    "u uni do'stlariga va guruhlarga forward qiladi.\n\n"
    "Yuborish mumkin: matn, rasm / video / GIF / fayl (izohi bilan) yoki stiker. "
    "Qalin, kursiv, havola va <b>premium emojilar</b> saqlanadi.\n\n"
    "<code>{link}</code> — foydalanuvchining shaxsiy havolasi "
    "(<code>...?start=ref&lt;ID&gt;</code>)\n"
    "<code>{name}</code> — postni tarqatayotgan odamning ismi\n\n"
    "ℹ️ Post ostiga shu havolali <b>🔘 Post tugmasi</b> avtomatik qo'shiladi."
)

JOIN_TEXT = (
    "🔘 <b>Post tugmasi</b>\n\n"
    "Tarqatish posti ostidagi tugma uchun yangi matn yuboring. Tugma bosilganda "
    "post egasining shaxsiy havolasi ochiladi.\n"
    f"Standart: <b>{DEFAULT_CONTEST_JOIN_TEXT}</b>\n\n"
    "Premium emoji ishlatsangiz, uni matn bilan birga yuboring — birinchi premium "
    "emoji tugma ikonkasiga aylanadi.\n\n"
    f"Maksimum: {BUTTON_LIMIT} ta belgi."
)


# --------------------------------------------------------------------- bosh ekran
async def show(message: Message, state: FSMContext) -> None:
    settings = await get_contest_settings()
    enabled = bool(settings["enabled"])
    icon = "✅ bor" if settings["icon_custom_emoji_id"] else "yo'q"
    if settings["post"]:
        post = f"admin o'rnatgan ({TYPE_LABELS.get(settings['post']['type'], '')})"
    else:
        post = "standart matn"
    join = escape(settings["join_text"] or DEFAULT_CONTEST_JOIN_TEXT)
    if not settings["join_text"]:
        join += " (standart)"
    elif settings["join_icon"]:
        join += " + premium emoji"

    await state.set_state(ContestSG.show)
    await message.answer(
        "🎁 <b>Konkurs tugmasi</b>\n\n"
        f"Holat: <b>{'🟢 KO‘RINADI' if enabled else '🔴 YASHIRILGAN'}</b>\n"
        f"Matni: <b>{escape(str(settings['text']))}</b>\n"
        f"Premium emoji: <b>{icon}</b>\n"
        f"Rangi: <b>{button_style_label(settings['style'])}</b>\n"
        f"Joylashuvi: <b>{contest_position_label(str(settings['position']))}</b>\n\n"
        f"Tarqatish posti: <b>{post}</b>\n"
        f"Post tugmasi: <b>{join}</b>\n"
        f"Post tugmasi rangi: <b>{button_style_label(settings['join_style'])}</b>\n\n"
        "Tugma bosilganda foydalanuvchiga post keladi. Undagi havola — o'sha "
        "odamning shaxsiy taklif havolasi (oxirida uning Telegram ID si). Post "
        "orqali kirgan har bir yangi odam unga +1 ball bo'ladi.",
        reply_markup=contest_settings_kb(
            enabled,
            str(settings["position"]),
            bool(settings["post"]),
            bool(settings["join_text"] or settings["join_icon"])
            or settings["join_style"] != DEFAULT_CONTEST_STYLE,
        ),
    )


@router.message(PanelSG.home, F.text == BTN_CONTEST)
async def open_section(message: Message, state: FSMContext) -> None:
    await show(message, state)


@router.message(ContestSG.show, F.text.in_({BTN_ON, BTN_OFF}))
async def toggle(message: Message, state: FSMContext) -> None:
    settings = await get_contest_settings()
    await set_contest_enabled(not bool(settings["enabled"]))
    await message.answer("✅ O'zgartirildi")
    await show(message, state)


@router.message(ContestSG.show, F.text.in_({BTN_CT_TOP, BTN_CT_BOTTOM}))
async def move(message: Message, state: FSMContext) -> None:
    position = CONTEST_TOP if message.text == BTN_CT_TOP else CONTEST_BOTTOM
    await set_contest_position(position)
    await message.answer(f"✅ Joylashuvi: <b>{contest_position_label(position)}</b>")
    await show(message, state)


# ---------------------------------------------------------------------- tugma nomi
@router.message(ContestSG.show, F.text == BTN_CT_RENAME)
async def ask_text(message: Message, state: FSMContext) -> None:
    await state.set_state(ContestSG.waiting_text)
    await message.answer(RENAME_TEXT, reply_markup=cancel_kb())


@router.message(ContestSG.waiting_text, NOT_COMMAND)
async def save_text(message: Message, state: FSMContext) -> None:
    text, icon_custom_emoji_id = extract_button_text_and_icon(message)
    if not text or len(text) > BUTTON_LIMIT:
        await message.answer(
            f"❗️ Tugma nomi bo'sh bo'lmasin va {BUTTON_LIMIT} ta belgidan oshmasin. "
            "Premium emoji yuborsangiz, uning yoniga tugma nomini ham yozing.",
            reply_markup=cancel_kb(),
        )
        return
    if text in {USER_BACK, USER_HOME}:
        await message.answer(
            "❗️ Bu matn menyuning xizmat tugmasi uchun band. Boshqa nom yuboring.",
            reply_markup=cancel_kb(),
        )
        return
    root_items = await get_items(None)
    points = await get_my_points_settings()
    rating = await get_rating_settings()
    if any(item.title == text for item in root_items) or text in {
        points["text"],
        rating["text"],
    }:
        await message.answer(
            "❗️ Asosiy menyuda bunday nomli tugma bor. Boshqa nom yuboring.",
            reply_markup=cancel_kb(),
        )
        return

    settings = await get_contest_settings()
    try:
        await message.answer(
            "👇 Tugma shunday ko'rinadi:",
            reply_markup=menu_kb(
                [],
                is_root=True,
                my_points_enabled=False,
                contest_enabled=True,
                contest_text=text,
                contest_style=settings["style"],
                contest_icon_custom_emoji_id=icon_custom_emoji_id,
            ),
        )
    except TelegramBadRequest:
        await message.answer(PREMIUM_REJECTED, reply_markup=cancel_kb())
        return
    await set_contest_text(text, icon_custom_emoji_id)
    await message.answer("✅ Tugma nomi saqlandi")
    await show(message, state)


# ---------------------------------------------------------------- ranglar (2 xil)
@router.message(ContestSG.show, F.text == BTN_CT_STYLE)
async def ask_style(message: Message, state: FSMContext) -> None:
    settings = await get_contest_settings()
    await state.set_state(ContestSG.style)
    await message.answer(
        "🎨 <b>Konkurs tugmasi rangi</b>\n\n"
        f"Hozir: <b>{button_style_label(settings['style'])}</b>",
        reply_markup=button_style_kb(),
    )


@router.message(ContestSG.style, F.text.in_(set(BUTTON_STYLE_OPTIONS)))
async def save_style(message: Message, state: FSMContext) -> None:
    style = BUTTON_STYLE_OPTIONS[message.text]
    await set_contest_style(style)
    await message.answer(f"✅ Tugma rangi: <b>{button_style_label(style)}</b>")
    await show(message, state)


@router.message(ContestSG.show, F.text == BTN_CT_JOIN_STYLE)
async def ask_join_style(message: Message, state: FSMContext) -> None:
    settings = await get_contest_settings()
    await state.set_state(ContestSG.join_style)
    await message.answer(
        "🎨 <b>Post tugmasi rangi</b>\n\n"
        f"Hozir: <b>{button_style_label(settings['join_style'])}</b>",
        reply_markup=button_style_kb(),
    )


@router.message(ContestSG.join_style, F.text.in_(set(BUTTON_STYLE_OPTIONS)))
async def save_join_style(message: Message, state: FSMContext) -> None:
    style = BUTTON_STYLE_OPTIONS[message.text]
    await set_contest_join_style(style)
    await message.answer(f"✅ Post tugmasi rangi: <b>{button_style_label(style)}</b>")
    await show(message, state)


@router.message(ContestSG.style, F.text == BTN_BACK)
@router.message(ContestSG.join_style, F.text == BTN_BACK)
async def style_back(message: Message, state: FSMContext) -> None:
    await show(message, state)


# ---------------------------------------------------------------------------- post
async def _preview(message: Message, settings: dict) -> None:
    """Adminning o'z havolasi bilan — foydalanuvchi aynan shuni ko'radi."""
    user = message.from_user
    link = await ref_link(message.bot, user.id)
    await send_contest_post(
        message.bot, message.chat.id, settings, link=link, name=user.full_name
    )


@router.message(ContestSG.show, F.text == BTN_CT_POST)
async def ask_post(message: Message, state: FSMContext) -> None:
    await state.set_state(ContestSG.waiting_post)
    await message.answer(POST_TEXT, reply_markup=cancel_kb())
    await message.answer("👇 Hozirgi post (havola sizniki):")
    await _preview(message, await get_contest_settings())


@router.message(ContestSG.waiting_post, NOT_COMMAND)
async def save_post(message: Message, state: FSMContext) -> None:
    post = extract_contest_post(message)
    if post is None:
        await message.answer(
            "❗️ Matn, rasm / video / GIF / fayl yoki stiker yuboring.",
            reply_markup=cancel_kb(),
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

    settings = await get_contest_settings()
    await message.answer("👇 Foydalanuvchi shu ko'rinishda oladi:")
    try:
        await _preview(message, {**settings, "post": post})
    except TelegramBadRequest:
        await message.answer(
            "❗️ Post <b>saqlanmadi</b>: Telegram uni qabul qilmadi (format yoki "
            "premium emoji). Bot egasida Telegram Premium faol ekanini tekshiring.",
            reply_markup=cancel_kb(),
        )
        return

    await set_contest_post(post["type"], post["file_id"], post["text_html"])
    await message.answer("✅ Tarqatish posti saqlandi")
    if post["type"] not in NO_TEXT_TYPES and "{link}" not in (post["text_html"] or ""):
        await message.answer(
            "ℹ️ Matnda <code>{link}</code> yo'q — havola faqat post ostidagi "
            "tugmada bo'ladi."
        )
    await show(message, state)


@router.message(ContestSG.show, F.text == BTN_VIEW)
async def view_post(message: Message, state: FSMContext) -> None:
    await message.answer("👇 Foydalanuvchi shu ko'rinishda oladi (havola sizniki):")
    await _preview(message, await get_contest_settings())
    await show(message, state)


@router.message(ContestSG.show, F.text == BTN_CT_POST_RESET)
async def ask_reset_post(message: Message, state: FSMContext) -> None:
    await state.set_state(ContestSG.confirm_post_reset)
    await message.answer(
        "♻️ Tarqatish posti standart matnga qaytarilsinmi?",
        reply_markup=confirm_delete_kb(),
    )


@router.message(ContestSG.confirm_post_reset, F.text == BTN_YES_DELETE)
async def reset_post(message: Message, state: FSMContext) -> None:
    await delete_contest_post()
    await message.answer("♻️ Standart postga qaytarildi")
    await show(message, state)


@router.message(ContestSG.confirm_post_reset, F.text == BTN_NO)
async def keep_post(message: Message, state: FSMContext) -> None:
    await show(message, state)


# --------------------------------------------------------------------- post tugmasi
@router.message(ContestSG.show, F.text == BTN_CT_JOIN)
async def ask_join(message: Message, state: FSMContext) -> None:
    settings = await get_contest_settings()
    link = await ref_link(message.bot, message.from_user.id)
    await state.set_state(ContestSG.waiting_join)
    await message.answer(JOIN_TEXT, reply_markup=cancel_kb())
    await message.answer(
        "👇 Hozirgi tugma:",
        reply_markup=join_kb(
            link, settings["join_text"], settings["join_icon"], settings["join_style"]
        ),
    )


@router.message(ContestSG.waiting_join, NOT_COMMAND)
async def save_join(message: Message, state: FSMContext) -> None:
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

    settings = await get_contest_settings()
    link = await ref_link(message.bot, message.from_user.id)
    try:
        await message.answer(
            "👇 Tugma shunday ko'rinadi:",
            reply_markup=join_kb(link, text, icon_custom_emoji_id, settings["join_style"]),
        )
    except TelegramBadRequest:
        await message.answer(PREMIUM_REJECTED, reply_markup=cancel_kb())
        return

    await set_contest_join_button(text, icon_custom_emoji_id)
    await message.answer("✅ Post tugmasi saqlandi")
    await show(message, state)


@router.message(ContestSG.show, F.text == BTN_CT_JOIN_RESET)
async def reset_join(message: Message, state: FSMContext) -> None:
    await delete_contest_join_button()
    await message.answer(
        f"♻️ Post tugmasi standartga qaytarildi: <b>{DEFAULT_CONTEST_JOIN_TEXT}</b>"
    )
    await show(message, state)
