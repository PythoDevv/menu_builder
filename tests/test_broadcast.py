import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.admin.broadcast import _send_one, got_message


class BroadcastInlineKeyboardTest(unittest.IsolatedAsyncioTestCase):
    async def test_received_post_saves_its_inline_keyboard(self) -> None:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Kirish", url="https://example.com")]
            ]
        )
        state = SimpleNamespace(
            update_data=AsyncMock(),
            set_state=AsyncMock(),
        )
        message = SimpleNamespace(
            chat=SimpleNamespace(id=123),
            message_id=456,
            reply_markup=markup,
            answer=AsyncMock(),
        )

        with patch("handlers.admin.broadcast.get_active_user_ids", new=AsyncMock(return_value=[])):
            await got_message(message, state)

        saved = state.update_data.await_args.kwargs
        self.assertEqual(saved["from_chat_id"], 123)
        self.assertEqual(saved["message_id"], 456)
        self.assertEqual(
            saved["reply_markup"], markup.model_dump(mode="json", exclude_none=True)
        )

    async def test_copy_uses_the_saved_inline_keyboard(self) -> None:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Kirish", url="https://example.com")]
            ]
        )
        bot = SimpleNamespace(copy_message=AsyncMock())

        result = await _send_one(bot, 10, 20, 30, markup)

        self.assertEqual(result, "sent")
        bot.copy_message.assert_awaited_once_with(
            10, 20, 30, reply_markup=markup
        )
