"""
Marlboro Project — Daily bonus + Top players
"""

import time
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from database.db import Database
from utils.keyboards import back_kb, top_menu_kb
from utils.helpers import ts_now, cooldown_remaining, format_cooldown
from utils.texts import format_number
from utils.logger import log_action
from config import DAILY_BONUS, VIP_BONUSES

router = Router()
DAILY_COOLDOWN = 86400  # 24 hours


@router.callback_query(F.data == "daily")
@router.message(Command("daily"))
async def daily_bonus(event) -> None:
    user_id = event.from_user.id
    row = await Database.get_user(user_id)

    cd = cooldown_remaining(row["last_daily"], DAILY_COOLDOWN)
    if cd > 0:
        text = (
            f"🎁 <b>Ежедневный бонус</b>\n\n"
            f"Ты уже получил бонус сегодня!\n"
            f"Следующий через: <b>{format_cooldown(cd)}</b>\n\n"
            f"🔥 Текущий стрик: <b>{row['daily_streak']} дней</b>"
        )
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text, parse_mode="HTML")
        return

    vip = row["vip_status"]
    bonus_mult = VIP_BONUSES.get(vip, VIP_BONUSES["none"])

    # Calculate streak bonus
    now = ts_now()
    last = row["last_daily"] or 0
    if now - last <= DAILY_COOLDOWN * 1.5:
        new_streak = row["daily_streak"] + 1
    else:
        new_streak = 1

    base_coins = DAILY_BONUS + (new_streak - 1) * 50
    coins = int(base_coins * bonus_mult["coins"])
    xp = int(50 * bonus_mult["xp"])

    # Streak milestone bonuses
    bonus_text = ""
    extra_item = None
    if new_streak % 7 == 0:
        extra_coins = 1000 * (new_streak // 7)
        coins += extra_coins
        bonus_text = f"\n🎉 <b>7-дневный бонус: +{format_number(extra_coins)} монет!</b>"
    if new_streak == 30:
        extra_item = 39  # VIP silver card
        bonus_text += "\n💫 <b>30-дневный бонус: VIP Silver карта!</b>"
    if new_streak == 100:
        extra_item = 40  # VIP gold card
        bonus_text += "\n🥇 <b>100-дневный бонус: VIP Gold карта!</b>"

    await Database.add_balance(user_id, coins)
    new_level = await Database.add_xp(user_id, xp)
    await Database.update_user(user_id, last_daily=now, daily_streak=new_streak)

    if extra_item:
        await Database.add_item(user_id, extra_item, 1)

    level_up = f"\n🎉 Уровень: {row['level']} → {new_level}!" if new_level > row["level"] else ""

    text = (
        f"🎁 <b>Ежедневный бонус получен!</b>\n\n"
        f"💰 +{format_number(coins)} монет\n"
        f"🎯 +{xp} XP{level_up}\n"
        f"🔥 Стрик: <b>{new_streak} {'день' if new_streak == 1 else 'дней'}</b>"
        f"{bonus_text}"
    )
    await log_action("daily", user_id, f"Ежедневный бонус: +{coins} монет, стрик {new_streak}")

    # Check streak achievements
    from database.db import get_db
    db = await get_db()
    if new_streak >= 7:
        await db.execute("INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, 'daily7')", (user_id,))
    if new_streak >= 30:
        await db.execute("INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, 'daily30')", (user_id,))
    await db.commit()

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        await event.answer("🎁 Бонус получен!")
    else:
        await event.answer(text, reply_markup=back_kb(), parse_mode="HTML")


# ── Top players ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "top_menu")
@router.message(Command("top"))
async def top_menu(event) -> None:
    text = "🏆 <b>Топ игроков</b>\n\nВыбери категорию:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=top_menu_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=top_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("top:"))
async def show_top(cb: CallbackQuery) -> None:
    field = cb.data.split(":")[1]
    field_names = {
        "balance":    ("💰 Топ по балансу",  "баланс",     "монет"),
        "level":      ("📈 Топ по уровню",   "уровень",    "ур."),
        "pvp_wins":   ("⚔️ Топ PvP",         "победы",     "побед"),
        "referrals":  ("👥 Топ рефералы",    "рефералы",   "реф."),
    }
    title, label, unit = field_names.get(field, ("🏆 Топ", field, ""))
    top = await Database.get_top_users(field, 10)

    medals = ["🥇", "🥈", "🥉"]
    lines = [f"{title}\n"]
    for i, u in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = u["first_name"] or "Игрок"
        val = u[field]
        lines.append(f"{medal} <b>{name}</b> — {format_number(val)} {unit}")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("top_menu"), parse_mode="HTML")
    await cb.answer()
