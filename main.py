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

from dotenv import load_dotenv
from util import func
from util import states
from util import keyboards
from util import middleware
from util.config import server_db_path, base_dir
from util.literature_searching import search_literature
from util.states import AutoAuth, AcceptAuthForm, AnonChatState, Form

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.jobstores.base import JobLookupError

from redis.asyncio import Redis

from aiogram.utils.markdown import hlink
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.storage.redis import RedisStorage
from aiogram import Bot, Dispatcher, types, flags, filters, F
from aiogram.types import (
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

load_dotenv()


API_TOKEN = os.getenv("TOKEN")

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
dp = Dispatcher(storage=RedisStorage(Redis(host="redis", port=6379)))
tz = pytz.timezone("Europe/Moscow")

os.environ["TZ"] = "Europe/Moscow"
time.tzset()

jobstores = {"default": RedisJobStore(host="redis", port=6379)}
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


with open("./books/literature.json", "r", encoding="utf8") as jsonfile:
    literature = json.load(jsonfile)


@dp.inline_query()
async def inline_handler(inline_query: InlineQuery):
    query = inline_query.query or ""
    books = search_literature(literature, query)
    results = []
    for id, book in enumerate(books):
        link = hlink("⬇️ Скачать", book["download"]["download_link"])
        description = book["publishing_date"]
        message_text = f"{book['publishing_date']} | {book['title']}\n\n{book['description']}\n\n{link}"
        if book["authors"]:
            with_authors = " и др." if len(book["authors"]) != 1 else ""
            description += f" | {book['authors'][0]}{with_authors}"
            message_text = (
                f"<b>{book['publishing_date']} | {book['title']}</b>\n\n"
                f"<b>ℹ️ Описание:</b>\n{book['description']}\n\n<b>©️ Авторы:</b>\n{book['authors'][0]}{with_authors}\n\n{link}"
            )
        results.append(
            InlineQueryResultArticle(
                id=str(id),
                title=book["title"],
                input_message_content=InputTextMessageContent(
                    message_text=message_text, parse_mode="HTML"
                ),
                description=description,
                thumbnail_url=book["image_url"],
            )
        )
    await bot.answer_inline_query(inline_query.id, results)


@dp.chosen_inline_result()
async def chosen_inline_handler(result: ChosenInlineResult):
    print(result)


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
        caption=f"Рады вас видеть, @{message.from_user.username}!\n\nЭто бот, созданный инженерно-педагогическим факультетом, группой прикладного программирования, в котором Вы сможете найти полезную информацию.\n\nБот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\nПочему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
        reply_markup=keyboards.main_menu_buttons(),
    )


@dp.callback_query(F.data == "main_menu")
@flags.authorization(is_authorized=True)
async def main_menu(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=main_menu_image,
        caption=f"Рады вас видеть, @{callback.from_user.username}!\n\nЭто бот, созданный инженерно-педагогическим факультетом, группой прикладного программирования, в котором Вы сможете найти полезную информацию.\n\nБот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\nПочему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
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
        caption=f"Имя: {name}\n"
        f"Фамилия: {family}\n\n"
        f"Факультет: {faculty}\n"
        f"Группа: {student_code[:-2]}\n"
        f"Курс: {int(student_code[6:-2]) - (datetime.datetime.now().year - 2001)}\n\n"
        f"Номер студ.: {student_code}\n",
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
        caption = f"\nВы включили рассылку на {str(set_hour)}:00"
    except JobLookupError:
        caption = "После включения рассылки вам будет приходить расписание в выбранное вами время."
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
    caption = f"\nВы включили рассылку на {hour}:00"
    try:
        job = scheduler.get_job(str(user_id))
        if not job:
            raise JobLookupError(str(user_id))
        set_hour = job.trigger.fields[5]
        if int(str(set_hour)) == hour:
            return await callback.answer("У вас уже включена рассылка на это время")
        job.remove()
        if hour == -1:
            caption = "После включения рассылки вам будет приходить расписание в выбранное вами время."
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
        caption=f"Приглашено: {count}\n\n"
        f"Вас пригласил: {refer}\n"
        f"Дата приглашения: {date}\n\n"
        f"Ваша ссылка:\n"
        f"https://t.me/{(await bot.get_me()).id}?start={user_id}",
        reply_markup=keyboards.back_to_profile(),
    )


@dp.callback_query(F.data == "auto_auth")
async def auto_auth_begin(callback: types.CallbackQuery, state: FSMContext):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer(
        "Отправьте текстом номер Вашего студенческого билета (чёрный). Без пробелов, лишних символов, запятых и т.д.",
    )
    await state.set_state(AutoAuth.student_code)


@dp.message(AutoAuth.student_code)
async def auto_auth_end(message: types.Message, state: FSMContext):
    await message.answer(
        "Отлично! Теперь также отправьте красный номер на студенческом.",
    )
    await state.update_data(student_code=message.text)
    await state.set_state(AutoAuth.code)


@dp.message(AutoAuth.code)
async def auto_auth_end(message: types.Message, state: FSMContext):
    data = await state.get_data()
    student_code = data.get("student_code")
    await state.clear()
    code = message.text
    auth_status = await func.authorize(student_code, code)
    if auth_status == -1:
        b_auth = types.InlineKeyboardButton(
            text="🔐 Вручную", callback_data="support_auth"
        )
        await message.answer(
            '⚠️ Ошибка сервера. Система БНТУ не отвечает. Автоматическая авторизация временно недоступна, но Вы можете авторизоваться вручную через фото профиля по кнопке "Вручную".',
            reply_markup=keyboards.auth_error(),
        )
    elif auth_status == 0:
        await message.answer(
            "❌ Студент с такими данными не найден в системе БНТУ. Вы можете повторить попытку, написав /start.",
        )
    else:
        async with aiosqlite.connect(server_db_path) as db:
            async with db.cursor() as cursor:
                code = hashlib.sha256(code.encode()).hexdigest()
                await cursor.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                    (
                        message.from_user.id,
                        auth_status[0],
                        auth_status[1],
                        student_code,
                        code,
                    ),
                )
            await db.commit()
        await message.answer(
            f"✅ {auth_status[0]}, авторизация прошла успешно! Теперь Вы подтвержденный студент БНТУ! Вы можете вызвать главное меню командой /start"
        )
        await bot.send_message(
            id_owner,
            f"✅ Пользователь автоматически авторизован @{message.from_user.username} ({message.from_user.full_name}).",
        )


@dp.callback_query(F.data == "support_auth")
async def auth_begin(callback: types.CallbackQuery, state: FSMContext):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=example_photo,
        caption="📷 Отправьте фото Вашего студенческого билета, чтобы мы могли убедиться в том, что Вы являетесь нашим студентом. Фото должно быть чётким, в хорошем освещении и без бликов.",
    )
    await state.set_state(Form.photo)


@dp.message(Form.photo)
async def auth_end(message: types.Message, state: FSMContext):
    if not message.photo:
        return await message.answer("Пожалуйста, отправьте именно фото.")
    photo = message.photo[-1]
    await bot.send_photo(
        id_owner,
        photo=photo.file_id,
        caption=f"Фото студенческого билета от пользователя @{message.from_user.username} (ID: {message.from_user.id})",
        reply_markup=keyboards.support_auth(message.from_user.id),
    )
    await message.answer(
        "Фото получено и отправлено на проверку. Ожидайте подтверждения."
    )
    await state.clear()


@dp.callback_query(F.data.split()[0] == "accept_auth")
async def accept_auth(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption="Введите данные через запятую: ФИО, Факультет, Код студента (черный), Код билета (красный)."
    )
    await state.set_state(AcceptAuthForm.id)
    await state.update_data(id=int(callback.data.split()[1]))
    await state.set_state(AcceptAuthForm.text)


@dp.message(AcceptAuthForm.text)
async def accept_auth_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    id = data.get("id")
    await state.clear()
    fio = message.text.split(",")[0]
    fac = message.text.split(",")[1].replace(" ", "")
    student_code = message.text.split(",")[2]
    bilet_code = message.text.split(",")[3]
    code = hashlib.sha256(bilet_code.encode()).hexdigest()
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                (id, fio, fac, student_code, code),
            )
        await db.commit()
    await message.answer("Пользователь был успешно авторизован.")
    await bot.send_message(
        id,
        f"✅ {fio.split()[1]}, авторизация была подтверждена, теперь Вы подтвержденный студент БНТУ! Вы можете вызвать главное меню командой /start",
    )


@dp.callback_query(F.data == "anonymous_chat")
@flags.authorization(is_authorized=True)
async def anonymous_chat(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer(
        text=(
            "🕵🏻‍♂️ Добро пожаловать в анонимный чат БНТУ. "
            "Здесь Вы можете найти себе собеседника для того, "
            "чтобы скоротать время на скучной паре или просто "
            "повеселиться общаясь с другими студентами своего "
            "университета. Также не будет лишним найти новые "
            "знакомства.\n\n⚠️ Перед тем, как начать пользоваться "
            "анонимным чатом, обязательно прочитай правила.\n\n"
            "Если вы хотите пожаловаться на нарушение правил, "
            "ответьте на сообщение с нарушением коммандой /report\n\n"
            "Чтобы выйти из диалога, напишите в чат команду /leave_chat\n\n"
            "Приятного время провождения!"
        ),
        reply_markup=keyboards.anonymous_chat_menu(),
    )


@dp.callback_query(F.data == "search_anonymous_chat")
@flags.banned(isnt_banned=True)
@flags.authorization(is_authorized=True)
async def search_anonymous_chat(callback: types.CallbackQuery, state: FSMContext):
    user2_id = callback.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            if await (
                await cursor.execute(
                    "SELECT user1_id, user2_id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                    (user2_id, user2_id),
                )
            ).fetchone():
                return await callback.message.edit_text("❗️ Вы уже в анонимном чате.")
            if user1_id := (
                await (
                    await cursor.execute(
                        "SELECT user1_id FROM chats WHERE user2_id IS NULL"
                    )
                ).fetchone()
            ):
                user1_id = user1_id[0]
                await cursor.execute(
                    "UPDATE chats SET user2_id=(?) WHERE user1_id=(?)",
                    (user2_id, user1_id),
                )
                await callback.message.edit_text("👥 Собеседник найден.")
                await bot.send_message(user1_id, "👥 Собеседник найден.")
            else:
                await cursor.execute(
                    "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)",
                    (user2_id, None),
                )
                await callback.message.edit_text("🔎 Идет поиск собеседника.")
        await state.set_state(AnonChatState.in_chat)
        await db.commit()


@dp.message(Command("report"))
@flags.authorization(is_authorized=True)
async def report(message: types.Message):
    if reply_message := message.reply_to_message:
        message_id = reply_message.message_id
        user_id = reply_message.from_user.id
        if user_id == message.from_user.id:
            return message.answer("Вы не можете пожаловаться на себя")
        async with aiosqlite.connect(server_db_path) as db:
            async with db.cursor() as cursor:
                if data := await (
                    await cursor.execute(
                        "SELECT user_id, chat_id FROM messages WHERE bot_message_id = (?)",
                        (message_id,),
                    )
                ).fetchone():
                    reported_user_id, anon_chat_id = data
                    await bot.send_message(
                        moderators_chat_id,
                        (
                            f"Жалоба на пользователя ID: {reported_user_id}\n"
                            f"От пользователя: {message.from_user.username}"
                        ),
                        reply_markup=keyboards.report_menu(
                            reported_user_id, message.from_user.id
                        ),
                    )
                    await func.send_message(
                        bot,
                        moderators_chat_id,
                        reply_message,
                        anon_chat_id,
                        is_report=True,
                    )
                    return message.answer("Жалоба отправлена")
                return message.answer("Нужно отвечать на сообщение из диалога")
    message.answer("Вы должны ответить на сообщение с нарушением этой коммандой")


async def admin_panel(message, state=None):
    if state:
        await state.clear()
    is_callback = isinstance(message, types.CallbackQuery)
    if is_callback:
        message = message.message
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            count = (
                await (await cursor.execute("SELECT COUNT(id) FROM users")).fetchone()
            )[0]
            faculties = await (
                await cursor.execute("SELECT faculty FROM users")
            ).fetchall()
    if is_callback:
        return await message.edit_text(
            f"Пользователей: {count}\nФакультетов: {len(set(faculties))}",
            reply_markup=keyboards.admin_panel_menu(),
        )
    await message.answer(
        f"Пользователей: {count}\nФакультетов: {len(set(faculties))}",
        reply_markup=keyboards.admin_panel_menu(),
    )


@dp.message(Command("admin"))
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_panel_by_callback(message: types.Message, state: FSMContext):
    await admin_panel(message, state)


@dp.callback_query(F.data.contains("admin_panel"))
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_panel_by_callback(callback: types.CallbackQuery, state: FSMContext):
    await admin_panel(callback, state)


@dp.callback_query(F.data.split()[0] == "add_event")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_user(callback: types.CallbackQuery, state: FSMContext):
    args = callback.data.split()
    if len(args) == 1:
        return await callback.message.edit_text(
            "Выберите какое мероприятие вы хотите добавить:",
            reply_markup=keyboards.choose_event_type(),
        )
    event_type = args[1]
    await state.clear()
    await state.update_data(event_type=event_type)
    await state.set_state(states.InputEventData.name)
    return await callback.message.edit_text("Введите название мероприятия.")


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


@dp.callback_query(F.data == "search_user")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_user(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите способ поиска пользователя:",
        reply_markup=keyboards.search_user_buttons(),
    )


@dp.callback_query(F.data == "search_by_user_id")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_user_id(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputUserID.InputByUserID)
    await callback.message.edit_text("Отправьте Telegram ID пользователя")


@dp.callback_query(F.data == "search_by_group_number")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_group_number(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputUserID.InputByGroupNumber)
    await callback.message.edit_text(
        "Отправьте номер студенческого билета пользователя"
    )


@dp.message(states.InputUserID.InputByUserID)
async def input_user_id(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        user_id = int(message.text)
    except ValueError:
        await state.clear()
        return await message.answer(
            "Введите корректное число.", reply_markup=keyboards.back_to_admin_panel()
        )
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (
                await cursor.execute(
                    "SELECT student_code, FullName, faculty FROM users WHERE id = ?",
                    (user_id,),
                )
            ).fetchone()
    if not response:
        return await message.answer(
            "Пользователь не найден", reply_markup=keyboards.back_to_admin_panel()
        )
    text = "Информация о пользователе:\n\n"
    info_lines = ["Номер студ.билета:", "Фамилия и имя:", "Факультет:"]
    for info_line, info in zip(info_lines, response):
        text += f"{info_line}\n<blockquote>{info}</blockquote>\n\n"
    await message.answer(
        text.rstrip("\n"),
        reply_markup=keyboards.control_user_buttons(user_id),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.split()[0] == "send_message_for_user")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def send_message_for_user(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"Отправьте сообщение, которое хотите отправить пользователю с ID: {callback.data.split()[1]}"
    )
    await state.set_state(states.InputMessageForUser.user_id)
    await state.update_data(user_id=int(callback.data.split()[1]))
    await state.set_state(states.InputMessageForUser.message)


@dp.callback_query(F.data.split()[0] == "send_message_for_group")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def send_message_for_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"Отправьте сообщение, которое хотите отправить группе {callback.data.split()[1]}"
    )
    await state.set_state(states.InputMessageForGroup.group_id)
    await state.update_data(group_id=int(callback.data.split()[1]))
    await state.set_state(states.InputMessageForGroup.message)


@dp.message(states.InputMessageForGroup.message)
async def input_send_message_for_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    group_number = data.get("group_id")
    await state.clear()
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            users = await (
                await cursor.execute(
                    "SELECT id FROM users WHERE substr(student_code, 1, length(student_code) - 2) = ?",
                    (str(group_number),),
                )
            ).fetchall()
    sending = 0
    banned = 0
    for user_id in users:
        try:
            await bot.send_message(
                chat_id=user_id[0], text=f"Сообщение от администратора:\n{message.text}"
            )
            sending += 1
        except TelegramForbiddenError as e:
            if "bot was blocked by the user" in str(e):
                banned += 1
        except:
            pass
    await message.answer(
        f"Рассылка пользователям группы {group_number} завершена!\n\n"
        f"Отправлено: {sending}\n"
        f"Забанили: {banned}\n"
        f"Неизвестно: {len(users) - (sending + banned)}\n"
    )


@dp.message(states.InputMessageForUser.message)
async def input_send_message_for_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    await state.clear()
    try:
        await bot.send_message(
            chat_id=user_id, text=f"Сообщение от администратора:\n{message.text}"
        )
    except TelegramForbiddenError as e:
        if "bot was blocked by the user" in str(e):
            return await message.answer(f"Пользователь заблокировал бота.")
    await message.answer(f"Сообщение отправлено пользователю!")


@dp.message(states.InputUserID.InputByGroupNumber)
async def input_group_number(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        group_number = int(message.text)
    except ValueError:
        await state.clear()
        return await message.answer(
            "Введите корректное число.", reply_markup=keyboards.back_to_admin_panel()
        )
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (
                await cursor.execute(
                    "SELECT id, FullName, faculty FROM users WHERE student_code = ?",
                    (group_number,),
                )
            ).fetchone()
    if not response:
        return await message.answer(
            "Пользователь не найден", reply_markup=keyboards.back_to_admin_panel()
        )
    text = "Информация о пользователе:\n\n"
    info_lines = ["ID телеграм аккаунта:", "Фамилия и имя:", "Факультет:"]
    for info_line, info in zip(info_lines, response):
        text += f"{info_line}\n<blockquote>{info}</blockquote>\n\n"
    return await message.answer(
        text.rstrip("\n"),
        reply_markup=keyboards.control_user_buttons(response[0]),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "search_group")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_group_input(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputGroupNumber.userInput)
    return await callback.message.edit_text(
        "Отправьте номер группы:", reply_markup=keyboards.back_to_admin_panel()
    )


@dp.message(states.InputGroupNumber.userInput)
async def search_group(message: types.Message, state: FSMContext):
    group_number = message.text
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (
                await cursor.execute(
                    "SELECT id, student_code, FullName, faculty "
                    "FROM users WHERE CAST(student_code AS TEXT) LIKE (?)",
                    (group_number + "%",),
                )
            ).fetchall()
    if not response:
        return await message.answer(
            "Нет результатов", reply_markup=keyboards.back_to_admin_panel()
        )
    users_amount = len(response)
    faculty = response[0][-1]
    text = (
        f"Информация о группе {group_number}:\n"
        f"Кол-во пользователей: {users_amount}\n"
        f"Факультет: {faculty}\n\n"
        "Пользователи:\n"
    )
    text += "\n".join(
        [
            f"{i + 1}. {info[2]} (Telegram ID: {info[0]}; Номер студ. билета: {info[1]})"
            for i, info in enumerate(response)
        ]
    )
    await message.answer(
        text, reply_markup=keyboards.control_group_buttons(group_number)
    )


@dp.callback_query(F.data == "search_faculty")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_faculty_input(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Искать пользователей из факультета:",
        reply_markup=keyboards.search_faculty_buttons(),
    )


@dp.callback_query(F.data == "search_by_faculty_abbr")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_faculty_abbr(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputFaculty.InputByLetters)
    await callback.message.edit_text(
        "Введите аббревиатуру факультета:", reply_markup=keyboards.back_to_admin_panel()
    )


@dp.callback_query(F.data == "search_by_faculty_number")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_faculty_number(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputFaculty.InputByNumbers)
    return await callback.message.edit_text(
        "Введите номер факультета:", reply_markup=keyboards.back_to_admin_panel()
    )


@dp.message(states.InputFaculty.InputByLetters)
async def input_faculty_abbr(message: types.Message, state: FSMContext):
    await state.clear()
    abbr = message.text.upper()
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (
                await cursor.execute(
                    "SELECT id, FullName FROM users WHERE faculty = (?)", (abbr,)
                )
            ).fetchall()
    if not response:
        return await message.answer(
            "Нет результатов", reply_markup=keyboards.back_to_admin_panel()
        )
    users_amount = len(response)
    text = f'Информация о факультете "{abbr}":\nКол-во пользователей: {users_amount}'
    await message.answer(text, reply_markup=keyboards.back_to_admin_panel())


@dp.message(states.InputFaculty.InputByNumbers)
async def input_faculty_numbers(message: types.Message, state: FSMContext):
    await state.clear()
    faculty = message.text
    if len(faculty) != 3:
        return await message.answer(
            "Номер факультета должен состоять из трех цифр",
            reply_markup=keyboards.back_to_admin_panel(),
        )
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (
                await cursor.execute(
                    "SELECT id, FullName, faculty "
                    "FROM users WHERE CAST(student_code AS TEXT) LIKE (?)",
                    (faculty + "%",),
                )
            ).fetchall()
    if not response:
        return await message.answer(
            "Нет результатов", reply_markup=keyboards.back_to_admin_panel()
        )
    users_amount = len(response)
    faculty_abbr = response[0][-1]
    text = (
        f'Информация о факультете "{faculty_abbr}":\n'
        f"Кол-во пользователей: {users_amount}"
    )
    await message.answer(text, reply_markup=keyboards.back_to_admin_panel())


@dp.callback_query(F.data == "admin_schedule")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_schedule(callback: types.CallbackQuery):
    schedule_files = os.listdir("./schedules/")
    sorted_by_modification_time = sorted(
        schedule_files,
        key=lambda entry: os.path.getmtime(os.path.join("./schedules/", entry)),
        reverse=True,
    )
    newest_modification = datetime.datetime.fromtimestamp(
        os.path.getmtime(os.path.join("./schedules/", sorted_by_modification_time[0])),
        pytz.timezone("Europe/Moscow"),
    ).strftime("%d.%m.%Y %H:%M:%S")
    oldest_modificatiom = datetime.datetime.fromtimestamp(
        os.path.getmtime(os.path.join("./schedules/", sorted_by_modification_time[-1])),
        pytz.timezone("Europe/Moscow"),
    ).strftime("%d.%m.%Y %H:%M:%S")
    await callback.message.edit_text(
        f"Самое последнее изменение: {newest_modification} ({sorted_by_modification_time[0]})\n"
        f"Самое давнее изменение: {oldest_modificatiom} ({sorted_by_modification_time[-1]})",
        reply_markup=keyboards.back_to_admin_panel(),
    )


@dp.callback_query(F.data == "admin_literature")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_literature(callback: types.CallbackQuery):
    modification_time = datetime.datetime.fromtimestamp(
        os.path.getmtime("./books/literature.json"), pytz.timezone("Europe/Moscow")
    ).strftime("%d.%m.%Y %H:%M:%S")
    count = 0
    for _, books in literature.items():
        count += int(books["count"][1:-1])
    await callback.message.edit_text(
        f"Последнее изменение литературы: {modification_time}\nКол-во книг: {count}",
        reply_markup=keyboards.back_to_admin_panel(),
    )


@dp.callback_query(F.data.contains("ban_user"))
@flags.owner(is_owner=True)
@flags.moderator(is_moderator=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def button_ban_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split(" ")[1])
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO bans_anon_chat (user_id) VALUES (?)", (user_id,)
            )
            await db.commit()
    await callback.message.edit_text(
        f"Пользователь ID: {user_id} забанен",
    )


@dp.message(Command("ban_user"))
@flags.owner(is_owner=True)
@flags.moderator(is_moderator=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def ban_user(message, command: filters.Command):
    if not command.args:
        return message.answer("Пожалуйста укажите ID пользователя")
    user_id = int(command.args)
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO bans_anon_chat (user_id) VALUES (?)", (user_id,)
            )
            await db.commit()
    await message.answer("Пользователь блокирован")


@dp.message(Command("unban_user"))
@flags.owner(is_owner=True)
@flags.moderator(is_moderator=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def unban_user(message, command: filters.Command):
    if not command.args:
        return message.answer("Пожалуйста укажите ID пользователя")
    user_id = int(command.args)
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM bans_anon_chat WHERE user_id = (?)", (user_id,)
            )
            await db.commit()
    await message.answer("Пользователь разблокирован")


@dp.pre_checkout_query()
async def on_pre_checkout_query(
    pre_checkout_query: types.PreCheckoutQuery,
):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(message: types.Message):
    if message.successful_payment.invoice_payload == "unban_payment":
        user_id = message.from_user.id
        async with aiosqlite.connect(server_db_path) as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM bans_anon_chat WHERE user_id = (?)", (user_id,)
                )
                await db.commit()
        await message.answer(
            "Поздравляем с успешным приобретением разблокиорвки!",
            message_effect_id="5104841245755180586",
        )


@dp.message(Command("leave_chat"))
@flags.authorization(is_authorized=True)
async def leave_chat(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            if user_ids := await (
                await cursor.execute(
                    "SELECT user1_id, user2_id, id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                    (user_id, user_id),
                )
            ).fetchone():
                for i in range(2):
                    if user_ids[i]:
                        await bot.send_message(
                            user_ids[i],
                            "⛔️ Диалог окончен.",
                            reply_markup=keyboards.anonymous_chat_menu(),
                        )
                await cursor.execute(
                    "DELETE FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                    (user_id, user_id),
                )
                await state.clear()
        await db.commit()


@dp.message(AnonChatState.in_chat)
@flags.banned(isnt_banned=True)
async def on_message(message: types.message.Message, **kwargs):
    if message.via_bot:
        return
    media_group = kwargs.get("media_group")
    user_id = message.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            if user_ids := await (
                await cursor.execute(
                    "SELECT user1_id, user2_id, id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                    (user_id, user_id),
                )
            ).fetchone():
                chat_id = user_ids[-1]
                if user_ids[1] is None:
                    return
                if user_ids[0] == user_id:
                    sent_message = await func.send_message(
                        bot, user_ids[1], message, chat_id, media_group
                    )
                else:
                    sent_message = await func.send_message(
                        bot, user_ids[0], message, chat_id, media_group
                    )
                await cursor.execute(
                    """INSERT INTO messages
                    (chat_id, user_id, user_message_id, bot_message_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, user_id, message.message_id, sent_message.message_id),
                )
                await db.commit()


@dp.message_reaction(AnonChatState.in_chat)
async def on_chat_update(message_reaction: types.MessageReactionUpdated):
    user1_id = message_reaction.user.id
    if user1_id == bot.id:
        return
    message_id = message_reaction.message_id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            chat_id = (
                await (
                    await cursor.execute(
                        "SELECT id FROM chats WHERE user2_id = ? OR user1_id = ?",
                        (user1_id, user1_id),
                    )
                ).fetchone()
            )[0]
            if await (
                await cursor.execute(
                    "SELECT chat_id FROM messages WHERE bot_message_id = ?",
                    (message_id,),
                )
            ).fetchone():
                id_for_reaction, user2_id = await (
                    await cursor.execute(
                        """SELECT user_message_id, user_id FROM messages WHERE
                    bot_message_id = ?""",
                        (message_id,),
                    )
                ).fetchone()
            else:
                users = await (
                    await cursor.execute(
                        "SELECT user1_id, user2_id FROM chats WHERE id = ?", (chat_id,)
                    )
                ).fetchone()
                id_for_reaction = (
                    await (
                        await cursor.execute(
                            """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                            (message_id,),
                        )
                    ).fetchone()
                )[0]
                for user in users:
                    if user != user1_id:
                        user2_id = user
    await bot.set_message_reaction(
        user2_id, message_id=id_for_reaction, reaction=message_reaction.new_reaction
    )


@dp.edited_message(AnonChatState.in_chat)
async def on_chat_edit_message(message: types.Message):
    user1_id = message.from_user.id
    message_id = message.message_id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            chat_id = (
                await (
                    await cursor.execute(
                        "SELECT id FROM chats WHERE user2_id = ? OR user1_id = ?",
                        (user1_id, user1_id),
                    )
                ).fetchone()
            )[0]
            users = await (
                await cursor.execute(
                    "SELECT user1_id, user2_id FROM chats WHERE id = ?", (chat_id,)
                )
            ).fetchone()
            for user in users:
                if user != user1_id:
                    user2_id = user
            response = await (
                await cursor.execute(
                    """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                    (message_id,),
                )
            ).fetchone()
            fallback_response_inc = await (
                await cursor.execute(
                    """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                    (message_id + 1,),
                )
            ).fetchone()
            fallback_response_dec = await (
                await cursor.execute(
                    """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                    (message_id - 1,),
                )
            ).fetchone()
            if not response:
                id_to_edit = (
                    fallback_response_inc
                    if fallback_response_inc
                    else fallback_response_dec
                )
            else:
                id_to_edit = response
            if not id_to_edit:
                return await message.answer(
                    "НЕ СООБЩАЙТЕ ОБ ЭТОМ В ПОДДЕРЖКУ!\n\n"
                    "Изменение сообщения для вашего собеседеника не удалось.\n"
                    "Это известная ошибка и над ее решением уже работают."
                )
            id_to_edit = id_to_edit[0]
    if message.text:
        await bot.edit_message_text(
            message.text + "\n\n(Ред.)", chat_id=user2_id, message_id=id_to_edit
        )
    elif message.caption:
        await bot.edit_message_caption(
            caption=message.caption + "\n\n(Ред.)",
            chat_id=user2_id,
            message_id=id_to_edit,
        )


@dp.callback_query(F.data.split()[0] == "studsovet")
@flags.authorization(is_authorized=True)
async def studsovet(callback: types.CallbackQuery):
    if "return" in callback.data:
        await callback.message.edit_caption(
            caption="🎓 Студенческий совет БНТУ – молодёжная структура, деятельность которой направлена на поддержку и реализацию студенческих инициатив, взаимодействие от имени представителей обучающихся с руководством БНТУ, совместное решение вопросов жизнедеятельности студенческой молодёжи и помощи в реализации личностного потенциала в различных направлениях.",
            reply_markup=keyboards.studsovet_buttons(),
        )
    else:
        if await func.safe_delete(callback) is None:
            return
        await callback.message.answer_photo(
            photo=studsovet_photo,
            caption="🎓 Студенческий совет БНТУ – молодёжная структура, деятельность которой направлена на поддержку и реализацию студенческих инициатив, взаимодействие от имени представителей обучающихся с руководством БНТУ, совместное решение вопросов жизнедеятельности студенческой молодёжи и помощи в реализации личностного потенциала в различных направлениях.",
            reply_markup=keyboards.studsovet_buttons(),
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
                event_type, page, events_count, is_owner, event_id
            ),
        )
    else:
        await callback.message.answer_photo(
            photo=studsovet_photo,
            caption=f"🎉 {event_name}\n\n📃 Описание:\n{event['description']}\n\n⏳ Дата: {datetime.datetime.fromtimestamp(event['date']).strftime('%Y.%m.%d %H:%M')}\n\n👥 Записано: {len(event['members'])}",
            reply_markup=keyboards.events_buttons(
                event_type, page, events_count, is_owner, event_id
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
async def edit_event(callback: types.CallbackQuery):
    raise NotImplementedError("Бля отвечаю братка потом сделаю")


@dp.callback_query(F.data == "studsovet_support")
@flags.authorization(is_authorized=True)
async def studsovet_support(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="📌 Выберите интересующий Вас раздел подачи заявки с идеей или жалобой:",
        reply_markup=keyboards.studsovet_support_choice_buttons(),
    )


@dp.callback_query(F.data.split()[0] == "stud_support")
@flags.authorization(is_authorized=True)
async def stud_support(callback: types.CallbackQuery, state: FSMContext):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer(
        f'🧩 Отправьте Ваше сообщение с идеей или жалобой по разделу "{callback.data.split(" ", 1)[1]}":'
    )
    await state.set_state(states.InputStudsovetReport.category)
    await state.update_data(category=callback.data.split(" ", 1)[1])


@dp.message(states.InputStudsovetReport.category)
async def auto_auth_end(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("category")
    await bot.send_message(
        chat_id=studsovet_chat_id,
        text=f"⚠️ Заявка от {'@' + message.from_user.username if message.from_user.username else message.from_user.full_name}\n\n"
        f"🗂 Раздел: {category}\n\n"
        f"📃 Содержание:\n{message.text}",
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


@dp.callback_query(F.data == "schedule")
@flags.authorization(is_authorized=True)
async def schedule(callback: types.CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=schedule_image,
        caption="📚 Выберите нужное Вам расписание занятий:",
        reply_markup=keyboards.schedule_menu(),
    )


@dp.callback_query(F.data == "return_schedule")
@flags.authorization(is_authorized=True)
async def return_schedule(callback: types.CallbackQuery):
    await callback.message.edit_caption(
        caption="📚 Выберите нужное Вам расписание занятий:",
        reply_markup=keyboards.schedule_menu(),
    )


@dp.callback_query(F.data.split()[0] == "send_schedule")
@flags.authorization(is_authorized=True)
async def send_schedule(callback: types.CallbackQuery):
    if callback.data.split()[1] in ["week", "next_week"]:
        return await callback.message.edit_caption(
            caption="📚 Выберите нужный Вам день недели с расписанием:",
            reply_markup=keyboards.schedule_menu_other(callback.data.split()[1]),
        )
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
    tomorrow = callback.data.split()[1] == "tomorrow"
    date = func.get_week_and_day(tomorrow=tomorrow)
    week, day = date
    await callback.message.edit_caption(
        caption=f"{day}:\n{func.get_schedule(group, week, day)}",
        reply_markup=keyboards.schedule_menu(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.split()[0] == "send_schedule_week")
@flags.authorization(is_authorized=True)
async def schedule_week(callback: types.CallbackQuery):
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            student_code = (
                await (
                    await cursor.execute(
                        "SELECT student_code FROM users WHERE id = (?)",
                        (callback.from_user.id,),
                    )
                ).fetchone()
            )[0]
        group = student_code[:-2]
        with open(f"schedules/schedule_{group}.json", "r", encoding="utf8") as jsonfile:
            schedule_base = json.load(jsonfile)["Schedule"]
    date = func.get_week_and_day()
    week, _ = date
    if callback.data.split()[2] == "next_week":
        week = [1, 0][week]
    day = callback.data.split()[1]
    await callback.message.edit_caption(
        caption=func.get_schedule(group, week, day),
        reply_markup=keyboards.schedule_menu_other(callback.data.split()[2]),
        parse_mode="HTML",
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
        caption=f"Если у Вас есть предложения, идеи или Вы нашли баг, то можете соообщить об этом, мы постараемся как можно быстрее ответить на Ваше сообщение.\n\nОбращаться по юзернейму {user_owner}",
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
    dp.update.middleware(middleware.MediaGroupMiddleware())
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
