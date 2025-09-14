from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject

import aiosqlite

from func import auth_send

import os

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
                async with aiosqlite.connect("server.db") as db:
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
                async with aiosqlite.connect("server.db") as db:
                    async with db.cursor() as cursor:
                        if await (await cursor.execute(
                            "SELECT user_id FROM bans_anon_chat WHERE user_id = (?)",
                            (event.from_user.id, )
                        )).fetchone():
                            return await event.answer(
                                "Доступ к анонимному чату заблокирован для вас",
                                show_alert=True
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
                async with aiosqlite.connect("server.db") as db:
                    async with db.cursor() as cursor:
                        if event.from_user.id != int(id_admin):
                            return await event.answer(
                                "Нет доступа",
                                show_alert=True
                            )
                        else:
                            return await handler(event, data)
        else:
            return await handler(event, data)
