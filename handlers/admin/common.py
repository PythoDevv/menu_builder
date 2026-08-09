"""Admin panel uchun umumiy narsalar: filtr, router va ro'yxat mosligi.

Reply tugmada callback_data yo'q, shuning uchun ro'yxat chiqarilganda
"tugma matni -> id" mosligi FSM ma'lumotiga yoziladi va tugma bosilganda
o'sha yerdan o'qiladi.
"""

from typing import Optional

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from keyboards.admin_kb import admin_home_kb
from handlers.admin.states import PanelSG
from utils.admins import is_admin

HOME_TEXT = "👑 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:"
PICK_TEXT = "❗️ Pastdagi tugmalardan birini tanlang."

#: "Xabarni kutamiz" turidagi holatlar komandalarni ushlab qolmasligi kerak
NOT_COMMAND = ~Command("start", "admin")

#: FSM kalitlari
KEY_LABELS = "labels"  # tugma matni -> id
KEY_NODE = "node"  # admin menyuda turgan tugma
KEY_ITEM = "item"  # ochilgan kanal / admin / menyu tugmasi id si


class IsAdmin(BaseFilter):
    """Ro'yxat xotirada (utils.admins), shuning uchun bazaga murojaat yo'q."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and is_admin(user.id)


def admin_router() -> Router:
    """Faqat adminlar uchun router."""
    router = Router()
    router.message.filter(IsAdmin())
    return router


async def show_home(message: Message, state: FSMContext, text: str = HOME_TEXT) -> None:
    await state.set_data({})
    await state.set_state(PanelSG.home)
    await message.answer(text, reply_markup=admin_home_kb())


async def save_labels(state: FSMContext, labels: dict[str, int]) -> None:
    await state.update_data({KEY_LABELS: labels})


async def pick_label(state: FSMContext, text: Optional[str]) -> Optional[int]:
    data = await state.get_data()
    return (data.get(KEY_LABELS) or {}).get(text or "")
