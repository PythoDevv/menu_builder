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
SUPER_ADMIN_COMMANDS = ADMIN_COMMANDS + [
    BotCommand(command="superadmin", description="Superadmin panel")
]


async def set_default_commands(bot: Bot) -> None:
    await bot.set_my_commands(USER_COMMANDS, scope=BotCommandScopeDefault())


async def set_admin_commands(bot: Bot, tg_id: int, *, super_admin: bool = False) -> None:
    """Adminga komandalarni ko'rsatadi; /superadmin faqat `.env` adminiga."""
    try:
        commands = SUPER_ADMIN_COMMANDS if super_admin else ADMIN_COMMANDS
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=tg_id))
    except TelegramAPIError:
        # foydalanuvchi botni ochmagan bo'lsa xato beradi — muhim emas
        logger.warning("Admin %s uchun komandalar o'rnatilmadi", tg_id)


async def reset_commands(bot: Bot, tg_id: int) -> None:
    """Adminlikdan chiqarilganda shaxsiy komandalarni olib tashlaydi."""
    try:
        await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=tg_id))
    except TelegramAPIError:
        logger.warning("Admin %s uchun komandalar tozalanmadi", tg_id)
