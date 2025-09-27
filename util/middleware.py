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

id_owner = os.getenv('ID_OWNER')


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


class OwnerMiddleware(BaseMiddleware):
    """
    Checks if user is owner
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        owner = get_flag(data, "owner") or {}
        if owner.get("is_owner"):
            data["allowed"] = data.get("allowed") or event.from_user.id == int(id_owner)
            return await handler(event, data)
        else:
            return await handler(event, data)


class ModeratorMiddleware(BaseMiddleware):
    """
    Checks if user is moderator
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        moderator = get_flag(data, "moderator") or {}
        if moderator.get("is_moderator"):
            async with aiosqlite.connect(server_db_path) as db:
                async with db.cursor() as cursor:
                    moderators_id = await (await cursor.execute(
                        "SELECT id FROM moderators WHERE id = ?",
                        (event.from_user.id, )
                    )).fetchone()
                    if not moderators_id:
                        data["allowed"] = data.get("allowed") or False
                        return await handler(event, data)
                    else:
                        data["allowed"] = data.get("allowed") or True
                        return await handler(event, data)
        else:
            return await handler(event, data)


class PermissonMiddleware(BaseMiddleware):
    """
    Checks if user has permissions
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        permissions = get_flag(data, "permissions") or {}
        if permissions.get("any_permission"):
            if data.get("allowed"):
                return await handler(event, data)
            return await event.answer(
                "Нет доступа",
                show_alert=True
            )
        else:
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
            first_message = messages[0]
            data["media_group"] = messages
            data["first_message"] = first_message
            return await handler(event, data)
