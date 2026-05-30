"""
Marlboro Project — Business system
"""

import time
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db import Database, get_db
from utils.keyboards import business_menu_kb, back_kb
from utils.helpers import ts_now, BUSINESS_TYPES
from utils.texts import format_number
from utils.logger import log_action
from config import VIP_BONUSES

router = Router()
COLLECT_INTERVAL = 3600  # 1 hour


@router.callback_query(F.data == "business_menu")
async def business_menu(cb: CallbackQuery) -> None:
    text = (
        "💼 <b>Бизнесы</b>\n\n"
        "Купи бизнес и получай пассивный доход каждый час!\n\n"
    )
    for key, b in BUSINESS_TYPES.items():
        text += f"{b['name']} — {format_number(b['buy_price'])} 💰 | +{format_number(b['base_income'])}/час\n"
    await cb.message.edit_text(text, reply_markup=business_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "business_buy")
async def business_buy(cb: CallbackQuery) -> None:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    for key, bt in BUSINESS_TYPES.items():
        b.row(InlineKeyboardButton(
            text=f"{bt['name']} — {format_number(bt['buy_price'])} 💰",
            callback_data=f"biz_purchase:{key}"
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="business_menu"))
    await cb.message.edit_text(
        "💼 <b>Купить бизнес</b>\n\nВыбери:",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data.startswith("biz_purchase:"))
async def biz_purchase(cb: CallbackQuery) -> None:
    biz_type = cb.data.split(":")[1]
    user_id = cb.from_user.id
    bt = BUSINESS_TYPES.get(biz_type)
    if not bt:
        await cb.answer("❌ Бизнес не найден!", show_alert=True)
        return

    db = await get_db()
    async with db.execute(
        "SELECT id FROM businesses WHERE user_id = ? AND type = ?", (user_id, biz_type)
    ) as cur:
        existing = await cur.fetchone()
    if existing:
        await cb.answer("❌ Ты уже владеешь этим бизнесом!", show_alert=True)
        return

    ok = await Database.deduct_balance(user_id, bt["buy_price"])
    if not ok:
        await cb.answer(f"❌ Нужно {format_number(bt['buy_price'])} монет!", show_alert=True)
        return

    await db.execute(
        "INSERT INTO businesses (user_id, type, income) VALUES (?, ?, ?)",
        (user_id, biz_type, bt["base_income"])
    )
    await db.commit()

    await log_action("business", user_id, f"Купил бизнес: {bt['name']}")

    from database.db import get_db as gdb
    dbb = await gdb()
    await dbb.execute(
        "INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, 'businessman')",
        (user_id,)
    )
    await dbb.commit()

    await cb.message.edit_text(
        f"✅ <b>{bt['name']}</b> куплен!\n\nДоход: <b>{format_number(bt['base_income'])} монет/час</b>",
        reply_markup=back_kb("business_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "business_list")
async def business_list(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    db = await get_db()
    async with db.execute("SELECT * FROM businesses WHERE user_id = ?", (user_id,)) as cur:
        businesses = await cur.fetchall()

    if not businesses:
        await cb.message.edit_text(
            "💼 <b>Мои бизнесы</b>\n\nУ тебя пока нет бизнесов. Купи в разделе 'Купить бизнес'!",
            reply_markup=back_kb("business_menu"), parse_mode="HTML"
        )
        await cb.answer()
        return

    now = ts_now()
    lines = ["💼 <b>Мои бизнесы</b>\n"]
    for biz in businesses:
        bt = BUSINESS_TYPES.get(biz["type"], {})
        last = biz["last_collect"] or biz["purchased_at"]
        hours_ready = (now - last) // COLLECT_INTERVAL
        pending = min(hours_ready, 24) * biz["income"]
        lines.append(
            f"{bt.get('name','Бизнес')} (ур. {biz['level']})\n"
            f"  +{format_number(biz['income'])}/час | Готово: {format_number(pending)} 💰"
        )
    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("business_menu"), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "business_collect")
async def business_collect(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    db = await get_db()
    async with db.execute("SELECT * FROM businesses WHERE user_id = ?", (user_id,)) as cur:
        businesses = await cur.fetchall()

    if not businesses:
        await cb.answer("❌ У тебя нет бизнесов!", show_alert=True)
        return

    now = ts_now()
    total = 0
    for biz in businesses:
        last = biz["last_collect"] or biz["purchased_at"]
        hours = (now - last) // COLLECT_INTERVAL
        if hours < 1:
            continue
        earned = min(hours, 24) * biz["income"]

        row = await Database.get_user(user_id)
        vip_bonus = VIP_BONUSES.get(row["vip_status"], VIP_BONUSES["none"])
        earned = int(earned * vip_bonus["coins"])
        total += earned

        await db.execute("UPDATE businesses SET last_collect=? WHERE id=?", (now, biz["id"]))
    await db.commit()

    if total == 0:
        await cb.answer("⏰ Ещё рано собирать доход! Возвращайся через час.", show_alert=True)
        return

    await Database.add_balance(user_id, total)
    await cb.message.edit_text(
        f"✅ <b>Доход собран!</b>\n\n💰 Получено: <b>{format_number(total)} монет</b>",
        reply_markup=back_kb("business_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "business_upgrade")
async def business_upgrade(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    db = await get_db()
    async with db.execute("SELECT * FROM businesses WHERE user_id = ?", (user_id,)) as cur:
        businesses = await cur.fetchall()

    if not businesses:
        await cb.answer("❌ У тебя нет бизнесов!", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    for biz in businesses:
        bt = BUSINESS_TYPES.get(biz["type"], {})
        upgrade_cost = int(bt.get("buy_price", 5000) * (biz["level"] * 0.5))
        new_income = int(biz["income"] * bt.get("upgrade_mult", 1.5))
        b.row(InlineKeyboardButton(
            text=f"{bt.get('name','Бизнес')} ур.{biz['level']}→{biz['level']+1} | {format_number(upgrade_cost)}💰",
            callback_data=f"biz_upgrade:{biz['id']}:{upgrade_cost}:{new_income}"
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="business_menu"))
    await cb.message.edit_text("⬆️ <b>Улучшить бизнес</b>\n", reply_markup=b.as_markup(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("biz_upgrade:"))
async def biz_upgrade(cb: CallbackQuery) -> None:
    _, biz_id_str, cost_str, new_income_str = cb.data.split(":")
    biz_id, cost, new_income = int(biz_id_str), int(cost_str), int(new_income_str)

    ok = await Database.deduct_balance(cb.from_user.id, cost)
    if not ok:
        await cb.answer(f"❌ Нужно {format_number(cost)} монет!", show_alert=True)
        return

    db = await get_db()
    await db.execute(
        "UPDATE businesses SET level = level + 1, income = ? WHERE id = ? AND user_id = ?",
        (new_income, biz_id, cb.from_user.id)
    )
    await db.commit()
    await cb.message.edit_text(
        f"⬆️ <b>Бизнес улучшен!</b>\n\nНовый доход: <b>{format_number(new_income)}/час</b>",
        reply_markup=back_kb("business_menu"), parse_mode="HTML"
    )
    await cb.answer()
