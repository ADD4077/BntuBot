from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject, LabeledPrice, Message, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder

import aiosqlite

from util.func import auth_send

import os

from util.config import server_db_path
from util.states import AnonChatState

from collections import defaultdict
import asyncio

from dotenv import load_dotenv

load_dotenv()

id_admin = os.getenv('ID_ADMIN')


class AuthorizationMiddleware(BaseMiddleware):
    """
    Checks if user is authorized to use the bot
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        authorization = get_flag(data, "authorization")
        if authorization:
            if authorization["is_authorized"]:
                async with aiosqlite.connect(server_db_path) as db:
                    async with db.cursor() as cursor:
                        if await (await cursor.execute(
                            "SELECT id FROM users WHERE id = (?)",
                            (event.from_user.id, )
                        )).fetchone():
                            return await handler(event, data)
                        else:
                            return await auth_send(data['bot'], event)
        else:
            return await handler(event, data)


class BanMiddleware(BaseMiddleware):
    """
    Checks if user is banned in anonymous chat
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        banned = get_flag(data, "banned")
        if banned:
            if banned["isnt_banned"]:
                async with aiosqlite.connect(server_db_path) as db:
                    async with db.cursor() as cursor:
                        if await (await cursor.execute(
                            "SELECT user_id FROM bans_anon_chat WHERE user_id = (?)",
                            (event.from_user.id, )
                        )).fetchone():
                            builder = InlineKeyboardBuilder()
                            builder.button(
                                text="Оплатить 100 XTR",
                                pay=True
                            )

                            prices = [LabeledPrice(label="XTR", amount=100)]
                            if isinstance(event, Message):
                                message = event
                            else:
                                message = event.message
                            return await message.answer_invoice(
                                title="Разблокировка в анонимном чате",
                                description=(
                                    "Доступ к анонимному чату был заблокирован для Вас.\n"
                                    "Вы можете приобрести разблокировку за 100 звезд или "
                                    "обратиться в поддержку если считаете блокировку ошибочной"
                                ),
                                prices=prices,
                                provider_token="",
                                payload="unban_payment",
                                currency="XTR",
                                reply_markup=builder.as_markup()
                            )
                        else:
                            return await handler(event, data)
        else:
            return await handler(event, data)


class AdminMiddleware(BaseMiddleware):
    """
    Checks if user is admin
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        admin = get_flag(data, "admin")
        if admin:
            if admin["is_admin"]:
                async with aiosqlite.connect(server_db_path) as db:
                    async with db.cursor() as cursor:
                        # fetch admins from db in future
                        if event.from_user.id != int(id_admin):
                            return await event.answer(
                                "Нет доступа",
                                show_alert=True
                            )
                        else:
                            return await handler(event, data)
        else:
            return await handler(event, data)


class MediaGroupMiddlewaref(BaseMiddleware):
    def __init__(self, latency: float = 1.0):
        super().__init__()
        self.latency = latency
        self.media_groups = {}

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        if not event.message:
            return await handler(event, data)
        if event.message.media_group_id:
            media_group_id = event.message.media_group_id
            if self.media_groups.get(media_group_id):
                self.media_groups[media_group_id].append(event.message)
            else:
                self.media_groups[media_group_id] = [event.message]
            data["media_group"] = self.media_groups[media_group_id]
        return await handler(event, data)


class MediaGroupMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 1.0):
        super().__init__()
        self.latency = latency
        self.media_groups: Dict[int, list[Message]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not event.message or not event.message.media_group_id:
            return await handler(event, data)
        if (await data["state"].get_state()) == AnonChatState.in_chat:
            media_group_id = event.message.media_group_id
            if media_group_id not in self.media_groups:
                self.media_groups[media_group_id] = []
            self.media_groups[media_group_id].append(event.message)
            if media_group_id in self.tasks:
                self.tasks[media_group_id].cancel()
            self.tasks[media_group_id] = asyncio.create_task(
                self._flush_group(media_group_id, handler, event, data)
            )
        else:
            return await handler(event, data)

    async def _flush_group(
        self,
        media_group_id: str,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ):
        try:
            await asyncio.sleep(self.latency)
        except asyncio.CancelledError:
            return

        messages = self.media_groups.pop(media_group_id, [])
        self.tasks.pop(media_group_id, None)

        if messages:
            # First message is usually the one with caption
            first_message = messages[0]

            # Pass media group explicitly via middleware `data`
            data["media_group"] = messages
            data["first_message"] = first_message

            # Call handler with the original event (unchanged) + updated data
            return await handler(event, data)
