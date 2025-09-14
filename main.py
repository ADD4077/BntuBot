import os
import pytz
import asyncio
import aiosqlite
import json
import hashlib

from aiogram.utils.markdown import hlink
from aiogram.types import ChosenInlineResult, InlineQuery, \
                          InlineQueryResultArticle, InputTextMessageContent
from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, types, flags, filters
from aiogram.filters.command import Command
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardMarkup


# star imports are bad due to overshadowing and currently
# removed using this
from func import get_week_and_day, \
                 get_tomorrow_week_and_day, \
                 authorize, \
                 Form, \
                 AcceptAuthForm, \
                 AutoAuth

import func
from literature_searching import search_literature
import middleware

from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('TOKEN')

main_menu_image = os.getenv('MAIN_IMAGE')
example_photo = os.getenv('EXAMPLE_IMAGE')
map_photo = os.getenv('MAP_IMAGE')

user_admin = os.getenv('USER_ADMIN')
id_admin = os.getenv('ID_ADMIN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
tz = pytz.timezone("Europe/Moscow")

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
    b_schedule = types.InlineKeyboardButton(
        text="📅 Расписание",
        callback_data="schedule"
    )
    b_litter = types.InlineKeyboardButton(
        text="📜 Литература",
        switch_inline_query_current_chat=''
    )
    # b_pass = types.InlineKeyboardButton(
    #     text="📌 Зачёты",
    #     callback_data="passes"
    # )
    row_lessons = [b_schedule, b_litter]
    b_map = types.InlineKeyboardButton(
        text="🗺️ Карта",
        callback_data="map"
    )
    b_chat = types.InlineKeyboardButton(
        text="🕵🏻‍♂️ Анонимный чат",
        callback_data="anonymous_chat"
    )
    row_map = [b_map, b_chat]
    b_tgk = types.InlineKeyboardButton(
        text="📎 Наш Канал",
        url="https://t.me/BNTUnity"
    )
    b_site = types.InlineKeyboardButton(
        text="🌐 Сайт БНТУ",
        url="https://bntu.by"
    )
    row_url = [b_tgk, b_site]
    b_help = types.InlineKeyboardButton(
        text="🛠️ Поддержка",
        callback_data="help"
    )
    row_help = [b_help]
    rows = [row_lessons, row_map, row_url, row_help]
    main_menu_markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer_photo(
            photo=main_menu_image,
            caption=f"💚 Рады вас видеть, @{message.from_user.username}!\n\n🧩 Это бот инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\n📗 Бот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\n🍀 Почему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
            reply_markup=main_menu_markup
        )


@dp.callback_query(F.data == "main_menu")
@flags.authorization(is_authorized=True)
async def main_menu(callback: types.CallbackQuery):
    b_schedule = types.InlineKeyboardButton(
        text="📅 Расписание",
        callback_data="schedule"
    )
    b_litter = types.InlineKeyboardButton(
        text="📜 Литература",
        switch_inline_query_current_chat=''
    )
    # b_pass = types.InlineKeyboardButton(
    #     text="📌 Зачёты",
    #     callback_data="passes"
    # )
    row_lessons = [b_schedule, b_litter]
    b_map = types.InlineKeyboardButton(
        text="🗺️ Карта",
        callback_data="map"
    )
    b_chat = types.InlineKeyboardButton(
        text="🕵🏻‍♂️ Анонимный чат",
        callback_data="anonymous_chat"
    )
    row_map = [b_map, b_chat]
    b_tgk = types.InlineKeyboardButton(
        text="📎 Наш Канал",
        url="https://t.me/BNTUnity"
    )
    b_site = types.InlineKeyboardButton(
        text="🌐 Сайт БНТУ",
        url="https://bntu.by"
    )
    row_url = [b_tgk, b_site]
    b_help = types.InlineKeyboardButton(
        text="🛠️ Поддержка",
        callback_data="help"
    )
    row_help = [b_help]
    rows = [row_lessons, row_map, row_url, row_help]
    main_menu_markup = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await callback.message.edit_caption(
            photo=main_menu_image,
            caption=f"💚 Рады вас видеть, @{callback.from_user.username}!\n\n🧩 Это бот инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\n📗 Бот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\n🍀 Почему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
            reply_markup=main_menu_markup
        )
    # dont use bare except
    except Exception:
        await callback.message.delete()
        await callback.message.answer_photo(
                photo=main_menu_image,
                caption=f"💚 Рады вас видеть, @{callback.from_user.username}!\n\n🧩 Это бот инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\n📗 Бот поможет Вам быстро и просто посмотреть расписание вашего факультета на ближайшие пару дней или полностью, требования для автомата по разным предметам, а также литературу, нужную для освоения определенных предметов.\n\n🍀 Почему стоит пользоваться ботом?\n• Быстро и не нужно ждать\n• Надёжно и безопасно\n• Удобно и просто\n• Проверено другими",
                reply_markup=main_menu_markup
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
    auth_status = await authorize(student_code, code)
    if auth_status == -1:
        b_auth = types.InlineKeyboardButton(
            text="🔐 Вручную",
            callback_data="support_auth"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[b_auth]])
        await message.answer(
            '⚠️ Ошибка сервера. Система БНТУ не отвечает. Автоматическая авторизация временно недоступна, но Вы можете авторизоваться вручную через фото профиля по кнопке "Вручную".',
            reply_markup=markup
        )
    elif auth_status == 0:
        await message.answer(
            "❌ Студент с такими данными не найден в системе БНТУ. Вы можете повторить попытку, написав /start.",
        )
    else:
        async with aiosqlite.connect("server.db") as db:
            async with db.cursor() as cursor:
                code = hashlib.sha256(code.encode()).hexdigest()
                await cursor.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                    (message.from_user.id, auth_status[0], auth_status[1], student_code, code)
                )
            await db.commit()
        await message.answer(f'✅ {auth_status[0]}, авторизация прошла успешно! Теперь Вы подтвержденный студент БНТУ! Вы можете вызвать главное меню командой /start')
        await bot.send_message(
            id_admin, f'✅ Пользователь автоматически авторизован @{message.from_user.username} ({message.from_user.full_name}).'
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
    b_auth = types.InlineKeyboardButton(
        text="🔐 Авторизовать",
        callback_data=f"accept_auth {message.from_user.id}"
    )
    row_auth = [b_auth]
    b_decline = types.InlineKeyboardButton(
        text="Отклонить",
        callback_data="decline_auth"
    )
    row_decline = [b_decline]
    rows = [row_auth, row_decline]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    photo = message.photo[-1]
    await bot.send_photo(
        id_admin,
        photo=photo.file_id,
        caption=f"Фото студенческого билета от пользователя @{message.from_user.username} (ID: {message.from_user.id})",
        reply_markup=markup
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
    async with aiosqlite.connect("server.db") as db:
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
    b_search = types.InlineKeyboardButton(
        text="🔎 Начать поиск",
        callback_data="search_anonymous_chat"
    )
    row_search = [b_search]
    b_rules = types.InlineKeyboardButton(
        text="Правила чата",
        url="https://telegra.ph/Pravila-Anonimnogo-CHata-09-14"
    )
    row_rules = [b_rules]
    rows = [row_search, row_rules]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
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
            "💚 Приятного время провождения!"
        ), 
        reply_markup=markup
    )


@dp.callback_query(F.data == "search_anonymous_chat")
@flags.banned(isnt_banned=True)
@flags.authorization(is_authorized=True)
async def search_anonymous_chat(callback: types.CallbackQuery):
    user2_id = callback.from_user.id
    async with aiosqlite.connect("server.db") as db:
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
        await db.commit()


@dp.message(Command("report"))
@flags.authorization(is_authorized=True)
async def report(callback: types.CallbackQuery):
    if message := callback.reply_to_message:
        message_id = message.message_id
        user_id = message.from_user.id
        if user_id == callback.from_user.id:
            return callback.answer("Вы не можете пожаловаться на себя")
        async with aiosqlite.connect("server.db") as db:
            async with db.cursor() as cursor:
                if data := await (await cursor.execute(
                    "SELECT user_id, chat_id FROM messages WHERE bot_message_id = (?)",
                    (message_id, )
                )).fetchone():
                    reported_user_id, anon_chat_id = data
                    b_ban_user = types.InlineKeyboardButton(
                        text="Забанить нарушителя",
                        callback_data=f"ban_user {reported_user_id}"
                    )
                    b_ban_sender = types.InlineKeyboardButton(
                        text="Забанить отправителя",
                        callback_data=f"ban_user {callback.from_user.id}"
                    )
                    row_bans = [b_ban_user, b_ban_sender]
                    rows = [row_bans]
                    markup = InlineKeyboardMarkup(inline_keyboard=rows)
                    await bot.send_message(
                        id_admin,
                        (
                            f"Жалоба на пользователя ID: {reported_user_id}\n"
                            f"От пользователя: {callback.from_user.username}"
                        ),
                        reply_markup=markup
                    )
                    await func.send_message(
                        bot,
                        id_admin,
                        message,
                        anon_chat_id
                    )
                    return callback.answer("Жалоба отправлена")
                return callback.answer("Нужно отвечать на сообщение из диалога")
    return callback.answer("Вы должны ответить на сообщение с нарушением этой коммандой")


@dp.callback_query(F.data.contains("ban_user"))
@flags.authorization(is_authorized=True)
async def ban_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split(" ")[1])
    async with aiosqlite.connect("server.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO bans_anon_chat (user_id) VALUES (?)",
                (user_id, )
            )
            await db.commit()
    return callback.answer(
        f"Пользователь ID: {user_id} забанен",
        show_alert=True
    )


@dp.message(Command("unban_user"))
@flags.admin(is_admin=True)
@flags.authorization(is_authorized=True)
async def unban_user(callback: types.CallbackQuery, command: filters.Command):
    if not command.args:
        return callback.answer("Пожалуйста укажите ID пользователя")
    user_id = int(command.args)
    async with aiosqlite.connect("server.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM bans_anon_chat WHERE user_id = (?)",
                (user_id, )
            )
            await db.commit()
    return callback.answer("Пользователь разблокирован")


@dp.pre_checkout_query()
async def on_pre_checkout_query(
    pre_checkout_query: types.PreCheckoutQuery,
):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(message: types.Message):
    if message.successful_payment.invoice_payload == "unban_payment":
        user_id = message.from_user.id
        async with aiosqlite.connect("server.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM bans_anon_chat WHERE user_id = (?)",
                    (user_id, )
                )
                await db.commit()
        return await message.answer(
            "Поздравляем с успешным приобретением разблокиорвки!",
            message_effect_id="5104841245755180586"
        )


@dp.message(Command("leave_chat"))
@flags.authorization(is_authorized=True)
async def leave_chat(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect("server.db") as db:
        async with db.cursor() as cursor:
            if user_ids := await (await cursor.execute(
                "SELECT user1_id, user2_id, id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                (user_id, user_id)
            )).fetchone():
                b_search = types.InlineKeyboardButton(
                    text="🔎 Начать поиск",
                    callback_data=f"search_anonymous_chat"
                )
                row_search = [b_search]
                rows = [row_search]
                markup = InlineKeyboardMarkup(inline_keyboard=rows)
                for i in range(2):
                    if user_ids[i]:
                        await bot.send_message(
                            user_ids[i], 
                            "⛔️ Диалог окончен.",
                            reply_markup=markup
                        )
                await cursor.execute(
                    "DELETE FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                    (user_id, user_id)
                )
        await db.commit()


@dp.message()
async def on_message(message: types.message.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("server.db") as db:
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
                        chat_id
                    )
                else:
                    sent_message = await func.send_message(
                        bot,
                        user_ids[0],
                        message,
                        chat_id
                    )
                await cursor.execute(
                    """INSERT INTO messages
                    (chat_id, user_id, user_message_id, bot_message_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, user_id, message.message_id, sent_message.message_id)
                )
                await db.commit()


@dp.callback_query(F.data == "map")
@flags.authorization(is_authorized=True)
async def main_menu(callback: types.CallbackQuery):
    back = types.InlineKeyboardButton(
        text="Убрать",
        callback_data="delete"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[back]])
    await callback.message.answer_photo(
        photo=map_photo,
        caption='🗺️ Карта мини-городка БНТУ',
        reply_markup=markup
    )
    await callback.answer()


@dp.callback_query(F.data == "passes")
@flags.authorization(is_authorized=True)
async def passes_button(callback: types.CallbackQuery):
    rows = []
    for i in list(passes):
        b = types.InlineKeyboardButton(
            text=i,
            callback_data=f"get_passes {i}"
        )
        rows.append([b])
    back = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="main_menu"
    )
    rows.append([back])
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_caption(
        caption='📗 Выберите нужный Вам предмет:',
        reply_markup=markup
    )


@dp.callback_query(F.data.split()[0] == "get_passes")
@flags.authorization(is_authorized=True)
async def pass_button(callback: types.CallbackQuery):
    text = f"{callback.data.split()[1]} | "+passes[callback.data.split()[1]]
    back = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="passes"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[back]])
    await callback.message.edit_caption(
        caption=text,
        reply_markup=markup, parse_mode="HTML"
    )


@dp.callback_query(F.data == "schedule")
@flags.authorization(is_authorized=True)
async def schedule(callback: types.CallbackQuery):
    b_together = types.InlineKeyboardButton(
        text="Сегодня",
        callback_data="send_schedule together"
    )
    b_tomorrow = types.InlineKeyboardButton(
        text="Завтра",
        callback_data="send_schedule tomorrow"
    )
    row_days = [b_together, b_tomorrow]
    b_next_week = types.InlineKeyboardButton(
        text="След. неделя",
        callback_data="send_schedule next_week"
    )
    b_this_week = types.InlineKeyboardButton(
        text="Эта неделя",
        callback_data="send_schedule week"
    )
    row_weeks = [b_this_week, b_next_week]
    back = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="main_menu"
    )
    row_back = [back]
    rows = [row_days, row_weeks, row_back]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await callback.message.edit_caption(
            caption='📚 Выберите нужное Вам расписание занятий:',
            reply_markup=markup
            )
    # specify your exceptions
    except Exception:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=main_menu_image,
            caption='📚 Выберите нужное Вам расписание занятий:',
            reply_markup=markup
        )


@dp.callback_query(F.data.split()[0] == "send_schedule")
@flags.authorization(is_authorized=True)
async def schedule(callback: types.CallbackQuery):
    async with aiosqlite.connect("server.db") as db:
        async with db.cursor() as cursor:
            student_code = (await (await cursor.execute(
                "SELECT student_code FROM users WHERE id = (?)",
                (callback.from_user.id, )
            )).fetchone())[0]
    group = student_code[:-2]
    with open(f"schedules/schedule_{group}.json", "r", encoding='utf8') as jsonfile:
        schedule_base = json.load(jsonfile)['Schedule']
    if callback.data.split()[1] == 'week':
        date = get_week_and_day()
        week, day = date
        back = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="schedule"
        )
        row = [back]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        for i in schedule_base[week]:
            text += f"\n{i}:\n"
            for j in schedule_base[week][i]:
                text += f'<blockquote>{j["Time"]} | {j["Matter"]}\n{j["Frame"]} корп., {j["Classroom"]} аудит.\n{j["Teacher"]}</blockquote>\n'
        await callback.message.delete()
        await callback.message.answer(
            f'{text}',
            reply_markup=markup, parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'next_week':
        date = get_week_and_day()
        week, day = date
        reversing_list = [1, 0]
        week = reversing_list[week]
        back = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="schedule"
        )
        row = [back]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        for i in schedule_base[week]:
            text += f"\n{i}:\n"
            for j in schedule_base[week][i]:
                text += f'<blockquote>{j["Time"]} | {j["Matter"]}\n{j["Frame"]} корп., {j["Classroom"]} аудит.\n{j["Teacher"]}</blockquote>\n'
        await callback.message.delete()
        await callback.message.answer(
            f'{text}',
            reply_markup=markup, parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'together':
        date = get_week_and_day()
        week, day = date
        back = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="schedule"
        )
        row = [back]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        try:
            for i in schedule_base[week][day]:
                text += f'<blockquote>{i["Time"]} | {i["Matter"]}\n{i["Frame"]} корп., {i["Classroom"]} аудит.\n{i["Teacher"]}</blockquote>\n'
        except KeyError:
            text += "Занятий нет 🎉"
        await callback.message.delete()
        await callback.message.answer(
            f'{day}:\n{text}',
            reply_markup=markup, parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'tomorrow':
        date = get_tomorrow_week_and_day()
        week, day = date
        back = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="schedule"
        )
        row = [back]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        try:
            for i in schedule_base[week][day]:
                text += f'<blockquote>{i["Time"]} | {i["Matter"]}\n{i["Frame"]} корп., {i["Classroom"]} аудит.\n{i["Teacher"]}</blockquote>\n'
        except KeyError:
            text += "Занятий нет 🎉"
        await callback.message.delete()
        await callback.message.answer(
            f'{day}:\n{text}',
            reply_markup=markup, parse_mode="HTML"
        )


@dp.callback_query(F.data == "delete")
async def delete(callback: types.CallbackQuery):
    await callback.message.delete()


@dp.callback_query(F.data.split()[0] == "help")
@flags.authorization(is_authorized=True)
async def help(callback: types.CallbackQuery):
    back = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="main_menu"
    )
    row_back = [back]
    b_privacy = types.InlineKeyboardButton(
        text="Политика конфиденциальности",
        url=f"https://telegra.ph/Politika-konfidencialnosti-09-08-51"
    )
    row_privacy = [b_privacy]
    rows = [row_back, row_privacy]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.delete()
    await callback.message.answer(
        f'Если у Вас есть предложения, идеи или Вы нашли баг, то можете соообщить об этом, мы постараемся как можно быстрее ответить на Ваше сообщение.\n\nОбращаться по юзернейму {user_admin}',
        reply_markup=markup
    )


async def main():
    async with aiosqlite.connect('server.db') as db:
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

        await db.commit()
    me = await bot.get_me()
    print(f'@{me.username} ({me.first_name})')
    dp.message.middleware(middleware.AuthorizationMiddleware())
    dp.callback_query.middleware(middleware.AuthorizationMiddleware())
    dp.message.middleware(middleware.BanMiddleware())
    dp.callback_query.middleware(middleware.BanMiddleware())
    dp.message.middleware(middleware.AdminMiddleware())
    dp.callback_query.middleware(middleware.AdminMiddleware())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
