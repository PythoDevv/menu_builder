#!/usr/bin/env python3
"""Build lesson_menu.json from the Telegram HTML export and media folder."""

import argparse
import html
import json
import re
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
            result.append(lesson(number, topic, ALIJON_EXTRA_FILES[number]))

    return sorted(result, key=lambda item: item["number"])


def build_jahongir_lessons(export_dir: Path) -> List[Dict[str, Any]]:
    files_by_number = {}
    for file_path in (export_dir / "video_files").glob("Tajvid_fani_*.mp4"):
        match = re.match(r"Tajvid_fani_(\d+)_", file_path.name, re.I)
        if match:
            files_by_number[int(match.group(1))] = file_path

    missing = sorted(set(JAHONGIR_TOPICS) - set(files_by_number))
    if missing:
        raise ValueError(f"Jahongir qori video files are missing: {missing}")

    return [
        lesson(
            number,
            JAHONGIR_TOPICS[number],
            str(files_by_number[number].relative_to(export_dir)),
        )
        for number in sorted(JAHONGIR_TOPICS)
    ]


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


def build_payload(export_dir: Path) -> Dict[str, Any]:
    messages = parse_html_messages(export_dir / "messages.html")
    muallimi = build_muallimi_lessons(messages)
    alijon = build_alijon_lessons(messages)
    jahongir = build_jahongir_lessons(export_dir)

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
    print(f"Wrote {lesson_count} lessons to {args.output}")


if __name__ == "__main__":
    main()
