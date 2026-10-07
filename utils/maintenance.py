"""Database restore/reset vaqtida yangi update'larni DBdan uzoq tutadi."""

from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from utils.scheduler import scheduler

MAINTENANCE_TEXT = (
    "🛠 Hozir texnik xizmat ketmoqda. Iltimos, bir ozdan keyin qayta urinib ko'ring."
)
_active = False


def is_maintenance_active() -> bool:
    return _active


@asynccontextmanager
async def maintenance_mode():
    """Update va cron DB ishlarini vaqtincha to'xtatib turadi."""
    global _active
    _active = True
    scheduler_was_running = scheduler.running
    if scheduler_was_running:
        scheduler.pause()
    try:
        yield
    finally:
        try:
            if scheduler_was_running:
                scheduler.resume()
        finally:
            _active = False


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not _active:
            return await handler(event, data)

        if isinstance(event, Update):
            if event.callback_query:
                await event.callback_query.answer(MAINTENANCE_TEXT, show_alert=True)
            elif event.message:
                await event.message.answer(MAINTENANCE_TEXT)
        return None
