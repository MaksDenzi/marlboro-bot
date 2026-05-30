"""
Marlboro Project — Ban/Mute check middleware
"""

import time
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database.db import Database
from config import OWNER_ID


class BanCheckMiddleware(BaseMiddleware):
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

        if user and user.id != OWNER_ID:
            row = await Database.get_user(user.id)
            if row:
                now = int(time.time())

                # Ban check
                if row["is_banned"]:
                    ban_exp = row["ban_expires"]
                    if ban_exp and ban_exp < now:
                        # Auto-unban
                        await Database.update_user(user.id, is_banned=0, ban_reason=None, ban_expires=None)
                    else:
                        reason = row["ban_reason"] or "Нарушение правил"
                        expire_str = ""
                        if ban_exp:
                            expire_str = f"\nДо: {time.strftime('%Y-%m-%d %H:%M', time.localtime(ban_exp))}"
                        msg = f"🚫 <b>Вы заблокированы</b>\nПричина: {reason}{expire_str}"
                        if isinstance(event, Message):
                            await event.answer(msg, parse_mode="HTML")
                        elif isinstance(event, CallbackQuery):
                            await event.answer("🚫 Вы заблокированы.", show_alert=True)
                        return

                # Mute check (only for messages)
                if isinstance(event, Message) and row["is_muted"]:
                    mute_exp = row["mute_expires"]
                    if mute_exp and mute_exp < now:
                        await Database.update_user(user.id, is_muted=0, mute_expires=None)
                    else:
                        expire_str = ""
                        if mute_exp:
                            expire_str = f"\nДо: {time.strftime('%Y-%m-%d %H:%M', time.localtime(mute_exp))}"
                        await event.answer(f"🔇 Вы заглушены{expire_str}", parse_mode="HTML")
                        return

        return await handler(event, data)
