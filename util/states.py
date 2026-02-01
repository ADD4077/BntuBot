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


class InputUserID(StatesGroup):
    InputByUserID = State()
    InputByGroupNumber = State()


class InputGroupNumber(StatesGroup):
    userInput = State()


class InputFaculty(StatesGroup):
    InputByNumbers = State()
    InputByLetters = State()


class InputMessageForUser(StatesGroup):
    user_id = State()
    message = State()


class InputMessageForGroup(StatesGroup):
    group_id = State()
    message = State()


class InputStudsovetReport(StatesGroup):
    category = State()


class InputEventData(StatesGroup):
    event_type = State()
    name = State()
    date = State()
    description = State()
    contacts = State()
    members = State()
    image = State()


class EditEventData(StatesGroup):
    edit = State()
