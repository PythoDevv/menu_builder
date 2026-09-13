import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from scripts.build_lesson_menu_data import (
    ALIJON_EXTRA_FILES,
    JAHONGIR_TOPICS,
    build_alijon_lessons,
    build_jahongir_lessons,
    caption_html,
)
from utils.content import send_content


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LessonSourceTests(unittest.TestCase):
    def test_caption_html_is_safe_for_telegram(self) -> None:
        value = (
            '<a href="" onclick="bad()">#tag</a><br><strong>1-dars</strong> '
            '<a href="https://example.com">manba</a>'
        )

        self.assertEqual(
            '#tag\n<b>1-dars</b> <a href="https://example.com">manba</a>',
            caption_html(value),
        )

    def test_every_lesson_has_a_source_message_id(self) -> None:
        payload = json.loads(
            (PROJECT_ROOT / "data" / "lesson_menu.json").read_text(encoding="utf-8")
        )
        lessons = [
            content
            for parent in payload["parents"]
            for section in parent["sections"]
            for item in section["items"]
            for content in item["contents"]
        ]

        self.assertEqual(462, len(lessons))
        self.assertTrue(all(item.get("source_message_id") for item in lessons))
        self.assertEqual(401, sum(item["type"] == "video" for item in lessons))
        self.assertEqual(61, sum(item["type"] == "document" for item in lessons))
        self.assertEqual(462, len({item["source_message_id"] for item in lessons}))

    def test_extra_alijon_lessons_take_ids_from_html_messages(self) -> None:
        messages = [
            {"file": file_path, "message_id": 100 + number, "text": ""}
            for number, file_path in ALIJON_EXTRA_FILES.items()
        ]

        lessons = build_alijon_lessons(messages)

        self.assertEqual([126, 127, 128], [item["source_message_id"] for item in lessons])

    def test_jahongir_lessons_take_ids_from_html_messages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export_dir = Path(directory)
            video_dir = export_dir / "video_files"
            video_dir.mkdir()
            messages = []
            for number in JAHONGIR_TOPICS:
                file_path = f"video_files/Tajvid_fani_{number}_dars.mp4"
                (export_dir / file_path).touch()
                messages.append(
                    {"file": file_path, "message_id": 200 + number, "text": ""}
                )

            lessons = build_jahongir_lessons(export_dir, messages)

        self.assertEqual(31, len(lessons))
        self.assertEqual(
            list(range(201, 232)),
            [item["source_message_id"] for item in lessons],
        )


class SendContentTests(unittest.TestCase):
    def test_source_message_is_copied_without_uploading(self) -> None:
        bot = SimpleNamespace(copy_message=AsyncMock(), send_video=AsyncMock())
        content = SimpleNamespace(
            type="video",
            file_id=None,
            text_html="<b>1-dars</b>",
            source_chat_id=-1001234567890,
            source_message_id=105,
        )

        asyncio.run(send_content(bot, 998877, content, reply_markup="keyboard"))

        bot.copy_message.assert_awaited_once_with(
            chat_id=998877,
            from_chat_id=-1001234567890,
            message_id=105,
            caption="<b>1-dars</b>",
            reply_markup="keyboard",
        )
        bot.send_video.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
