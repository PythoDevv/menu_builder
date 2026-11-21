""""Konkursda qatnashish" tugmasi: shaxsiy havolali tarqatish posti.

Foydalanuvchi tugmani bosadi -> bot unga post yuboradi. Postdagi `{link}` va
post ostidagi tugma — o'sha odamning o'z taklif havolasi
(`https://t.me/<bot>?start=ref<tg_id>`, Ballarim bilan bir xil). Foydalanuvchi
postni do'stlariga forward qiladi: inline URL tugma forwardda ham saqlanadi,
shu havola orqali kirgan har bir yangi odam unga +1 ball bo'lib sanaladi.
"""

from html import escape
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from db.queries import DEFAULT_CONTEST_JOIN_TEXT
from utils.content import send_raw_content
from utils.texts import DEFAULT_CONTEST_POST_TEXT

#: Post sifatida qabul qilinadigan media (izohi bilan). Stiker izohsiz bo'ladi.
POST_MEDIA = ("photo", "video", "animation", "document")
#: Izohsiz turlar — `{link}` faqat post ostidagi tugmada bo'ladi
NO_TEXT_TYPES = ("sticker",)

UNKNOWN_NAME = "Do'stingiz"


def default_post() -> dict:
    return {"type": "text", "file_id": None, "text_html": DEFAULT_CONTEST_POST_TEXT}


def extract_contest_post(message: Message) -> Optional[dict]:
    """Matn, bitta media + izoh yoki stiker.

    Matn HTML ko'rinishida saqlanadi: aiogram premium custom emojini
    `<tg-emoji emoji-id="...">` tegi bilan yozadi, shuning uchun premium
    emojilar ham, `{link}` o'rinbosari ham buzilmaydi.
    """
    if message.text:
        return {"type": "text", "file_id": None, "text_html": message.html_text}
    for kind in POST_MEDIA:
        media = getattr(message, kind)
        if not media:
            continue
        file_id = media[-1].file_id if kind == "photo" else media.file_id
        text_html = message.html_text if message.caption else ""
        return {"type": kind, "file_id": file_id, "text_html": text_html}
    if message.sticker:
        return {"type": "sticker", "file_id": message.sticker.file_id, "text_html": None}
    return None


def render_post(post: dict, *, link: str, name: str) -> dict:
    """`str.format()` emas — admin matnidagi tasodifiy `{` xato bermasin."""
    text = post.get("text_html")
    if not text:
        return dict(post)
    text = text.replace("{link}", link).replace("{name}", escape(name or UNKNOWN_NAME))
    return {**post, "text_html": text}


def join_kb(
    link: str,
    text: Optional[str] = None,
    icon_custom_emoji_id: Optional[str] = None,
    style: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Post ostidagi havola tugmasi. Matn qo'yilmagan bo'lsa — "✅ Qatnashish"."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text or DEFAULT_CONTEST_JOIN_TEXT,
                    url=link,
                    style=style,
                    icon_custom_emoji_id=icon_custom_emoji_id if text else None,
                )
            ]
        ]
    )


async def send_contest_post(
    bot: Bot, chat_id: int, settings: dict, *, link: str, name: str
) -> None:
    """`settings` — `get_contest_settings()` natijasi (post va tugma shu yerdan)."""
    await send_raw_content(
        bot,
        chat_id,
        render_post(settings.get("post") or default_post(), link=link, name=name),
        reply_markup=join_kb(
            link,
            settings.get("join_text"),
            settings.get("join_icon"),
            settings.get("join_style"),
        ),
    )
