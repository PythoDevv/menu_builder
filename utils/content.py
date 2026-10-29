"""Kontentni xabardan olish va foydalanuvchiga qayta yuborish."""

import json
from typing import Optional, Union

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    MessageEntity,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import CONTENT_ARCHIVE_CHAT_ID
from db.models import Content

Markup = Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove]

# Custom emoji ID va boshqa entitylarni HTML parserdan o'tkazmay, aynan Telegramga
# qaytarish uchun text_html ustunida saqlanadigan versiyalangan format.
FORMATTED_TEXT_PREFIX = "tg_entities_v1:"
COPIED_MESSAGE_PREFIX = "tg_copy_v1:"
COPIED_MESSAGE_GROUP_PREFIX = "tg_copy_group_v1:"
# aiogram rich_message ichidagi kelajak blokni parse qila olmasa, polling qatlami
# uni olib tashlab, xabarni copy qilish kerakligini shu marker bilan bildiradi.
RICH_MESSAGE_COPY_MARKER = "_rich_message_copy_needed"

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
    "message_copy": "📋 Asl post nusxasi",
    "message_group": "🖼 Albom",
}


class ContentArchiveNotConfiguredError(RuntimeError):
    """Rich post uchun arxiv kanal belgilanmaganda ko'tariladi."""


def _copied_message_ref(chat_id: int, message_id: int) -> str:
    """DBdagi file_id ustunida nusxa olinadigan xabarning manzilini saqlaydi."""
    return f"{COPIED_MESSAGE_PREFIX}{chat_id}:{message_id}"


def _parse_copied_message_ref(value: Optional[str]) -> Optional[tuple[int, int]]:
    """Arxiv xabari manzilini xavfsiz o'qiydi."""
    if not value or not value.startswith(COPIED_MESSAGE_PREFIX):
        return None
    try:
        chat_id, message_id = value[len(COPIED_MESSAGE_PREFIX) :].rsplit(":", 1)
        return int(chat_id), int(message_id)
    except (TypeError, ValueError):
        return None


def _copied_message_group_ref(chat_id: int, message_ids: list[int]) -> str:
    """Arxivdagi albom a'zolarini bitta ixcham DB qiymatiga aylantiradi."""
    return f"{COPIED_MESSAGE_GROUP_PREFIX}{chat_id}:{','.join(map(str, message_ids))}"


def _parse_copied_message_group_ref(
    value: Optional[str],
) -> Optional[tuple[int, list[int]]]:
    """Arxiv albomi manzilini o'qiydi va Telegram limitlarini tekshiradi."""
    if not value or not value.startswith(COPIED_MESSAGE_GROUP_PREFIX):
        return None
    try:
        chat_id_raw, message_ids_raw = value[len(COPIED_MESSAGE_GROUP_PREFIX) :].split(
            ":", 1
        )
        message_ids = [int(value) for value in message_ids_raw.split(",")]
        if not 2 <= len(message_ids) <= 100 or message_ids != sorted(set(message_ids)):
            return None
        return int(chat_id_raw), message_ids
    except (TypeError, ValueError):
        return None


def extract_button_text_and_icon(message: Message) -> tuple[str, Optional[str]]:
    """Tugma nomi va undagi birinchi premium custom emoji ID sini ajratadi.

    Telegram tugma ikonkasini matn entitysi bilan emas, alohida
    ``icon_custom_emoji_id`` maydonida kutadi. Shu sabab birinchi custom emoji
    matndan olinadi va uning ID si ikonka sifatida qaytariladi.
    """
    text = message.text or ""
    entity = next(
        (
            item
            for item in (message.entities or [])
            if item.type == "custom_emoji" and item.custom_emoji_id
        ),
        None,
    )
    if entity is None:
        return text.strip(), None

    encoded = text.encode("utf-16-le")
    start = entity.offset * 2
    end = (entity.offset + entity.length) * 2
    label = (encoded[:start] + encoded[end:]).decode("utf-16-le").strip()
    return label, entity.custom_emoji_id


def _serialize_formatted_text(
    text: str, entities: list[MessageEntity]
) -> str:
    """Raw matn va Telegram entitylarini IDlari bilan JSON ko'rinishida saqlaydi."""
    payload = {
        "text": text,
        "entities": [
            entity.model_dump(mode="json", exclude_none=True) for entity in entities
        ],
    }
    return FORMATTED_TEXT_PREFIX + json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    )


def _deserialize_formatted_text(
    value: Optional[str],
) -> Optional[tuple[str, list[MessageEntity]]]:
    """Yangi entity formatini o'qiydi; eski HTML kontent uchun None qaytaradi."""
    if not value or not value.startswith(FORMATTED_TEXT_PREFIX):
        return None
    try:
        payload = json.loads(value[len(FORMATTED_TEXT_PREFIX) :])
        text = payload["text"]
        entities = [MessageEntity.model_validate(item) for item in payload["entities"]]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(text, str):
        return None
    return text, entities


def _stored_text(
    raw_text: Optional[str],
    entities: Optional[list[MessageEntity]],
    html_text: Optional[str],
) -> Optional[str]:
    """Matnni Telegram entity IDlari bilan saqlaydi; eski HTML fallback bo'lib qoladi."""
    entity_list = list(entities or [])
    if raw_text is not None:
        return _serialize_formatted_text(raw_text, entity_list)
    return html_text


def extract_content(message: Message) -> Optional[dict]:
    """Admin xabaridan file_id va formatlangan matnni ajratib oladi.

    Raw matn barcha Telegram entitylari bilan saqlanadi. Shu jumladan premium
    custom emoji ID si ham parse qilinmay, yuborishda Telegramga qaytariladi.
    Eski HTML kontentlar avvalgidek ishlashda davom etadi.
    """
    # Rich messages oddiy text/entitylarga aylanmaydi. Ularni Telegramning o'zi
    # nusxalashi kerak, aks holda premium emoji va bloklar yo'qolishi mumkin.
    if (
        getattr(message, "rich_message", None) is not None
        or getattr(message, RICH_MESSAGE_COPY_MARKER, False)
    ):
        return {"type": "rich_message", "file_id": None, "text_html": None}

    caption = _stored_text(
        message.caption,
        getattr(message, "caption_entities", None),
        getattr(message, "html_caption", None) if message.caption is not None else None,
    )

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
        return {
            "type": "text",
            "file_id": None,
            "text_html": _stored_text(message.text, message.entities, message.html_text),
        }
    return None


async def prepare_content(bot: Bot, message: Message) -> Optional[dict]:
    """Kontentni saqlashga tayyorlaydi; rich postni doimiy arxivga ko'chiradi.

    Oddiy xabarlar avvalgi ``file_id`` va entitylar mexanizmi bilan qaytadi.
    Rich post esa arxivdagi chat/message ID bilan qaytadi: keyin foydalanuvchiga
    ``copyMessage`` qilinadi va Telegram formati to'liq saqlanadi.
    """
    data = extract_content(message)
    if data is None or data["type"] != "rich_message":
        return data

    if CONTENT_ARCHIVE_CHAT_ID is None:
        raise ContentArchiveNotConfiguredError(
            "CONTENT_ARCHIVE_CHAT_ID sozlanmagan"
        )

    copied = await bot.copy_message(
        chat_id=CONTENT_ARCHIVE_CHAT_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    return {
        "type": "message_copy",
        "file_id": _copied_message_ref(CONTENT_ARCHIVE_CHAT_ID, copied.message_id),
        "text_html": None,
    }


async def prepare_media_group(
    bot: Bot, source_chat_id: int, source_message_ids: list[int]
) -> dict:
    """Admin yuborgan albomni arxivga bitta guruh bo'lib nusxalaydi.

    ``copyMessages`` Telegram tomonida albom ko'rinishini saqlaydi. Keyin aynan
    shu arxiv IDlar bilan foydalanuvchiga ham bitta albom qaytariladi.
    """
    if CONTENT_ARCHIVE_CHAT_ID is None:
        raise ContentArchiveNotConfiguredError(
            "CONTENT_ARCHIVE_CHAT_ID sozlanmagan"
        )
    message_ids = sorted(set(source_message_ids))
    if not 2 <= len(message_ids) <= 100:
        raise ValueError("Albom 2 dan 100 tagacha xabardan iborat bo'lishi kerak")

    copied = await bot.copy_messages(
        chat_id=CONTENT_ARCHIVE_CHAT_ID,
        from_chat_id=source_chat_id,
        message_ids=message_ids,
    )
    copied_ids = [message.message_id for message in copied]
    if len(copied_ids) != len(message_ids):
        raise ValueError("Albomning barcha rasmlari arxivga nusxalanmadi")
    return {
        "type": "message_group",
        "file_id": _copied_message_group_ref(CONTENT_ARCHIVE_CHAT_ID, copied_ids),
        "text_html": None,
    }


async def send_content(
    bot: Bot,
    chat_id: int,
    content: Content,
    reply_markup: Optional[Markup] = None,
) -> None:
    """Saqlangan kontentni file_id va Telegram entitylari bilan yuboradi."""
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

    formatted = _deserialize_formatted_text(text)
    rendered_text = formatted[0] if formatted else text
    rendered_entities = formatted[1] if formatted else None

    if t == "message_copy":
        source = _parse_copied_message_ref(fid)
        if source is None:
            raise ValueError("Saqlangan post manzili noto'g'ri")
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=source[0],
            message_id=source[1],
            reply_markup=reply_markup,
        )
        return

    if t == "message_group":
        source = _parse_copied_message_group_ref(fid)
        if source is None:
            raise ValueError("Saqlangan albom manzili noto'g'ri")
        # copyMessages albom guruhlanishini saqlaydi. Bot API bu metodga
        # reply_markup qabul qilmaydi; menyu reply-klaviaturasi foydalanuvchida
        # avvaldan turadi va o'zgarishsiz qoladi.
        await bot.copy_messages(
            chat_id=chat_id,
            from_chat_id=source[0],
            message_ids=source[1],
        )
        return

    caption_options = (
        {"caption_entities": rendered_entities, "parse_mode": None}
        if formatted
        else {}
    )

    if t == "text":
        if formatted:
            await bot.send_message(
                chat_id,
                rendered_text or "—",
                entities=rendered_entities,
                parse_mode=None,
                reply_markup=reply_markup,
            )
        else:
            await bot.send_message(chat_id, text or "—", reply_markup=reply_markup)
    elif t == "photo":
        await bot.send_photo(
            chat_id,
            fid,
            caption=rendered_text,
            **caption_options,
            reply_markup=reply_markup,
        )
    elif t == "video":
        await bot.send_video(
            chat_id,
            fid,
            caption=rendered_text,
            **caption_options,
            reply_markup=reply_markup,
        )
    elif t == "animation":
        await bot.send_animation(
            chat_id,
            fid,
            caption=rendered_text,
            **caption_options,
            reply_markup=reply_markup,
        )
    elif t == "document":
        await bot.send_document(
            chat_id,
            fid,
            caption=rendered_text,
            **caption_options,
            reply_markup=reply_markup,
        )
    elif t == "audio":
        await bot.send_audio(
            chat_id,
            fid,
            caption=rendered_text,
            **caption_options,
            reply_markup=reply_markup,
        )
    elif t == "voice":
        await bot.send_voice(
            chat_id,
            fid,
            caption=rendered_text,
            **caption_options,
            reply_markup=reply_markup,
        )
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
    if content.type == "message_group":
        group = _parse_copied_message_group_ref(content.file_id)
        size = len(group[1]) if group else 0
        return f"{index}. {label} · {size} ta"
    formatted = _deserialize_formatted_text(content.text_html)
    preview = ((formatted[0] if formatted else content.text_html) or "").replace(
        "\n", " "
    )
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
