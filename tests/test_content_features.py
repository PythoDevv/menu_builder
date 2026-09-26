import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from db.models import MenuItem
from keyboards.user_kb import COLUMNS_ONE, COLUMNS_TWO, menu_kb
from utils.content import extract_content, send_content


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


class MenuButtonStyleTest(unittest.TestCase):
    def test_menu_button_uses_saved_style(self) -> None:
        item = MenuItem(title="Yashil tugma", position=1)
        item.button_style = "success"

        keyboard = menu_kb([item], is_root=True, columns=COLUMNS_ONE)

        button = keyboard.keyboard[0][0]
        self.assertEqual(button.model_dump(exclude_none=True)["style"], "success")

    def test_menu_button_omits_default_style(self) -> None:
        item = MenuItem(title="Oddiy tugma", position=1)
        item.button_style = None

        keyboard = menu_kb([item], is_root=True, columns=COLUMNS_ONE)

        button = keyboard.keyboard[0][0]
        self.assertNotIn("style", button.model_dump(exclude_none=True))


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
