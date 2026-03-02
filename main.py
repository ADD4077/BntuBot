import os
import sys
import pytz
import json
import time
import asyncio
import hashlib
import logging
import datetime
import aiosqlite
import multiprocessing

from dotenv import load_dotenv
from util import func
from util import states
from util import keyboards
from util import middleware
from util.config import server_db_path, base_dir
from util.states import AutoAuth, AcceptAuthForm, Form

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.base import JobLookupError

from redis.asyncio import Redis


from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher, types, flags, filters, F
from aiogram.types import Message

load_dotenv()


API_TOKEN = os.getenv("TOKEN")
redis_password = os.getenv("REDIS_PASSWORD")

main_menu_image = os.getenv("MAIN_IMAGE")
schedule_image = os.getenv("SCHEDULE_IMAGE")
support_image = os.getenv("SUPPORT_IMAGE")
profile_image = os.getenv("PROFILE_IMAGE")
example_photo = os.getenv("EXAMPLE_IMAGE")
map_photo = os.getenv("MAP_IMAGE")
mailing_photo = os.getenv("MAILING_IMAGE")
studsovet_photo = os.getenv("STUDSOVET_IMAGE")

user_owner = os.getenv("USER_OWNER")
id_owner = int(os.getenv("ID_OWNER"))
moderators_chat_id = int(os.getenv("MODERATORS_CHAT_ID"))
support_chat_id = int(os.getenv("SUPPORT_CHAT_ID"))
studsovet_chat_id = int(os.getenv("STUDSOVET_CHAT_ID"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(
    storage=RedisStorage(Redis(host="redis", port=6379, password=redis_password))
)
tz = pytz.timezone("Europe/Moscow")

os.environ["TZ"] = "Europe/Moscow"
time.tzset()

jobstores = {"default": RedisJobStore(host="redis", port=6379, password=redis_password)}
scheduler = AsyncIOScheduler(jobstores=jobstores)


os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler(
            base_dir
            / "logs"
            / f"{__name__}_{datetime.datetime.now(tz).strftime('%d-%m-%Y_%H-%M-%S')}.log",
            mode="w",
        ),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logger = logging.getLogger(__name__)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical(
        "Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback)
    )


sys.excepthook = handle_exception


with open("passes.json", "r", encoding="utf8") as jsonfile:
    passes = json.load(jsonfile)


@dp.message(Command("start"))
@flags.authorization(is_authorized=True)
async def start(message: types.Message):
    user_id = message.from_user.id
    if message.text != "/start":
        refer_id = message.text.replace("/start ", "", 1)
        if refer_id.isdigit() and str(user_id) != refer_id:
            async with aiosqlite.connect(server_db_path) as db:
                async with db.cursor() as cursor:
                    if (
                        await (
                            await cursor.execute(
                                "SELECT id FROM users WHERE id = ?", (user_id,)
                            )
                        ).fetchone()
                    ) is None:
                        if (
                            await (
                                await cursor.execute(
                                    "SELECT id FROM users WHERE id = ?", (refer_id,)
                                )
                            ).fetchone()
                        ) is not None:
                            if (
                                await (
                                    await cursor.execute(
                                        "SELECT user_id FROM referals WHERE user_id = ?",
                                        (user_id,),
                                    )
                                ).fetchone()
                            ) is None:
                                await cursor.execute(
                                    "INSERT INTO referals (user_id, refer_id, time) VALUES (?, ?, ?)",
                                    (user_id, refer_id, time.time()),
                                )
                await db.commit()
    await message.answer_photo(
        photo=main_menu_image,
        caption=f"🤍 Рады вас видеть, @{message.from_user.username}!\n\n📂 Это бот, созданный специально для студентов БНТУ, в нём Вы сможете найти полезную информацию, посмотреть расписание на любой день недели, а также литературу, нужную для освоения определенных предметов.\n\n❔ Почему стоит использовать:\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
        reply_markup=keyboards.main_menu_buttons(),
    )


@dp.callback_query(F.data == "main_menu")
@flags.authorization(is_authorized=True)
async def main_menu(callback: types.CallbackQuery, state: FSMContext):
    if await func.safe_delete(callback) is None:
        return
    await state.clear()
    await callback.message.answer_photo(
        photo=main_menu_image,
        caption=f"🤍 Рады вас видеть, @{callback.from_user.username}!\n\n📂 Это бот, созданный специально для студентов БНТУ, в нём Вы сможете найти полезную информацию, посмотреть расписание на любой день недели, а также литературу, нужную для освоения определенных предметов.\n\n❔ Почему стоит использовать:\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
        reply_markup=keyboards.main_menu_buttons(),
    )


@dp.callback_query(F.data == "profile")
@flags.authorization(is_authorized=True)
async def profile(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    user_id = callback.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            family, name = (
                await (
                    await cursor.execute(
                        "SELECT FullName FROM users WHERE id = ?", (user_id,)
                    )
                ).fetchone()
            )[0].split()[:2]
            faculty = (
                await (
                    await cursor.execute(
                        "SELECT faculty FROM users WHERE id = ?", (user_id,)
                    )
                ).fetchone()
            )[0]
            student_code = (
                await (
                    await cursor.execute(
                        "SELECT student_code FROM users WHERE id = ?", (user_id,)
                    )
                ).fetchone()
            )[0]
    await callback.message.answer_photo(
        photo=profile_image,
        caption=f"👤 {family} {name}\n"
        f"Номер студ.: {student_code}\n\n"
        f"🎓 Факультет: {faculty}\n"
        f"👥 Группа: {student_code[:-2]}\n"
        f"📖 Курс: {int(student_code[6:-2]) - (datetime.datetime.now().year - 2002)}\n",
        reply_markup=keyboards.profile_buttons(),
    )


@dp.callback_query(F.data == "scheduled_message")
@flags.authorization(is_authorized=True)
async def scheduled_message(callback: types.CallbackQuery):
    if not await func.safe_delete(callback):
        return
    user_id = callback.from_user.id
    try:
        job = scheduler.get_job(str(user_id))
        if not job:
            raise JobLookupError(str(user_id))
        set_hour = job.trigger.fields[5]
        caption = f"\n✅ Вы включили рассылку на {str(set_hour)}:00"
    except JobLookupError:
        caption = "📩 После включения рассылки вам будет приходить расписание в выбранное вами время."
    await callback.message.answer_photo(
        caption=caption,
        photo=mailing_photo,
        reply_markup=keyboards.select_time(),
    )


async def delete_message(user_id: int, message_id: int):
    await bot.delete_message(user_id, message_id)


async def scheduled_schedule(user_id: int, group: int):
    week, day = func.get_week_and_day()
    text = func.get_schedule(group, week, day)
    message = await bot.send_message(user_id, f"{day}:\n{text}", parse_mode="HTML")
    scheduler.add_job(
        delete_message,
        "date",
        run_date=datetime.datetime.now() + datetime.timedelta(hours=24),
        args=[user_id, message.message_id],
        id=f"{user_id}-{message.message_id}",
    )


@dp.callback_query(F.data.split()[0] == "select_time")
async def select_time(callback: types.CallbackQuery):
    hour = int(callback.data.split()[1])
    user_id = callback.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            group = (
                await (
                    await cursor.execute(
                        "SELECT student_code FROM users WHERE id = (?)",
                        (callback.from_user.id,),
                    )
                ).fetchone()
            )[0]
    caption = f"\n✅ Вы включили рассылку на {hour}:00"
    try:
        job = scheduler.get_job(str(user_id))
        if not job:
            raise JobLookupError(str(user_id))
        set_hour = job.trigger.fields[5]
        if int(str(set_hour)) == hour:
            return await callback.answer("У вас уже включена рассылка на это время")
        job.remove()
        if hour == -1:
            caption = "📩  После включения рассылки вам будет приходить расписание в выбранное вами время."
            await callback.message.edit_caption(
                caption=caption, reply_markup=keyboards.select_time()
            )
            return await callback.answer("Вы отключили рассылку")
        scheduler.add_job(
            scheduled_schedule,
            "cron",
            hour=hour,
            minute=0,
            args=[user_id, group],
            id=str(user_id),
        )
        await callback.message.edit_caption(
            caption=caption, reply_markup=keyboards.select_time()
        )
        return await callback.answer(f"Вы переподключили рассылку на {hour}:00")
    except JobLookupError:
        if hour == -1:
            return await callback.answer("Вы еще не подключали рассылку")
    scheduler.add_job(
        scheduled_schedule,
        "cron",
        hour=hour,
        minute=0,
        args=[user_id, group],
        id=str(user_id),
    )
    await callback.message.edit_caption(
        caption=caption, reply_markup=keyboards.select_time()
    )
    return await callback.answer("Успешно")


@dp.callback_query(F.data == "referal_system")
@flags.authorization(is_authorized=True)
async def referal_system(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    user_id = callback.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            ref_info = await (
                await cursor.execute(
                    "SELECT refer_id, time FROM referals WHERE user_id = ?", (user_id,)
                )
            ).fetchone()
            count = len(
                (
                    await (
                        await cursor.execute(
                            "SELECT user_id FROM referals WHERE refer_id = ?",
                            (user_id,),
                        )
                    ).fetchall()
                )
            )
            if ref_info is not None:
                refer_id, timer = ref_info
                refer = (
                    await (
                        await cursor.execute(
                            "SELECT FullName FROM users WHERE id = ?", (refer_id,)
                        )
                    ).fetchone()
                )[0]
                dt = datetime.datetime.fromtimestamp(timer)
                date = dt.strftime("%d.%m.%y %H:%M")
            else:
                refer = "Нет"
                date = "Нет"
    await callback.message.answer_photo(
        photo=profile_image,
        caption=f"➕ Приглашено: {count}\n\n"
        f"🫂 Вас пригласил: {refer}\n"
        f"⌛️ Дата приглашения: {date}\n\n"
        f"🔗 Ваша ссылка:\n"
        f"https://t.me/{(await bot.get_me()).id}?start={user_id}",
        reply_markup=keyboards.back_to_profile(),
    )


@dp.message(Command("add_event"))
@flags.owner(is_owner=True)
@flags.studcouncil_member(is_member=True)
@flags.permissions(any_permission=True)
async def add_event_command(message: Message):
    return await message.answer(
        "Выберите какое мероприятие вы хотите добавить:",
        reply_markup=keyboards.choose_event_type(),
    )


@dp.callback_query(F.data.split()[0] == "add_event")
@flags.owner(is_owner=True)
@flags.studcouncil_member(is_member=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def add_event_query(callback: types.CallbackQuery, state: FSMContext):
    args = callback.data.split()
    if len(args) == 1:
        return await callback.message.edit_caption(
            text="Выберите какое мероприятие вы хотите добавить:",
            reply_markup=keyboards.choose_event_type(True),
        )
    event_type = args[1]
    await state.clear()
    await state.update_data(event_type=event_type)
    await state.set_state(states.InputEventData.name)
    return await callback.message.answer("Введите название мероприятия.")


@dp.message(states.InputEventData.name)
async def input_event_name(message: types.Message, state: FSMContext):
    await state.set_state(states.InputEventData.date)
    await state.update_data(name=message.text)
    return await message.answer("Введи дату мероприятия в формате дд.мм.гггг чч:мм")


@dp.message(states.InputEventData.date)
async def input_event_date(message: types.Message, state: FSMContext):
    timestamp = datetime.datetime.strptime(message.text, "%d.%m.%Y %H:%M").timestamp()
    await state.update_data(date=str(int(timestamp)))
    await state.set_state(states.InputEventData.description)
    return await message.answer("Введите описание мероприятия.")


@dp.message(states.InputEventData.description)
async def input_event_description(message: types.Message, state: FSMContext):
    await state.set_state(states.InputEventData.contacts)
    await state.update_data(description=message.text)
    return await message.answer(
        "Введите контакты организаторов мероприятия. Каждый контакт с новой строки."
    )


@dp.message(states.InputEventData.contacts)
async def input_event_contacts(message: types.Message, state: FSMContext):
    await state.set_state(states.InputEventData.members)
    await state.update_data(contacts=message.text.split("\n"))
    return await message.answer(
        "Введите участников мероприятия. Каждый участник с новой строки."
    )


@dp.message(states.InputEventData.members)
async def input_event_members(message: types.Message, state: FSMContext):
    await state.set_state(states.InputEventData.image)
    await state.update_data(members=message.text.split("\n"))
    return await message.answer("Введите ссылку на фото для мероприятия.")


@dp.message(states.InputEventData.image)
async def input_event_image(message: types.Message, state: FSMContext):
    await state.update_data(image=message.text)
    data = await state.get_data()
    await state.clear()
    event_type = data["event_type"]
    name = data["name"]
    date = data["date"]
    description = data["description"]
    contacts = data["contacts"]
    members = data["members"]
    image = data["image"]
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            res = await cursor.execute(
                "INSERT INTO events (type, name, date, description, image_url) "
                "VALUES (?, ?, ?, ?, ?)",
                (event_type, name, int(date), description, image),
            )
            await db.commit()
            event_id = res.lastrowid
            for contact in contacts:
                await cursor.execute(
                    "INSERT INTO event_contacts (event_id, contact) VALUES (?, ?)",
                    (event_id, contact),
                )
            for member in members:
                await cursor.execute(
                    "INSERT INTO event_members (event_id, member) VALUES (?, ?)",
                    (event_id, member),
                )
            await db.commit()
    return message.answer("Мероприятие добавлено.")


@dp.callback_query(F.data == "message_support")
async def message_support(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "➡️ Отправьте сообщение, которое рассмотрит разработчик или модера.",
        reply_markup=keyboards.back_to_main(),
    )
    await callback.answer()
    await state.set_state(states.SupportStates.message)


@dp.message(states.SupportStates.message)
async def on_support_message(message: Message, state: FSMContext):
    await bot.forward_message(id_owner, message.chat.id, message.message_id)
    await bot.send_message(
        id_owner,
        f"Обращение от пользователя @{message.from_user.username}",
        reply_markup=keyboards.support_answer_buttons(message.from_user.id),
    )
    await message.answer("Ваше сообщение отправлено!")
    await state.clear()


@dp.callback_query(F.data.startswith("answer_support"))
async def answer_support(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Напишите Ваш ответ.")
    await callback.answer()
    await state.set_state(states.SupportStates.answer)
    await state.set_data({"user_id": callback.data.split(" ")[1]})


@dp.message(states.SupportStates.answer)
async def on_answer_support(message: Message, state: FSMContext):
    user_id = (await state.get_data()).get("user_id")
    await bot.send_message(user_id, "Ответ от поддержки:")
    await func.send_message(bot, int(user_id), message, is_report=True)
    await state.clear()
    await message.answer("Ответ отправлен!")


@dp.callback_query(F.data.split()[0] == "studsovet")
@flags.authorization(is_authorized=True)
async def studsovet(callback: types.CallbackQuery):
    is_owner = callback.from_user.id == id_owner
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            isStudentCouncilMember = await (
                await cursor.execute(
                    "SELECT user_id FROM studcouncil_members WHERE user_id = (?)",
                    (callback.from_user.id,),
                )
            ).fetchone()
    if "return" in callback.data:
        await callback.message.edit_caption(
            caption="🎓 Студенческий совет БНТУ – молодёжная структура, деятельность которой направлена на поддержку и реализацию студенческих инициатив, взаимодействие от имени представителей обучающихся с руководством БНТУ, совместное решение вопросов жизнедеятельности студенческой молодёжи и помощи в реализации личностного потенциала в различных направлениях.",
            reply_markup=keyboards.studsovet_buttons(
                is_owner or isStudentCouncilMember
            ),
        )
    else:
        if await func.safe_delete(callback) is None:
            return
        await callback.message.answer_photo(
            photo=studsovet_photo,
            caption="🎓 Студенческий совет БНТУ – молодёжная структура, деятельность которой направлена на поддержку и реализацию студенческих инициатив, взаимодействие от имени представителей обучающихся с руководством БНТУ, совместное решение вопросов жизнедеятельности студенческой молодёжи и помощи в реализации личностного потенциала в различных направлениях.",
            reply_markup=keyboards.studsovet_buttons(
                is_owner or isStudentCouncilMember
            ),
        )


@dp.callback_query(F.data == "studsovet_staff_menu")
@flags.authorization(is_authorized=True)
async def studsovet_staff_menu(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        photo=studsovet_photo,
        caption="Выберите факультет, студенческий совет которого Вас интересует, для получения информации о председателях факультетов и общежитий:",
        reply_markup=keyboards.studsovet_staff_menu_buttons(),
    )


@dp.callback_query(F.data.split()[0] == "events")
@dp.callback_query(F.data == "studsovet_events_begin")
@flags.authorization(is_authorized=True)
async def studsovet_events(callback: types.CallbackQuery):
    is_owner = callback.from_user.id == id_owner
    args = callback.data.split()
    event_type = args[1]
    page = args[2]
    events = {}
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            isStudentCouncilMember = await (
                await cursor.execute(
                    "SELECT user_id FROM studcouncil_members WHERE user_id = (?)",
                    (callback.from_user.id,),
                )
            ).fetchone()
            res = await (
                await cursor.execute(
                    "SELECT id, name, date, description, image_url FROM events WHERE type = (?)",
                    (event_type,),
                )
            ).fetchall()
            if not res:
                return callback.message.answer("Мероприятий нет")
            for event in res:
                event_id = event[0]
                contacts = await (
                    await cursor.execute(
                        "SELECT contact FROM event_contacts WHERE event_id = (?)",
                        (event_id,),
                    )
                ).fetchall()
                members = await (
                    await cursor.execute(
                        "SELECT member FROM event_members WHERE event_id = (?)",
                        (event_id,),
                    )
                ).fetchall()
                events[event[1]] = {
                    "date": event[2],
                    "description": event[3],
                    "contacts": [contact[0] for contact in contacts],
                    "members": [member[0] for member in members],
                    "images": event[4],
                    "event_id": event_id,
                }
    events_count = len(events.keys())
    event_name = list(events.keys())[int(page) - 1]
    event = events[event_name]
    if await func.safe_delete(callback) is None:
        return
    if event["images"]:
        await callback.message.answer_photo(
            photo=event["images"],
            caption=f"🎉 {event_name}\n\n📃 Описание:\n{event['description']}\n\n⏳ Дата: {datetime.datetime.fromtimestamp(event['date']).strftime('%Y.%m.%d %H:%M')}\n\n👥 Записано: {len(event['members'])}",
            reply_markup=keyboards.events_buttons(
                event_type,
                page,
                events_count,
                is_owner or isStudentCouncilMember,
                event_id,
            ),
        )
    else:
        await callback.message.answer_photo(
            photo=studsovet_photo,
            caption=f"🎉 {event_name}\n\n📃 Описание:\n{event['description']}\n\n⏳ Дата: {datetime.datetime.fromtimestamp(event['date']).strftime('%Y.%m.%d %H:%M')}\n\n👥 Записано: {len(event['members'])}",
            reply_markup=keyboards.events_buttons(
                event_type,
                page,
                events_count,
                is_owner or isStudentCouncilMember,
                event_id,
            ),
        )


@dp.callback_query(F.data.split()[0] == "delete_event")
async def delete_event(callback: types.CallbackQuery):
    event_id = int(callback.data.split()[1])
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute("DELETE FROM events WHERE id = (?)", (event_id,))
            await cursor.execute(
                "DELETE FROM event_members WHERE event_id = (?)", (event_id,)
            )
            await cursor.execute(
                "DELETE FROM event_contacts WHERE event_id = (?)", (event_id,)
            )
        await db.commit()
    await callback.message.answer("Мероприятие удалено")


@dp.callback_query(F.data.split()[0] == "edit_event")
async def edit_event(callback: types.CallbackQuery, state: FSMContext):
    args = callback.data.split()[1:]
    event_id = args[0]
    if len(args) == 1:
        return await callback.message.answer(
            "Выберите какой пункт вы хотите редактировать.",
            reply_markup=keyboards.edit_event_choose(args[0]),
        )
    field = args[1]
    await state.set_state(states.EditEventData.edit)
    await state.set_data({"event_id": event_id, "field": field})
    match field:
        case "name":
            return await callback.message.edit_text("Введите новое название.")
        case "description":
            return await callback.message.edit_text("Введите новое описание.")
        case "date":
            return await callback.message.edit_text(
                "Введите новую дату в формате 'дд.мм.гггг чч:мм'."
            )
        case "contacts":
            return await callback.message.edit_text(
                "Введите новые контакты. Каждый контакт с новой строки."
            )
        case "members":
            return await callback.message.edit_text(
                "Введите новых участников. Каждый участник с новой строки."
            )
        case "image":
            return await callback.message.edit_text("Введите новую ссылку на картинку.")


@dp.message(states.EditEventData.edit)
async def edit_event_field(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data["event_id"]
    field = data["field"]
    text = message.text
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            match field:
                case "name":
                    await cursor.execute(
                        "UPDATE events SET name = ? WHERE id = ?", (text, event_id)
                    )
                case "description":
                    await cursor.execute(
                        "UPDATE events SET description = ? WHERE id = ?",
                        (text, event_id),
                    )
                case "date":
                    timestamp = datetime.datetime.strptime(
                        text, "%d.%m.%Y %H:%M"
                    ).timestamp()
                    await cursor.execute(
                        "UPDATE events SET date = ? WHERE id = ?", (timestamp, event_id)
                    )
                case "contacts":
                    await cursor.execute(
                        "DELETE FROM event_contacts WHERE event_id = ?", (event_id,)
                    )
                    for line in text.split("\n"):
                        await cursor.execute(
                            "INSERT INTO event_contacts(event_id, contact) VALUES (?, ?)",
                            (event_id, line),
                        )
                case "members":
                    await cursor.execute(
                        "DELETE FROM event_members WHERE event_id = ?", (event_id,)
                    )
                    for line in text.split("\n"):
                        await cursor.execute(
                            "INSERT INTO event_members(event_id, member) VALUES (?, ?)",
                            (event_id, line),
                        )
                case "image":
                    await cursor.execute(
                        "UPDATE events SET image_url = ? WHERE id = ?", (text, event_id)
                    )
        await db.commit()
    return await message.answer("Успешно изменено")


@dp.callback_query(F.data.split()[0] == "studsovet_support")
@flags.authorization(is_authorized=True)
async def studsovet_support(callback: types.CallbackQuery, state: FSMContext):
    args = callback.data.split()[1:]
    if not args:
        return await callback.message.edit_caption(
            caption="📌 Выберите как вы хотите подать заявку или жалобу:",
            reply_markup=keyboards.choose_support_type(),
        )
    if args[0] == "anonymous":
        await state.set_data({"anonymous": True})
    elif args[0] == "not_anonymous":
        await state.set_data({"anonymous": False})
    return await callback.message.edit_caption(
        caption="📌 Выберите интересующий Вас раздел подачи заявки с идеей или жалобой:",
        reply_markup=keyboards.studsovet_support_choice_buttons(),
    )


@dp.callback_query(F.data.split()[0] == "stud_support")
@flags.authorization(is_authorized=True)
async def stud_support(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        f'🧩 Отправьте Ваше сообщение с идеей или жалобой по разделу "{callback.data.split(" ", 1)[1]}":'
    )
    await state.set_state(states.InputStudsovetReport.category)
    await state.update_data(category=callback.data.split(" ", 1)[1])


@dp.message(states.InputStudsovetReport.category)
async def auto_auth_end(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("category")
    is_anonymous = data.get("anonymous")
    if is_anonymous:
        text = f"Заявка\n🗂 Раздел: {category}\n\n📃 Содержание:\n{message.text}"
    else:
        async with aiosqlite.connect(server_db_path) as db:
            async with db.cursor() as cursor:
                student_info = await (
                    await cursor.execute(
                        "SELECT student_code, FullName, faculty FROM users WHERE id = (?)",
                        (message.from_user.id,),
                    )
                ).fetchone()

        text = (
            f"⚠️ Заявка от {'@' + message.from_user.username if message.from_user.username else message.from_user.full_name}\n\n"
            "Информация о студенте:\n"
            f"Номер студенческого: {student_info[0]}\n"
            f"Фамилия и имя: {student_info[1]}\n"
            f"Факультет: {student_info[2]}\n"
            f"🗂 Раздел: {category}\n\n"
            f"📃 Содержание:\n{message.text}"
        )

    await bot.send_message(
        chat_id=studsovet_chat_id,
        text=text,
    )
    await message.answer(
        "✅ Ваше сообщение было отправлено в студсовет, при необходимости мы свяжемся с Вами. Спасибо!",
    )
    await state.clear()


@dp.callback_query(F.data.split()[0] == "student_coucil_staff")
@flags.authorization(is_authorized=True)
async def student_coucil_staff(callback: types.CallbackQuery):
    if "return" in callback.data:
        if await func.safe_delete(callback) is None:
            return
        await callback.message.answer_photo(
            photo=studsovet_photo,
            caption=f"{callback.data.split()[1]}",
            reply_markup=keyboards.student_coucil_staff_create(
                callback.data.split()[1]
            ),
        )
    else:
        await callback.message.edit_caption(
            caption=f"{callback.data.split()[1]}",
            reply_markup=keyboards.student_coucil_staff_create(
                callback.data.split()[1]
            ),
        )


@dp.callback_query(F.data.split()[0] == "faculty_student_council")
@flags.authorization(is_authorized=True)
async def faculty_student_council(callback: types.CallbackQuery):
    with open(
        f"student_councils/student_council_chairmans.json", "r", encoding="utf8"
    ) as jsonfile:
        concil = json.load(jsonfile)[callback.data.split()[1]]
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=concil["faculty"]["image_url"],
        caption=f"{concil['faculty']['name']}\n\n{concil['faculty']['job_title']}",
        reply_markup=keyboards.faculty_student_council_return(callback.data.split()[1]),
    )


@dp.callback_query(F.data.split()[0] == "hostel_student_council")
@flags.authorization(is_authorized=True)
async def hostel_student_council(callback: types.CallbackQuery):
    with open(
        f"student_councils/student_council_chairmans.json", "r", encoding="utf8"
    ) as jsonfile:
        print([callback.data.split()[1], callback.data.split()[2]])
        concil = json.load(jsonfile)[callback.data.split()[1]]["hostels"][
            callback.data.split()[2]
        ]
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=concil["image_url"],
        caption=f"{concil['name']}\n\n{concil['job_title']}",
        reply_markup=keyboards.faculty_student_council_return(callback.data.split()[1]),
    )


@dp.callback_query(F.data == "map")
@flags.authorization(is_authorized=True)
async def university_map(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=map_photo,
        caption="🗺️ Карта мини-городка БНТУ",
        reply_markup=keyboards.map_menu(),
    )


@dp.callback_query(F.data == "passes")
@flags.authorization(is_authorized=True)
async def passes_button(callback: types.CallbackQuery):
    passes = []
    for i in list(passes):
        b = types.InlineKeyboardButton(text=i, callback_data=f"get_passes {i}")
        passes.append(b)
    await callback.message.edit_caption(
        caption="📗 Выберите нужный Вам предмет:",
        reply_markup=keyboards.passes_menu(passes),
    )


@dp.callback_query(F.data.split()[0] == "get_passes")
@flags.authorization(is_authorized=True)
async def pass_button(callback: types.CallbackQuery):
    text = f"{callback.data.split()[1]} | " + passes[callback.data.split()[1]]
    await callback.message.edit_caption(
        caption=text, reply_markup=keyboards.pass_detail_menu(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "delete")
async def delete(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return


@dp.callback_query(F.data.split()[0] == "help")
@flags.authorization(is_authorized=True)
async def help(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=support_image,
        caption=f"📌 Если у Вас есть предложения, идеи или Вы нашли баг, то можете соообщить об этом, мы постараемся как можно быстрее ответить на Ваше сообщение.\n\n✏️ Обращаться по юзернейму {user_owner}",
        reply_markup=keyboards.help_menu(),
    )


@dp.message(Command("add_moderator"))
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
async def add_moderator(message: types.Message, command: Command):
    if not command.args:
        return message.answer("Пожалуйста укажите ID пользователя")
    user_id = int(command.args)
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            student_code = await (
                await cursor.execute(
                    "SELECT student_code FROM users WHERE id = ?", (user_id,)
                )
            ).fetchone()
            if not student_code:
                return await message.answer("Пользователь не найден")
            student_code = student_code[0]
            await cursor.execute(
                "INSERT INTO moderators (id, student_code) VALUES (?, ?)",
                (user_id, student_code),
            )
            await db.commit()
    await message.answer("Пользователь назначен модератором")


@dp.message(Command("add_studcouncil_member"))
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
async def add_studcouncil_member(message: types.Message, command: Command):
    if not command.args:
        return message.answer("Пожалуйста укажите ID пользователя")
    user_id = int(command.args)
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            student_code = await (
                await cursor.execute(
                    "SELECT student_code FROM users WHERE id = ?", (user_id,)
                )
            ).fetchone()
            if not student_code:
                return await message.answer("Пользователь не найден")
            student_code = student_code[0]
            await cursor.execute(
                "INSERT INTO moderators (id, student_code) VALUES (?, ?)",
                (user_id, student_code),
            )
            await db.commit()
    await message.answer("Пользователь назначен членом студсовета")


async def main():
    os.makedirs("databases", exist_ok=True)
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                id INT PRIMARY KEY,
                FullName TEXT,
                faculty TEXT,
                student_code TEXT,
                code TEXT UNIQUE
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS chats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INT NOT NULL,
                user2_id INT
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_message_id INTEGER NOT NULL,
                bot_message_id INTEGER NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats(id)
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS bans_anon_chat(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS moderators(
                id INT PRIMARY KEY,
                student_code TEXT NOT NULL,
                hired_at DATETIME DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (student_code) REFERENCES users(student_code)
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS referals(
                user_id INT PRIMARY KEY,
                refer_id INT NOT NULL,
                time DATETIME DEFAULT (datetime('now', 'localtime'))
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                date INT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT NOT NULL
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS event_contacts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INT NOT NULL,
                contact TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS event_members(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INT NOT NULL,
                member TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events(id)
            )""")
            await cursor.execute("""CREATE TABLE IF NOT EXISTS studcouncil_members(
                user_id INT PRIMARY KEY,
                student_code INT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (student_code) REFERENCES users(student_code)
            )""")

        await db.commit()
    me = await bot.get_me()
    logger.info(f"@{me.username} ({me.first_name})")
    dp.message.middleware(middleware.AuthorizationMiddleware())
    dp.callback_query.middleware(middleware.AuthorizationMiddleware())
    dp.message.middleware(middleware.BanMiddleware())
    dp.callback_query.middleware(middleware.BanMiddleware())
    dp.message.middleware(middleware.OwnerMiddleware())
    dp.callback_query.middleware(middleware.OwnerMiddleware())
    dp.message.middleware(middleware.ModeratorMiddleware())
    dp.callback_query.middleware(middleware.ModeratorMiddleware())
    dp.message.middleware(middleware.PermissonMiddleware())
    dp.callback_query.middleware(middleware.PermissonMiddleware())
    dp.message.middleware(middleware.StudentCouncilMiddleware())
    dp.callback_query.middleware(middleware.StudentCouncilMiddleware())
    dp.update.middleware(middleware.MediaGroupMiddleware())
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
