"""Polling navbatidagi yaroqsiz bitta update butun botni to'xtatmasligi uchun himoya."""

import logging
from typing import Any

from pydantic import ValidationError

from aiogram.client.bot import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import ClientDecodeError
from aiogram.methods import GetUpdates, Response, TelegramMethod
from aiogram.types import Update

logger = logging.getLogger(__name__)


class FaultTolerantSession(AiohttpSession):
    """Yangi, hali aiogram tanimaydigan update'ni o'tkazib yuboradi.

    Telegram ba'zan Bot API ga yangi maydon yoki blok qo'shadi. Aiogram butun
    ``getUpdates`` javobini biryo'la tekshiradi: bitta noma'lum update xato bersa,
    offset siljimaydi va bot aynan o'sha update'ni qayta-qayta oladi. Bu session
    faqat shunday update'ni bo'sh placeholder bilan almashtiradi. Dispatcher uni
    tasdiqlab navbatdan oladi, qolgan haqiqiy update'lar esa odatdagidek ishlaydi.
    """

    def check_response(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        status_code: int,
        content: str,
    ) -> Response[Any]:
        try:
            return super().check_response(bot, method, status_code, content)
        except ClientDecodeError as exc:
            # Faqat muvaffaqiyatli getUpdates javobidagi modelga sig'magan bitta
            # update uchun fallback ishlaydi. API/network xatolari odatdagidek
            # aiogram tomonidan qayta uriniladi.
            if not isinstance(method, GetUpdates) or not isinstance(exc.data, dict):
                raise
            raw_updates = exc.data.get("result")
            if exc.data.get("ok") is not True or not isinstance(raw_updates, list):
                raise

            updates: list[Update] = []
            skipped_ids: list[int] = []
            for raw_update in raw_updates:
                try:
                    updates.append(Update.model_validate(raw_update, context={"bot": bot}))
                except ValidationError:
                    update_id = (
                        raw_update.get("update_id") if isinstance(raw_update, dict) else None
                    )
                    # Update ID bilinmasa uni tasdiqlab tashlash xavfsiz emas.
                    if not isinstance(update_id, int):
                        raise exc
                    skipped_ids.append(update_id)
                    # Bo'sh Update dispatcher tomonidan event sifatida ishlanmaydi,
                    # ammo uning update_id si offsetni siljitib, zaharli xabarni
                    # Telegram navbatidan olib tashlaydi.
                    updates.append(Update.model_validate({"update_id": update_id}))

            if not skipped_ids:
                raise

            logger.error(
                "Aiogram taniydigan formatda bo'lmagan update(lar) o'tkazib yuborildi: %s. "
                "Bot ishlashda davom etadi; rich post kerak bo'lsa aiogramni yangilang.",
                ", ".join(map(str, skipped_ids)),
            )
            response_type = Response[method.__returning__]  # type: ignore[index]
            return response_type(ok=True, result=updates)
