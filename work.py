"""
Marlboro Project — Work system
"""

import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from database.db import Database
from utils.keyboards import back_kb
from utils.helpers import ts_now, cooldown_remaining, format_cooldown, WORK_JOBS
from utils.logger import log_action
from utils.texts import format_number
from config import WORK_COOLDOWN, VIP_BONUSES

router = Router()


@router.callback_query(F.data == "work")
@router.message(Command("work"))
async def do_work(event) -> None:
    user_id = event.from_user.id
    row = await Database.get_user(user_id)

    cd = cooldown_remaining(row["last_work"], WORK_COOLDOWN)
    if cd > 0:
        text = f"⏰ <b>Работа</b>\n\nУже работаешь!\nСледующая работа через: <b>{format_cooldown(cd)}</b>"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text, parse_mode="HTML")
        return

    # Check energy
    if row["energy"] < 10:
        text = (
            "⚡ <b>Недостаточно энергии!</b>\n\n"
            f"Энергия: {row['energy']}/100\n"
            "Энергия восстанавливается на 10 единиц каждый час."
        )
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text, parse_mode="HTML")
        return

    job = random.choice(WORK_JOBS)
    vip = row["vip_status"]
    bonus = VIP_BONUSES.get(vip, VIP_BONUSES["none"])

    coins = random.randint(job["min_coins"], job["max_coins"])
    coins = int(coins * bonus["coins"])
    xp = int(job["xp"] * bonus["xp"])
    job_text = random.choice(job["texts"])

    await Database.add_balance(user_id, coins)
    new_level = await Database.add_xp(user_id, xp)
    await Database.update_user(user_id, last_work=ts_now(), energy=max(0, row["energy"] - 10))

    old_level = row["level"]
    level_up_text = f"\n🎉 <b>Уровень повышен: {old_level} → {new_level}!</b>" if new_level > old_level else ""

    text = (
        f"💼 <b>{job['name']}</b>\n\n"
        f"📋 {job_text}\n\n"
        f"💰 Заработано: <b>+{format_number(coins)} монет</b>\n"
        f"🎯 Опыт: <b>+{xp} XP</b>\n"
        f"⚡ Энергия: {max(0, row['energy']-10)}/100\n"
        f"{level_up_text}\n"
        f"⏰ Следующая работа через: <b>{format_cooldown(WORK_COOLDOWN)}</b>"
    )

    await log_action("work", user_id, f"Работа: {job['name']}, заработал {coins}")

    # Check achievement
    if new_level >= 5:
        from database.db import get_db
        db = await get_db()
        async with db.execute(
            "SELECT 1 FROM achievements WHERE user_id = ? AND achievement = 'lvl5'", (user_id,)
        ) as cur:
            if not await cur.fetchone():
                await db.execute(
                    "INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, 'lvl5')", (user_id,)
                )
                await db.commit()

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb(), parse_mode="HTML")
