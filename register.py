"""
Marlboro Project — Auto-register middleware
Updates last_seen on every interaction.
"""

import time
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.db import Database


class RegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict], Awaitable[Any]],
        event: Any,
        data: dict,
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            row = await Database.get_user(user.id)
            if row:
                await Database.update_user(
                    user.id,
                    username=user.username,
                    first_name=user.first_name or "",
                    last_name=user.last_name or "",
                    last_seen=int(time.time()),
                )
            # If not registered, /start handler will do it

        return await handler(event, data)
