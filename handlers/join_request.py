"""Yopiq kanalga tashlangan qo'shilish so'rovini ushlab qolamiz."""

import logging

from aiogram import Router
from aiogram.types import ChatJoinRequest

from db.queries import add_join_request, get_channel_by_chat_id
from utils.subscription import clear_cache

router = Router()
logger = logging.getLogger(__name__)


@router.chat_join_request()
async def on_join_request(event: ChatJoinRequest) -> None:
    channel = await get_channel_by_chat_id(event.chat.id)
    if channel is None:
        return
    await add_join_request(event.from_user.id, channel.id)
    clear_cache(event.from_user.id)
    logger.info("Zayafka: %s -> %s", event.from_user.id, channel.title)
