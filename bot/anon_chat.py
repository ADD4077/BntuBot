from aiogram import Router, F, flags
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    MessageReactionUpdated,
    PreCheckoutQuery,
)
from aiogram.filters.command import Command
from aiogram.exceptions import TelegramForbiddenError
import aiosqlite
import os
from util.config import server_db_path
from util import keyboards
from util import states
from util import func


moderators_chat_id = int(os.getenv("MODERATORS_CHAT_ID"))


dp = Router()


@dp.callback_query(F.data == "anonymous_chat")
@flags.authorization(is_authorized=True)
async def anonymous_chat(callback: CallbackQuery):
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
async def search_anonymous_chat(callback: CallbackQuery, state: FSMContext):
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

                try:
                    await callback.bot.send_message(user1_id, "👥 Собеседник найден.")
                except TelegramForbiddenError as e:
                    if "bot was blocked by the user" in str(e):
                        await cursor.execute(
                            "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)",
                            (user2_id, None),
                        )
                        await cursor.execute(
                            "DELETE FROM chats WHERE user1_id = (?)", (user1_id,)
                        )
                        await callback.message.edit_text("🔎 Идет поиск собеседника.")
                else:
                    await callback.message.edit_text("👥 Собеседник найден.")
            else:
                await cursor.execute(
                    "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)",
                    (user2_id, None),
                )
                await callback.message.edit_text("🔎 Идет поиск собеседника.")
        await state.set_state(states.AnonChatState.in_chat)
        await db.commit()


@dp.message(Command("report"))
@flags.authorization(is_authorized=True)
async def report(message: Message):
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
                    await message.bot.send_message(
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


@dp.pre_checkout_query()
async def on_pre_checkout_query(
    pre_checkout_query: PreCheckoutQuery,
):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(message: Message):
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
async def leave_chat(callback: CallbackQuery, state: FSMContext):
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
                        await callback.bot.send_message(
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


@dp.message(states.AnonChatState.in_chat)
@flags.banned(isnt_banned=True)
async def on_message(message: Message, **kwargs):
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
                        message.bot, user_ids[1], message, chat_id, media_group
                    )
                else:
                    sent_message = await func.send_message(
                        message.bot, user_ids[0], message, chat_id, media_group
                    )
                await cursor.execute(
                    """INSERT INTO messages
                    (chat_id, user_id, user_message_id, bot_message_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, user_id, message.message_id, sent_message.message_id),
                )
                await db.commit()


@dp.message_reaction(states.AnonChatState.in_chat)
async def on_chat_update(message_reaction: MessageReactionUpdated):
    user1_id = message_reaction.user.id
    if user1_id == message_reaction.bot.id:
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
    await message_reaction.bot.set_message_reaction(
        user2_id, message_id=id_for_reaction, reaction=message_reaction.new_reaction
    )


@dp.edited_message(states.AnonChatState.in_chat)
async def on_chat_edit_message(message: Message):
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
        await message.bot.edit_message_text(
            message.text + "\n\n(Ред.)", chat_id=user2_id, message_id=id_to_edit
        )
    elif message.caption:
        await message.bot.edit_message_caption(
            caption=message.caption + "\n\n(Ред.)",
            chat_id=user2_id,
            message_id=id_to_edit,
        )
