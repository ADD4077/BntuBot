from datetime import datetime, timedelta

from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardMarkup

from typing import Union


def get_week_and_day(today: Union[None, datetime] = None) -> (int, str):
    """
    Returns number of week and name of the day as tuple
    If today variable isnt provided uses datetime.now().date()
    """
    if not today:
        today = datetime.now().date()
    elif isinstance(today, datetime):
        today = today.date()
    start_date = datetime(today.year, 9, 1).date()
    if today < start_date:
        start_date = datetime(today.year - 1, 9, 1).date()
    delta_days = (today - start_date).days
    day_of_week_index = delta_days % 7
    week_number = (delta_days // 7) % 2
    days = [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье"
    ]
    day_name = days[day_of_week_index]
    return week_number, day_name


# Better way to do this will be to add tomorrow argument to get_week_and_day
# Subject to discuss
def get_tomorrow_week_and_day(today=None):
    if today is None:
        today = datetime.now().date()
    else:
        if isinstance(today, datetime):
            today = today.date()
    tomorrow = today + timedelta(days=1)
    return get_week_and_day(tomorrow)


class Form(StatesGroup):
    photo = State()


class AcceptAuthForm(StatesGroup):
    id = State()
    text = State()


async def auth_send(bot, message):
    b_auth = types.InlineKeyboardButton(
        text="Авторизоваться",
        callback_data="auth"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[b_auth]])
    await bot.send_message(
        message.from_user.id,
        f'Привет, @{message.from_user.username}!, чтобы использовать бота, нужно авторизоваться c помощью студенческого билета. Для этого нажмите кнопку "Авторизация".',
        reply_markup=markup
    )
