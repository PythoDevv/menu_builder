"""Admin panel holatlari.

Reply tugmalarda callback_data yo'q — shuning uchun "hozir qaysi ekrandaman"
degan ma'lumot FSM holatida saqlanadi. Admin panelga /admin bilan kiriladi,
'🚪 Chiqish' bilan chiqiladi (holat tozalanadi -> oddiy foydalanuvchi rejimi).
"""

from aiogram.fsm.state import State, StatesGroup


class PanelSG(StatesGroup):
    home = State()


class AdminSG(StatesGroup):
    browse = State()
    one = State()
    confirm_delete = State()
    waiting_id = State()


class ChannelSG(StatesGroup):
    browse = State()
    one = State()
    confirm_delete = State()
    waiting_chat = State()
    waiting_type = State()


class MenuSG(StatesGroup):
    node = State()
    confirm_delete = State()
    contents = State()
    waiting_title = State()
    waiting_rename = State()
    waiting_content = State()
    # taklif sharti: yangi tugma qo'shishda so'raladi va keyin ham o'zgartiriladi
    ask_ref = State()
    waiting_ref_count = State()
    ref = State()
    waiting_ref_edit = State()


class RefTextSG(StatesGroup):
    """Taklif sharti bajarilmaganda chiqadigan matn."""

    show = State()
    confirm_reset = State()
    waiting_text = State()


class StartSG(StatesGroup):
    show = State()
    confirm_delete = State()
    waiting_message = State()


class SubSG(StatesGroup):
    show = State()
    confirm_reset = State()
    waiting_message = State()


class PhoneSG(StatesGroup):
    show = State()


class LayoutSG(StatesGroup):
    show = State()


class BroadcastSG(StatesGroup):
    waiting_message = State()
    confirm = State()


class ExcelSG(StatesGroup):
    show = State()


#: Admin panelning barcha holatlari — "🏠 Admin panel" / "❌ Bekor qilish" /
#: "🚪 Chiqish" tugmalari shu holatlarning hammasida ishlashi uchun kerak.
ALL_STATES = (
    *PanelSG.__all_states__,
    *AdminSG.__all_states__,
    *ChannelSG.__all_states__,
    *MenuSG.__all_states__,
    *StartSG.__all_states__,
    *SubSG.__all_states__,
    *RefTextSG.__all_states__,
    *PhoneSG.__all_states__,
    *LayoutSG.__all_states__,
    *BroadcastSG.__all_states__,
    *ExcelSG.__all_states__,
)
