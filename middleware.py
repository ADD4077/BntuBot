from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject

import aiosqlite

from func import auth_send


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
        if authorization is not None:
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
