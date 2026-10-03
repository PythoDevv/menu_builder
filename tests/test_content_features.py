import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.types import Chat, Message, MessageEntity, User

from db.models import MenuItem
from keyboards.admin_kb import button_style_kb
from keyboards.user_kb import COLUMNS_ONE, COLUMNS_TWO, menu_kb
from utils.content import (
    FORMATTED_TEXT_PREFIX,
    extract_button_text_and_icon,
    extract_content,
    send_content,
)
from utils.referral import render_my_points_text


class PremiumStickerTest(unittest.TestCase):
    def test_extract_content_keeps_sticker_file_id(self) -> None:
        message = SimpleNamespace(
            caption=None,
            photo=None,
            video=None,
            animation=None,
            document=None,
            audio=None,
            voice=None,
            video_note=None,
            sticker=SimpleNamespace(file_id="premium-sticker-file-id"),
            text=None,
        )

        self.assertEqual(
            extract_content(message),
            {
                "type": "sticker",
                "file_id": "premium-sticker-file-id",
                "text_html": None,
            },
        )


class PremiumStickerSendingTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_content_resends_sticker_by_file_id(self) -> None:
        bot = SimpleNamespace(send_sticker=AsyncMock())
        content = SimpleNamespace(
            type="sticker",
            file_id="premium-sticker-file-id",
            text_html=None,
        )

        await send_content(bot, chat_id=123, content=content)

        bot.send_sticker.assert_awaited_once_with(
            123,
            "premium-sticker-file-id",
            reply_markup=None,
        )


class CustomEmojiContentTest(unittest.IsolatedAsyncioTestCase):
    def _message(self) -> Message:
        return Message(
            message_id=1,
            date=0,
            chat=Chat(id=123, type="private"),
            from_user=User(id=321, is_bot=False, first_name="Admin"),
            text="✅ Barcha savollar",
            entities=[
                MessageEntity(
                    type="custom_emoji",
                    offset=0,
                    length=1,
                    custom_emoji_id="content-premium-emoji-id",
                )
            ],
        )

    async def test_custom_emoji_content_is_saved_with_entity_id(self) -> None:
        data = extract_content(self._message())

        self.assertIsNotNone(data)
        self.assertTrue(data["text_html"].startswith(FORMATTED_TEXT_PREFIX))
        self.assertIn("content-premium-emoji-id", data["text_html"])

    async def test_custom_emoji_content_is_sent_as_telegram_entity(self) -> None:
        data = extract_content(self._message())
        bot = SimpleNamespace(send_message=AsyncMock())
        content = SimpleNamespace(
            type="text",
            file_id=None,
            text_html=data["text_html"],
        )

        await send_content(bot, chat_id=123, content=content)

        call = bot.send_message.await_args
        self.assertEqual(call.args[:2], (123, "✅ Barcha savollar"))
        self.assertIsNone(call.kwargs["parse_mode"])
        self.assertEqual(
            call.kwargs["entities"][0].custom_emoji_id,
            "content-premium-emoji-id",
        )


class MenuButtonStyleTest(unittest.TestCase):
    def test_admin_color_picker_previews_supported_colors(self) -> None:
        keyboard = button_style_kb()
        styles = [
            button.model_dump(exclude_none=True).get("style")
            for button in keyboard.keyboard[1]
        ]

        self.assertEqual(styles, ["primary", "success", "danger"])

    def test_menu_button_uses_saved_style(self) -> None:
        item = MenuItem(title="Yashil tugma", position=1)
        item.button_style = "success"

        keyboard = menu_kb([item], is_root=True, columns=COLUMNS_ONE)

        button = keyboard.keyboard[0][0]
        self.assertEqual(button.model_dump(exclude_none=True)["style"], "success")

    def test_menu_button_uses_saved_custom_emoji_icon(self) -> None:
        item = MenuItem(title="Barcha savollar", position=1)
        item.button_style = "success"
        item.icon_custom_emoji_id = "menu-premium-emoji-id"

        keyboard = menu_kb([item], is_root=True, columns=COLUMNS_ONE)

        button = keyboard.keyboard[0][0]
        self.assertEqual(button.text, "Barcha savollar")
        self.assertEqual(
            button.model_dump(exclude_none=True)["icon_custom_emoji_id"],
            "menu-premium-emoji-id",
        )

    def test_menu_button_omits_default_style(self) -> None:
        item = MenuItem(title="Oddiy tugma", position=1)
        item.button_style = None

        keyboard = menu_kb([item], is_root=True, columns=COLUMNS_ONE)

        button = keyboard.keyboard[0][0]
        self.assertNotIn("style", button.model_dump(exclude_none=True))

    def test_my_points_button_can_be_hidden(self) -> None:
        keyboard = menu_kb(
            [],
            is_root=True,
            columns=COLUMNS_ONE,
            my_points_enabled=False,
        )

        self.assertEqual(keyboard.__class__.__name__, "ReplyKeyboardRemove")

    def test_my_points_button_uses_custom_text_and_style(self) -> None:
        keyboard = menu_kb(
            [],
            is_root=True,
            columns=COLUMNS_ONE,
            my_points_text="⭐ Mening natijam",
            my_points_style="primary",
        )

        button = keyboard.keyboard[0][0]
        self.assertEqual(button.text, "⭐ Mening natijam")
        self.assertEqual(button.model_dump(exclude_none=True)["style"], "primary")

    def test_my_points_button_uses_custom_emoji_icon(self) -> None:
        keyboard = menu_kb(
            [],
            is_root=True,
            my_points_text="Ballarim",
            my_points_icon_custom_emoji_id="premium-emoji-id",
        )

        button = keyboard.keyboard[0][0]
        self.assertEqual(
            button.model_dump(exclude_none=True)["icon_custom_emoji_id"],
            "premium-emoji-id",
        )

    def test_custom_emoji_is_extracted_from_button_label(self) -> None:
        message = SimpleNamespace(
            text="🏆 Ballarim",
            entities=[
                MessageEntity(
                    type="custom_emoji",
                    offset=0,
                    length=2,
                    custom_emoji_id="premium-emoji-id",
                )
            ],
        )

        self.assertEqual(
            extract_button_text_and_icon(message),
            ("Ballarim", "premium-emoji-id"),
        )

    def test_my_points_template_replaces_count_and_link(self) -> None:
        rendered = render_my_points_text(
            "Ball: <b>{count}</b>\n{link}",
            count=7,
            link="https://t.me/example?start=ref1",
        )

        self.assertEqual(
            rendered,
            "Ball: <b>7</b>\nhttps://t.me/example?start=ref1",
        )


class MenuLayoutTest(unittest.TestCase):
    def test_two_columns_pair_long_titles(self) -> None:
        items = [
            MenuItem(title="Birinchi uzun menyu tugmasi", position=1),
            MenuItem(title="Ikkinchi uzun menyu tugmasi", position=2),
        ]

        keyboard = menu_kb(items, is_root=True, columns=COLUMNS_TWO)

        self.assertEqual(
            [button.text for button in keyboard.keyboard[0]],
            [item.title for item in items],
        )


if __name__ == "__main__":
    unittest.main()
