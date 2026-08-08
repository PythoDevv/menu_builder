from aiogram.fsm.state import State, StatesGroup


class ChannelSG(StatesGroup):
    waiting_chat = State()
    waiting_type = State()


class MenuSG(StatesGroup):
    waiting_title = State()
    waiting_rename = State()
    waiting_content = State()


class StartSG(StatesGroup):
    waiting_message = State()


class BroadcastSG(StatesGroup):
    waiting_message = State()
