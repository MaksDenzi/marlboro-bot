"""
Marlboro Project — Item trading between players
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import back_kb
from utils.helpers import ts_now, mention
from utils.texts import format_number, get_item_data
from utils.logger import log_action

router = Router()


class TradeState(StatesGroup):
    target = State()
    offer_item = State()
    offer_amount = State()
    request_item = State()
    request_amount = State()


@router.callback_query(F.data == "trade_menu")
@router.message(Command("trade"))
async def trade_menu(event, state: FSMContext) -> None:
    text = (
        "🔁 <b>Обмен предметами</b>\n\n"
        "Предложи обмен другому игроку.\n\n"
        "Введи @username или ID игрока для начала обмена:"
    )
    await state.set_state(TradeState.target)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(TradeState.target)
async def trade_target(msg: Message, state: FSMContext) -> None:
    target_text = msg.text.strip().lstrip("@")
    db = await get_db()
    target_row = None
    try:
        target_id = int(target_text)
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (target_id,)) as cur:
            target_row = await cur.fetchone()
    except ValueError:
        async with db.execute("SELECT * FROM users WHERE username = ?", (target_text,)) as cur:
            target_row = await cur.fetchone()

    if not target_row:
        await msg.answer("❌ Игрок не найден!", reply_markup=back_kb())
        await state.clear()
        return
    if target_row["user_id"] == msg.from_user.id:
        await msg.answer("❌ Нельзя торговать с собой!")
        return

    items = await Database.get_inventory(msg.from_user.id)
    if not items:
        await msg.answer("❌ Твой инвентарь пуст!", reply_markup=back_kb())
        await state.clear()
        return

    await state.update_data(target_id=target_row["user_id"], target_name=target_row["first_name"])
    await state.set_state(TradeState.offer_item)

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    for inv_row in items[:15]:
        item = get_item_data(inv_row["item_id"])
        if item:
            b.row(InlineKeyboardButton(
                text=f"{item.get('emoji','📦')} {item['name']} × {inv_row['amount']}",
                callback_data=f"trade_offer_item:{inv_row['item_id']}"
            ))
    b.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="trade_menu"))
    await msg.answer(
        f"🔁 Обмен с <b>{target_row['first_name']}</b>\n\nВыбери предмет для предложения:",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("trade_offer_item:"))
async def trade_offer_item(cb: CallbackQuery, state: FSMContext) -> None:
    item_id = int(cb.data.split(":")[1])
    await state.update_data(offer_item_id=item_id)
    await state.set_state(TradeState.offer_amount)
    item = get_item_data(item_id)
    inv = await Database.get_item_in_inventory(cb.from_user.id, item_id)
    await cb.message.edit_text(
        f"📦 {item['name'] if item else 'Предмет'}\nУ тебя: {inv['amount'] if inv else 0}\n\nСколько предлагаешь?",
        reply_markup=back_kb("trade_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(TradeState.offer_amount)
async def trade_offer_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if amount < 1:
        await msg.answer("❌ Минимум 1!")
        return
    data = await state.get_data()
    inv = await Database.get_item_in_inventory(msg.from_user.id, data["offer_item_id"])
    if not inv or inv["amount"] < amount:
        await msg.answer("❌ Недостаточно предметов!", reply_markup=back_kb("trade_menu"))
        await state.clear()
        return
    await state.update_data(offer_amount=amount)
    await state.set_state(TradeState.request_item)
    await msg.answer(
        "Что хочешь получить взамен? Введи название предмета или ID предмета\n(или 'coins' для монет):"
    )


@router.message(TradeState.request_item)
async def trade_request_item(msg: Message, state: FSMContext) -> None:
    text = msg.text.strip()
    await state.update_data(request_item_text=text)
    await state.set_state(TradeState.request_amount)
    await msg.answer("Сколько?")


@router.message(TradeState.request_amount)
async def trade_request_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if amount < 1:
        await msg.answer("❌ Минимум 1!")
        return

    data = await state.get_data()
    from_user_id = msg.from_user.id
    target_id = data["target_id"]
    target_name = data["target_name"]
    offer_item_id = data["offer_item_id"]
    offer_amount = data["offer_amount"]
    request_text = data["request_item_text"]

    # Resolve request item
    request_item_id = None
    request_coins = 0
    if request_text.lower() == "coins":
        request_coins = amount
    else:
        from utils.texts import get_all_items
        all_items = get_all_items()
        try:
            request_item_id = int(request_text)
        except ValueError:
            matched = [i for i in all_items if request_text.lower() in i["name"].lower()]
            if matched:
                request_item_id = matched[0]["id"]

    if not request_item_id and not request_coins:
        await msg.answer("❌ Предмет не найден!", reply_markup=back_kb("trade_menu"))
        await state.clear()
        return

    db = await get_db()
    await db.execute(
        """INSERT INTO trades (from_user_id, to_user_id, offer_item_id, offer_amount,
           request_item_id, request_amount, request_coins) VALUES (?,?,?,?,?,?,?)""",
        (from_user_id, target_id, offer_item_id, offer_amount,
         request_item_id, amount if request_item_id else 0, request_coins)
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid() as id") as cur:
        trade_id = (await cur.fetchone())["id"]

    offer_item = get_item_data(offer_item_id)
    req_item = get_item_data(request_item_id) if request_item_id else None
    offer_str = f"{offer_item['name'] if offer_item else 'Предмет'} × {offer_amount}"
    req_str = f"{req_item['name'] if req_item else 'Предмет'} × {amount}" if request_item_id else f"{format_number(request_coins)} монет"

    await state.clear()
    await msg.answer(
        f"✅ <b>Предложение обмена отправлено!</b>\n\n"
        f"👤 {target_name}\n"
        f"Ты даёшь: {offer_str}\nТы хочешь: {req_str}",
        reply_markup=back_kb(), parse_mode="HTML"
    )
    await log_action("trade", from_user_id, f"Предложил обмен игроку {target_id}: {offer_str} за {req_str}")

    # Notify target
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"trade_accept:{trade_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"trade_decline:{trade_id}"),
    )
    try:
        sender_row = await Database.get_user(from_user_id)
        await msg.bot.send_message(
            target_id,
            f"🔁 <b>{sender_row['first_name']}</b> предлагает обмен!\n\n"
            f"Даёт: {offer_str}\nХочет: {req_str}",
            reply_markup=b.as_markup(), parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("trade_accept:"))
async def trade_accept(cb: CallbackQuery) -> None:
    trade_id = int(cb.data.split(":")[1])
    user_id = cb.from_user.id
    db = await get_db()
    async with db.execute("SELECT * FROM trades WHERE id = ? AND status = 'pending'", (trade_id,)) as cur:
        trade = await cur.fetchone()
    if not trade or trade["to_user_id"] != user_id:
        await cb.answer("❌ Обмен недоступен!", show_alert=True)
        return

    # Execute trade
    from_uid = trade["from_user_id"]
    if trade["offer_item_id"]:
        ok1 = await Database.remove_item(from_uid, trade["offer_item_id"], trade["offer_amount"])
        if not ok1:
            await cb.answer("❌ У отправителя нет нужных предметов!", show_alert=True)
            return
        await Database.add_item(user_id, trade["offer_item_id"], trade["offer_amount"])

    if trade["request_item_id"]:
        ok2 = await Database.remove_item(user_id, trade["request_item_id"], trade["request_amount"])
        if not ok2:
            if trade["offer_item_id"]:
                await Database.add_item(from_uid, trade["offer_item_id"], trade["offer_amount"])
            await cb.answer("❌ У тебя нет нужных предметов!", show_alert=True)
            return
        await Database.add_item(from_uid, trade["request_item_id"], trade["request_amount"])
    elif trade["request_coins"]:
        ok3 = await Database.deduct_balance(user_id, trade["request_coins"])
        if not ok3:
            if trade["offer_item_id"]:
                await Database.add_item(from_uid, trade["offer_item_id"], trade["offer_amount"])
            await cb.answer("❌ Недостаточно монет!", show_alert=True)
            return
        await Database.add_balance(from_uid, trade["request_coins"])

    await db.execute("UPDATE trades SET status = 'completed' WHERE id = ?", (trade_id,))
    await db.commit()
    await cb.message.edit_text("✅ <b>Обмен завершён!</b>", parse_mode="HTML")
    await cb.answer()
    try:
        await cb.bot.send_message(from_uid, f"✅ Игрок принял твоё предложение обмена!")
    except Exception:
        pass


@router.callback_query(F.data.startswith("trade_decline:"))
async def trade_decline(cb: CallbackQuery) -> None:
    trade_id = int(cb.data.split(":")[1])
    db = await get_db()
    await db.execute("UPDATE trades SET status = 'declined' WHERE id = ?", (trade_id,))
    await db.commit()
    await cb.message.edit_text("❌ <b>Обмен отклонён.</b>", parse_mode="HTML")
    await cb.answer()
