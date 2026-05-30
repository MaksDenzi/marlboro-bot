"""
Marlboro Project — Promo codes
"""

import time
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database
from utils.keyboards import back_kb
from utils.texts import format_number, get_item_data
from utils.logger import log_action

router = Router()


class PromoState(StatesGroup):
    enter_code = State()


@router.callback_query(F.data == "promo")
@router.message(Command("promo"))
async def promo_start(event, state: FSMContext) -> None:
    await state.set_state(PromoState.enter_code)
    text = "🎟️ <b>Промокод</b>\n\nВведи промокод для активации:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(PromoState.enter_code)
async def promo_use(msg: Message, state: FSMContext) -> None:
    code = msg.text.strip().upper()
    user_id = msg.from_user.id

    promo = await Database.get_promo(code)
    if not promo or not promo["is_active"]:
        await msg.answer("❌ Промокод не найден или неактивен!", reply_markup=back_kb())
        await state.clear()
        return

    now = int(time.time())
    if promo["expires_at"] and promo["expires_at"] < now:
        await msg.answer("❌ Промокод истёк!", reply_markup=back_kb())
        await state.clear()
        return

    if promo["uses_left"] == 0:
        await msg.answer("❌ Промокод уже использован максимальное количество раз!", reply_markup=back_kb())
        await state.clear()
        return

    used = await Database.use_promo(code, user_id)
    if not used:
        await msg.answer("❌ Ты уже использовал этот промокод!", reply_markup=back_kb())
        await state.clear()
        return

    # Apply reward
    reward_text = ""
    if promo["reward_type"] == "coins":
        await Database.add_balance(user_id, promo["reward_amount"])
        reward_text = f"💰 +{format_number(promo['reward_amount'])} монет"
    elif promo["reward_type"] == "item" and promo["reward_item_id"]:
        await Database.add_item(user_id, promo["reward_item_id"], promo["reward_amount"] or 1)
        item = get_item_data(promo["reward_item_id"])
        reward_text = f"📦 {item['name'] if item else 'Предмет'} × {promo['reward_amount'] or 1}"
    elif promo["reward_type"] == "xp":
        await Database.add_xp(user_id, promo["reward_amount"])
        reward_text = f"🎯 +{promo['reward_amount']} XP"

    # Decrease uses
    from database.db import get_db
    db = await get_db()
    if promo["uses_left"] > 0:
        await db.execute(
            "UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ? AND uses_left > 0",
            (code,)
        )
        await db.commit()

    await log_action("promo", user_id, f"Активировал промокод {code}: {reward_text}")
    await state.clear()
    await msg.answer(
        f"✅ <b>Промокод активирован!</b>\n\n🎁 Награда:\n{reward_text}",
        reply_markup=back_kb(), parse_mode="HTML"
    )
