import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from db.base import close_db, init_db
from handlers import fallback, join_request, menu, start
from handlers.admin import admins, broadcast, channels, export, menu_items, panel
from handlers.admin import settings as admin_settings
from middlewares.sub_mw import PhoneMiddleware, SubscriptionMiddleware
from middlewares.user_mw import UserMiddleware
from utils.admins import admin_ids, refresh_admins
from utils.commands import set_admin_commands, set_default_commands
from utils.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    await set_default_commands(bot)
    for admin_id in admin_ids():
        await set_admin_commands(bot, admin_id)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    if not BOT_TOKEN:
        raise SystemExit("❌ .env faylida BOT_TOKEN yo'q")

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # middlewarelar. Obuna ekrani inline bo'lgani uchun callback ham tekshiriladi.
    dp.update.outer_middleware(UserMiddleware())
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(SubscriptionMiddleware())
        observer.outer_middleware(PhoneMiddleware())

    # routerlar: avval admin panel, keyin oddiy foydalanuvchi.
    # panel.router — barcha ekranda ishlaydigan tugmalar (/admin, 🏠, ❌, 🚪),
    # panel.fallback_router — admin holatidagi tanilmagan xabar (eng oxirida).
    dp.include_routers(
        panel.router,
        admins.router,
        channels.router,
        menu_items.router,
        admin_settings.router,
        broadcast.router,
        export.router,
        panel.fallback_router,
        join_request.router,
        start.router,
        menu.router,
        fallback.router,
    )

    await init_db()
    if not await refresh_admins():
        logger.warning("⚠️ Admin yo'q — .env dagi ADMINS ni to'ldiring")
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
