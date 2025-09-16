from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    photo = State()


class AcceptAuthForm(StatesGroup):
    id = State()
    text = State()


class AutoAuth(StatesGroup):
    student_code = State()
    code = State()


class AnonChatState(StatesGroup):
    in_chat = State()