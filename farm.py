"""
Marlboro Project — Farm system
"""

import time
import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import farm_menu_kb, back_kb
from utils.helpers import ts_now, format_cooldown
from utils.texts import get_item_data, format_number
from utils.logger import log_action
from config import VIP_BONUSES

router = Router()

SEEDS = {18: 3600, 19: 7200, 20: 10800, 21: 21600}


@router.callback_query(F.data == "farm_menu")
async def farm_menu(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    db = await get_db()
    async with db.execute("SELECT * FROM farm_plots WHERE user_id = ? ORDER BY slot", (user_id,)) as cur:
        plots = await cur.fetchall()

    now = ts_now()
    lines = ["🌾 <b>Ферма</b>\n"]
    for p in plots:
        slot_num = p["slot"] + 1
        if p["seed_id"] is None:
            lines.append(f"Грядка {slot_num}: 🟫 Пустая")
        else:
            item = get_item_data(p["seed_id"])
            name = item["name"] if item else "Семя"
            if now >= p["ready_at"]:
                lines.append(f"Грядка {slot_num}: ✅ {name} — ГОТОВО!")
            else:
                remaining = format_cooldown(p["ready_at"] - now)
                lines.append(f"Грядка {slot_num}: 🌱 {name} — {remaining}")
    text = "\n".join(lines)
    await cb.message.edit_text(text, reply_markup=farm_menu_kb(), parse_mode="HTML")
    await cb.answer()


class FarmState(StatesGroup):
    choose_slot = State()
    choose_seed = State()


@router.callback_query(F.data == "farm_plant")
async def farm_plant_start(cb: CallbackQuery, state: FSMContext) -> None:
    user_id = cb.from_user.id
    db = await get_db()
    async with db.execute(
        "SELECT * FROM farm_plots WHERE user_id = ? AND seed_id IS NULL ORDER BY slot", (user_id,)
    ) as cur:
        empty_plots = await cur.fetchall()

    if not empty_plots:
        await cb.answer("🌾 Все грядки заняты! Сначала собери урожай.", show_alert=True)
        return

    # Get seeds from inventory
    async with db.execute(
        "SELECT i.item_id, i.amount FROM inventory i WHERE i.user_id = ?", (user_id,)
    ) as cur:
        inv = await cur.fetchall()

    seeds_in_inv = [(r["item_id"], r["amount"]) for r in inv if r["item_id"] in SEEDS]
    if not seeds_in_inv:
        await cb.answer("🌱 Нет семян! Купи в магазине.", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    for item_id, amount in seeds_in_inv:
        item = get_item_data(item_id)
        if item:
            b.row(InlineKeyboardButton(
                text=f"{item.get('emoji','🌱')} {item['name']} × {amount}",
                callback_data=f"farm_use_seed:{item_id}:{empty_plots[0]['slot']}"
            ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="farm_menu"))
    await cb.message.edit_text(
        f"🌱 Выбери семя для посадки (грядка {empty_plots[0]['slot']+1}):",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data.startswith("farm_use_seed:"))
async def farm_plant_seed(cb: CallbackQuery) -> None:
    _, item_id_str, slot_str = cb.data.split(":")
    item_id = int(item_id_str)
    slot = int(slot_str)
    user_id = cb.from_user.id

    ok = await Database.remove_item(user_id, item_id, 1)
    if not ok:
        await cb.answer("❌ Семя не найдено!", show_alert=True)
        return

    grow_time = SEEDS.get(item_id, 3600)
    now = ts_now()
    db = await get_db()
    await db.execute(
        "UPDATE farm_plots SET seed_id=?, planted_at=?, ready_at=? WHERE user_id=? AND slot=?",
        (item_id, now, now + grow_time, user_id, slot)
    )
    await db.commit()

    item = get_item_data(item_id)
    await cb.message.edit_text(
        f"🌱 <b>{item['name']}</b> посажена на грядку {slot+1}!\n"
        f"⏰ Готово через: <b>{format_cooldown(grow_time)}</b>",
        reply_markup=back_kb("farm_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "farm_harvest")
async def farm_harvest(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    db = await get_db()
    now = ts_now()
    async with db.execute(
        "SELECT * FROM farm_plots WHERE user_id=? AND seed_id IS NOT NULL AND ready_at <= ?",
        (user_id, now)
    ) as cur:
        ready = await cur.fetchall()

    if not ready:
        await cb.answer("🌾 Нечего собирать! Подожди, пока созреет.", show_alert=True)
        return

    row = await Database.get_user(user_id)
    vip_bonus = VIP_BONUSES.get(row["vip_status"], VIP_BONUSES["none"])
    total_earned = 0
    harvested = []

    for plot in ready:
        from data.items_loader import get_seed_yield
        seed_id = plot["seed_id"]
        item = get_item_data(seed_id)
        if not item:
            continue
        base_yield = item.get("yield", 3)
        yield_item_name = item.get("yield_item", "Урожай")
        amount = max(1, int(base_yield * vip_bonus["coins"]))

        # Find yield item by name
        from utils.texts import get_all_items
        all_items = get_all_items()
        yield_item = next((i for i in all_items if i["name"] == yield_item_name), None)
        if yield_item:
            await Database.add_item(user_id, yield_item["id"], amount)
            total_earned += yield_item.get("price", 0) * amount
            harvested.append(f"{yield_item.get('emoji','🌾')} {yield_item_name} × {amount}")

        await db.execute(
            "UPDATE farm_plots SET seed_id=NULL, planted_at=NULL, ready_at=NULL WHERE id=?",
            (plot["id"],)
        )

    await db.commit()
    xp_gain = len(ready) * 25
    await Database.add_xp(user_id, xp_gain)

    harvest_list = "\n".join(harvested) if harvested else "Ничего"
    await cb.message.edit_text(
        f"🌾 <b>Урожай собран!</b>\n\n{harvest_list}\n\n+{xp_gain} XP",
        reply_markup=back_kb("farm_menu"), parse_mode="HTML"
    )
    await log_action("farm", user_id, f"Собрал урожай: {len(ready)} грядок")
    await cb.answer()


@router.callback_query(F.data == "farm_status")
async def farm_status(cb: CallbackQuery) -> None:
    await farm_menu(cb)
