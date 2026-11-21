"""Yopiq kanal linki: N ta odam taklif qilganga shaxsiy, bir martalik havola.

Qachon ishlaydi:
  * har bir yangi taklifda (`middlewares/user_mw.py`) — taklif qilgan odamga
    tabrik boradi ("+1 ball, jami N ta, yana M ta qoldi"), shart shu taklif bilan
    bajarilgan bo'lsa, ortidan havolali post yuboriladi;
  * foydalanuvchi "Ballarim" tugmasini bosganda — shart avvalroq bajarilgan,
    lekin havola hali berilmagan bo'lsa (masalan admin bo'limni keyinroq yoqqan
    yoki kerakli sonni kamaytirgan).

Havola `member_limit=1` bilan ochiladi: boshqaga berib yuborilsa ham faqat bitta
odam kira oladi. Post foydalanuvchiga yetib bormasa (botni bloklagan) havola
bekor qilinadi va bazaga yozilmaydi — keyingi safar qaytadan beriladi.
"""

import asyncio
import logging
import time
from contextlib import suppress
from html import escape
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from db.queries import (
    add_private_link_grant,
    get_private_link_grant,
    get_private_link_settings,
    get_ref_notify_text,
    get_referral_count,
)
from utils.admins import admin_ids
from utils.content import send_raw_content
from utils.texts import DEFAULT_PRIVATE_LINK_TEXT, DEFAULT_REF_NOTIFY_TEXT

logger = logging.getLogger(__name__)

#: Shu kalitlardan biri bor qator faqat yopiq kanal maqsadi faol bo'lganda chiqadi
GOAL_KEYS = ("{need}", "{left}")

BTN_JOIN = "🔐 Kanalga kirish"
UNKNOWN_NAME = "Yangi foydalanuvchi"

#: Telegram invite link nomi uchun limit
LINK_NAME_LIMIT = 32
#: Kanal sozlamasi buzilgan bo'lsa adminlarni har taklifda bezovta qilmaslik uchun
ALERT_INTERVAL = 30 * 60

ALERT_TEXT = (
    "⚠️ <b>Yopiq kanal linki</b> yaratilmadi.\n\n"
    "Bot kanalda admin va <b>“Foydalanuvchilarni taklif qilish”</b> huquqi borligini "
    "tekshiring.\nXato: <code>{error}</code>"
)

#: Bir vaqtda ikkita taklif kelsa bitta odamga ikkita havola ochilmasin
_lock = asyncio.Lock()
_last_alert = 0.0


def _replace(template: str, values: dict[str, str]) -> str:
    """`str.format()` emas — admin matnidagi tasodifiy `{` xato bermasin."""
    for key, value in values.items():
        template = template.replace(key, value)
    return template


def goal_active(settings: dict) -> bool:
    """Bo'lim yoqilgan va to'liq sozlanganmi (kanal + takliflar soni)."""
    return bool(settings["enabled"] and settings["chat_id"] and settings["need"] > 0)


def render_notify_text(
    template: str, *, name: str, count: int, need: int, has_goal: bool
) -> str:
    """Tabrik matni.

    Maqsad yo'q bo'lsa (bo'lim o'chiq yoki havola allaqachon olingan) `{need}` /
    `{left}` bor qatorlar butunlay olib tashlanadi — "yana 0 ta qoldi" chiqmasin.
    """
    if not has_goal:
        lines = template.split("\n")
        template = "\n".join(line for line in lines if not any(k in line for k in GOAL_KEYS))
    return _replace(
        template,
        {
            "{name}": escape(name or UNKNOWN_NAME),
            "{count}": str(count),
            "{need}": str(need),
            "{left}": str(max(need - count, 0)),
        },
    ).strip()


def default_post() -> dict:
    return {"type": "text", "file_id": None, "text_html": DEFAULT_PRIVATE_LINK_TEXT}


def render_post(post: dict, *, link: str, count: int, need: int) -> dict:
    values = {"{link}": link, "{count}": str(count), "{need}": str(need)}
    return {**post, "text_html": _replace(post.get("text_html") or "", values)}


def join_kb(
    link: str, text: Optional[str] = None, icon_custom_emoji_id: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Post ostidagi tugma. Admin matn qo'ymagan bo'lsa — standart "🔐 Kanalga kirish"."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text or BTN_JOIN,
                    url=link,
                    icon_custom_emoji_id=icon_custom_emoji_id if text else None,
                )
            ]
        ]
    )


async def send_post(
    bot: Bot, chat_id: int, settings: dict, *, link: str, count: int, need: int
) -> None:
    """Havolali postni yuboradi: matndagi `{link}` + ostida "Kanalga kirish" tugmasi.

    `settings` — `get_private_link_settings()` natijasi (post va tugma shu yerdan).
    """
    await send_raw_content(
        bot,
        chat_id,
        render_post(settings.get("post") or default_post(), link=link, count=count, need=need),
        reply_markup=join_kb(
            link, settings.get("button_text"), settings.get("button_icon")
        ),
    )


async def _alert_admins(bot: Bot, error: Exception) -> None:
    global _last_alert
    now = time.monotonic()
    if _last_alert and now - _last_alert < ALERT_INTERVAL:
        return
    _last_alert = now
    text = ALERT_TEXT.format(error=escape(str(error)))
    for admin_id in admin_ids():
        with suppress(TelegramAPIError):
            await bot.send_message(admin_id, text)


async def grant_if_earned(
    bot: Bot,
    user_tg_id: int,
    count: Optional[int] = None,
    settings: Optional[dict] = None,
) -> bool:
    """Shart bajarilgan va havola hali berilmagan bo'lsa — yaratib yuboradi.

    True -> havola shu chaqiruvda yuborildi.
    """
    settings = settings or await get_private_link_settings()
    if not goal_active(settings):
        return False
    chat_id, need = settings["chat_id"], settings["need"]
    if count is None:
        count = await get_referral_count(user_tg_id)
    if count < need:
        return False

    async with _lock:
        if await get_private_link_grant(user_tg_id, chat_id) is not None:
            return False
        try:
            invite = await bot.create_chat_invite_link(
                chat_id,
                name=f"Taklif {user_tg_id}"[:LINK_NAME_LIMIT],
                member_limit=1,
            )
        except TelegramAPIError as exc:
            logger.error("Yopiq kanal havolasi yaratilmadi (%s): %s", chat_id, exc)
            await _alert_admins(bot, exc)
            return False

        try:
            await send_post(
                bot, user_tg_id, settings, link=invite.invite_link, count=count, need=need
            )
        except TelegramAPIError as exc:
            # yetib bormagan havola ochiq qolmasin; keyingi safar qayta beriladi
            logger.warning("Havolali post yetib bormadi (%s): %s", user_tg_id, exc)
            with suppress(TelegramAPIError):
                await bot.revoke_chat_invite_link(chat_id, invite.invite_link)
            return False

        await add_private_link_grant(user_tg_id, chat_id, invite.invite_link)

    logger.info("Yopiq kanal havolasi berildi: %s (%s ta taklif)", user_tg_id, count)
    return True


async def notify_referrer(bot: Bot, referrer_id: int, new_user_name: str) -> None:
    """Yangi taklifdan keyin: taklif qilganga tabrik + kerak bo'lsa havola."""
    count = await get_referral_count(referrer_id)
    logger.info("Yangi taklif: %s -> jami %s ta", referrer_id, count)

    settings = await get_private_link_settings()
    need = settings["need"]
    has_goal = (
        goal_active(settings)
        and count < need
        and await get_private_link_grant(referrer_id, settings["chat_id"]) is None
    )
    template = await get_ref_notify_text() or DEFAULT_REF_NOTIFY_TEXT
    options = {"link_preview_options": LinkPreviewOptions(is_disabled=True)}

    def render(text: str) -> str:
        return render_notify_text(
            text, name=new_user_name, count=count, need=need, has_goal=has_goal
        )

    try:
        try:
            await bot.send_message(referrer_id, render(template), **options)
        except TelegramBadRequest:
            # admin matnidagi HTML qator olib tashlanganda buzilishi mumkin
            await bot.send_message(referrer_id, render(DEFAULT_REF_NOTIFY_TEXT), **options)
    except TelegramForbiddenError:
        return  # botni bloklagan — havola ham yetib bormaydi
    except TelegramAPIError as exc:
        logger.warning("Tabrik yuborilmadi (%s): %s", referrer_id, exc)

    await grant_if_earned(bot, referrer_id, count=count, settings=settings)
