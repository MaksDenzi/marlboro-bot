"""
Marlboro Project — Mining system
"""

import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from database.db import Database
from utils.keyboards import back_kb
from utils.helpers import ts_now, cooldown_remaining, format_cooldown, MINE_RESOURCES, weighted_choice
from utils.texts import format_number, get_item_data
from utils.logger import log_action
from config import MINE_COOLDOWN, VIP_BONUSES

router = Router()


@router.callback_query(F.data == "mine")
@router.message(Command("mine"))
async def do_mine(event) -> None:
    user_id = event.from_user.id
    row = await Database.get_user(user_id)

    cd = cooldown_remaining(row["last_mine"], MINE_COOLDOWN)
    if cd > 0:
        text = f"⛏️ <b>Майнинг</b>\n\nШахта уже разрабатывается!\nВернись через: <b>{format_cooldown(cd)}</b>"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text, parse_mode="HTML")
        return

    if row["energy"] < 15:
        text = "⚡ Недостаточно энергии для майнинга! (нужно 15)"
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
        return

    # Get equipped pickaxe for efficiency multiplier
    from database.db import get_db
    db = await get_db()
    efficiency = 1
    async with db.execute(
        "SELECT item_id FROM inventory WHERE user_id = ? AND equipped = 1", (user_id,)
    ) as cur:
        equipped = await cur.fetchall()
    for eq in equipped:
        item = get_item_data(eq["item_id"])
        if item and item.get("type") == "mining_tool":
            efficiency = item.get("efficiency", 1)
            break

    vip = row["vip_status"]
    bonus = VIP_BONUSES.get(vip, VIP_BONUSES["none"])

    # Mine resources (1-3 + efficiency bonus)
    mines = random.randint(1, 2 + efficiency)
    found = []
    for _ in range(mines):
        res = weighted_choice(MINE_RESOURCES)
        amount = random.randint(res["min"], max(res["min"], res["max"] + efficiency - 1))
        amount = max(1, int(amount * bonus["drop"]))
        await Database.add_item(user_id, res["item_id"], amount)
        found.append(f"{res['emoji']} {res['name']} × {amount}")

    xp = random.randint(15, 40 + efficiency * 5)
    xp = int(xp * bonus["xp"])
    new_level = await Database.add_xp(user_id, xp)
    await Database.update_user(user_id, last_mine=ts_now(), energy=max(0, row["energy"] - 15))

    level_up = f"\n🎉 Уровень повышен: {row['level']} → {new_level}!" if new_level > row["level"] else ""
    found_text = "\n".join(found)

    text = (
        f"⛏️ <b>Майнинг</b>\n\n"
        f"Найдено:\n{found_text}\n\n"
        f"🎯 +{xp} XP{level_up}\n"
        f"⚡ Энергия: {max(0, row['energy']-15)}/100\n"
        f"⏰ Следующий заход через: <b>{format_cooldown(MINE_COOLDOWN)}</b>"
    )

    await log_action("mining", user_id, f"Добыл {len(found)} ресурсов, эффект. {efficiency}")

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb(), parse_mode="HTML")
