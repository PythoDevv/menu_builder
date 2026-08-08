"""Har bir update'da foydalanuvchini bazaga yozib/yangilab boradi."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from db.queries import get_or_create_user


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if tg_user and not tg_user.is_bot:
            data["db_user"] = await get_or_create_user(
                tg_user.id, tg_user.full_name, tg_user.username
            )
        return await handler(event, data)
