import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, MessageEntity, PhotoSize, Sticker, User

import handlers.menu as menu
import utils.referral as referral
from db.queries import (
    CONTEST_BOTTOM,
    DEFAULT_CONTEST_JOIN_TEXT,
    DEFAULT_CONTEST_TEXT,
    K_CONTEST_JOIN_STYLE,
    K_CONTEST_POSITION,
    K_CONTEST_POST_FILE,
    K_CONTEST_POST_TEXT,
    K_CONTEST_POST_TYPE,
    K_CONTEST_STYLE,
    parse_contest_settings,
)
from keyboards.admin_kb import BTN_CT_BOTTOM, BTN_CT_JOIN_RESET, BTN_CT_TOP, contest_settings_kb
from keyboards.user_kb import menu_kb
from db.models import MenuItem
from utils.contest import extract_contest_post, join_kb, render_post
from utils.texts import DEFAULT_CONTEST_POST_TEXT


def _message(**fields) -> Message:
    return Message(
        message_id=1,
        date=0,
        chat=Chat(id=10, type="private"),
        from_user=User(id=10, is_bot=False, first_name="Admin"),
        **fields,
    )


def _texts(keyboard) -> list[list[str]]:
    return [[button.text for button in row] for row in keyboard.keyboard]


class ContestSettingsTest(unittest.TestCase):
    def test_defaults_visible_green_and_on_top(self) -> None:
        settings = parse_contest_settings({})
        self.assertTrue(settings["enabled"])
        self.assertEqual(settings["text"], DEFAULT_CONTEST_TEXT)
        self.assertEqual(settings["style"], "success")
        self.assertEqual(settings["position"], "top")
        self.assertIsNone(settings["post"])
        self.assertIsNone(settings["join_text"])
        self.assertEqual(settings["join_style"], "success")

    def test_plain_style_is_kept_apart_from_missing_value(self) -> None:
        settings = parse_contest_settings({K_CONTEST_STYLE: "", K_CONTEST_JOIN_STYLE: ""})
        self.assertIsNone(settings["style"])
        self.assertIsNone(settings["join_style"])

    def test_saved_post_and_position(self) -> None:
        settings = parse_contest_settings(
            {
                K_CONTEST_POSITION: CONTEST_BOTTOM,
                K_CONTEST_POST_TYPE: "photo",
                K_CONTEST_POST_FILE: "file-1",
                K_CONTEST_POST_TEXT: "Rasm {link}",
            }
        )
        self.assertEqual(settings["position"], "bottom")
        self.assertEqual(
            settings["post"], {"type": "photo", "file_id": "file-1", "text_html": "Rasm {link}"}
        )

    def test_unknown_position_falls_back_to_top(self) -> None:
        self.assertEqual(parse_contest_settings({K_CONTEST_POSITION: "x"})["position"], "top")


class ContestMenuTest(unittest.TestCase):
    def _kb(self, position: str):
        items = [MenuItem(title="A", position=1), MenuItem(title="B", position=2)]
        return menu_kb(
            items,
            is_root=True,
            my_points_text="🏆 Ballarim",
            rating_enabled=False,
            contest_enabled=True,
            contest_text="✅ Konkursda qatnashish",
            contest_style="success",
            contest_position=position,
        )

    def test_contest_button_is_full_width_row_on_top_by_default(self) -> None:
        keyboard = self._kb("top")
        self.assertEqual(
            _texts(keyboard),
            [["✅ Konkursda qatnashish"], ["A", "B"], ["🏆 Ballarim"]],
        )
        self.assertEqual(keyboard.keyboard[0][0].style, "success")

    def test_contest_button_can_be_moved_to_the_bottom(self) -> None:
        self.assertEqual(
            _texts(self._kb("bottom")),
            [["A", "B"], ["🏆 Ballarim"], ["✅ Konkursda qatnashish"]],
        )

    def test_hidden_by_default_in_keyboard_helper(self) -> None:
        keyboard = menu_kb([MenuItem(title="A", position=1)], is_root=True)
        self.assertNotIn(DEFAULT_CONTEST_TEXT, sum(_texts(keyboard), []))


class ContestPostTest(unittest.TestCase):
    def test_render_puts_personal_link_and_escaped_name(self) -> None:
        post = render_post(
            {"type": "text", "file_id": None, "text_html": "{name}: {link}"},
            link="https://t.me/bot?start=ref42",
            name="<Ali>",
        )
        self.assertEqual(post["text_html"], "&lt;Ali&gt;: https://t.me/bot?start=ref42")

    def test_default_post_contains_link_placeholder(self) -> None:
        self.assertIn("{link}", DEFAULT_CONTEST_POST_TEXT)

    def test_premium_emoji_survives_as_html(self) -> None:
        message = _message(
            text="⭐ Qo'shiling {link}",
            entities=[
                MessageEntity(type="custom_emoji", offset=0, length=1, custom_emoji_id="555")
            ],
        )
        post = extract_contest_post(message)
        self.assertEqual(post["type"], "text")
        self.assertIn('<tg-emoji emoji-id="555">⭐</tg-emoji>', post["text_html"])
        self.assertIn("{link}", post["text_html"])

    def test_photo_caption_and_sticker_are_accepted(self) -> None:
        photo = _message(
            photo=[PhotoSize(file_id="small", file_unique_id="s", width=1, height=1),
                   PhotoSize(file_id="big", file_unique_id="b", width=9, height=9)],
            caption="Rasm {link}",
        )
        self.assertEqual(
            extract_contest_post(photo),
            {"type": "photo", "file_id": "big", "text_html": "Rasm {link}"},
        )
        sticker = _message(
            sticker=Sticker(
                file_id="st", file_unique_id="u", type="regular", width=1, height=1,
                is_animated=False, is_video=False,
            )
        )
        self.assertEqual(
            extract_contest_post(sticker),
            {"type": "sticker", "file_id": "st", "text_html": None},
        )

    def test_join_button_default_and_custom(self) -> None:
        default = join_kb("https://t.me/x", style="success").inline_keyboard[0][0]
        self.assertEqual(default.text, DEFAULT_CONTEST_JOIN_TEXT)
        self.assertEqual(default.style, "success")
        self.assertIsNone(default.icon_custom_emoji_id)

        custom = join_kb("https://t.me/x", "Kirish", "777", "danger").inline_keyboard[0][0]
        self.assertEqual(
            (custom.text, custom.url, custom.icon_custom_emoji_id, custom.style),
            ("Kirish", "https://t.me/x", "777", "danger"),
        )


class ContestAdminKbTest(unittest.TestCase):
    def test_position_toggle_offers_the_other_side(self) -> None:
        top = sum(_texts(contest_settings_kb(True, "top", False, False)), [])
        bottom = sum(_texts(contest_settings_kb(True, "bottom", False, True)), [])
        self.assertIn(BTN_CT_BOTTOM, top)
        self.assertNotIn(BTN_CT_JOIN_RESET, top)
        self.assertIn(BTN_CT_TOP, bottom)
        self.assertIn(BTN_CT_JOIN_RESET, bottom)


class ContestHandlerTest(unittest.IsolatedAsyncioTestCase):
    def _event(self) -> SimpleNamespace:
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        return SimpleNamespace(
            bot=bot,
            chat=SimpleNamespace(id=777),
            from_user=SimpleNamespace(id=777, full_name="Vali"),
        )

    async def test_post_carries_the_users_own_id_at_the_end_of_the_link(self) -> None:
        event = self._event()
        settings = parse_contest_settings({})
        with (
            patch.object(referral, "_username", "konkurs_bot"),
            patch.object(menu, "get_contest_settings", AsyncMock(return_value=settings)),
        ):
            await menu.contest(event)

        link = "https://t.me/konkurs_bot?start=ref777"
        call = event.bot.send_message.await_args
        self.assertEqual(call.args[0], 777)
        self.assertIn(link, call.args[1])
        button = call.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual((button.text, button.url), (DEFAULT_CONTEST_JOIN_TEXT, link))

    async def test_broken_custom_post_falls_back_to_default(self) -> None:
        event = self._event()
        event.bot.send_photo.side_effect = TelegramBadRequest(
            method=SendMessage(chat_id=1, text="x"), message="wrong file"
        )
        settings = parse_contest_settings(
            {K_CONTEST_POST_TYPE: "photo", K_CONTEST_POST_FILE: "old", K_CONTEST_POST_TEXT: "x"}
        )
        with (
            patch.object(referral, "_username", "konkurs_bot"),
            patch.object(menu, "get_contest_settings", AsyncMock(return_value=settings)),
        ):
            await menu.contest(event)

        self.assertIn("?start=ref777", event.bot.send_message.await_args.args[1])


if __name__ == "__main__":
    unittest.main()
