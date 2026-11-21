import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Chat, Message, MessageOriginChannel, PhotoSize, User

import utils.private_link as private_link
from handlers.admin.private_link import extract_post
from keyboards.admin_kb import (
    BTN_PL_BUTTON_RESET,
    BTN_PL_NOTIFY_RESET,
    BTN_PL_POST_RESET,
    private_link_kb,
)
from utils.channels import parse_chat_target
from utils.private_link import (
    BTN_JOIN,
    grant_if_earned,
    join_kb,
    notify_referrer,
    render_notify_text,
    render_post,
)

LINK = "https://t.me/+personal"
TEMPLATE = (
    "🎉 {name} qo'shildi\n"
    "🏆 Jami: <b>{count}</b> ta\n"
    "🔐 Yana <b>{left}</b> ta (kerak: {need})"
)


def _settings(**overrides) -> dict:
    data = {
        "enabled": True,
        "chat_id": -1001,
        "chat_title": "Yopiq",
        "need": 3,
        "post": None,
    }
    data.update(overrides)
    return data


def _bot() -> SimpleNamespace:
    return SimpleNamespace(
        create_chat_invite_link=AsyncMock(return_value=SimpleNamespace(invite_link=LINK)),
        revoke_chat_invite_link=AsyncMock(),
        send_message=AsyncMock(),
    )


def _message(**fields) -> Message:
    return Message(
        message_id=1,
        date=0,
        chat=Chat(id=10, type="private"),
        from_user=User(id=10, is_bot=False, first_name="Admin"),
        **fields,
    )


class RenderTest(unittest.TestCase):
    def test_goal_lines_are_kept_while_the_goal_is_active(self) -> None:
        text = render_notify_text(TEMPLATE, name="Ali", count=1, need=3, has_goal=True)
        self.assertIn("Jami: <b>1</b>", text)
        self.assertIn("Yana <b>2</b> ta (kerak: 3)", text)

    def test_goal_lines_are_dropped_without_a_goal(self) -> None:
        text = render_notify_text(TEMPLATE, name="Ali", count=5, need=3, has_goal=False)
        self.assertIn("Jami: <b>5</b>", text)
        self.assertNotIn("Yana", text)

    def test_new_user_name_is_escaped(self) -> None:
        text = render_notify_text("{name}", name="<b>x</b>", count=1, need=0, has_goal=False)
        self.assertEqual(text, "&lt;b&gt;x&lt;/b&gt;")

    def test_empty_name_gets_a_fallback(self) -> None:
        text = render_notify_text("{name}", name="", count=1, need=0, has_goal=False)
        self.assertEqual(text, private_link.UNKNOWN_NAME)

    def test_post_placeholders(self) -> None:
        post = {"type": "photo", "file_id": "F", "text_html": "{count}/{need}: {link}"}
        rendered = render_post(post, link=LINK, count=3, need=3)
        self.assertEqual(rendered["text_html"], f"3/3: {LINK}")
        self.assertEqual(rendered["file_id"], "F")
        self.assertEqual(post["text_html"], "{count}/{need}: {link}")  # asl o'zgarmaydi


class GrantTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        private_link._last_alert = 0.0

    def _patch(self, grant=None):
        return (
            patch("utils.private_link.get_private_link_grant", AsyncMock(return_value=grant)),
            patch("utils.private_link.add_private_link_grant", AsyncMock()),
        )

    async def test_disabled_section_does_nothing(self) -> None:
        bot = _bot()
        result = await grant_if_earned(bot, 7, count=10, settings=_settings(enabled=False))
        self.assertFalse(result)
        bot.create_chat_invite_link.assert_not_awaited()

    async def test_not_enough_referrals(self) -> None:
        bot = _bot()
        get_grant, add_grant = self._patch()
        with get_grant as get_mock, add_grant:
            result = await grant_if_earned(bot, 7, count=2, settings=_settings())
        self.assertFalse(result)
        get_mock.assert_not_awaited()
        bot.create_chat_invite_link.assert_not_awaited()

    async def test_creates_one_time_link_sends_post_and_records(self) -> None:
        bot = _bot()
        get_grant, add_grant = self._patch()
        with get_grant, add_grant as add_mock:
            result = await grant_if_earned(bot, 7, count=3, settings=_settings())

        self.assertTrue(result)
        bot.create_chat_invite_link.assert_awaited_once()
        args, kwargs = bot.create_chat_invite_link.await_args
        self.assertEqual(args[0], -1001)
        self.assertEqual(kwargs["member_limit"], 1)

        bot.send_message.assert_awaited_once()
        sent_args, sent_kwargs = bot.send_message.await_args
        self.assertEqual(sent_args[0], 7)
        self.assertIn(LINK, sent_args[1])
        button = sent_kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual((button.text, button.url), (BTN_JOIN, LINK))
        add_mock.assert_awaited_once_with(7, -1001, LINK)

    async def test_admin_button_text_and_icon_are_used(self) -> None:
        bot = _bot()
        get_grant, add_grant = self._patch()
        settings = _settings(button_text="VIP ga kirish", button_icon="555")
        with get_grant, add_grant:
            await grant_if_earned(bot, 7, count=3, settings=settings)
        button = bot.send_message.await_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(
            (button.text, button.url, button.icon_custom_emoji_id),
            ("VIP ga kirish", LINK, "555"),
        )

    async def test_already_granted_user_gets_nothing_new(self) -> None:
        bot = _bot()
        get_grant, add_grant = self._patch(grant=SimpleNamespace(invite_link=LINK))
        with get_grant, add_grant as add_mock:
            result = await grant_if_earned(bot, 7, count=9, settings=_settings())
        self.assertFalse(result)
        bot.create_chat_invite_link.assert_not_awaited()
        add_mock.assert_not_awaited()

    async def test_undelivered_link_is_revoked_and_not_recorded(self) -> None:
        bot = _bot()
        bot.send_message.side_effect = TelegramForbiddenError(Mock(), "blocked")
        get_grant, add_grant = self._patch()
        with get_grant, add_grant as add_mock:
            result = await grant_if_earned(bot, 7, count=3, settings=_settings())
        self.assertFalse(result)
        bot.revoke_chat_invite_link.assert_awaited_once_with(-1001, LINK)
        add_mock.assert_not_awaited()

    async def test_missing_rights_alerts_admins_once(self) -> None:
        bot = _bot()
        bot.create_chat_invite_link.side_effect = TelegramBadRequest(Mock(), "no rights")
        get_grant, add_grant = self._patch()
        with get_grant, add_grant, patch("utils.private_link.admin_ids", return_value={1}):
            await grant_if_earned(bot, 7, count=3, settings=_settings())
            await grant_if_earned(bot, 8, count=3, settings=_settings())
        self.assertEqual(bot.send_message.await_count, 1)
        self.assertEqual(bot.send_message.await_args.args[0], 1)


class NotifyReferrerTest(unittest.IsolatedAsyncioTestCase):
    async def _run(self, count: int, settings: dict, grant=None):
        bot = _bot()
        with (
            patch("utils.private_link.get_referral_count", AsyncMock(return_value=count)),
            patch("utils.private_link.get_private_link_settings", AsyncMock(return_value=settings)),
            patch("utils.private_link.get_private_link_grant", AsyncMock(return_value=grant)),
            patch("utils.private_link.get_ref_notify_text", AsyncMock(return_value=TEMPLATE)),
            patch("utils.private_link.grant_if_earned", AsyncMock()) as grant_mock,
        ):
            await notify_referrer(bot, 7, "Ali")
        return bot, grant_mock

    async def test_progress_is_shown_before_the_goal(self) -> None:
        bot, grant_mock = await self._run(1, _settings())
        text = bot.send_message.await_args.args[1]
        self.assertIn("Jami: <b>1</b>", text)
        self.assertIn("Yana <b>2</b>", text)
        grant_mock.assert_awaited_once()

    async def test_goal_line_disappears_when_reached(self) -> None:
        bot, grant_mock = await self._run(3, _settings())
        text = bot.send_message.await_args.args[1]
        self.assertIn("Jami: <b>3</b>", text)
        self.assertNotIn("Yana", text)
        self.assertEqual(grant_mock.await_args.kwargs["count"], 3)

    async def test_no_goal_line_when_section_is_off(self) -> None:
        bot, _ = await self._run(1, _settings(enabled=False))
        self.assertNotIn("Yana", bot.send_message.await_args.args[1])

    async def test_no_goal_line_after_the_link_was_given(self) -> None:
        bot, _ = await self._run(1, _settings(), grant=SimpleNamespace(invite_link=LINK))
        self.assertNotIn("Yana", bot.send_message.await_args.args[1])


class AdminHelpersTest(unittest.TestCase):
    def test_text_post(self) -> None:
        post = extract_post(_message(text="Havola: {link}"))
        self.assertEqual(post, {"type": "text", "file_id": None, "text_html": "Havola: {link}"})

    def test_photo_post_uses_the_largest_size_and_caption(self) -> None:
        sizes = [
            PhotoSize(file_id=f"p{i}", file_unique_id=f"u{i}", width=i, height=i)
            for i in (1, 2)
        ]
        post = extract_post(_message(photo=sizes, caption="{link}"))
        self.assertEqual(post, {"type": "photo", "file_id": "p2", "text_html": "{link}"})

    def test_channel_target_from_forward_and_text(self) -> None:
        forwarded = _message(
            text="post",
            forward_origin=MessageOriginChannel(
                date=0, chat=Chat(id=-1009, type="channel"), message_id=5
            ),
        )
        self.assertEqual(parse_chat_target(forwarded), -1009)
        self.assertEqual(parse_chat_target(_message(text="-100123")), -100123)
        self.assertEqual(parse_chat_target(_message(text="https://t.me/kanal")), "@kanal")
        self.assertIsNone(parse_chat_target(_message(text="salom")))

    def test_reset_buttons_only_for_custom_texts(self) -> None:
        resets = {BTN_PL_POST_RESET, BTN_PL_BUTTON_RESET, BTN_PL_NOTIFY_RESET}

        def texts(kb):
            return {button.text for row in kb.keyboard for button in row}

        self.assertFalse(resets & texts(private_link_kb(True, False, False, False)))
        full = private_link_kb(True, True, True, True)
        self.assertTrue(resets <= texts(full))
        self.assertTrue(all(len(row) <= 2 for row in full.keyboard))

    def test_join_button_falls_back_to_default(self) -> None:
        button = join_kb(LINK).inline_keyboard[0][0]
        self.assertEqual((button.text, button.icon_custom_emoji_id), (BTN_JOIN, None))
        # admin matni yo'q bo'lsa eski ikonka ham ishlatilmaydi
        button = join_kb(LINK, None, "555").inline_keyboard[0][0]
        self.assertEqual((button.text, button.icon_custom_emoji_id), (BTN_JOIN, None))


if __name__ == "__main__":
    unittest.main()
