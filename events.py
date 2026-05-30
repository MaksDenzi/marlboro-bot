"""
Marlboro Project — RPG Events system
"""

import random
import time
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from database.db import Database, get_db
from utils.keyboards import back_kb
from utils.texts import format_number
from utils.helpers import ts_now
from utils.logger import log_action

router = Router()

RANDOM_EVENTS = [
    {
        "id": "meteor",
        "name": "☄️ Метеоритный дождь",
        "description": "С неба падают метеориты! Ищи редкие минералы!",
        "reward_type": "items",
        "items": [29, 30, 31],
        "min_amount": 1,
        "max_amount": 3,
    },
    {
        "id": "treasure",
        "name": "🏴‍☠️ Пиратский клад",
        "description": "Найден зарытый пиратский клад!",
        "reward_type": "coins",
        "min_coins": 500,
        "max_coins": 3000,
    },
    {
        "id": "dragon",
        "name": "🐉 Дракон атакует!",
        "description": "Дракон напал на деревню! Объединитесь и отгоните его!",
        "reward_type": "xp",
        "min_xp": 100,
        "max_xp": 500,
    },
    {
        "id": "festival",
        "name": "🎉 Городской фестиваль",
        "description": "В городе праздник! Все получают двойной заработок!",
        "reward_type": "coins",
        "min_coins": 300,
        "max_coins": 1000,
    },
    {
        "id": "wizard",
        "name": "🧙 Странствующий волшебник",
        "description": "Волшебник раздаёт зелья всем желающим!",
        "reward_type": "items",
        "items": [13, 14, 15, 16],
        "min_amount": 1,
        "max_amount": 2,
    },
    {
        "id": "gold_rush",
        "name": "⛏️ Золотая лихорадка",
        "description": "В горах нашли огромный золотой жилой!",
        "reward_type": "items",
        "items": [28, 29, 31],
        "min_amount": 1,
        "max_amount": 5,
    },
]


@router.message(Command("event"))
async def check_event(msg: Message) -> None:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM rpg_events WHERE is_active = 1 AND ends_at > ? ORDER BY created_at DESC LIMIT 1",
        (ts_now(),)
    ) as cur:
        event = await cur.fetchone()

    if not event:
        await msg.answer(
            "🌟 <b>Активных событий нет</b>\n\nСледи за объявлениями — события случаются неожиданно!",
            parse_mode="HTML"
        )
        return

    # Check if user participated
    async with db.execute(
        "SELECT score FROM event_participants WHERE event_id = ? AND user_id = ?",
        (event["id"], msg.from_user.id)
    ) as cur:
        participation = await cur.fetchone()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    if participation:
        text = (
            f"🌟 <b>Активное событие: {event['name']}</b>\n\n"
            f"{event['description']}\n\n"
            f"✅ Ты уже участвуешь! Счёт: {participation['score']}"
        )
        await msg.answer(text, parse_mode="HTML")
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⚡ Участвовать!", callback_data=f"event_join:{event['id']}")
        ]])
        ends_str = time.strftime("%d.%m %H:%M", time.localtime(event["ends_at"]))
        text = (
            f"🌟 <b>Активное событие: {event['name']}</b>\n\n"
            f"{event['description']}\n\n"
            f"🏆 Награда: {format_number(event['reward_coins'])} монет + {event['reward_xp']} XP\n"
            f"⏰ До: {ends_str}"
        )
        await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("event_join:"))
async def event_join(cb: CallbackQuery) -> None:
    event_id = int(cb.data.split(":")[1])
    user_id = cb.from_user.id
    db = await get_db()

    async with db.execute("SELECT * FROM rpg_events WHERE id = ? AND is_active = 1", (event_id,)) as cur:
        event = await get_db()  # type: ignore

    # Participate and give reward
    async with db.execute(
        "SELECT * FROM rpg_events WHERE id = ? AND is_active = 1", (event_id,)
    ) as cur:
        event_row = await cur.fetchone()

    if not event_row:
        await cb.answer("❌ Событие уже закончилось!", show_alert=True)
        return

    async with db.execute(
        "SELECT 1 FROM event_participants WHERE event_id = ? AND user_id = ?",
        (event_id, user_id)
    ) as cur:
        if await cur.fetchone():
            await cb.answer("❌ Ты уже участвуешь!", show_alert=True)
            return

    score = random.randint(50, 200)
    await db.execute(
        "INSERT INTO event_participants (event_id, user_id, score) VALUES (?, ?, ?)",
        (event_id, user_id, score)
    )
    await db.commit()

    reward_coins = event_row["reward_coins"] or 0
    reward_xp = event_row["reward_xp"] or 0
    if reward_coins > 0:
        await Database.add_balance(user_id, reward_coins)
    if reward_xp > 0:
        await Database.add_xp(user_id, reward_xp)

    await cb.message.edit_text(
        f"✅ <b>Ты участвуешь в событии!</b>\n\n"
        f"Получено: +{format_number(reward_coins)} монет, +{reward_xp} XP\n"
        f"Твой счёт: {score}",
        parse_mode="HTML"
    )
    await cb.answer("⚡ Участие засчитано!")
    await log_action("event", user_id, f"Участвовал в событии #{event_id}, получил {reward_coins} монет")
