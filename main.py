import os
import sys
import pytz
import asyncio
import aiosqlite
import datetime
import json
import hashlib
import logging

from aiogram.utils.markdown import hlink
from aiogram.types import ChosenInlineResult, InlineQuery, \
                          InlineQueryResultArticle, InputTextMessageContent
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, types, flags, filters, F
from aiogram.filters.command import Command
from aiogram.exceptions import TelegramForbiddenError

from util.StateStorge import SQLiteStorage
from util import func
from util.literature_searching import search_literature
from util import middleware
from util.states import AutoAuth, AcceptAuthForm, AnonChatState, Form
from util import states
from util.config import server_db_path
from util import keyboards

from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('TOKEN')

main_menu_image = os.getenv('MAIN_IMAGE')
example_photo = os.getenv('EXAMPLE_IMAGE')
map_photo = os.getenv('MAP_IMAGE')

user_owner = os.getenv('USER_OWNER')
id_owner = int(os.getenv('ID_OWNER'))
moderators_chat_id = int(os.getenv("MODERATORS_CHAT_ID"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=SQLiteStorage())
tz = pytz.timezone("Europe/Moscow")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler(
            f"./logs/{__name__}_{datetime.datetime.now(tz).strftime('%d-%m-%Y_%H-%M-%S')}.log",
            mode="w"
        ),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger(__name__)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical(
        "Uncaught exception:",
        exc_info=(exc_type, exc_value, exc_traceback)
    )


sys.excepthook = handle_exception
# with open('schedule.json', 'r', encoding="utf8") as json_file:
#     schedule_base = json.load(json_file)


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
        link = hlink('⬇️ Скачать', book['download']['download_link'])
        description = book["publishing_date"]
        message_text = f"{book['publishing_date']} | {book['title']}\n\n{book['description']}\n\n{link}"
        if book["authors"]:
            with_authors = ' и др.' if len(book["authors"]) != 1 else ''
            description += f" | {book['authors'][0]}{with_authors}"
            message_text = (
                f"<b>{book['publishing_date']} | {book['title']}</b>\n\n"
                f"<b>ℹ️ Описание:</b>\n{book['description']}\n\n<b>©️ Авторы:</b>\n{book['authors'][0]}{with_authors}\n\n{link}"
            )
        results.append(InlineQueryResultArticle(
            id=str(id),
            title=book['title'],
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode="HTML"
            ),
            description=description,
            thumbnail_url=book["image_url"]
        ))
    await bot.answer_inline_query(inline_query.id, results)


@dp.chosen_inline_result()
async def chosen_inline_handler(result: ChosenInlineResult):
    print(result)


@dp.message(Command("start"))
@flags.authorization(is_authorized=True)
async def start(message: types.Message):
    await message.answer_photo(
            photo=main_menu_image,
            caption=f"💚 Рады вас видеть, @{message.from_user.username}!\n\n🧩 Это бот инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\n📗 Бот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\n🍀 Почему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
            reply_markup=keyboards.main_menu_buttons()
        )


@dp.callback_query(F.data == "main_menu")
@flags.authorization(is_authorized=True)
async def main_menu(callback: types.CallbackQuery):
    try:
        await callback.message.edit_caption(
            photo=main_menu_image,
            caption=f"💚 Рады вас видеть, @{callback.from_user.username}!\n\n🧩 Это бот инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\n📗 Бот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\n🍀 Почему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
            reply_markup=keyboards.main_menu_buttons()
        )
    # dont use bare except
    except Exception:
        await callback.message.delete()
        await callback.message.answer_photo(
                photo=main_menu_image,
                caption=f"💚 Рады вас видеть, @{callback.from_user.username}!\n\n🧩 Это бот инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\n📗 Бот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\n🍀 Почему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
                reply_markup=keyboards.main_menu_buttons()
            )


@dp.callback_query(F.data == "auto_auth")
async def auto_auth_begin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "🧩 Отправьте текстом номер Вашего студенческого билета (чёрный). Без пробелов, лишних символов, запятых и т.д.",
    )
    await state.set_state(AutoAuth.student_code)


@dp.message(AutoAuth.student_code)
async def auto_auth_end(message: types.Message, state: FSMContext):
    await message.answer(
        "🧩 Отлично! Теперь также отправьте красный номер на студенческом.",
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
            text="🔐 Вручную",
            callback_data="support_auth"
        )
        await message.answer(
            '⚠️ Ошибка сервера. Система БНТУ не отвечает. Автоматическая авторизация временно недоступна, но Вы можете авторизоваться вручную через фото профиля по кнопке "Вручную".',
            reply_markup=keyboards.auth_error()
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
                    (message.from_user.id, auth_status[0], auth_status[1], student_code, code)
                )
            await db.commit()
        await message.answer(f'✅ {auth_status[0]}, авторизация прошла успешно! Теперь Вы подтвержденный студент БНТУ! Вы можете вызвать главное меню командой /start')
        await bot.send_message(
            id_owner, f'✅ Пользователь автоматически авторизован @{message.from_user.username} ({message.from_user.full_name}).'
        )


@dp.callback_query(F.data == "support_auth")
async def auth_begin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
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
        reply_markup=keyboards.support_auth(message.from_user.id)
    )
    await message.answer("Фото получено и отправлено на проверку. Ожидайте подтверждения.")
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
    fio = message.text.split(',')[0]
    fac = message.text.split(',')[1].replace(' ', '')
    student_code = message.text.split(',')[2]
    bilet_code = message.text.split(',')[3]
    code = hashlib.sha256(bilet_code.encode()).hexdigest()
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                (id, fio, fac, student_code, code)
            )
        await db.commit()
    await message.answer("Пользователь был успешно авторизован.")
    await bot.send_message(
        id, f'✅ {fio.split()[1]}, авторизация была подтверждена, теперь Вы подтвержденный студент БНТУ! Вы можете вызвать главное меню командой /start'
    )


@dp.callback_query(F.data == "anonymous_chat")
@flags.authorization(is_authorized=True)
async def anonymous_chat(callback: types.CallbackQuery):
    await callback.message.delete()
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
            "💚 Приятного время провождения!"
        ), 
        reply_markup=keyboards.anonymous_chat_menu()
    )


@dp.callback_query(F.data == "search_anonymous_chat")
@flags.banned(isnt_banned=True)
@flags.authorization(is_authorized=True)
async def search_anonymous_chat(callback: types.CallbackQuery, state: FSMContext):
    user2_id = callback.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            if await (await cursor.execute(
                "SELECT user1_id, user2_id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                (user2_id, user2_id)
            )).fetchone():
                return await callback.message.edit_text(
                    "❗️ Вы уже в анонимном чате."
                )
            if user1_id := (await (await cursor.execute(
                "SELECT user1_id FROM chats WHERE user2_id IS NULL"
            )).fetchone()):
                user1_id = user1_id[0]
                await cursor.execute(
                    "UPDATE chats SET user2_id=(?) WHERE user1_id=(?)",
                    (user2_id, user1_id)
                )
                await callback.message.edit_text(
                    "👥 Собеседник найден."
                )
                await bot.send_message(
                    user1_id,
                    "👥 Собеседник найден."
                )
            else:
                await cursor.execute(
                    "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)",
                    (user2_id, None)
                )
                await callback.message.edit_text(
                    "🔎 Идет поиск собеседника."
                )
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
                if data := await (await cursor.execute(
                    "SELECT user_id, chat_id FROM messages WHERE bot_message_id = (?)",
                    (message_id, )
                )).fetchone():
                    reported_user_id, anon_chat_id = data
                    await bot.send_message(
                        moderators_chat_id,
                        (
                            f"Жалоба на пользователя ID: {reported_user_id}\n"
                            f"От пользователя: {message.from_user.username}"
                        ),
                        reply_markup=keyboards.report_menu(
                            reported_user_id, message.from_user.id
                        )
                    )
                    await func.send_message(
                        bot,
                        moderators_chat_id,
                        reply_message,
                        anon_chat_id,
                        is_report=True
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
            count = (await (await cursor.execute("SELECT COUNT(id) FROM users")).fetchone())[0]
            faculties = await (await cursor.execute("SELECT faculty FROM users")).fetchall()
    if is_callback:
        return await message.edit_text(
            f"Пользователей: {count}\n"
            f"Факультетов: {len(set(faculties))}",
            reply_markup=keyboards.admin_panel_menu()
        )
    await message.answer(
        f"Пользователей: {count}\n"
        f"Факультетов: {len(set(faculties))}",
        reply_markup=keyboards.admin_panel_menu()
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


@dp.callback_query(F.data == "search_user")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_user(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите способ поиска пользователя:",
        reply_markup=keyboards.search_user_buttons()
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
    await callback.message.edit_text("Отправьте номер студенческого билета пользователя")


@dp.message(states.InputUserID.InputByUserID)
async def input_user_id(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        user_id = int(message.text)
    except ValueError:
        await state.clear()
        return await message.answer(
            "Введите корректное число.",
            reply_markup=keyboards.back_to_admin_panel()
        )
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (await cursor.execute(
                "SELECT student_code, FullName, faculty FROM users WHERE id = ?",
                (user_id, )
            )).fetchone()
    if not response:
        return await message.answer(
            "Пользователь не найден",
            reply_markup=keyboards.back_to_admin_panel()
        )
    text = "Информация о пользователе:\n\n"
    info_lines = ["Номер студ.билета:", "Фамилия и имя:", "Факультет:"]
    for info_line, info in zip(info_lines, response):
        text += f"{info_line}\n<blockquote>{info}</blockquote>\n\n"
    await message.answer(
        text.rstrip("\n"),
        reply_markup=keyboards.control_user_buttons(user_id),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.split()[0] == "send_message_for_user")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def send_message_for_user(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(f'Отправьте сообщение, которое хотите отправить пользователю с ID: {callback.data.split()[1]}')
    await state.set_state(states.InputMessageForUser.user_id)
    await state.update_data(user_id=int(callback.data.split()[1]))
    await state.set_state(states.InputMessageForUser.message)


@dp.callback_query(F.data.split()[0] == "send_message_for_group")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def send_message_for_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(f'Отправьте сообщение, которое хотите отправить группе {callback.data.split()[1]}')
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
            users = await (await cursor.execute(
                "SELECT id FROM users WHERE substr(student_code, 1, length(student_code) - 2) = ?",
                (str(group_number),)
            )).fetchall()
    sending=0
    banned=0
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id[0], text=f"Сообщение от администратора:\n{message.text}")
            sending+=1
        except TelegramForbiddenError as e:
            if "bot was blocked by the user" in str(e):
                banned+=1
    await message.answer(
        f'Рассылка пользователям группы {group_number} завершена!\n\n'
        f'Отправлено: {sending}\n'
        f'Забанили: {banned}\n'
        f'Неизвестно: {len(users) - (sending+banned)}\n'
        )


@dp.message(states.InputMessageForUser.message)
async def input_send_message_for_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    await state.clear()
    try:
        await bot.send_message(chat_id=user_id, text=f"Сообщение от администратора:\n{message.text}")
    except TelegramForbiddenError as e:
        if "bot was blocked by the user" in str(e):
            return await message.answer(f'Пользователь заблокировал бота.')
    await message.answer(f'Сообщение отправлено пользователю!')
    

@dp.message(states.InputUserID.InputByGroupNumber)
async def input_group_number(message: types.Message, state: FSMContext):
    await state.clear()
    try:
        group_number = int(message.text)
    except ValueError:
        await state.clear()
        return await message.answer(
            "Введите корректное число.",
            reply_markup=keyboards.back_to_admin_panel()
        )
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (await cursor.execute(
                "SELECT id, FullName, faculty FROM users WHERE student_code = ?",
                (group_number, )
            )).fetchone()
    if not response:
        return await message.answer(
            "Пользователь не найден",
            reply_markup=keyboards.back_to_admin_panel()
        )
    text = "Информация о пользователе:\n\n"
    info_lines = ["ID телеграм аккаунта:", "Фамилия и имя:", "Факультет:"]
    for info_line, info in zip(info_lines, response):
        text += f"{info_line}\n<blockquote>{info}</blockquote>\n\n"
    return await message.answer(
        text.rstrip("\n"),
        reply_markup=keyboards.control_user_buttons(response[0]),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "search_group")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_group_input(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputGroupNumber.userInput)
    return await callback.message.edit_text(
        "Отправьте номер группы:",
        reply_markup=keyboards.back_to_admin_panel()
    )


@dp.message(states.InputGroupNumber.userInput)
async def search_group(message: types.Message, state: FSMContext):
    group_number = message.text
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (await cursor.execute(
                "SELECT id, student_code, FullName, faculty "
                "FROM users WHERE CAST(student_code AS TEXT) LIKE (?)",
                (group_number+"%", )
            )).fetchall()
    if not response:
        return await message.answer(
            "Нет результатов",
            reply_markup=keyboards.back_to_admin_panel()
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
            f"{i+1}. {info[2]} (Telegram ID: {info[0]}; Номер студ. билета: {info[1]})"
            for i, info in enumerate(response)
        ]
    )
    await message.answer(
        text,
        reply_markup=keyboards.control_group_buttons(group_number)
    )


@dp.callback_query(F.data == "search_faculty")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_faculty_input(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Искать пользователей из факультета:",
        reply_markup=keyboards.search_faculty_buttons()
    )


@dp.callback_query(F.data == "search_by_faculty_abbr")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_faculty_abbr(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputFaculty.InputByLetters)
    await callback.message.edit_text(
        "Введите аббревиатуру факультета:",
        reply_markup=keyboards.back_to_admin_panel()
    )


@dp.callback_query(F.data == "search_by_faculty_number")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_faculty_number(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(states.InputFaculty.InputByNumbers)
    return await callback.message.edit_text(
        "Введите номер факультета:",
        reply_markup=keyboards.back_to_admin_panel()
    )


@dp.message(states.InputFaculty.InputByLetters)
async def input_faculty_abbr(message: types.Message, state: FSMContext):
    await state.clear()
    abbr = message.text.upper()
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (await cursor.execute(
                "SELECT id, FullName "
                "FROM users WHERE faculty = (?)",
                (abbr, )
            )).fetchall()
    if not response:
        return await message.answer(
            "Нет результатов",
            reply_markup=keyboards.back_to_admin_panel()
        )
    users_amount = len(response)
    text = (
        f'Информация о факультете "{abbr}":\n'
        f"Кол-во пользователей: {users_amount}"
    )
    await message.answer(
        text,
        reply_markup=keyboards.back_to_admin_panel()
    )


@dp.message(states.InputFaculty.InputByNumbers)
async def input_faculty_numbers(message: types.Message, state: FSMContext):
    await state.clear()
    faculty = message.text
    if len(faculty) != 3:
        return await message.answer(
            "Номер факультета должен состоять из трех цифр",
            reply_markup=keyboards.back_to_admin_panel()
        )
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            response = await (await cursor.execute(
                "SELECT id, FullName, faculty "
                "FROM users WHERE CAST(student_code AS TEXT) LIKE (?)",
                (faculty+"%", )
            )).fetchall()
    if not response:
        return await message.answer(
            "Нет результатов",
            reply_markup=keyboards.back_to_admin_panel()
        )
    users_amount = len(response)
    faculty_abbr = response[0][-1]
    text = (
        f'Информация о факультете "{faculty_abbr}":\n'
        f"Кол-во пользователей: {users_amount}"
    )
    await message.answer(
        text,
        reply_markup=keyboards.back_to_admin_panel()
    )


@dp.callback_query(F.data == "admin_schedule")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_schedule(callback: types.CallbackQuery):
    schedule_files = os.listdir("./schedules/")
    sorted_by_modification_time = sorted(
        schedule_files,
        key=lambda entry: os.path.getmtime(
            os.path.join("./schedules/", entry)
        ),
        reverse=True
    )
    newest_modification = datetime.datetime.fromtimestamp(
        os.path.getmtime(
            os.path.join(
                "./schedules/",
                sorted_by_modification_time[0]
            )
        ),
        pytz.timezone("Europe/Moscow")
    ).strftime("%d.%m.%Y %H:%M:%S")
    oldest_modificatiom = datetime.datetime.fromtimestamp(
        os.path.getmtime(
            os.path.join(
                "./schedules/",
                sorted_by_modification_time[-1]
            )
        ),
        pytz.timezone("Europe/Moscow")
    ).strftime("%d.%m.%Y %H:%M:%S")
    await callback.message.edit_text(
        f"Самое последнее изменение: {newest_modification} ({sorted_by_modification_time[0]})\n"
        f"Самое давнее изменение: {oldest_modificatiom} ({sorted_by_modification_time[-1]})",
        reply_markup=keyboards.back_to_admin_panel()
    )


@dp.callback_query(F.data == "admin_literature")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_literature(callback: types.CallbackQuery):
    modification_time = datetime.datetime.fromtimestamp(
        os.path.getmtime(
            "./books/literature.json"
        ),
        pytz.timezone("Europe/Moscow")
    ).strftime("%d.%m.%Y %H:%M:%S")
    count = 0
    for _, books in literature.items():
        count += int(books["count"][1:-1])
    await callback.message.edit_text(
        f"Последнее изменение литературы: {modification_time}\n"
        f"Кол-во книг: {count}",
        reply_markup=keyboards.back_to_admin_panel()
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
                "INSERT INTO bans_anon_chat (user_id) VALUES (?)",
                (user_id, )
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
                "INSERT INTO bans_anon_chat (user_id) VALUES (?)",
                (user_id, )
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
                "DELETE FROM bans_anon_chat WHERE user_id = (?)",
                (user_id, )
            )
            await db.commit()
    await message.answer("Пользователь разблокирован")


@dp.pre_checkout_query()
async def on_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery,):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(message: types.Message):
    if message.successful_payment.invoice_payload == "unban_payment":
        user_id = message.from_user.id
        async with aiosqlite.connect(server_db_path) as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM bans_anon_chat WHERE user_id = (?)",
                    (user_id, )
                )
                await db.commit()
        await message.answer(
            "Поздравляем с успешным приобретением разблокиорвки!",
            message_effect_id="5104841245755180586"
        )


@dp.message(Command("leave_chat"))
@flags.authorization(is_authorized=True)
async def leave_chat(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            if user_ids := await (await cursor.execute(
                "SELECT user1_id, user2_id, id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                (user_id, user_id)
            )).fetchone():
                for i in range(2):
                    if user_ids[i]:
                        await bot.send_message(
                            user_ids[i], 
                            "⛔️ Диалог окончен.",
                            reply_markup=keyboards.anonymous_chat_menu()
                        )
                await cursor.execute(
                    "DELETE FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                    (user_id, user_id)
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
            if user_ids := await (await cursor.execute(
                "SELECT user1_id, user2_id, id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                (user_id, user_id)
            )).fetchone():
                chat_id = user_ids[-1]
                if user_ids[1] is None:
                    return
                if user_ids[0] == user_id:
                    sent_message = await func.send_message(
                        bot,
                        user_ids[1],
                        message,
                        chat_id,
                        media_group
                    )
                else:
                    sent_message = await func.send_message(
                        bot,
                        user_ids[0],
                        message,
                        chat_id,
                        media_group
                    )
                await cursor.execute(
                    """INSERT INTO messages
                    (chat_id, user_id, user_message_id, bot_message_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, user_id, message.message_id, sent_message.message_id)
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
            chat_id = (await (await cursor.execute(
                "SELECT id FROM chats "
                "WHERE user2_id = ? "
                "OR user1_id = ?",
                (user1_id, user1_id)
            )).fetchone())[0]
            if await (await cursor.execute(
                "SELECT chat_id FROM messages WHERE bot_message_id = ?",
                (message_id, )
            )).fetchone():
                id_for_reaction, user2_id = (await (await cursor.execute(
                    """SELECT user_message_id, user_id FROM messages WHERE
                    bot_message_id = ?""",
                    (message_id, )
                )).fetchone())
            else:
                users = await (await cursor.execute(
                    "SELECT user1_id, user2_id FROM chats WHERE id = ?",
                    (chat_id, )
                )).fetchone()
                id_for_reaction = (await (await cursor.execute(
                    """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                    (message_id, )
                )).fetchone())[0]
                for user in users:
                    if user != user1_id:
                        user2_id = user
    await bot.set_message_reaction(
        user2_id,
        message_id=id_for_reaction,
        reaction=message_reaction.new_reaction
    )


@dp.edited_message(AnonChatState.in_chat)
async def on_chat_edit_message(message: types.Message):
    user1_id = message.from_user.id
    message_id = message.message_id
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            chat_id = (await (await cursor.execute(
                "SELECT id FROM chats "
                "WHERE user2_id = ? "
                "OR user1_id = ?",
                (user1_id, user1_id)
            )).fetchone())[0]
            users = await (await cursor.execute(
                "SELECT user1_id, user2_id FROM chats WHERE id = ?",
                (chat_id, )
            )).fetchone()
            for user in users:
                if user != user1_id:
                    user2_id = user
            response = (await (await cursor.execute(
                    """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                    (message_id, )
                )).fetchone())
            fallback_response_inc = (await (await cursor.execute(
                    """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                    (message_id+1, )
                )).fetchone())
            fallback_response_dec = (await (await cursor.execute(
                    """SELECT bot_message_id FROM messages WHERE
                    user_message_id = ?""",
                    (message_id-1, )
                )).fetchone())
            if not response:
                id_to_edit = fallback_response_inc if fallback_response_inc else fallback_response_dec
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
            message.text + "\n\n(Ред.)",
            chat_id=user2_id,
            message_id=id_to_edit
        )
    elif message.caption:
        await bot.edit_message_caption(
            caption=message.caption + "\n\n(Ред.)",
            chat_id=user2_id,
            message_id=id_to_edit,
        )


@dp.callback_query(F.data == "map")
@flags.authorization(is_authorized=True)
async def university_map(callback: types.CallbackQuery):
    await callback.message.answer_photo(
        photo=map_photo,
        caption='🗺️ Карта мини-городка БНТУ',
        reply_markup=keyboards.map_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "passes")
@flags.authorization(is_authorized=True)
async def passes_button(callback: types.CallbackQuery):
    passes = []
    for i in list(passes):
        b = types.InlineKeyboardButton(
            text=i,
            callback_data=f"get_passes {i}"
        )
        passes.append(b)
    await callback.message.edit_caption(
        caption='📗 Выберите нужный Вам предмет:',
        reply_markup=keyboards.passes_menu(passes)
    )


@dp.callback_query(F.data.split()[0] == "get_passes")
@flags.authorization(is_authorized=True)
async def pass_button(callback: types.CallbackQuery):
    text = f"{callback.data.split()[1]} | "+passes[callback.data.split()[1]]
    await callback.message.edit_caption(
        caption=text,
        reply_markup=keyboards.pass_detail_menu(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "schedule")
@flags.authorization(is_authorized=True)
async def schedule(callback: types.CallbackQuery):
    try:
        await callback.message.edit_caption(
            caption='📚 Выберите нужное Вам расписание занятий:',
            reply_markup=keyboards.schedule_menu()
            )
    except Exception:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=main_menu_image,
            caption='📚 Выберите нужное Вам расписание занятий:',
            reply_markup=keyboards.schedule_menu()
        )


@dp.callback_query(F.data.split()[0] == "send_schedule")
@flags.authorization(is_authorized=True)
async def schedule(callback: types.CallbackQuery):
    async with aiosqlite.connect(server_db_path) as db:
        async with db.cursor() as cursor:
            student_code = (await (await cursor.execute(
                "SELECT student_code FROM users WHERE id = (?)",
                (callback.from_user.id, )
            )).fetchone())[0]
    group = student_code[:-2]
    with open(f"schedules/schedule_{group}.json", "r", encoding='utf8') as jsonfile:
        schedule_base = json.load(jsonfile)['Schedule']
    if callback.data.split()[1] == 'week':
        date = func.get_week_and_day()
        week, day = date
        text = ''
        for i in schedule_base[week]:
            text += f"\n{i}:\n"
            for j in schedule_base[week][i]:
                teacher_text = ("\n" + j["Teacher"]) if j["Teacher"] else ""
                text += f'<blockquote>{j["Time"]} | {j["Matter"]}\n{j["Frame"]} корп., {j["Classroom"]} аудит.{teacher_text}</blockquote>\n'
        await callback.message.delete()
        await callback.message.answer(
            f'{text}',
            reply_markup=keyboards.back_to_schedule(),
            parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'next_week':
        date = func.get_week_and_day()
        week, day = date
        reversing_list = [1, 0]
        week = reversing_list[week]
        text = ''
        for i in schedule_base[week]:
            text += f"\n{i}:\n"
            for j in schedule_base[week][i]:
                teacher_text = ("\n" + j["Teacher"]) if j["Teacher"] else ""
                text += f'<blockquote>{j["Time"]} | {j["Matter"]}\n{j["Frame"]} корп., {j["Classroom"]} аудит.{teacher_text}</blockquote>\n'
        await callback.message.delete()
        await callback.message.answer(
            f'{text}',
            reply_markup=keyboards.back_to_schedule(), parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'together':
        date = func.get_week_and_day()
        week, day = date
        text = ''
        try:
            for i in schedule_base[week][day]:
                teacher_text = ("\n" + i["Teacher"]) if i["Teacher"] else ""
                text += f'<blockquote>{i["Time"]} | {i["Matter"]}\n{i["Frame"]} корп., {i["Classroom"]} аудит.{teacher_text}</blockquote>\n'
        except KeyError:
            text += "Занятий нет 🎉"
        await callback.message.delete()
        await callback.message.answer(
            f'{day}:\n{text}',
            reply_markup=keyboards.back_to_schedule(), parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'tomorrow':
        date = func.get_tomorrow_week_and_day()
        week, day = date
        text = ''
        try:
            for i in schedule_base[week][day]:
                teacher_text = ("\n" + i["Teacher"]) if i["Teacher"] else ""
                text += f'<blockquote>{i["Time"]} | {i["Matter"]}\n{i["Frame"]} корп., {i["Classroom"]} аудит.{teacher_text}</blockquote>\n'
        except KeyError:
            text += "Занятий нет 🎉"
        await callback.message.delete()
        await callback.message.answer(
            f'{day}:\n{text}',
            reply_markup=keyboards.back_to_schedule(), parse_mode="HTML"
        )


@dp.callback_query(F.data == "delete")
async def delete(callback: types.CallbackQuery):
    await callback.message.delete()


@dp.callback_query(F.data.split()[0] == "help")
@flags.authorization(is_authorized=True)
async def help(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        f'Если у Вас есть предложения, идеи или Вы нашли баг, то можете соообщить об этом, мы постараемся как можно быстрее ответить на Ваше сообщение.\n\nОбращаться по юзернейму {user_owner}',
        reply_markup=keyboards.help_menu()
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
            student_code = await (await cursor.execute(
                "SELECT student_code FROM users WHERE "
                "id = ?",
                (user_id, )
            )).fetchone()
            if not student_code:
                return await message.answer("Пользователь не найден")
            student_code = student_code[0]
            await cursor.execute(
                "INSERT INTO moderators (id, student_code) VALUES (?, ?)",
                (user_id, student_code)
            )
            await db.commit()
    await message.answer("Пользователь назначен модератором")


async def main():
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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
