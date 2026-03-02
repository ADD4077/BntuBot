from aiogram import Router, F, flags
from aiogram.types import CallbackQuery
import aiosqlite
import os
from util.config import server_db_path
from util import keyboards
from util import func


schedule_image = os.getenv("SCHEDULE_IMAGE")


dp = Router()


@dp.callback_query(F.data == "schedule")
@flags.authorization(is_authorized=True)
async def schedule(callback: CallbackQuery):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=schedule_image,
        caption="📚 Выберите нужное Вам расписание занятий:",
        reply_markup=keyboards.schedule_menu(),
    )


@dp.callback_query(F.data == "return_schedule")
@flags.authorization(is_authorized=True)
async def return_schedule(callback: CallbackQuery):
    await callback.message.edit_caption(
        caption="📚 Выберите нужное Вам расписание занятий:",
        reply_markup=keyboards.schedule_menu(),
    )


@dp.callback_query(F.data.split()[0] == "send_schedule")
@flags.authorization(is_authorized=True)
async def send_schedule(callback: CallbackQuery):
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
async def schedule_week(callback: CallbackQuery):
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
    date = func.get_week_and_day()
    week, _ = date
    if callback.data.split()[2] == "next_week":
        week = [1, 0][week]
    day = callback.data.split()[1]
    await callback.message.edit_caption(
        caption=f"🗞 {day}:\n{func.get_schedule(group, week, day)}",
        reply_markup=keyboards.schedule_menu_other(callback.data.split()[2]),
        parse_mode="HTML",
    )
