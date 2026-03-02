from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import aiosqlite
import hashlib
import os
from util.config import server_db_path
from util import keyboards
from util import states
from util import func


example_photo = os.getenv("EXAMPLE_IMAGE")
id_owner = int(os.getenv("ID_OWNER"))


dp = Router()


@dp.callback_query(F.data == "auto_auth")
async def auto_auth_begin(callback: CallbackQuery, state: FSMContext):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer(
        "Отправьте текстом номер Вашего студенческого билета (чёрный). Без пробелов, лишних символов, запятых и т.д.",
    )
    await state.set_state(states.AutoAuth.student_code)


@dp.message(states.AutoAuth.student_code)
async def auto_auth_student_code(message: Message, state: FSMContext):
    await message.answer(
        "Отлично! Теперь также отправьте красный номер на студенческом.",
    )
    await state.update_data(student_code=message.text)
    await state.set_state(states.AutoAuth.code)


@dp.message(states.AutoAuth.code)
async def auto_auth_end(message: Message, state: FSMContext):
    data = await state.get_data()
    student_code = data.get("student_code")
    await state.clear()
    code = message.text
    auth_status = await func.authorize(student_code, code)
    if auth_status == -1:
        b_auth = InlineKeyboardButton(text="🔐 Вручную", callback_data="support_auth")
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
        await message.bot.send_message(
            id_owner,
            f"✅ Пользователь автоматически авторизован @{message.from_user.username} ({message.from_user.full_name}).",
        )


@dp.callback_query(F.data == "support_auth")
async def auth_begin(callback: CallbackQuery, state: FSMContext):
    if await func.safe_delete(callback) is None:
        return
    await callback.message.answer_photo(
        photo=example_photo,
        caption="📷 Отправьте фото Вашего студенческого билета, чтобы мы могли убедиться в том, что Вы являетесь нашим студентом. Фото должно быть чётким, в хорошем освещении и без бликов.",
    )
    await state.set_state(states.Form.photo)


@dp.message(states.Form.photo)
async def auth_end(message: Message, state: FSMContext):
    if not message.photo:
        return await message.answer("Пожалуйста, отправьте именно фото.")
    photo = message.photo[-1]
    await message.bot.send_photo(
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
async def accept_auth(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption="Введите данные через запятую: ФИО, Факультет, Код студента (черный), Код билета (красный)."
    )
    await state.set_state(states.AcceptAuthForm.id)
    await state.update_data(id=int(callback.data.split()[1]))
    await state.set_state(states.AcceptAuthForm.text)


@dp.message(states.AcceptAuthForm.text)
async def accept_auth_2(message: Message, state: FSMContext):
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
    await message.bot.send_message(
        id,
        f"✅ {fio.split()[1]}, авторизация была подтверждена, теперь Вы подтвержденный студент БНТУ! Вы можете вызвать главное меню командой /start",
    )
