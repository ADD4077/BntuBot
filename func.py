from aiogram.utils.keyboard import InlineKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram import types

from datetime import datetime, timedelta

from typing import Union
import aiosqlite
import requests
import json
import bs4
import re

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


class AnonChatState(StatesGroup):
    in_chat = State()


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
                _, _, faculty, *_ = line.split(",")
                break
        faculty = faculty.replace(" ", "")
        return fullname, faculty
    return False


def next_element(element):
    return element.next_sibling.next_sibling


def parse_literature() -> None:
    """
    Parses literature and saves it in ./books/ directory
    """
    literature = {}
    for faculty, endpoint in literature_per_faculty.items():
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
                    a_element = row.find("h4", class_="artifact-title").find("a")
                    title = a_element.text
                    literature_link = "https://rep.bntu.by" + a_element["href"]
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
                            .append(author.text.replace(",", ""))
                    publishing_date = row.find("span", class_="date").text
                    literature[collection_title]["items"][-1]["publishing_date"] = \
                        publishing_date
                    description = \
                        row.find("div", class_="artifact-abstract").text
                    literature[collection_title]["items"][-1]["description"] = \
                        description
                    response = requests.get(literature_link)
                    soup = bs4.BeautifulSoup(response.content, "html.parser")
                    i_element = soup.find("i", class_="glyphicon-file")
                    literature[collection_title]["items"][-1]["download"] = {}
                    if i_element:
                        a_element = i_element.find_parent("a")
                        size = a_element.text.split(" (")[1].replace(")", "")
                        filetype = a_element.text.split(" (")[0].lstrip()
                        download_link = "https://rep.bntu.by" + a_element["href"]
                    else:
                        size = "0"
                        filetype = "N/A"
                        download_link = "Not found"
                    literature[collection_title]["items"][-1]["download"]["size"] = size
                    literature[collection_title]["items"][-1]["download"]["type"] = filetype
                    literature[collection_title]["items"][-1]["download"]["download_link"] = download_link

    with open(
        "./books/literature.json",
        "w", encoding="utf8"
    ) as jsonfile:
        json.dump(literature, jsonfile, indent=4, ensure_ascii=False)
    return None

replacements = {
    'Практ': 'Практ.',
    'Лекц': 'Лекц.',
    'Лаб': 'Лаб.'
}

pattern = re.compile(r'\(\s*(Практ|Лекц|Лаб)[^)]*\)', re.IGNORECASE)


def parse_schedule() -> None:
    """
    Parses schedules and saves it into ./schedules/ directory
    """
    faculties = [
        "atf",  "fgde", "msf",  "mtf",
        "fmmp", "ef",   "fitr", "ftug",
        "ipf",  "fes",  "af",   "sf",
        "psf",  "ftk",  "vtf",  "stf"
    ]

    for faculty in faculties:
        endpoint = f"https://bntu.by/raspisanie/{faculty}"
        response = requests.get(endpoint, verify=False)
        soup = bs4.BeautifulSoup(response.content, "html.parser")
        courses = soup.find_all("input", class_="course-checkbox")
        groups = []
        group_div = soup.find("div", attrs={"id": "group"})

        for i in range(len(courses)):
            select = group_div.find("select", attrs={"name": f"group{i+1}"})
            for child in select.find_all(recursive=False):
                if child["value"] != "Номер:":
                    groups.append(child["value"])

        for group in groups:
            headers = {"cookie": f"group={group};"}
            response = requests.get(
                endpoint+"/table",
                headers=headers,
                verify=False
            )
            soup = bs4.BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table", class_="sheduleTable")
            schedule_data = {}
            schedule_data["Schedule"] = []
            for week in range(2):
                table = tables[week]
                schedule_data["Schedule"].append({})
                if table:
                    if table.find("tbody"):
                        rows = table.find("tbody").find_all("tr")
                    else:
                        rows = table.find_all("tr")

                    for row in rows:
                        day_element = row.find("td", class_="newDay")

                        if day_element:
                            day = day_element.text.replace("\n", "")\
                                                  .replace(" ", "")
                            schedule_data["Schedule"][week][day] = []

                        time_element = row.find("td", class_="time")

                        if not time_element:
                            continue

                        time = time_element.text

                        matter_element = next_element(time_element)
                        matter = matter_element.text

                        teacher_element = next_element(matter_element)
                        teacher = teacher_element.text

                        frame_element = next_element(teacher_element)
                        frame = frame_element.text

                        classroom_element = next_element(frame_element)
                        classroom = classroom_element.text

                        if time:
                            schedule_data["Schedule"][week][day].append(
                                {
                                    "Time": time,
                                    "Matter": pattern.sub(
                                        lambda match:
                                            f"({replacements[match.group(1).capitalize()]})",
                                        matter
                                    ),
                                    "Teacher": re.sub(
                                        r'\s+',
                                        ' ', teacher
                                    ).lstrip().rstrip(),
                                    "Frame": frame,
                                    "Classroom": classroom
                                }
                            )
            with open(
                f"./schedules/schedule_{group}.json", "w", encoding="utf8"
            ) as jsonfile:
                json.dump(
                    schedule_data,
                    jsonfile,
                    indent=4,
                    ensure_ascii=False
                )
    return None


async def send_message(
        bot, chat_id: int,
        message: types.message.Message,
        anon_chat_id: int
):
    replying = message.reply_to_message
    if replying:
        reply_message_id = replying.message_id
        async with aiosqlite.connect("server.db") as db:
            async with db.cursor() as cursor:
                if replying.from_user.id != message.from_user.id:
                    id_for_reply = (await (await cursor.execute(
                        """SELECT user_message_id FROM messages
                        WHERE chat_id = ?
                        AND
                        bot_message_id = ?""",
                        (anon_chat_id, reply_message_id)
                    )).fetchone())[0]
                else:
                    id_for_reply = (await (await cursor.execute(
                        """SELECT bot_message_id FROM messages
                        WHERE chat_id = ?
                        AND
                        user_message_id = ?""",
                        (anon_chat_id, reply_message_id)
                    )).fetchone())[0]
    text = message.text
    photos = message.photo
    videos = message.video
    files = message.document
    sticker = message.sticker
    voice = message.voice
    circle = message.video_note
    builder = MediaGroupBuilder(caption=text)
    if photos:
        builder.add_photo(media=photos[-1].file_id)
    if videos:
        builder.add_video(media=videos.file_id)
    if files:
        builder.add_document(media=files.file_id)
    if photos or videos or files:
        if replying:
            return (await bot.send_media_group(
                chat_id,
                media=builder.build(),
                reply_to_message_id=id_for_reply
            ))[0]
        return (await bot.send_media_group(
            chat_id,
            media=builder.build()
        ))[0]
    if sticker:
        if replying:
            return await bot.send_sticker(
                chat_id,
                sticker=sticker.file_id,
                reply_to_message_id=id_for_reply
            )
        return await bot.send_sticker(
            chat_id,
            sticker=sticker.file_id
        )
    if voice:
        if replying:
            return await bot.send_voice(
                chat_id,
                voice=voice.file_id,
                reply_to_message_id=id_for_reply
            )
        return await bot.send_voice(
            chat_id,
            voice=voice.file_id
        )
    if circle:
        if replying:
            return await bot.send_video_note(
                chat_id,
                video_note=circle.file_id,
                reply_to_message_id=id_for_reply
            )
        return await bot.send_video_note(
            chat_id,
            video_note=circle.file_id
        )
    if text:
        if replying:
            return await bot.send_message(
                chat_id,
                text,
                reply_to_message_id=id_for_reply
            )
        return await bot.send_message(chat_id, text)
