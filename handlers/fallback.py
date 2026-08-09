"""Botda inline tugma qolmadi — eski xabardagi tugma bosilsa shu ishlaydi."""

from aiogram import Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query()
async def stale_button(callback: CallbackQuery) -> None:
    await callback.answer(
        "♻️ Bot yangilandi — tugmalar endi pastda chiqadi.\n/start bosing.",
        show_alert=True,
    )
