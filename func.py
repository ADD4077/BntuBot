from datetime import datetime, timedelta

from aiogram.fsm.state import State, StatesGroup
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardMarkup

from typing import Union

import bs4
import requests

import json

with open("./literature_per_faculty.json", "r") as jsonfile:
    literature_per_faculty = json.load(jsonfile)

requests.packages.urllib3.disable_warnings()


def get_week_and_day(today: Union[None, datetime] = None) -> tuple[int, str]:
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

class AutoAuth(StatesGroup):
    student_code = State()
    code = State()

async def auth_send(bot, message):
    b_auth = types.InlineKeyboardButton(
        text="🔐 Авторизоваться",
        callback_data="auto_auth"
    )
    b_privacy = types.InlineKeyboardButton(
        text="Политика конфиденциальности",
        url="https://telegra.ph/Politika-konfidencialnosti-09-08-51"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[b_auth], [b_privacy]])
    await bot.send_message(
        message.from_user.id,
        f'Привет, @{message.from_user.username}!, чтобы использовать бота, нужно авторизоваться c помощью студенческого билета. Для этого нажмите кнопку "Авторизация".',
        reply_markup=markup
    )


async def authorize(login: str, password: str) -> Union[bool, tuple[str, str]]:
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


def next_element(element):
    return element.next_sibling.next_sibling


def parse_literature() -> None:
    for faculty, endpoint in literature_per_faculty.items():
        literature = {}
        response = requests.get(endpoint)
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        collections = soup.find_all("h4", class_="artifact-title")
        for collection in collections:
            children = collection.find_all(recursive=False)
            link_element = children[0]
            if link_element.find_all("span", recursive=False):
                link = "https://rep.bntu.by" + link_element["href"] + \
                       "/browse?rpp=9999&sort_by=1&type=title"
                collection_title = \
                    link_element.find_all(recursive=False)[0].text
                literature[collection_title] = {}
                literature_count = children[1].text
                literature[collection_title]["count"] = literature_count
                literature[collection_title]["items"] = []
                response = requests.get(link)
                soup = bs4.BeautifulSoup(response.content, "html.parser")
                rows = soup.find_all("div", class_="item-wrapper")
                for row in rows:
                    literature[collection_title]["items"].append({})
                    title = \
                        row.find("h4", class_="artifact-title").find("a").text
                    literature[collection_title]["items"][-1]["title"] = title
                    image_element = row.find(
                        "img",
                        class_=["img-responsive", "img-thumbnail"]
                    )
                    if image_element.get("src"):
                        image_link = \
                            "https://rep.bntu.by" + image_element["src"]
                    else:
                        image_link = None
                    literature[collection_title]["items"][-1]["image_url"] = \
                        image_link
                    authors = \
                        row.find(
                            "span", class_="author"
                        ).small.find_all("span")
                    literature[collection_title]["items"][-1]["authors"] = []
                    for author in authors:
                        literature[collection_title]["items"][-1]["authors"] \
                            .append(author.text)
                    publishing_date = row.find("span", class_="date").text
                    literature[collection_title]["items"][-1]["publishing_date"] = \
                        publishing_date
                    description = \
                        row.find("div", class_="artifact-abstract").text
                    literature[collection_title]["items"][-1]["description"] = \
                        description

        with open(
            f"./books/literature_{faculty}.json",
            "w", encoding="utf8"
        ) as jsonfile:
            json.dump(literature, jsonfile, indent=4, ensure_ascii=False)
