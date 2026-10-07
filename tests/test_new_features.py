import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aiogram.types import Chat, Message, Update, User
from sqlalchemy.dialects import postgresql

from db.models import Channel, MenuItem
from db.queries import reset_referral_points
from keyboards.user_kb import menu_kb
from middlewares.sub_mw import SubscriptionMiddleware
from utils.commands import ADMIN_COMMANDS, SUPER_ADMIN_COMMANDS, set_admin_commands
from utils.maintenance import MaintenanceMiddleware, is_maintenance_active, maintenance_mode


class DefaultTwoColumnTest(unittest.TestCase):
    def test_items_without_a_saved_size_default_to_two_columns(self) -> None:
        first = MenuItem(title="Birinchi", position=1)
        second = MenuItem(title="Ikkinchi", position=2)

        keyboard = menu_kb(
            [first, second],
            is_root=True,
            my_points_enabled=False,
            rating_enabled=False,
        )

        self.assertEqual(
            [[button.text for button in row] for row in keyboard.keyboard],
            [["Birinchi", "Ikkinchi"]],
        )


class StartSubscriptionGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_always_shows_all_active_channels_before_menu(self) -> None:
        event = Message(
            message_id=1,
            date=0,
            chat=Chat(id=100, type="private"),
            from_user=User(id=200, is_bot=False, first_name="User"),
            text="/start ref123",
        )
        private = Channel(
            id=1,
            chat_id=-1001,
            title="Yopiq kanal",
            invite_link="https://t.me/+invite",
            is_private=True,
            is_active=True,
        )
        handler = AsyncMock()
        bot = SimpleNamespace()

        with (
            patch("middlewares.sub_mw.get_channels", AsyncMock(return_value=[private])),
            patch("middlewares.sub_mw.clear_cache", Mock()) as clear_cache,
            patch("middlewares.sub_mw.send_sub_prompt", AsyncMock()) as prompt,
            patch("middlewares.sub_mw.check_subscription", AsyncMock()) as check,
        ):
            await SubscriptionMiddleware()(handler, event, {"bot": bot})

        clear_cache.assert_called_once_with(200)
        prompt.assert_awaited_once_with(bot, 100, [private])
        check.assert_not_awaited()
        handler.assert_not_awaited()


class SuperAdminCommandsTest(unittest.IsolatedAsyncioTestCase):
    async def test_regular_admin_does_not_get_superadmin_command(self) -> None:
        self.assertNotIn("superadmin", [item.command for item in ADMIN_COMMANDS])
        self.assertIn("superadmin", [item.command for item in SUPER_ADMIN_COMMANDS])

        bot = SimpleNamespace(set_my_commands=AsyncMock())
        await set_admin_commands(bot, 123, super_admin=False)
        commands = bot.set_my_commands.await_args.args[0]
        self.assertNotIn("superadmin", [item.command for item in commands])


class MaintenanceModeTest(unittest.IsolatedAsyncioTestCase):
    async def test_updates_are_blocked_while_database_is_being_restored(self) -> None:
        middleware = MaintenanceMiddleware()
        handler = AsyncMock(return_value="handled")
        update = Update(update_id=1)

        async with maintenance_mode():
            self.assertTrue(is_maintenance_active())
            result = await middleware(handler, update, {})

        self.assertIsNone(result)
        handler.assert_not_awaited()
        self.assertFalse(is_maintenance_active())


class _ResetSession:
    def __init__(self) -> None:
        self.statement = None
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    async def execute(self, statement):
        self.statement = statement
        return SimpleNamespace(rowcount=7)

    async def commit(self) -> None:
        self.committed = True


class ResetPointsQueryTest(unittest.IsolatedAsyncioTestCase):
    async def test_only_referral_links_are_cleared(self) -> None:
        session = _ResetSession()
        with patch("db.queries.session_maker", return_value=session):
            changed = await reset_referral_points()

        sql = str(
            session.statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.assertEqual(changed, 7)
        self.assertTrue(session.committed)
        self.assertIn("UPDATE users SET referred_by=NULL", sql)
        self.assertIn("users.referred_by IS NOT NULL", sql)


if __name__ == "__main__":
    unittest.main()
