"""
Marlboro Project — Anti-spam middleware
"""

import time
from collections import defaultdict, deque
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from config import SPAM_LIMIT, SPAM_WINDOW


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._user_times: dict[int, deque] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[Any, dict], Awaitable[Any]],
        event: Any,
        data: dict,
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            now = time.time()
            times = self._user_times[user_id]

            # Drop old timestamps
            while times and now - times[0] > SPAM_WINDOW:
                times.popleft()

            times.append(now)
            if len(times) > SPAM_LIMIT:
                if isinstance(event, Message):
                    await event.answer("⏳ Слишком много запросов! Подожди немного.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⏳ Не так быстро!", show_alert=False)
                return

        return await handler(event, data)
