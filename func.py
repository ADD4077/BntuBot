from datetime import datetime, timedelta

from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardMarkup

from typing import Union

import bs4
import requests


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


def authorize(login: str, password: str) -> Union[bool, tuple[str, str]]:
    """
    Checks if user is student or not
    If student return fullname and faculty
    Otherwise return False
    """
    session = requests.Session()
    response = session.get("https://bntu.by/user/login", verify=False)
    cookies = response.cookies
    soup = bs4.BeautifulSoup(response.content, "html.parser")
    token = soup.form.find("input", attrs={"name": "_token"})["value"]

    headers = {
        "cookie": f"XSRF-TOKEN={cookies['XSRF-TOKEN']};\
                    laravel_session={cookies['laravel_session']}"
    }

    data = {
        "_token": token,
        "username": login,
        "password": password
    }

    response = session.post(
        "https://bntu.by/user/auth",
        headers=headers, data=data, verify=False
    )
    soup = bs4.BeautifulSoup(response.content, "html.parser")
    if "pay" in response.url:
        fullname = soup.find(
            "h1",
            class_="newsName"
        ).next_sibling.next_sibling.text.split(",")[1][1:-22]
        info_div = soup.find("div", class_="dashboardInfo")
        for line in info_div.contents:
            if "курс" in line:
                _, _, faculty, _ = line.split(",")
                break
        faculty = faculty.replace(" ", "")
        return fullname, faculty
    return False
