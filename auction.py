"""
Marlboro Project — Auction house
"""

import time
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import auction_menu_kb, back_kb
from utils.helpers import ts_now
from utils.texts import get_item_data, format_number, get_all_items
from utils.logger import log_action
from config import AUCTION_FEE_PERCENT, AUCTION_MIN_PRICE, AUCTION_MAX_DURATION_HOURS

router = Router()


class AuctionState(StatesGroup):
    choose_item = State()
    set_price = State()
    set_duration = State()
    bid_lot = State()
    bid_amount = State()


@router.callback_query(F.data == "auction_menu")
async def auction_menu(cb: CallbackQuery) -> None:
    text = (
        "🏛️ <b>Аукцион</b>\n\n"
        "Продавай и покупай предметы у других игроков!\n\n"
        f"⚠️ Комиссия за выставление: <b>{int(AUCTION_FEE_PERCENT*100)}%</b>\n"
        f"⏰ Макс. срок: <b>{AUCTION_MAX_DURATION_HOURS} часов</b>"
    )
    await cb.message.edit_text(text, reply_markup=auction_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "auction_list")
async def auction_list(cb: CallbackQuery) -> None:
    lots = await Database.get_active_auctions(15)
    if not lots:
        await cb.message.edit_text(
            "🏛️ <b>Аукцион</b>\n\nАктивных лотов нет.",
            reply_markup=back_kb("auction_menu"), parse_mode="HTML"
        )
        await cb.answer()
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    lines = ["🏛️ <b>Активные лоты</b>\n"]

    for lot in lots:
        item = get_item_data(lot["item_id"])
        item_name = item["name"] if item else f"Предмет #{lot['item_id']}"
        item_emoji = item.get("emoji", "📦") if item else "📦"
        current = lot["current_bid"] or lot["start_price"]
        expires_in = lot["expires_at"] - ts_now()
        exp_str = f"{expires_in//3600}ч {(expires_in%3600)//60}м" if expires_in > 0 else "Истёк"

        lines.append(
            f"{item_emoji} <b>{item_name}</b> × {lot['amount']}\n"
            f"  💰 {format_number(current)} | ⏰ {exp_str} | 👤 {lot['seller_name']}"
        )
        b.row(InlineKeyboardButton(
            text=f"{item_emoji} {item_name} — {format_number(current)} 💰",
            callback_data=f"auction_bid:{lot['id']}"
        ))

    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="auction_menu"))
    await cb.message.edit_text("\n".join(lines), reply_markup=b.as_markup(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("auction_bid:"))
async def auction_bid_start(cb: CallbackQuery, state: FSMContext) -> None:
    lot_id = int(cb.data.split(":")[1])
    db = await get_db()
    async with db.execute("SELECT * FROM auction WHERE id = ? AND status = 'active'", (lot_id,)) as cur:
        lot = await cur.fetchone()

    if not lot:
        await cb.answer("❌ Лот недоступен!", show_alert=True)
        return
    if lot["seller_id"] == cb.from_user.id:
        await cb.answer("❌ Нельзя ставить на свой лот!", show_alert=True)
        return

    item = get_item_data(lot["item_id"])
    item_name = item["name"] if item else f"Предмет #{lot['item_id']}"
    current = lot["current_bid"] or lot["start_price"]
    min_bid = current + 1

    row = await Database.get_user(cb.from_user.id)
    await state.set_state(AuctionState.bid_amount)
    await state.update_data(lot_id=lot_id, item_name=item_name, min_bid=min_bid)
    await cb.message.edit_text(
        f"🏛️ <b>Ставка на лот</b>\n\n"
        f"📦 Предмет: <b>{item_name}</b> × {lot['amount']}\n"
        f"💰 Текущая ставка: <b>{format_number(current)}</b>\n"
        f"💵 Твой баланс: <b>{format_number(row['balance'])}</b>\n\n"
        f"Введи сумму ставки (минимум {format_number(min_bid)}):",
        reply_markup=back_kb("auction_list"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(AuctionState.bid_amount)
async def auction_bid_amount(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lot_id = data["lot_id"]
    min_bid = data["min_bid"]
    item_name = data["item_name"]

    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return

    if amount < min_bid:
        await msg.answer(f"❌ Минимальная ставка: {format_number(min_bid)} монет!")
        return

    user_id = msg.from_user.id
    row = await Database.get_user(user_id)
    if row["balance"] < amount:
        await msg.answer("❌ Недостаточно монет!", reply_markup=back_kb("auction_list"))
        await state.clear()
        return

    db = await get_db()
    async with db.execute("SELECT * FROM auction WHERE id = ? AND status = 'active'", (lot_id,)) as cur:
        lot = await cur.fetchone()
    if not lot:
        await msg.answer("❌ Лот уже закрыт!", reply_markup=back_kb("auction_menu"))
        await state.clear()
        return

    # Return previous bidder's coins
    if lot["buyer_id"] and lot["current_bid"]:
        await Database.add_balance(lot["buyer_id"], lot["current_bid"])

    # Reserve new bid
    ok = await Database.deduct_balance(user_id, amount)
    if not ok:
        await msg.answer("❌ Ошибка снятия монет!", reply_markup=back_kb("auction_list"))
        await state.clear()
        return

    await db.execute(
        "UPDATE auction SET current_bid=?, buyer_id=? WHERE id=?",
        (amount, user_id, lot_id)
    )
    await db.commit()
    await state.clear()

    await msg.answer(
        f"✅ <b>Ставка принята!</b>\n\n"
        f"📦 {item_name}\n"
        f"💰 Ставка: <b>{format_number(amount)} монет</b>",
        reply_markup=back_kb("auction_list"), parse_mode="HTML"
    )
    await log_action("auction", user_id, f"Ставка {amount} на лот #{lot_id} ({item_name})")


@router.callback_query(F.data == "auction_sell")
async def auction_sell_start(cb: CallbackQuery, state: FSMContext) -> None:
    user_id = cb.from_user.id
    items = await Database.get_inventory(user_id)
    if not items:
        await cb.answer("🎒 Инвентарь пуст!", show_alert=True)
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    for inv_row in items[:20]:
        item = get_item_data(inv_row["item_id"])
        if item:
            b.row(InlineKeyboardButton(
                text=f"{item.get('emoji','📦')} {item['name']} × {inv_row['amount']}",
                callback_data=f"auction_pick:{inv_row['item_id']}:{inv_row['amount']}"
            ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="auction_menu"))
    await cb.message.edit_text(
        "🏛️ <b>Выставить лот</b>\n\nВыбери предмет:",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data.startswith("auction_pick:"))
async def auction_pick_item(cb: CallbackQuery, state: FSMContext) -> None:
    parts = cb.data.split(":")
    item_id, max_amount = int(parts[1]), int(parts[2])
    item = get_item_data(item_id)
    await state.set_state(AuctionState.set_price)
    await state.update_data(item_id=item_id, max_amount=max_amount, amount=1)
    await cb.message.edit_text(
        f"🏛️ Выставляешь: <b>{item['name'] if item else 'Предмет'}</b>\n\n"
        f"Введи стартовую цену (минимум {AUCTION_MIN_PRICE} монет):",
        reply_markup=back_kb("auction_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(AuctionState.set_price)
async def auction_set_price(msg: Message, state: FSMContext) -> None:
    try:
        price = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if price < AUCTION_MIN_PRICE:
        await msg.answer(f"❌ Минимальная цена: {AUCTION_MIN_PRICE} монет!")
        return
    await state.update_data(price=price)
    await state.set_state(AuctionState.set_duration)
    await msg.answer(f"⏰ Введи длительность аукциона в часах (1–{AUCTION_MAX_DURATION_HOURS}):")


@router.message(AuctionState.set_duration)
async def auction_set_duration(msg: Message, state: FSMContext) -> None:
    try:
        hours = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if hours < 1 or hours > AUCTION_MAX_DURATION_HOURS:
        await msg.answer(f"❌ Длительность: 1–{AUCTION_MAX_DURATION_HOURS} часов!")
        return

    data = await state.get_data()
    user_id = msg.from_user.id
    item_id = data["item_id"]
    price = data["price"]
    amount = data.get("amount", 1)
    item = get_item_data(item_id)

    # Fee
    fee = max(1, int(price * AUCTION_FEE_PERCENT))
    ok = await Database.deduct_balance(user_id, fee)
    if not ok:
        await msg.answer(f"❌ Нужно {fee} монет на комиссию!", reply_markup=back_kb("auction_menu"))
        await state.clear()
        return

    ok2 = await Database.remove_item(user_id, item_id, amount)
    if not ok2:
        await Database.add_balance(user_id, fee)
        await msg.answer("❌ Предмет не найден в инвентаре!", reply_markup=back_kb("auction_menu"))
        await state.clear()
        return

    db = await get_db()
    expires = ts_now() + hours * 3600
    await db.execute(
        "INSERT INTO auction (seller_id, item_id, amount, start_price, expires_at) VALUES (?,?,?,?,?)",
        (user_id, item_id, amount, price, expires)
    )
    await db.commit()
    await state.clear()

    await msg.answer(
        f"✅ <b>Лот выставлен!</b>\n\n"
        f"📦 {item['name'] if item else 'Предмет'} × {amount}\n"
        f"💰 Стартовая цена: {format_number(price)}\n"
        f"⏰ Длительность: {hours} ч.\n"
        f"💸 Комиссия: {fee} монет",
        reply_markup=back_kb("auction_menu"), parse_mode="HTML"
    )
    await log_action("auction", user_id, f"Выставил {item['name'] if item else item_id} за {price}")


@router.callback_query(F.data == "auction_my")
async def auction_my(cb: CallbackQuery) -> None:
    db = await get_db()
    async with db.execute(
        "SELECT * FROM auction WHERE seller_id = ? AND status = 'active' ORDER BY created_at DESC",
        (cb.from_user.id,)
    ) as cur:
        my_lots = await cur.fetchall()

    if not my_lots:
        await cb.message.edit_text(
            "🏛️ <b>Мои лоты</b>\n\nУ тебя нет активных лотов.",
            reply_markup=back_kb("auction_menu"), parse_mode="HTML"
        )
        await cb.answer()
        return

    lines = ["🏛️ <b>Мои лоты</b>\n"]
    for lot in my_lots:
        item = get_item_data(lot["item_id"])
        name = item["name"] if item else f"Предмет #{lot['item_id']}"
        cur_bid = lot["current_bid"] or lot["start_price"]
        lines.append(f"📦 {name} — текущая ставка: {format_number(cur_bid)} 💰")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("auction_menu"), parse_mode="HTML")
    await cb.answer()
