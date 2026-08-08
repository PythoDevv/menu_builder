"""Bot menyusidagi komandalar. Adminda qo'shimcha /admin ko'rinadi."""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

logger = logging.getLogger(__name__)

USER_COMMANDS = [BotCommand(command="start", description="Boshlash")]
ADMIN_COMMANDS = USER_COMMANDS + [
    BotCommand(command="admin", description="Admin panel")
]


async def set_default_commands(bot: Bot) -> None:
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())


async def set_admin_commands(bot: Bot, tg_id: int) -> None:
    """Adminga /admin komandasini ko'rsatadi."""
    try:
        await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=tg_id))
    except TelegramAPIError:
        # foydalanuvchi botni ochmagan bo'lsa xato beradi — muhim emas
        logger.warning("Admin %s uchun komandalar o'rnatilmadi", tg_id)


async def reset_commands(bot: Bot, tg_id: int) -> None:
    """Adminlikdan chiqarilganda shaxsiy komandalarni olib tashlaydi."""
    try:
        await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=tg_id))
    except TelegramAPIError:
        logger.warning("Admin %s uchun komandalar tozalanmadi", tg_id)
