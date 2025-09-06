import asyncio
import random, string, os, time, pytz
from datetime import datetime, timedelta
import sqlite3

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardMarkup

def get_week_and_day(today=None):
    if today is None:
        today = datetime.now().date()
    else:
        # если передан datetime, берем только дату
        if isinstance(today, datetime):
            today = today.date()
    start_date = datetime(today.year, 9, 1).date()
    # Если сегодня до 1 сентября, считаем, что отсчет с прошлого года
    if today < start_date:
        start_date = datetime(today.year - 1, 9, 1).date()
    # Количество дней с 1 сентября
    delta_days = (today - start_date).days
    # День недели: 0 - понедельник, 6 - воскресенье
    day_of_week_index = delta_days % 7
    # Номер недели: 1 или 2, меняется каждые 7 дней
    week_number = (delta_days // 7) % 2 + 1
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days[day_of_week_index]
    return week_number, day_name

def get_tomorrow_week_and_day(today=None):
    if today is None:
        today = datetime.now().date()
    else:
        if isinstance(today, datetime):
            today = today.date()
    
    tomorrow = today + timedelta(days=1)
    return get_week_and_day(tomorrow)

API_TOKEN = ''

main_menu_image = 'https://static.bntu.by/bntu/new/news/image_13225_e6c8ac4f2985830042f63740a43d1fdc.JPG'
example_photo = 'https://io.sb.by/storage01/iblock/f10/f10acc96303e9a3a20bc90ee0f118de1.jpg'
map_photo = 'https://bntu.by/storage/uploads/content/1580719298.jpg'

user_admin = '@'
id_admin = 1
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
tz = pytz.timezone("Europe/Moscow")

connection = sqlite3.connect(f'server.db')
cursor = connection.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users(
        id INT,
        FIO TEXT,
        fac TEXT,
        student_code INT,
        bilet_code INT
    )""")

schedule_base = {
    1:{
        "Понедельник": [
            "08:30 | Производственное обучение\n6 часов, 1/2 группы\n20 корпус, 301/303 аудитории\nст.пр. Астапчик Н.И.",
            "14:15 | (лаб.) Информатика\n1/2 группы\n20 корпус, 301/303 аудитории\nасс. Коваленко Э.В."
        ],
        "Вторник": [
            "08:00 | Информатика\n1 корпус, 450 аудитория\nпр. Михасик Е.И.",
            "10:25 | Физ. культура"
        ],
        "Среда": [
            "08:00 | (лаб.) Физика\n1/2 группы\n17 корпус, 401/412 аудитории",
            "09:55 | (лаб.) Физика\n1/2 группы\n17 корпус, 401/412 аудитории",
            "11:40 | (лаб.) Химия\n1/2 группы\n11 корпус, 506/510 аудитории\nдоц. Бурак Г.А.",
            "13:55 | (практ.) Математика\n17 корпус, 506 аудитория\nст.пр. Юхновская О.В."
        ],
        "Четверг": [
            "08:00 | Английский язык\n1/2 группы\n1 корпус, 432 аудитория\nст.пр. Здоронок Ю.А.",
            "09:55 | (практ.) Инженерная графика\n8 корпус, 518 аудитория",
            "11:40 | Физика\n17 корпус, ЗП\nпроф. Свирина Л.П.",
            "13:55 | Математика\n17 корпус, ЗП"
        ],
        "Пятница": [
            "10:25 | Физ. культура",
            "12:10 | Материаловедение\n20 корпус, 601 аудитория\nпр. Михасик Е.И.",
            "14:15 | (лаб.) Материаловедение\n1/2 группы\n20 корпус, 606 аудитория\nпр. Михасик Е.И."
        ],
        "Суббота": [
            "09:55 | Химия\n11 корпус, 507 аудитория\nдоц. Бурак Г.А.",
            "11:40 | Инженерная графика\n11 корпус, 507 аудитория\nст.пр. Хмельницкая Л.В."
        ]
    },
    2:{
        "Понедельник": [
            "08:30 | Производственное обучение\n6 часов, 1/2 группы\n20 корпус, 301/303 аудитории\nст.пр. Астапчик Н.И.",
            "14:15 | (лаб.) Информатика\n1/2 группы\n20 корпус, 301/303 аудитории\nасс. Коваленко Э.В."
        ],
        "Вторник": [
            "08:30 | Введение в инженерное образование\n20 корпус, 601 аудитория\nст.пр. Игнаткович И.В.",
            "10:25 | Физическая культура\nст.пр. Анципорович Н.П., Миклашевич Е.Ю.",
            "12:10 | Кураторский час\n20 корпус, 211 аудитория\nдоц. Евтухова Т.Е."
        ],
        "Среда": [
            "08:00 | (практ.) Инженерная графика\n8 корпус, 519 аудитория",
            "09:55 | (практ.) Английский язык, 1/2 группы\n1 корпус, 432 аудитория\nпр. Передня Н.И.",
            "09:55 | (практ.) Английский язык, 1/2 группы\n1 корпус, 440 аудитория\nст.пр. Здоронок Ю.А.",
            "11:40 | (лаб.) Химия, 1/2 группы\n11 корпус, 506 аудитория\nдоц. Бурак Г.А.",
            "11:40 | (лаб.) Химия, 1/2 группы\n11 корпус, 510 аудитория\nдоц. Бурак Г.А.",
            "13:55 | (практ.) Математика\n17 корпус, 506 аудитория\nст.пр. Юхновская О.В."
        ],
        "Четверг": [
            "09:55 | (лаб.) Физика\n17 корпус, 507 аудитория\nпроф. Свирина Л.П.",
            "11:40 | Физика\n17 корпус, ЗП\nпроф. Свирина Л.П.",
            "13:55 | (практ.) Английский язык, 1/2 группы\n1 корпус, 432 аудитория\nст.пр. Здоронок Ю.А.",
            "13:55 | (практ.) Английский язык, 1/2 группы\n1 корпус, 440 аудитория\nпр. Передня Н.И.",
            "15:40 | (практ.) Английский язык, 1/2 группы\n1 корпус, 440 аудитория\nпр. Передня Н.И."
        ],
        "Пятница": [
            "08:00 | Математика\n17 корпус, 2П",
            "10:25 | Физическая культура\nст.пр. Анципорович Н.П., Миклашевич Е.Ю.",
            "12:10 | Материаловедение\n20 корпус, 601 аудитория\nпр. Михасик Е.И.",
            "14:15 | (лаб.) Материаловедение, 1/2 группы\n20 корпус, 606 аудитория\nпр. Михасик Е.И."
        ],
        "Суббота": [
            "09:55 | Химия\n11 корпус, 507 аудитория\nдоц. Бурак Г.А.",
            "11:40 | Инженерная графика\n11 корпус, 507 аудитория\nст.пр. Хмельницкая Л.В."
        ]
        }
    }

passes = {
    'Информатика':'Михасик Евгений Игоревич\n\nТребования:\n<blockquote>1. Конспект\n2. Все лабораторные\n3. Реферат</blockquote>\n\nПлан реферата:\n<blockquote>Введение\nСодержание\n3 главы\nЗаключение\nСписок литературы</blockquote>\n\nТребования к реферату:\n<blockquote>Срок сдачи - 1 декабря\nдо 10 страниц\nTimes New Roman 14\n18 пунктов межстрочный интервал\nОтступ 1,25 см\nНумерация снизу по центру \nминимум 1 рисунок и 1 таблица\nОформление по ширине страницы</blockquote>',
    'Английский':'Здоронок И.А.\n\nТребования:\n<blockquote>1. Посещение всех занятий\n2. Сохранять листы работ для макулатуры\n3. Удовлетворительное поведение</blockquote>',
    'Математика':'Юхновская О.В.\n\nТребования:\n<blockquote>1. Посещение всех занятий\n2. Конспект</blockquote>\n\nПримечания:\n<blockquote>Можно пропустить 1 пару по неуважительной причине\nЗа каждую пропущенную пару на сессии будет даваться дополнительный вопрос</blockquote>',
    'Химия':'Бурак Г.А.\n\nТребования:\n<blockquote>1. Посещение всех занятий\n2. Конспект\n3. Написание всех лабораторных\n4. Минимум 6 баллов</blockquote>\n\nПримечания:\n<blockquote>Даже при отсутствии на лабораторных по уважительной причине, нужно договориться о том, чтобы переписать.\nДомашнее - 2 балла\nA часть - 2 балла\nB часть - 4 балла\nПрактическая - 2 балла\nТакже помимо заданий A и B части можно взять дополнительные задания C части для повышения балла</blockquote>'
}

async def auth_send(message):
    auth = types.InlineKeyboardButton(
        text="Авторизоваться",
        callback_data=f"auth"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[auth]])
    await bot.send_message(
        message.from_user.id,
        f'Привет, @{message.from_user.username}!, чтобы использовать бота, нужно авторизоваться c помощью студенческого билета. Для этого нажмите кнопку "Авторизация".',
        reply_markup=markup
    )

class Form(StatesGroup):
    photo = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    if cursor.execute(f"SELECT id FROM users WHERE id = {message.from_user.id}").fetchone() is None:
        await bot.send_message(
            id_admin,
            f"Новый пользователь @{message.from_user.username} ({message.from_user.full_name})."
        )
        await auth_send(message)
        return
    b_schedule = types.InlineKeyboardButton(
        text="Расписание",
        callback_data=f"schedule"
    )
    b_pass = types.InlineKeyboardButton(
        text="Зачёты",
        callback_data=f"passes"
    )
    row_lessons = [b_schedule, b_pass]
    b_litter = types.InlineKeyboardButton(
        text="Литература",
        callback_data=f"litterature"
    )
    row_lit = [b_litter]
    b_map = types.InlineKeyboardButton(
        text="Карта",
        callback_data=f"map"
    )
    b_site = types.InlineKeyboardButton(
        text="Сайт БНТУ",
        url=f"https://bntu.by"
    )
    row_site = [b_map, b_site]
    b_help = types.InlineKeyboardButton(
        text="Поддержка",
        callback_data=f"help"
    )
    row_help = [b_help]
    rows = [row_lessons, row_lit, row_site, row_help]
    main_menu_markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer_photo(
            photo = main_menu_image,
            caption = f"Рады вас видеть, @{message.from_user.username}!\n\nЭто БОТ инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\nБот может показать Вам расписание или требования для автомата по разным предметам.\n\n— Быстро\n— Надёжно\n— Проверено",
            reply_markup=main_menu_markup
        )

@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    if cursor.execute(f"SELECT id FROM users WHERE id = {callback.from_user.id}").fetchone() is None:
        await auth_send(callback)
        return
    b_schedule = types.InlineKeyboardButton(
        text="Расписание",
        callback_data=f"schedule"
    )
    b_pass = types.InlineKeyboardButton(
        text="Зачёты",
        callback_data=f"passes"
    )
    row_lessons = [b_schedule, b_pass]
    b_litter = types.InlineKeyboardButton(
        text="Литература",
        callback_data=f"litterature"
    )
    row_lit = [b_litter]
    b_map = types.InlineKeyboardButton(
        text="Карта",
        callback_data=f"map"
    )
    b_site = types.InlineKeyboardButton(
        text="Сайт БНТУ",
        url=f"https://bntu.by"
    )
    row_site = [b_map, b_site]
    b_help = types.InlineKeyboardButton(
        text="Поддержка",
        callback_data=f"help"
    )
    row_help = [b_help]
    rows = [row_lessons, row_lit, row_site, row_help]
    main_menu_markup = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await callback.message.edit_caption(
            photo = main_menu_image,
            caption=f"Рады вас видеть, @{callback.from_user.username}!\n\nЭто БОТ инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\nБот может показать Вам расписание или требования для автомата по разным предметам.\n\n— Быстро\n— Надёжно\n— Проверено",
            reply_markup=main_menu_markup
        )
    except:
        await callback.message.delete()
        await callback.message.answer_photo(
                photo = main_menu_image,
                caption = f"Рады вас видеть, @{callback.from_user.username}!\n\nЭто БОТ инженерно-педагогического факультета, группы прикладного программирования, в котором Вы сможете найти полезную информацию.\n\nБот может показать Вам расписание или требования для автомата по разным предметам.\n\n— Быстро\n— Надёжно\n— Проверено",
                reply_markup=main_menu_markup
            )

@dp.callback_query(F.data == "auth")
async def auth_begin(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer_photo(
        photo = example_photo,
        caption = f"Отправьте фото Вашего студенческого билета, чтобы мы могли убедиться в том, что Вы являетесь нашим студентом. Фото должно быть чётким, в хорошем освещении и без бликов.",
    )
    await state.set_state(Form.photo)

@dp.message(Form.photo)
async def auth_end(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте именно фото.")
        return
    b = types.InlineKeyboardButton(
        text="Авторизовать",
        callback_data=f"accept_auth {message.from_user.id}"
    )
    row = [b]
    b2 = types.InlineKeyboardButton(
        text="Отклонить",
        callback_data=f"decline_auth"
    )
    row2 = [b2]
    rows = [row, row2]
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

class AcceptAuthForm(StatesGroup):
    id = State()
    text = State()

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
    fac = message.text.split(',')[1]
    student_code = int(message.text.split(', ')[2])
    bilet_code = int(message.text.split(', ')[3])
    print([fio,fac,student_code,bilet_code])
    if cursor.execute(f"SELECT id FROM users WHERE id = {id}").fetchone() is not None:
        await message.answer("Уже есть в базе данных.")
        return
    cursor.execute(f"INSERT INTO users VALUES ({id}, '{fio}','{fac}', {student_code}, {bilet_code})")
    connection.commit()
    await message.answer("Пользователь был успешно авторизован.")
    await bot.send_message(
        id, f'{fio.split()[1]}, авторизация была подтверждена, теперь Вы подтвержденный студент БНТУ! Вы можете вызвать главное меню командой /start'
    )

@dp.callback_query(F.data == "map")
async def main_menu(callback: types.CallbackQuery):
    if cursor.execute(f"SELECT id FROM users WHERE id = {callback.from_user.id}").fetchone() is None:
        await auth_send(callback)
        return
    nazad = types.InlineKeyboardButton(
        text="Убрать",
        callback_data=f"delete"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[nazad]])
    await callback.message.answer_photo(
        photo=map_photo,
        caption=f'Карта мини-городка БНТУ.',
        reply_markup=markup
    )
    await callback.answer()

@dp.callback_query(F.data == "passes")
async def passes_button(callback: types.CallbackQuery):
    if cursor.execute(f"SELECT id FROM users WHERE id = {callback.from_user.id}").fetchone() is None:
        await auth_send(callback)
        return
    rows = []
    for i in list(passes):
        b = types.InlineKeyboardButton(
            text=i,
            callback_data=f"get_passes {i}"
        )
        rows.append([b])
    nazad = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=f"main_menu"
    )
    rows.append([nazad])
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.edit_caption(
        caption=f'Выберите нужный Вам предмет:',
        reply_markup=markup
    )

@dp.callback_query(F.data.split()[0] == "get_passes")
async def passes_button(callback: types.CallbackQuery):
    if cursor.execute(f"SELECT id FROM users WHERE id = {callback.from_user.id}").fetchone() is None:
        await auth_send(callback)
        return
    text = f"{callback.data.split()[1]} | "+passes[callback.data.split()[1]]
    nazad = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=f"passes"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[nazad]])
    await callback.message.edit_caption(
        caption=text,
        reply_markup=markup, parse_mode="HTML"
    )

@dp.callback_query(F.data == "schedule")
async def schedule(callback: types.CallbackQuery):
    if cursor.execute(f"SELECT id FROM users WHERE id = {callback.from_user.id}").fetchone() is None:
        await auth_send(callback)
        return
    b = types.InlineKeyboardButton(
        text="След. неделя",
        callback_data=f"send_schedule next_week"
    )
    b0 = types.InlineKeyboardButton(
        text="Эта неделя",
        callback_data=f"send_schedule week"
    )
    row1 = [b, b0]
    b1 = types.InlineKeyboardButton(
        text="Сегодня",
        callback_data=f"send_schedule together"
    )
    b2 = types.InlineKeyboardButton(
        text="Завтра",
        callback_data=f"send_schedule tomorrow"
    )
    row = [b1,b2]
    nazad = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=f"main_menu"
    )
    row2 = [nazad]
    rows = [row, row1, row2]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await callback.message.edit_caption(
            caption=f'Выберите нужное Вам расписание занятий:',
            reply_markup=markup
            )
    except:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo = main_menu_image,
            caption = f'Выберите нужное Вам расписание занятий:',
            reply_markup=markup
        )

@dp.callback_query(F.data.split()[0] == "send_schedule")
async def schedule(callback: types.CallbackQuery):
    if cursor.execute(f"SELECT id FROM users WHERE id = {callback.from_user.id}").fetchone() is None:
        await auth_send(callback)
        return
    if callback.data.split()[1] == 'week':
        week, day = get_week_and_day()
        nazad = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"schedule"
        )
        row = [nazad]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        for i in list(schedule_base[week]):
            text += f"\n{i}:\n"
            for j in schedule_base[week][i]:
                text += f"<blockquote>{j}</blockquote>\n"
        await callback.message.delete()
        await callback.message.answer(
            f'{text}',
            reply_markup=markup, parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'next_week':
        week, day = get_week_and_day()
        if week == 1:
            week = 2
        else:
            week = 1
        nazad = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"schedule"
        )
        row = [nazad]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        for i in list(schedule_base[week]):
            text += f"\n{i}:\n"
            for j in schedule_base[week][i]:
                text += f"<blockquote>{j}</blockquote>\n"
        await callback.message.delete()
        await callback.message.answer(
            f'{text}',
            reply_markup=markup, parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'together':
        week, day = get_week_and_day()
        nazad = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"schedule"
        )
        row = [nazad]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        for i in list(schedule_base[week][day]):
            text += f"<blockquote>{i}</blockquote>\n"
        await callback.message.delete()
        await callback.message.answer(
            f'{day}:\n{text}',
            reply_markup=markup, parse_mode="HTML"
        )
    elif callback.data.split()[1] == 'tomorrow':
        week, day = get_tomorrow_week_and_day()
        nazad = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"schedule"
        )
        row = [nazad]
        rows = [row]
        markup = InlineKeyboardMarkup(inline_keyboard=rows)
        text = ''
        for i in list(schedule_base[week][day]):
            text += f"<blockquote>{i}</blockquote>\n"
        await callback.message.delete()
        await callback.message.answer(
            f'{day}:\n{text}',
            reply_markup=markup, parse_mode="HTML"
        )

@dp.callback_query(F.data == "delete")
async def delete(callback: types.CallbackQuery):
    await callback.message.delete()

@dp.callback_query(F.data.split()[0] == "help")
async def help(callback: types.CallbackQuery):
    if cursor.execute(f"SELECT id FROM users WHERE id = {callback.from_user.id}").fetchone() is None:
        await auth_send(callback)
        return
    nazad = types.InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=f"main_menu"
    )
    row = [nazad]
    rows = [row]
    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback.message.delete()
    await callback.message.answer(
        f'Если у Вас есть предложения, идеи или Вы нашли баг, то можете соообщить об этом, мы постараемся как можно быстрее ответить на Ваше сообщение.\n\nОбращаться по юзернейму {user_admin}',
        reply_markup=markup
    )

async def main():
    me = await bot.get_me()
    print(f'@{me.username} ({me.first_name})')
    await dp.start_polling(bot)

asyncio.run(main())

