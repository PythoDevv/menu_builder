import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.types import Chat, Message, MessageEntity, User

from db.models import Channel, MenuItem
from keyboards.admin_kb import button_style_kb, row_size_ask_kb, row_size_kb
from keyboards.user_kb import menu_kb, subscribe_kb
from utils.content import (
    FORMATTED_TEXT_PREFIX,
    extract_button_text_and_icon,
    extract_content,
    send_content,
)
from utils.referral import render_my_points_text
from utils.rating import rating_limits, render_rating_text


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

        keyboard = menu_kb([item], is_root=True)

        button = keyboard.keyboard[0][0]
        self.assertEqual(button.model_dump(exclude_none=True)["style"], "success")

    def test_menu_button_uses_saved_custom_emoji_icon(self) -> None:
        item = MenuItem(title="Barcha savollar", position=1)
        item.button_style = "success"
        item.icon_custom_emoji_id = "menu-premium-emoji-id"

        keyboard = menu_kb([item], is_root=True)

        button = keyboard.keyboard[0][0]
        self.assertEqual(button.text, "Barcha savollar")
        self.assertEqual(
            button.model_dump(exclude_none=True)["icon_custom_emoji_id"],
            "menu-premium-emoji-id",
        )

    def test_menu_button_omits_default_style(self) -> None:
        item = MenuItem(title="Oddiy tugma", position=1)
        item.button_style = None

        keyboard = menu_kb([item], is_root=True)

        button = keyboard.keyboard[0][0]
        self.assertNotIn("style", button.model_dump(exclude_none=True))

    def test_my_points_button_can_be_hidden(self) -> None:
        keyboard = menu_kb(
            [],
            is_root=True,
            my_points_enabled=False,
        )

        self.assertEqual(keyboard.__class__.__name__, "ReplyKeyboardRemove")

    def test_my_points_button_uses_custom_text_and_style(self) -> None:
        keyboard = menu_kb(
            [],
            is_root=True,
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

    def test_rating_button_uses_custom_style_icon_and_two_column_row(self) -> None:
        keyboard = menu_kb(
            [],
            is_root=True,
            my_points_text="Ballarim",
            rating_enabled=True,
            rating_text="Reyting",
            rating_style="success",
            rating_icon_custom_emoji_id="rating-premium-emoji-id",
            rating_row_size=2,
        )

        self.assertEqual(
            [[button.text for button in row] for row in keyboard.keyboard],
            [["Ballarim", "Reyting"]],
        )
        rating_button = keyboard.keyboard[0][1]
        self.assertEqual(rating_button.model_dump(exclude_none=True)["style"], "success")
        self.assertEqual(
            rating_button.model_dump(exclude_none=True)["icon_custom_emoji_id"],
            "rating-premium-emoji-id",
        )

    def test_rating_three_column_layout_can_fill_with_adjacent_menu_button(self) -> None:
        item = MenuItem(title="Oldingi", position=1)
        item.row_size = 3

        keyboard = menu_kb(
            [item],
            is_root=True,
            my_points_text="Ballarim",
            rating_enabled=True,
            rating_text="Reyting",
            rating_row_size=3,
        )

        self.assertEqual(
            [[button.text for button in row] for row in keyboard.keyboard],
            [["Oldingi", "Ballarim", "Reyting"]],
        )


class RatingTemplateTest(unittest.TestCase):
    def test_users_keyword_renders_requested_top_and_normalizes_blank_lines(self) -> None:
        users = [
            (SimpleNamespace(full_name="Ali & Vali", username=None, tg_id=1), 12),
            (SimpleNamespace(full_name="Zarina", username=None, tg_id=2), 8),
            (SimpleNamespace(full_name="Kamol", username=None, tg_id=3), 4),
        ]

        rendered = render_rating_text(
            "Tepa\n\n\n{users-2}\nPast",
            users,
        )

        self.assertEqual(
            rendered,
            "Tepa\n\n1. Ali &amp; Vali — <b>12</b> ta\n"
            "2. Zarina — <b>8</b> ta\n\nPast",
        )

    def test_users_keyword_limits_are_safe(self) -> None:
        self.assertEqual(rating_limits("{users-0} / {users-999}"), [1, 50])


class MenuLayoutTest(unittest.TestCase):
    @staticmethod
    def _item(title: str, row_size: int) -> MenuItem:
        item = MenuItem(title=title, position=1)
        item.row_size = row_size
        return item

    def test_existing_default_items_each_use_full_row(self) -> None:
        items = [
            self._item("Birinchi", 1),
            self._item("Ikkinchi", 1),
        ]

        keyboard = menu_kb(items, is_root=True, my_points_enabled=False)

        self.assertEqual(
            [[button.text for button in row] for row in keyboard.keyboard],
            [["Birinchi"], ["Ikkinchi"]],
        )

    def test_consecutive_two_size_items_share_a_row(self) -> None:
        items = [self._item("Birinchi", 2), self._item("Ikkinchi", 2)]

        keyboard = menu_kb(items, is_root=True, my_points_enabled=False)

        self.assertEqual(
            [[button.text for button in row] for row in keyboard.keyboard],
            [["Birinchi", "Ikkinchi"]],
        )

    def test_new_item_picker_only_offers_one_or_two(self) -> None:
        keyboard = row_size_ask_kb()

        self.assertEqual(len(keyboard.keyboard[0]), 2)
        self.assertEqual(
            [button.text[:1] for button in keyboard.keyboard[0]],
            ["1", "2"],
        )

    def test_edit_picker_offers_one_through_four(self) -> None:
        keyboard = row_size_kb()

        choices = [
            button.text[:1] for row in keyboard.keyboard[:2] for button in row
        ]
        self.assertEqual(choices, ["1", "2", "3", "4"])

    def test_different_sizes_start_new_rows(self) -> None:
        items = [
            self._item("Ikki-1", 2),
            self._item("Uch-1", 3),
            self._item("Uch-2", 3),
            self._item("Uch-3", 3),
            self._item("To'rt-1", 4),
            self._item("To'rt-2", 4),
            self._item("To'rt-3", 4),
            self._item("To'rt-4", 4),
        ]

        keyboard = menu_kb(items, is_root=True, my_points_enabled=False)

        self.assertEqual(
            [[button.text for button in row] for row in keyboard.keyboard],
            [
                ["Ikki-1"],
                ["Uch-1", "Uch-2", "Uch-3"],
                ["To'rt-1", "To'rt-2", "To'rt-3", "To'rt-4"],
            ],
        )


class SubscriptionButtonTest(unittest.TestCase):
    def test_channel_button_uses_saved_custom_emoji_icon(self) -> None:
        channel = Channel(
            title="Premium kanal",
            username="premium_channel",
            is_private=False,
        )
        channel.icon_custom_emoji_id = "channel-premium-emoji-id"

        keyboard = subscribe_kb([channel])
        button = keyboard.inline_keyboard[0][0]

        self.assertEqual(button.text, "Premium kanal")
        self.assertEqual(
            button.model_dump(exclude_none=True)["icon_custom_emoji_id"],
            "channel-premium-emoji-id",
        )

    def test_check_button_uses_custom_text_and_premium_icon(self) -> None:
        keyboard = subscribe_kb(
            [],
            check_text="Obunani tekshirish",
            check_icon_custom_emoji_id="check-premium-emoji-id",
        )
        button = keyboard.inline_keyboard[-1][0]

        self.assertEqual(button.text, "Obunani tekshirish")
        self.assertEqual(
            button.model_dump(exclude_none=True)["icon_custom_emoji_id"],
            "check-premium-emoji-id",
        )


if __name__ == "__main__":
    unittest.main()
