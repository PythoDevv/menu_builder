import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from config import ADMINS, BOT_TOKEN
from db.base import close_db, init_db
from handlers import join_request, menu, start
from handlers.admin import broadcast, channels, export, menu_items, panel
from handlers.admin import settings as admin_settings
from middlewares.sub_mw import PhoneMiddleware, SubscriptionMiddleware
from middlewares.user_mw import UserMiddleware
from utils.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [BotCommand(command="start", description="Boshlash")],
        scope=BotCommandScopeDefault(),
    )
    for admin_id in ADMINS:
        try:
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Boshlash"),
                    BotCommand(command="admin", description="Admin panel"),
                ],
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except TelegramAPIError:
            logger.warning("Admin %s uchun komandalar o'rnatilmadi", admin_id)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    if not BOT_TOKEN:
        raise SystemExit("❌ .env faylida BOT_TOKEN yo'q")
    if not ADMINS:
        logger.warning("⚠️ ADMINS bo'sh — admin panelga hech kim kira olmaydi")

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # middlewarelar
    dp.update.outer_middleware(UserMiddleware())
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(SubscriptionMiddleware())
        observer.outer_middleware(PhoneMiddleware())

    # routerlar: avval admin, keyin oddiy foydalanuvchi
    dp.include_routers(
        panel.router,
        channels.router,
        menu_items.router,
        admin_settings.router,
        broadcast.router,
        export.router,
        join_request.router,
        start.router,
        menu.router,
    )

    await init_db()
    await start_scheduler()
    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logger.info("🚀 Bot ishga tushdi: @%s", me.username)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        stop_scheduler()
        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
