import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
)
from aiogram.methods import SendMessage
from aiogram.types import CallbackQuery, Chat, ChatJoinRequest, Message, Update, User

from handlers.admin.broadcast import _send_one
from middlewares.user_mw import UserMiddleware
from utils.user_status import BLOCKED, DEACTIVATED, NOT_STARTED, inactive_reason

METHOD = SendMessage(chat_id=1, text="x")
USER = User(id=42, is_bot=False, first_name="Ali")


def forbidden(text: str) -> TelegramForbiddenError:
    return TelegramForbiddenError(method=METHOD, message=f"Forbidden: {text}")


class InactiveReasonTest(unittest.TestCase):
    def test_telegram_403_texts_are_told_apart(self) -> None:
        self.assertEqual(inactive_reason(forbidden("bot was blocked by the user")), BLOCKED)
        self.assertEqual(inactive_reason(forbidden("user is deactivated")), DEACTIVATED)
        self.assertEqual(
            inactive_reason(forbidden("bot can't initiate conversation with a user")),
            NOT_STARTED,
        )
        self.assertEqual(
            inactive_reason(
                TelegramBadRequest(method=METHOD, message="Bad Request: chat not found")
            ),
            NOT_STARTED,
        )

    def test_other_errors_do_not_change_user(self) -> None:
        self.assertIsNone(
            inactive_reason(TelegramBadRequest(method=METHOD, message="message is too long"))
        )
        self.assertIsNone(inactive_reason(TelegramNetworkError(method=METHOD, message="x")))


class BroadcastClassifyTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_one_returns_the_reason(self) -> None:
        bot = SimpleNamespace(
            copy_message=AsyncMock(
                side_effect=forbidden("bot can't initiate conversation with a user")
            )
        )
        self.assertEqual(await _send_one(bot, 1, 2, 3), NOT_STARTED)


class UserMiddlewareTest(unittest.IsolatedAsyncioTestCase):
    async def _run(self, update: Update) -> AsyncMock:
        handler = AsyncMock()
        with patch(
            "middlewares.user_mw.get_or_create_user",
            new=AsyncMock(return_value=(SimpleNamespace(phone=None), None)),
        ) as create:
            await UserMiddleware()(handler, update, {"event_from_user": USER})
        handler.assert_awaited_once()
        return create

    async def test_join_request_does_not_create_user(self) -> None:
        update = Update(
            update_id=1,
            chat_join_request=ChatJoinRequest(
                chat=Chat(id=-100, type="channel"),
                from_user=USER,
                user_chat_id=42,
                date=0,
            ),
        )
        (await self._run(update)).assert_not_awaited()

    async def test_private_start_creates_user(self) -> None:
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=0,
                chat=Chat(id=42, type="private"),
                from_user=USER,
                text="/start",
            ),
        )
        (await self._run(update)).assert_awaited_once()

    async def test_group_message_does_not_create_user(self) -> None:
        update = Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=0,
                chat=Chat(id=-5, type="supergroup"),
                from_user=USER,
                text="salom",
            ),
        )
        (await self._run(update)).assert_not_awaited()

    async def test_private_callback_creates_user(self) -> None:
        update = Update(
            update_id=1,
            callback_query=CallbackQuery(
                id="1",
                from_user=USER,
                chat_instance="c",
                data="x",
                message=Message(message_id=1, date=0, chat=Chat(id=42, type="private")),
            ),
        )
        (await self._run(update)).assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
