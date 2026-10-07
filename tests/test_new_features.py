import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aiogram.types import Chat, Message, Update, User
from sqlalchemy.dialects import postgresql

from db.models import Channel, MenuItem, User as DBUser
from db.queries import get_winners_limit, reset_referral_points, set_winners_limit
from handlers.admin.winners import render_winners_report
from keyboards.user_kb import menu_kb
from middlewares.sub_mw import SubscriptionMiddleware
from utils.commands import ADMIN_COMMANDS, set_admin_commands
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
    async def test_superadmin_command_is_hidden_even_for_superadmin(self) -> None:
        self.assertNotIn("superadmin", [item.command for item in ADMIN_COMMANDS])

        bot = SimpleNamespace(set_my_commands=AsyncMock())
        await set_admin_commands(bot, 123, super_admin=True)
        commands = bot.set_my_commands.await_args.args[0]
        self.assertNotIn("superadmin", [item.command for item in commands])


class WinnersReportTest(unittest.TestCase):
    def test_report_contains_every_requested_user_field_in_one_message(self) -> None:
        user = DBUser(
            tg_id=123456789,
            full_name="Ali & Vali",
            username="ali_user",
        )

        report = render_winners_report([(user, 27)])

        self.assertIn("Ali &amp; Vali", report)
        self.assertIn("@ali_user", report)
        self.assertIn("123456789", report)
        self.assertIn("27", report)
        self.assertLessEqual(len(report), 4096)


class WinnersLimitTest(unittest.IsolatedAsyncioTestCase):
    async def test_limit_is_clamped_for_old_or_invalid_database_values(self) -> None:
        with patch("db.queries.get_setting", AsyncMock(return_value="999")):
            self.assertEqual(await get_winners_limit(), 20)

    async def test_admin_limit_is_saved_in_settings(self) -> None:
        with patch("db.queries.set_setting", AsyncMock()) as save:
            await set_winners_limit(7)
        save.assert_awaited_once_with("winners_limit", "7")


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
