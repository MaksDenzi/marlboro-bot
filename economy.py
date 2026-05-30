"""
Marlboro Project — Economy: balance, bank, transfers
"""

import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import economy_menu_kb, bank_menu_kb, back_kb
from utils.texts import format_number
from utils.logger import log_action

router = Router()


class TransferState(StatesGroup):
    waiting_target = State()
    waiting_amount = State()


class BankState(StatesGroup):
    waiting_amount = State()
    action = State()


@router.callback_query(F.data == "economy_menu")
async def economy_menu(cb: CallbackQuery) -> None:
    row = await Database.get_user(cb.from_user.id)
    text = (
        f"💰 <b>Экономика</b>\n\n"
        f"💵 Баланс: <b>{format_number(row['balance'])} монет</b>\n"
        f"🏦 В банке: <b>{format_number(row['bank'])} монет</b>\n"
        f"📊 Всего заработано: <b>{format_number(row['total_earned'])} монет</b>\n"
        f"💸 Всего потрачено: <b>{format_number(row['total_spent'])} монет</b>\n"
    )
    await cb.message.edit_text(text, reply_markup=economy_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.message(Command("balance"))
@router.callback_query(F.data == "balance")
async def show_balance(event) -> None:
    user_id = event.from_user.id
    row = await Database.get_user(user_id)
    text = (
        f"💰 <b>Баланс</b>\n\n"
        f"💵 На руках: <b>{format_number(row['balance'])} монет</b>\n"
        f"🏦 В банке: <b>{format_number(row['bank'])} монет</b>\n"
        f"📊 Итого: <b>{format_number(row['balance'] + row['bank'])} монет</b>"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("economy_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "bank_menu")
async def bank_menu(cb: CallbackQuery) -> None:
    row = await Database.get_user(cb.from_user.id)
    text = (
        f"🏦 <b>Банк</b>\n\n"
        f"💵 Наличные: <b>{format_number(row['balance'])} монет</b>\n"
        f"🏦 На счёте: <b>{format_number(row['bank'])} монет</b>\n\n"
        f"ℹ️ Храни монеты в банке, чтобы защитить от потери в PvP!"
    )
    await cb.message.edit_text(text, reply_markup=bank_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "bank_deposit")
async def bank_deposit_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BankState.waiting_amount)
    await state.update_data(action="deposit")
    row = await Database.get_user(cb.from_user.id)
    await cb.message.edit_text(
        f"🏦 <b>Пополнение банка</b>\n\nНа руках: <b>{format_number(row['balance'])} монет</b>\n\n"
        f"Введи сумму для вклада (или 'all' для всей суммы):",
        reply_markup=back_kb("bank_menu"),
        parse_mode="HTML",
    )
    await cb.answer()


@router.callback_query(F.data == "bank_withdraw")
async def bank_withdraw_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BankState.waiting_amount)
    await state.update_data(action="withdraw")
    row = await Database.get_user(cb.from_user.id)
    await cb.message.edit_text(
        f"🏦 <b>Снятие из банка</b>\n\nВ банке: <b>{format_number(row['bank'])} монет</b>\n\n"
        f"Введи сумму для снятия (или 'all' для всей суммы):",
        reply_markup=back_kb("bank_menu"),
        parse_mode="HTML",
    )
    await cb.answer()


@router.message(BankState.waiting_amount)
async def bank_process(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    action = data.get("action", "deposit")
    user_id = msg.from_user.id
    row = await Database.get_user(user_id)

    text = msg.text.strip().lower()
    try:
        amount = row["balance"] if text == "all" and action == "deposit" else \
                 row["bank"] if text == "all" and action == "withdraw" else int(text)
    except ValueError:
        await msg.answer("❌ Введи корректное число!", reply_markup=back_kb("bank_menu"))
        await state.clear()
        return

    if amount <= 0:
        await msg.answer("❌ Сумма должна быть больше 0!", reply_markup=back_kb("bank_menu"))
        await state.clear()
        return

    db = await get_db()
    if action == "deposit":
        if row["balance"] < amount:
            await msg.answer("❌ Недостаточно монет!", reply_markup=back_kb("bank_menu"))
            await state.clear()
            return
        await db.execute(
            "UPDATE users SET balance = balance - ?, bank = bank + ? WHERE user_id = ?",
            (amount, amount, user_id)
        )
        await db.commit()
        await msg.answer(
            f"✅ <b>{format_number(amount)} монет</b> положено в банк!",
            reply_markup=back_kb("bank_menu"), parse_mode="HTML"
        )
    else:
        if row["bank"] < amount:
            await msg.answer("❌ В банке недостаточно монет!", reply_markup=back_kb("bank_menu"))
            await state.clear()
            return
        await db.execute(
            "UPDATE users SET bank = bank - ?, balance = balance + ? WHERE user_id = ?",
            (amount, amount, user_id)
        )
        await db.commit()
        await msg.answer(
            f"✅ <b>{format_number(amount)} монет</b> снято из банка!",
            reply_markup=back_kb("bank_menu"), parse_mode="HTML"
        )
    await state.clear()


# ── Transfer ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "transfer_start")
@router.message(Command("send"))
async def transfer_start(event, state: FSMContext) -> None:
    await state.set_state(TransferState.waiting_target)
    text = "💸 <b>Перевод денег</b>\n\nВведи username или ID получателя:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("economy_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb("economy_menu"), parse_mode="HTML")


@router.message(TransferState.waiting_target)
async def transfer_target(msg: Message, state: FSMContext) -> None:
    target_text = msg.text.strip().lstrip("@")
    db = await get_db()

    # Try by username first, then by ID
    target_row = None
    try:
        target_id = int(target_text)
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (target_id,)) as cur:
            target_row = await cur.fetchone()
    except ValueError:
        async with db.execute(
            "SELECT * FROM users WHERE username = ?", (target_text,)
        ) as cur:
            target_row = await cur.fetchone()

    if not target_row:
        await msg.answer("❌ Игрок не найден!", reply_markup=back_kb("economy_menu"))
        await state.clear()
        return

    if target_row["user_id"] == msg.from_user.id:
        await msg.answer("❌ Нельзя переводить себе!", reply_markup=back_kb("economy_menu"))
        await state.clear()
        return

    await state.update_data(target_id=target_row["user_id"], target_name=target_row["first_name"])
    await state.set_state(TransferState.waiting_amount)
    row = await Database.get_user(msg.from_user.id)
    await msg.answer(
        f"💸 Перевод игроку <b>{target_row['first_name']}</b>\n\n"
        f"💰 У тебя: <b>{format_number(row['balance'])} монет</b>\n\n"
        f"Введи сумму перевода:",
        reply_markup=back_kb("economy_menu"), parse_mode="HTML"
    )


@router.message(TransferState.waiting_amount)
async def transfer_amount(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    target_id = data["target_id"]
    target_name = data["target_name"]
    sender_id = msg.from_user.id

    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи корректное число!")
        return

    if amount < 1:
        await msg.answer("❌ Минимальный перевод: 1 монета!")
        return

    success = await Database.deduct_balance(sender_id, amount)
    if not success:
        await msg.answer("❌ Недостаточно монет!", reply_markup=back_kb("economy_menu"))
        await state.clear()
        return

    await Database.add_balance(target_id, amount)
    await state.clear()

    await log_action("transfer", sender_id, f"Перевод {amount} монет игроку {target_id}")
    await msg.answer(
        f"✅ <b>{format_number(amount)} монет</b> переведено игроку <b>{target_name}</b>!",
        reply_markup=back_kb("economy_menu"), parse_mode="HTML"
    )
    # Notify receiver
    try:
        sender_row = await Database.get_user(sender_id)
        from aiogram import Bot
        from config import BOT_TOKEN
        # We notify via bot instance from DI
    except Exception:
        pass


@router.callback_query(F.data == "tx_history")
async def tx_history(cb: CallbackQuery) -> None:
    db = await get_db()
    async with db.execute(
        """SELECT type, amount, description, timestamp
        FROM transactions WHERE user_id = ?
        ORDER BY timestamp DESC LIMIT 15""",
        (cb.from_user.id,)
    ) as cur:
        rows = await cur.fetchall()

    if not rows:
        text = "📋 <b>История транзакций</b>\n\nПусто."
    else:
        lines = ["📋 <b>История транзакций</b>\n"]
        for r in rows:
            t_type = "➕" if r["type"] == "credit" else "➖"
            ts = time.strftime("%d.%m %H:%M", time.localtime(r["timestamp"]))
            lines.append(f"{t_type} <b>{format_number(r['amount'])}</b> монет — {ts}")
        text = "\n".join(lines)

    await cb.message.edit_text(text, reply_markup=back_kb("economy_menu"), parse_mode="HTML")
    await cb.answer()
