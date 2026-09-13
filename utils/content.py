"""Kontentni xabardan olish va foydalanuvchiga qayta yuborish."""

from typing import Optional, Union

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from db.models import Content

Markup = Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove]

TYPE_LABELS = {
    "text": "📝 Matn",
    "photo": "🖼 Rasm",
    "video": "🎬 Video",
    "document": "📄 Fayl",
    "audio": "🎵 Audio",
    "voice": "🎤 Ovozli xabar",
    "animation": "🎞 GIF",
    "video_note": "⭕️ Video xabar",
    "sticker": "🌟 Stiker",
}


def extract_content(message: Message) -> Optional[dict]:
    """Adminning xabaridan file_id + HTML matnni ajratib oladi."""
    caption = message.html_text if message.caption else None

    if message.photo:
        return {"type": "photo", "file_id": message.photo[-1].file_id, "text_html": caption}
    if message.video:
        return {"type": "video", "file_id": message.video.file_id, "text_html": caption}
    if message.animation:
        return {"type": "animation", "file_id": message.animation.file_id, "text_html": caption}
    if message.document:
        return {"type": "document", "file_id": message.document.file_id, "text_html": caption}
    if message.audio:
        return {"type": "audio", "file_id": message.audio.file_id, "text_html": caption}
    if message.voice:
        return {"type": "voice", "file_id": message.voice.file_id, "text_html": caption}
    if message.video_note:
        return {"type": "video_note", "file_id": message.video_note.file_id, "text_html": None}
    if message.sticker:
        return {"type": "sticker", "file_id": message.sticker.file_id, "text_html": None}
    if message.text:
        return {"type": "text", "file_id": None, "text_html": message.html_text}
    return None


async def send_content(
    bot: Bot,
    chat_id: int,
    content: Content,
    reply_markup: Optional[Markup] = None,
) -> None:
    """Saqlangan kontentni file_id yoki manba xabardan yuboradi."""
    t = content.type
    text = content.text_html
    fid = content.file_id
    source_chat_id = getattr(content, "source_chat_id", None)
    source_message_id = getattr(content, "source_message_id", None)

    if source_chat_id is not None and source_message_id is not None:
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=source_chat_id,
            message_id=source_message_id,
            caption=text,
            reply_markup=reply_markup,
        )
        return

    if t == "text":
        await bot.send_message(chat_id, text or "—", reply_markup=reply_markup)
    elif t == "photo":
        await bot.send_photo(chat_id, fid, caption=text, reply_markup=reply_markup)
    elif t == "video":
        await bot.send_video(chat_id, fid, caption=text, reply_markup=reply_markup)
    elif t == "animation":
        await bot.send_animation(chat_id, fid, caption=text, reply_markup=reply_markup)
    elif t == "document":
        await bot.send_document(chat_id, fid, caption=text, reply_markup=reply_markup)
    elif t == "audio":
        await bot.send_audio(chat_id, fid, caption=text, reply_markup=reply_markup)
    elif t == "voice":
        await bot.send_voice(chat_id, fid, caption=text, reply_markup=reply_markup)
    elif t == "video_note":
        await bot.send_video_note(chat_id, fid, reply_markup=reply_markup)
    elif t == "sticker":
        await bot.send_sticker(chat_id, fid, reply_markup=reply_markup)


async def send_raw_content(
    bot: Bot,
    chat_id: int,
    data: dict,
    reply_markup: Optional[Markup] = None,
) -> None:
    """extract_content() qaytargan dict yoki start-xabar dictini yuboradi."""

    class _Tmp:
        type = data.get("type")
        file_id = data.get("file_id")
        text_html = data.get("text_html")

    await send_content(bot, chat_id, _Tmp, reply_markup=reply_markup)  # type: ignore[arg-type]


def content_label(content: Content, index: int) -> str:
    label = TYPE_LABELS.get(content.type, content.type)
    preview = (content.text_html or "").replace("\n", " ")
    # HTML teglarini olib tashlaymiz — faqat ko'rinish uchun
    while "<" in preview and ">" in preview:
        start = preview.find("<")
        end = preview.find(">", start)
        if end == -1:
            break
        preview = preview[:start] + preview[end + 1 :]
    preview = preview.strip()
    if preview:
        preview = preview[:25] + ("…" if len(preview) > 25 else "")
        return f"{index}. {label} · {preview}"
    return f"{index}. {label}"
