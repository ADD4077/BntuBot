from aiogram import Router, F, flags
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
)
from aiogram.filters.command import Command
from aiogram import filters
from aiogram.exceptions import TelegramForbiddenError
import multiprocessing
import aiosqlite
import datetime
import json
import pytz
import os
from util.config import server_db_path
from util import keyboards
from util import states
from util import func


dp = Router()


with open("./books/literature.json", "r", encoding="utf8") as jsonfile:
    literature = json.load(jsonfile)


async def admin_panel(message, state=None):
    if state:
        await state.clear()
    is_callback = isinstance(message, CallbackQuery)
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
async def admin_panel_by_message(message: Message, state: FSMContext):
    await admin_panel(message, state)


@dp.callback_query(F.data.contains("admin_panel"))
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_panel_by_callback(callback: CallbackQuery, state: FSMContext):
    await admin_panel(callback, state)


@dp.callback_query(F.data.split()[0] == "admin_search")
@flags.owner(is_owner=True)
@flags.studcouncil_member(is_member=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_search(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите способ поиска:",
        reply_markup=keyboards.admin_panel_menu_search(),
    )


@dp.callback_query(F.data == "search_user")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_user(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите способ поиска пользователя:",
        reply_markup=keyboards.search_user_buttons(),
    )


@dp.callback_query(F.data == "search_by_user_id")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_user_id(callback: CallbackQuery, state: FSMContext):
    await state.set_state(states.InputUserID.InputByUserID)
    await callback.message.edit_text("Отправьте Telegram ID пользователя")


@dp.callback_query(F.data == "search_by_group_number")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_group_number(callback: CallbackQuery, state: FSMContext):
    await state.set_state(states.InputUserID.InputByGroupNumber)
    await callback.message.edit_text(
        "Отправьте номер студенческого билета пользователя"
    )


@dp.message(states.InputUserID.InputByUserID)
async def input_user_id(message: Message, state: FSMContext):
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
async def send_message_for_user(callback: CallbackQuery, state: FSMContext):
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
async def send_message_for_group(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"Отправьте сообщение, которое хотите отправить группе {callback.data.split()[1]}"
    )
    await state.set_state(states.InputMessageForGroup.group_id)
    await state.update_data(group_id=int(callback.data.split()[1]))
    await state.set_state(states.InputMessageForGroup.message)


@dp.message(states.InputMessageForGroup.message)
async def input_send_message_for_group(message: Message, state: FSMContext):
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
            await message.bot.send_message(
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
async def input_send_message_for_user(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    await state.clear()
    try:
        await message.bot.send_message(
            chat_id=user_id, text=f"Сообщение от администратора:\n{message.text}"
        )
    except TelegramForbiddenError as e:
        if "bot was blocked by the user" in str(e):
            return await message.answer("Пользователь заблокировал бота.")
    await message.answer("Сообщение отправлено пользователю!")


@dp.message(states.InputUserID.InputByGroupNumber)
async def input_group_number(message: Message, state: FSMContext):
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
async def search_group_input(callback: CallbackQuery, state: FSMContext):
    await state.set_state(states.InputGroupNumber.userInput)
    return await callback.message.edit_text(
        "Отправьте номер группы:", reply_markup=keyboards.back_to_admin_panel()
    )


@dp.message(states.InputGroupNumber.userInput)
async def search_group(message: Message):
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
        [f"{i + 1}. {info[2]} (ID: {info[0]})" for i, info in enumerate(response)]
    )
    await message.answer(
        text, reply_markup=keyboards.control_group_buttons(group_number)
    )


@dp.callback_query(F.data == "search_faculty")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_faculty_input(callback: CallbackQuery):
    await callback.message.edit_text(
        "Искать пользователей из факультета:",
        reply_markup=keyboards.search_faculty_buttons(),
    )


@dp.callback_query(F.data == "search_by_faculty_abbr")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_faculty_abbr(callback: CallbackQuery, state: FSMContext):
    await state.set_state(states.InputFaculty.InputByLetters)
    await callback.message.edit_text(
        "Введите аббревиатуру факультета:", reply_markup=keyboards.back_to_admin_panel()
    )


@dp.callback_query(F.data == "search_by_faculty_number")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def search_by_faculty_number(callback: CallbackQuery, state: FSMContext):
    await state.set_state(states.InputFaculty.InputByNumbers)
    return await callback.message.edit_text(
        "Введите номер факультета:", reply_markup=keyboards.back_to_admin_panel()
    )


@dp.message(states.InputFaculty.InputByLetters)
async def input_faculty_abbr(message: Message, state: FSMContext):
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
async def input_faculty_numbers(message: Message, state: FSMContext):
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
async def admin_schedule(callback: CallbackQuery):
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
        reply_markup=keyboards.literature_and_schedule_admin_buttons("schedule"),
    )


@dp.callback_query(F.data == "admin_literature")
@flags.owner(is_owner=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def admin_literature(callback: CallbackQuery):
    modification_time = datetime.datetime.fromtimestamp(
        os.path.getmtime("./books/literature.json"), pytz.timezone("Europe/Moscow")
    ).strftime("%d.%m.%Y %H:%M:%S")
    count = 0
    for _, books in literature.items():
        count += int(books["count"][1:-1])
    await callback.message.edit_text(
        f"Последнее изменение литературы: {modification_time}\nКол-во книг: {count}",
        reply_markup=keyboards.literature_and_schedule_admin_buttons("literature"),
    )


@dp.callback_query(F.data.startswith("parse"))
async def parse(callback: CallbackQuery):
    if "confirmed" not in callback.data:
        return callback.message.edit_text(
            "Подтвердите действие.",
            reply_markup=keyboards.literature_and_schedule_admin_buttons(
                f"{callback.data.split(' ')[1]} confirmed"
            ),
        )
    if callback.data.split(" ")[1] == "schedule":
        await callback.message.edit_text(
            "Парсинг начался.", reply_markup=keyboards.back_to_admin_panel()
        )
        multiprocessing.Process(target=func.parse_schedule).start()
    elif callback.data.split(" ")[1] == "literature":
        await callback.message.edit_text(
            "Парсинг начался.", reply_markup=keyboards.back_to_admin_panel()
        )
        multiprocessing.Process(target=func.parse_literature)
    else:
        raise NotImplementedError("Unknown data to parse.")


@dp.callback_query(F.data.contains("ban_user"))
@flags.owner(is_owner=True)
@flags.moderator(is_moderator=True)
@flags.permissions(any_permission=True)
@flags.authorization(is_authorized=True)
async def button_ban_user(callback: CallbackQuery):
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
