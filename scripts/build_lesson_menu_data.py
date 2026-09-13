#!/usr/bin/env python3
"""Build lesson_menu.json from the Telegram HTML export and media folder."""

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional


MESSAGE_START_RE = re.compile(
    r'(?=<div class="message default[^>]*id="message\d+">)'
)
MESSAGE_ID_RE = re.compile(
    r'<div class="message default[^>]*id="message(\d+)">'
)
VIDEO_RE = re.compile(r'href="(video_files/[^"]+\.(?:mp4|MP4))"', re.I)
TEXT_RE = re.compile(r'<div class="text">\s*(.*?)\s*</div>', re.S)


class _CaptionHTMLParser(HTMLParser):
    """Convert Telegram Desktop's HTML fragment to Telegram-safe HTML."""

    ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "a"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.open_tags: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        tag = {"strong": "b", "em": "i"}.get(tag, tag)
        if tag == "br":
            self.parts.append("\n")
        elif tag in self.ALLOWED_TAGS:
            if tag == "a":
                href = dict(attrs).get("href")
                if href:
                    self.parts.append(f'<a href="{html.escape(href, quote=True)}">')
                    self.open_tags.append(tag)
            else:
                self.parts.append(f"<{tag}>")
                self.open_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = {"strong": "b", "em": "i"}.get(tag, tag)
        if tag in self.open_tags:
            self.parts.append(f"</{tag}>")
            self.open_tags.remove(tag)

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data, quote=False))

    def result(self) -> str:
        return "".join(self.parts).strip()


def caption_html(value: str) -> str:
    parser = _CaptionHTMLParser()
    parser.feed(value)
    return parser.result()

JAHONGIR_TOPICS = {
    1: "Lahn ta'rifi, qismlari va hukmi",
    2: "Isti'oza va basmalaning holatlari",
    3: "Qur'on qiroatida tezlik darajalari",
    4: "Harflarning sifatlari",
    5: "Rahova, shidda va bayniya sifatlari",
    6: "Iste'lo, istefola, infitoh va itboq tovushlari",
    7: "Sukunli nun va tanvin: izhor qoidasi",
    8: "Sukunli nun va tanvin: idg'om qoidasi",
    9: "Sukunli nun va tanvin: iqlob qoidasi",
    10: "Sukunli nun va tanvin: ixfo qoidasi",
    11: "Sukunli mim qoidasi",
    12: "Tashdidli nun va mim, g'unna",
    13: "Sukunli lom qoidasi",
    14: "Ro harfining holati",
    15: "Mad: qismlari, turlari va hukmi",
    16: "Badal mad",
    17: "Mad muttasil",
    18: "Mad sila",
    19: "Mad lozim",
    20: "Mad oriz",
    21: "Mad lin",
    22: "Madning darajalari",
    23: "Idg'om mutamasilayn va mutajonisayn",
    24: "Idg'om mutoqoribayn",
    25: "Ziddi yo'q sifatlar",
    26: "Vaqf va ibtido",
    27: "Joiz vaqf",
    28: "Nojoiz vaqf",
    29: "Ibtido",
    30: "Ravm, ishmom va sukun",
    31: "Imola, nabr va tas'hil",
}

JAHONGIR_SURAS = {
    1: "Fotiha",
    2: "Nos",
    3: "Falaq",
    4: "Ixlos",
    5: "Masad",
    6: "Nasr",
    7: "Kofirun",
    8: "Kavsar",
    9: "Mo'un",
    10: "Quraysh",
    11: "Fil",
    12: "Humaza",
    13: "Asr",
    14: "Takosur",
    15: "Qori'a",
    16: "Odiyat",
    17: "Zalzala",
    18: "Bayyina 1–5-oyatlar",
    19: "Bayyina 6–8-oyatlar",
    20: "Qadr",
    21: "Alaq",
    22: "Tiyn",
    23: "Sharh",
    24: "Zuho",
    25: "Layl",
}

ALIJON_EXTRA_TOPICS = {
    26: "Mim harfi maxraji",
    27: "G'unna haqida",
    28: "Tartil, hadr va tahqiq haqida tushuncha",
}

ALIJON_EXTRA_FILES = {
    26: "video_files/26-sontg.mp4",
    27: "video_files/27-son tg.mp4",
    28: "video_files/28-son tg.mp4",
}

CYRILLIC_TO_LATIN = str.maketrans(
    {
        "А": "A", "а": "a", "Б": "B", "б": "b", "В": "V", "в": "v",
        "Г": "G", "г": "g", "Д": "D", "д": "d", "Е": "E", "е": "e",
        "Ё": "Yo", "ё": "yo", "Ж": "J", "ж": "j", "З": "Z", "з": "z",
        "И": "I", "и": "i", "Й": "Y", "й": "y", "К": "K", "к": "k",
        "Л": "L", "л": "l", "М": "M", "м": "m", "Н": "N", "н": "n",
        "О": "O", "о": "o", "П": "P", "п": "p", "Р": "R", "р": "r",
        "С": "S", "с": "s", "Т": "T", "т": "t", "У": "U", "у": "u",
        "Ф": "F", "ф": "f", "Х": "X", "х": "x", "Ц": "Ts", "ц": "ts",
        "Ч": "Ch", "ч": "ch", "Ш": "Sh", "ш": "sh", "Ъ": "'", "ъ": "'",
        "Ь": "", "ь": "", "Э": "E", "э": "e", "Ю": "Yu", "ю": "yu",
        "Я": "Ya", "я": "ya", "Ў": "O'", "ў": "o'", "Қ": "Q", "қ": "q",
        "Ғ": "G'", "ғ": "g'", "Ҳ": "H", "ҳ": "h",
    }
)


def clean_html_text(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " | ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return " ".join(html.unescape(value).split())


def latinize(value: str) -> str:
    return value.translate(CYRILLIC_TO_LATIN)


def parse_html_messages(html_file: Path) -> List[Dict[str, Any]]:
    document = html_file.read_text(encoding="utf-8")
    messages = []
    seen_files = set()

    for block in MESSAGE_START_RE.split(document):
        message_match = MESSAGE_ID_RE.match(block)
        video_match = VIDEO_RE.search(block)
        text_match = TEXT_RE.search(block)
        if not message_match or not video_match or not text_match:
            continue

        file_path = html.unescape(video_match.group(1))
        if file_path in seen_files:
            continue
        seen_files.add(file_path)
        messages.append(
            {
                "message_id": int(message_match.group(1)),
                "file": file_path,
                "text": clean_html_text(text_match.group(1)),
            }
        )

    return messages


def lesson(
    number: int,
    title: str,
    file_path: str,
    source_message_id: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "type": "video",
        "file": file_path,
        "source_message_id": source_message_id,
        "caption_html": f"<b>{number}-dars</b> — {html.escape(title)}",
    }


def build_muallimi_lessons(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for message in messages:
        match = re.search(
            r"Муаллими соний\s*\|\s*(\d+)-дарс\s*\|\s*(.+?)\s*\|\s*\|\s*©",
            message["text"],
        )
        if not match:
            match = re.search(
                r"Muallimi soniy\s*\|\s*(\d+)-dars\s*\|\s*(.+?)\s*\|\s*\|\s*©",
                message["text"],
            )
        if not match:
            continue
        number = int(match.group(1))
        topic = latinize(match.group(2)).strip().rstrip(".")
        result.append(
            lesson(
                number,
                topic,
                message["file"],
                message["message_id"],
            )
        )
    return sorted(result, key=lambda item: item["number"])


def build_alijon_lessons(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    message_ids_by_file = {
        message["file"]: message["message_id"] for message in messages
    }
    for message in messages:
        if "Shayx Alijon qori" not in message["text"]:
            continue
        match = re.search(
            r"(\d+)-son\s+(.+?)\s*\|\s*Shayx Alijon qori", message["text"]
        )
        if not match:
            continue
        number = int(match.group(1))
        topic = match.group(2).strip(' "')
        result.append(
            lesson(number, topic, message["file"], message["message_id"])
        )

    existing_numbers = {item["number"] for item in result}
    for number, topic in ALIJON_EXTRA_TOPICS.items():
        if number not in existing_numbers:
            file_path = ALIJON_EXTRA_FILES[number]
            message_id = message_ids_by_file.get(file_path)
            if message_id is None:
                raise ValueError(f"Source message ID is missing for {file_path}")
            result.append(lesson(number, topic, file_path, message_id))

    return sorted(result, key=lambda item: item["number"])


def build_jahongir_lessons(
    export_dir: Path, messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    message_ids_by_file = {
        message["file"]: message["message_id"] for message in messages
    }
    files_by_number = {}
    for file_path in (export_dir / "video_files").glob("Tajvid_fani_*.mp4"):
        match = re.match(r"Tajvid_fani_(\d+)_", file_path.name, re.I)
        if match:
            files_by_number[int(match.group(1))] = file_path

    missing = sorted(set(JAHONGIR_TOPICS) - set(files_by_number))
    if missing:
        raise ValueError(f"Jahongir qori video files are missing: {missing}")

    result = []
    for number in sorted(JAHONGIR_TOPICS):
        file_path = str(files_by_number[number].relative_to(export_dir))
        message_id = message_ids_by_file.get(file_path)
        if message_id is None:
            raise ValueError(f"Source message ID is missing for {file_path}")
        result.append(
            lesson(number, JAHONGIR_TOPICS[number], file_path, message_id)
        )
    return result


def group_lessons(lessons: List[Dict[str, Any]], size: int = 3) -> List[Dict[str, Any]]:
    groups = []
    for start in range(0, len(lessons), size):
        contents = lessons[start : start + size]
        first_number = contents[0]["number"]
        last_number = contents[-1]["number"]
        if first_number == last_number:
            title = f"🎬 {first_number}-dars"
        else:
            title = f"🎬 {first_number}–{last_number}-darslar"
        groups.append({"title": title, "contents": contents})
    return groups


def build_initial_payload(export_dir: Path) -> Dict[str, Any]:
    messages = parse_html_messages(export_dir / "messages.html")
    muallimi = build_muallimi_lessons(messages)
    alijon = build_alijon_lessons(messages)
    jahongir = build_jahongir_lessons(export_dir, messages)

    if len(muallimi) != 72:
        raise ValueError(f"Expected 72 Muallimi soniy lessons, found {len(muallimi)}")
    if len(alijon) != 28:
        raise ValueError(f"Expected 28 Alijon lessons, found {len(alijon)}")

    return {
        "schema_version": 1,
        "export_folder": export_dir.name,
        "group_size": 3,
        "parents": [
            {
                "title": "📹 Shayx Alijon qori darslari",
                "sections": [
                    {
                        "title": "📚 Muallimi soniy videodarslari",
                        "items": group_lessons(muallimi),
                    },
                    {
                        "title": "🎙 Tajvid savol-javoblari",
                        "items": group_lessons(alijon),
                    },
                ],
            },
            {
                "title": "📹 Jahongir qori darslari",
                "sections": [
                    {
                        "title": "📚 Tajvid fani",
                        "items": group_lessons(jahongir),
                    }
                ],
            },
        ],
    }


def parse_export_messages(html_file: Path) -> Dict[int, Dict[str, Any]]:
    """Parse IDs and media metadata even when Telegram did not download media."""
    document = html_file.read_text(encoding="utf-8")
    result: Dict[int, Dict[str, Any]] = {}
    for block in MESSAGE_START_RE.split(document):
        message_match = MESSAGE_ID_RE.match(block)
        if not message_match:
            continue

        media_type = None
        for candidate in ("video", "file", "photo", "audio", "voice"):
            if f"media_{candidate}" in block:
                media_type = "document" if candidate == "file" else candidate
                break

        text_match = TEXT_RE.search(block)
        title_match = re.search(
            r'<div class="title bold">\s*(.*?)\s*</div>', block, re.S
        )
        href_match = re.search(
            r'href="((?:video_files|files|photos|audio_files|voice_messages)/[^"]+)"',
            block,
            re.I,
        )
        result[int(message_match.group(1))] = {
            "type": media_type or "text",
            "text": clean_html_text(text_match.group(1)) if text_match else "",
            "caption_html": caption_html(text_match.group(1)) if text_match else "",
            "file_title": clean_html_text(title_match.group(1)) if title_match else "",
            "file": html.unescape(href_match.group(1)) if href_match else None,
        }
    return result


def _source_content(
    messages: Dict[int, Dict[str, Any]],
    message_id: int,
    number: int,
    title: str,
    media_type: str = "video",
) -> Dict[str, Any]:
    message = messages.get(message_id)
    if message is None:
        raise ValueError(f"Message {message_id} is missing from the export")
    if message["type"] != media_type:
        raise ValueError(
            f"Message {message_id}: expected {media_type}, found {message['type']}"
        )
    label = "dars" if media_type == "video" else "hujjat"
    caption_prefix = "Muqaddima" if number == 0 else f"{number}-{label}"
    caption_html = f"<b>{caption_prefix}</b>"
    if title.casefold() != caption_prefix.casefold():
        caption_html += f" — {html.escape(title)}"
    return {
        "number": number,
        "title": title,
        "type": media_type,
        "file": message.get("file"),
        "source_message_id": message_id,
        "caption_html": caption_html,
    }


def _video_range(
    messages: Dict[int, Dict[str, Any]],
    start_id: int,
    count: int,
    titles: Optional[Dict[int, str]] = None,
) -> List[Dict[str, Any]]:
    return [
        _source_content(
            messages,
            start_id + number - 1,
            number,
            (titles or {}).get(number, f"{number}-dars"),
        )
        for number in range(1, count + 1)
    ]


def _document_title(message: Dict[str, Any], fallback: str) -> str:
    title = message.get("file_title") or Path(message.get("file") or fallback).name
    title = re.sub(r"\.pdf$", "", title, flags=re.I).replace("_", " ")
    return " ".join(title.split())[:60]


def _document_items(
    messages: Dict[int, Dict[str, Any]], message_ids: List[int]
) -> List[Dict[str, Any]]:
    items = []
    for number, message_id in enumerate(message_ids, start=1):
        message = messages.get(message_id)
        if message is None:
            raise ValueError(f"Message {message_id} is missing from the export")
        title = _document_title(message, f"{number}-hujjat")
        content = _source_content(
            messages, message_id, number, title, media_type="document"
        )
        items.append({"title": f"📄 {title}", "contents": [content]})
    return items


def _section(title: str, lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"title": title, "items": group_lessons(lessons)}


def _day_section(title: str, lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
    items = group_lessons(lessons)
    for item in items:
        item["title"] = item["title"].replace("-darslar", "-kunlar").replace(
            "-dars", "-kun"
        )
    return {"title": title, "items": items}


def build_payload(export_dir: Path) -> Dict[str, Any]:
    """Build all default submenus from the complete 2026-09-13 export."""
    messages = parse_export_messages(export_dir / "messages.html")
    if max(messages, default=0) < 602:
        raise ValueError("A complete export containing messages through ID 602 is required")

    muallimi_titles = {}
    for number, message_id in enumerate(range(105, 177), start=1):
        match = re.search(
            r"(?:Муаллими соний|Muallimi soniy)\s*\|\s*"
            r"\d+-(?:дарс|dars)\s*\|\s*(.+?)\s*\|\s*\|\s*©",
            messages[message_id]["text"],
            re.I,
        )
        if not match:
            raise ValueError(f"Muallimi soniy title is missing in message {message_id}")
        muallimi_titles[number] = latinize(match.group(1)).strip().rstrip(".")
    muallimi = _video_range(messages, 105, 72, muallimi_titles)
    alijon_ids = list(range(178, 201)) + list(range(202, 207))
    alijon = []
    for number, message_id in enumerate(alijon_ids, start=1):
        match = re.search(
            r"\d+\s*-?son\s+(.+?)\s*\|\s*Shay[xh] Alijon [Qq]ori",
            messages[message_id]["text"],
            re.I,
        )
        if not match:
            raise ValueError(f"Alijon title is missing in message {message_id}")
        title = match.group(1).strip(' "')
        alijon.append(_source_content(messages, message_id, number, title))
    jahongir_tajvid = [
        _source_content(messages, 211 + number, number, JAHONGIR_TOPICS[number])
        for number in JAHONGIR_TOPICS
    ]
    jahongir_suras = _video_range(messages, 245, 25, JAHONGIR_SURAS)

    ayman = []
    for number, message_id in enumerate(range(272, 297), start=1):
        raw_title = messages[message_id]["text"].split(" | ", 1)[0]
        title = re.sub(r"^\d+\.\s*", "", raw_title).strip() or f"{number}-dars"
        ayman.append(_source_content(messages, message_id, number, title))

    yoldosh = _video_range(messages, 298, 12, JAHONGIR_SURAS)
    hasan_tajvid = _video_range(messages, 310, 27)

    iqro_entries = [
        {
            "title": "🎬 Kirish",
            "contents": [_source_content(messages, 338, 0, "Kirish")],
        }
    ]
    for number in range(1, 22):
        video_id = 339 if number == 1 else 337 + number * 2
        document_id = video_id + 1
        iqro_entries.append(
            {
                "title": f"🎬 {number}-dars",
                "contents": [
                    _source_content(messages, video_id, number, f"{number}-dars"),
                    _source_content(
                        messages,
                        document_id,
                        number,
                        f"{number}-dars qo'llanmasi",
                        media_type="document",
                    ),
                ],
            }
        )

    on_kecha_first = []
    for number in range(1, 10):
        video_id = 380 + number * 2
        on_kecha_first.append(
            {
                "number": number,
                "title": f"{number}-kun",
                "contents": [
                    _source_content(messages, video_id, number, f"{number}-kun"),
                    _source_content(
                        messages,
                        video_id + 1,
                        number,
                        f"{number}-kun qo'llanmasi",
                        media_type="document",
                    ),
                ],
            }
        )

    def grouped_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for start in range(0, len(entries), 3):
            chunk = entries[start : start + 3]
            first = chunk[0]["number"]
            last = chunk[-1]["number"]
            label = f"{first}-kun" if first == last else f"{first}–{last}-kunlar"
            result.append(
                {
                    "title": f"🎬 {label}",
                    "contents": [c for entry in chunk for c in entry["contents"]],
                }
            )
        return result

    on_kecha_second_intro = _source_content(
        messages, 401, 0, "2-bosqich — Muqaddima"
    )
    on_kecha_second = [
        _source_content(messages, 401 + number, number, f"2-bosqich — {number}-kun")
        for number in range(1, 11)
    ]
    on_kecha_third_intro = _source_content(
        messages, 413, 0, "3-bosqich — Muqaddima"
    )
    on_kecha_third = [
        _source_content(messages, 413 + number, number, f"3-bosqich — {number}-kun")
        for number in range(1, 11)
    ]

    shayx_muhammad = _video_range(messages, 425, 28)
    munavvar = _video_range(messages, 453, 42)
    english = [
        _source_content(messages, 501 + number, number, f"Tajweed — Day {number}")
        for number in range(1, 31)
    ]
    ali_zoirov = []
    for number, message_id in enumerate(range(532, 560), start=1):
        raw_title = messages[message_id]["text"].split(" | ", 1)[0]
        title = re.sub(r"^\d+\.\s*", "", raw_title).strip() or f"{number}-dars"
        ali_zoirov.append(_source_content(messages, message_id, number, title))

    return {
        "schema_version": 1,
        "export_folder": export_dir.name,
        "group_size": 3,
        "parents": [
            {
                "title": "📹 Shayx Alijon qori darslari",
                "sections": [
                    _section("📚 Muallimi soniy videodarslari", muallimi),
                    _section("🎙 Tajvid savol-javoblari", alijon),
                ],
            },
            {
                "title": "📹 Jahongir qori darslari",
                "sections": [
                    _section("📚 Tajvid fani", jahongir_tajvid),
                    _section("📖 Suralarni o'rganamiz", jahongir_suras),
                ],
            },
            {
                "title": "📹 Shayx Muhammad domla. Tartil",
                "sections": [_section("📚 Tartil asoslari", shayx_muhammad)],
            },
            {
                "title": "📹 Munavvar ustoza. Tajvid",
                "sections": [_section("📚 Tajvid videodarslari", munavvar)],
            },
            {
                "title": "📹 Hasanxon domla darslari",
                "sections": [
                    _section("📚 Tajvid darslari", hasan_tajvid),
                    {"title": "📖 Iqro darslari", "items": iqro_entries},
                    {
                        "title": "🌙 O'n kecha — 1-bosqich",
                        "items": grouped_entries(on_kecha_first),
                    },
                    {
                        "title": "🌙 O'n kecha — 2-bosqich",
                        "items": [
                            {"title": "🎬 Muqaddima", "contents": [on_kecha_second_intro]},
                            *_day_section("", on_kecha_second)["items"],
                        ],
                    },
                    {
                        "title": "🌙 O'n kecha — 3-bosqich",
                        "items": [
                            {"title": "🎬 Muqaddima", "contents": [on_kecha_third_intro]},
                            *_day_section("", on_kecha_third)["items"],
                        ],
                    },
                ],
            },
            {
                "title": "📹 Ali Zoirov darslari",
                "sections": [_section("📚 Arab harflari", ali_zoirov)],
            },
            {
                "title": "📹 Yo'ldosh Ibrohim. Suralar",
                "sections": [_section("📚 Tartil tahlili", yoldosh)],
            },
            {
                "title": "📹 Ayman Suvayd. Maxraj darslari",
                "sections": [_section("📚 Harflar maxraji", ayman)],
            },
            {
                "title": "📹 Tajweed in English",
                "sections": [_section("📚 30-day Tajweed", english)],
            },
            {
                "title": "📗 Muallim soniy. Pdf",
                "sections": [
                    {
                        "title": "📚 Muallim soniy kitoblari",
                        "items": _document_items(
                            messages, list(range(579, 587))
                        ),
                    }
                ],
            },
            {
                "title": "📘 Tajvid. Pdf",
                "sections": [
                    {
                        "title": "📚 Tajvid qo'llanmalari",
                        "items": _document_items(
                            messages, list(range(560, 569))
                        ),
                    }
                ],
            },
            {
                "title": "📙 Qur'oni Karim. Pdf",
                "sections": [
                    {
                        "title": "📚 Qur'oni Karim nusxalari",
                        "items": _document_items(
                            messages,
                            [587, 589, 590] + list(range(592, 603)),
                        ),
                    }
                ],
            },
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_dir", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "lesson_menu.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload(args.export_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lesson_count = sum(
        len(item["contents"])
        for parent in payload["parents"]
        for section in parent["sections"]
        for item in section["items"]
    )
    print(f"Wrote {lesson_count} content records to {args.output}")


if __name__ == "__main__":
    main()
