"""Polling navbatidagi yaroqsiz bitta update butun botni to'xtatmasligi uchun himoya."""

import logging
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from aiogram.client.bot import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import ClientDecodeError
from aiogram.methods import GetUpdates, Response, TelegramMethod
from aiogram.types import Update

from utils.content import RICH_MESSAGE_COPY_MARKER

logger = logging.getLogger(__name__)


class FaultTolerantSession(AiohttpSession):
    """Yangi, hali aiogram tanimaydigan update'ni o'tkazib yuboradi.

    Telegram ba'zan Bot API ga yangi maydon yoki blok qo'shadi. Aiogram butun
    ``getUpdates`` javobini biryo'la tekshiradi: bitta noma'lum update xato bersa,
    offset siljimaydi va bot aynan o'sha update'ni qayta-qayta oladi. Rich
    postning yangi bloki bilinmasa, session uning rich qismini modeldan olib tashlab,
    xabarni arxivga ``copyMessage`` qilish belgisi bilan handlerga uzatadi. Boshqa
    yaroqsiz update bo'sh placeholder bilan tasdiqlanadi. Shu tariqa dispatcher
    navbatni siljitadi, qolgan haqiqiy update'lar odatdagidek ishlaydi.
    """

    @staticmethod
    def _without_unparsed_rich_message(raw_update: Any) -> dict[str, Any] | None:
        """Noma'lum rich blokni olib, xabarni copy qilish markerini qo'yadi."""
        if not isinstance(raw_update, dict):
            return None
        raw_message = raw_update.get("message")
        if not isinstance(raw_message, dict) or "rich_message" not in raw_message:
            return None
        safe_update = deepcopy(raw_update)
        safe_message = safe_update["message"]
        safe_message.pop("rich_message", None)
        safe_message[RICH_MESSAGE_COPY_MARKER] = True
        return safe_update

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
            rich_copy_ids: list[int] = []
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

                    # Rich postning hali qo'llanmaydigan ichki bloki bo'lsa, butun
                    # xabarni yo'qotmaymiz: Telegramning o'zi keyin uni arxivga
                    # nusxalaydi. Rich qismni Python faqat o'qimaydi, xolos.
                    safe_update = self._without_unparsed_rich_message(raw_update)
                    if safe_update is not None:
                        try:
                            updates.append(
                                Update.model_validate(safe_update, context={"bot": bot})
                            )
                        except ValidationError:
                            pass
                        else:
                            rich_copy_ids.append(update_id)
                            continue

                    skipped_ids.append(update_id)
                    # Bo'sh Update dispatcher tomonidan event sifatida ishlanmaydi,
                    # ammo uning update_id si offsetni siljitib, zaharli xabarni
                    # Telegram navbatidan olib tashlaydi.
                    updates.append(Update.model_validate({"update_id": update_id}))

            if not skipped_ids and not rich_copy_ids:
                raise

            if rich_copy_ids:
                logger.warning(
                    "Aiogram tanimagan rich blokli update(lar) arxivga nusxalash uchun "
                    "qabul qilindi: %s.",
                    ", ".join(map(str, rich_copy_ids)),
                )
            if skipped_ids:
                logger.error(
                    "Aiogram taniydigan formatda bo'lmagan update(lar) o'tkazib yuborildi: %s. "
                    "Bot ishlashda davom etadi.",
                    ", ".join(map(str, skipped_ids)),
                )
            response_type = Response[method.__returning__]  # type: ignore[index]
            return response_type(ok=True, result=updates)
