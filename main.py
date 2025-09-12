import os
import pytz
import asyncio
import aiosqlite
import json
import hashlib

from aiogram.fsm.context import FSMContext
from aiogram import Bot, Dispatcher, types, flags
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
from middleware import AuthorizationMiddleware

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


@dp.message(Command("start"))
@flags.authorization(is_authorized=True)
async def start(message: types.Message):
    b_schedule = types.InlineKeyboardButton(
        text="📅 Расписание",
        callback_data="schedule"
    )
    b_pass = types.InlineKeyboardButton(
        text="📌 Зачёты",
        callback_data="passes"
    )
    row_lessons = [b_schedule, b_pass]
    # b_litter = types.InlineKeyboardButton(
    #     text="📜 Литература",
    #     callback_data="litterature"
    # )
    # row_lit = [b_litter]
    b_map = types.InlineKeyboardButton(
        text="🗺️ Карта",
        callback_data="map"
    )
    row_map = [b_map]
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
    b_chat = types.InlineKeyboardButton(
        text="Анонимный чат",
        callback_data="anonymous_chat"
    )
    row_chat = [b_chat]
    rows = [row_lessons, row_map, row_url, row_help, row_chat]
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
    b_pass = types.InlineKeyboardButton(
        text="📌 Зачёты",
        callback_data="passes"
    )
    row_lessons = [b_schedule, b_pass]
    # b_litter = types.InlineKeyboardButton(
    #     text="📜 Литература",
    #     callback_data="litterature"
    # )
    # row_lit = [b_litter]
    b_map = types.InlineKeyboardButton(
        text="🗺️ Карта",
        callback_data="map"
    )
    row_map = [b_map]
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
    b_chat = types.InlineKeyboardButton(
        text="Анонимный чат",
        callback_data="anonymous_chat"
    )
    row_chat = [b_chat]
    rows = [row_lessons, row_map, row_url, row_help, row_chat]
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
    user2_id = callback.from_user.id
    async with aiosqlite.connect("server.db") as db:
        async with db.cursor() as cursor:
            if await (await cursor.execute(
                "SELECT user1_id, user2_id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                (user2_id, user2_id)
            )).fetchone():
                return await bot.send_message(
                    user2_id,
                    "Вы уже в анонимном чате."
                )
            if user1_id := (await (await cursor.execute(
                "SELECT user1_id FROM chats WHERE user2_id IS NULL"
            )).fetchone()):
                user1_id = user1_id[0]
                await cursor.execute(
                    "UPDATE chats SET user2_id=(?) WHERE user1_id=(?)",
                    (user2_id, user1_id)
                )
                print(user2_id)
                print(user1_id)
                await bot.send_message(
                    user2_id,
                    "Собеседник найден."
                )
                await bot.send_message(
                    user1_id,
                    "Собеседник найден."
                )
            else:
                await cursor.execute(
                    "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)",
                    (user2_id, None)
                )
                await bot.send_message(
                    user2_id,
                    "Идет поиск собеседника."
                )
        await db.commit()
    return await callback.answer()


@dp.message(Command("leave_chat"))
@flags.authorization(is_authorized=True)
async def leave_chat(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with aiosqlite.connect("server.db") as db:
        async with db.cursor() as cursor:
            if user_ids := await (await cursor.execute(
                "SELECT user1_id, user2_id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                (user_id, user_id)
            )).fetchone():
                for user_id_ in user_ids:
                    if user_id_:
                        await bot.send_message(user_id_, "Диалог окончен.")
                await cursor.execute(
                    "DELETE FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                    (user_id, user_id)
                )
        await db.commit()
    return await callback.answer()


@dp.message()
async def on_message(message: types.message.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("server.db") as db:
        async with db.cursor() as cursor:
            if user_ids := await (await cursor.execute(
                "SELECT user1_id, user2_id FROM chats WHERE user1_id = (?) OR user2_id = (?)",
                (user_id, user_id)
            )).fetchone():
                if user_ids[1] is None:
                    return
                if user_ids[0] == user_id:
                    print(message.photo)
                    return await func.send_message(
                        bot,
                        user_ids[1],
                        message
                    )
                else:
                    return await func.send_message(
                        bot,
                        user_ids[0],
                        message
                    )


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

        await db.commit()
    me = await bot.get_me()
    print(f'@{me.username} ({me.first_name})')
    dp.message.middleware(AuthorizationMiddleware())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
