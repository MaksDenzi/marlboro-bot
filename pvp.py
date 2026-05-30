"""
Marlboro Project — PvP / Duels system
"""

import random
import time
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import pvp_menu_kb, duel_accept_kb, back_kb
from utils.helpers import ts_now, mention
from utils.texts import format_number
from utils.logger import log_action
from config import OWNER_ID

router = Router()


class DuelState(StatesGroup):
    waiting_opponent = State()
    waiting_bet = State()


@router.callback_query(F.data == "pvp_menu")
async def pvp_menu(cb: CallbackQuery) -> None:
    row = await Database.get_user(cb.from_user.id)
    text = (
        f"⚔️ <b>PvP / Дуэли</b>\n\n"
        f"Твоя статистика:\n"
        f"✅ Победы: <b>{row['pvp_wins']}</b>\n"
        f"❌ Поражения: <b>{row['pvp_losses']}</b>\n"
        f"⚔️ Атака: <b>{row['attack']}</b>  🛡️ Защита: <b>{row['defense']}</b>\n\n"
        f"В дуэли победитель получает ставку обоих игроков!"
    )
    await cb.message.edit_text(text, reply_markup=pvp_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "duel_start")
@router.message(Command("duel"))
async def duel_start(event, state: FSMContext) -> None:
    await state.set_state(DuelState.waiting_opponent)
    text = "⚔️ <b>Дуэль</b>\n\nВведи @username или ID противника:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("pvp_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(DuelState.waiting_opponent)
async def duel_opponent(msg: Message, state: FSMContext) -> None:
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
        await msg.answer("❌ Игрок не найден!", reply_markup=back_kb("pvp_menu"))
        await state.clear()
        return
    if target_row["user_id"] == msg.from_user.id:
        await msg.answer("❌ Нельзя вызвать себя на дуэль!")
        return
    if target_row["is_banned"]:
        await msg.answer("❌ Этот игрок заблокирован!")
        await state.clear()
        return

    await state.update_data(opponent_id=target_row["user_id"], opponent_name=target_row["first_name"])
    await state.set_state(DuelState.waiting_bet)
    row = await Database.get_user(msg.from_user.id)
    await msg.answer(
        f"⚔️ Дуэль с <b>{target_row['first_name']}</b>\n\n"
        f"💰 Твой баланс: <b>{format_number(row['balance'])}</b>\n\n"
        f"Введи ставку (0 = без ставки):",
        reply_markup=back_kb("pvp_menu"), parse_mode="HTML"
    )


@router.message(DuelState.waiting_bet)
async def duel_bet(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    opponent_id = data["opponent_id"]
    opponent_name = data["opponent_name"]
    challenger_id = msg.from_user.id

    try:
        bet = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if bet < 0:
        await msg.answer("❌ Ставка не может быть отрицательной!")
        return

    row = await Database.get_user(challenger_id)
    if bet > row["balance"]:
        await msg.answer("❌ Недостаточно монет для ставки!")
        return

    db = await get_db()
    await db.execute(
        "INSERT INTO duels (challenger, opponent, bet) VALUES (?, ?, ?)",
        (challenger_id, opponent_id, bet)
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid() as id") as cur:
        duel_id = (await cur.fetchone())["id"]

    await state.clear()
    challenger_name = msg.from_user.first_name

    await msg.answer(
        f"⚔️ <b>Вызов отправлен!</b>\n\n"
        f"Ждём, пока <b>{opponent_name}</b> примет дуэль.",
        parse_mode="HTML"
    )

    # Notify opponent
    try:
        from aiogram import Bot
        bot: Bot = msg.bot
        await bot.send_message(
            opponent_id,
            f"⚔️ <b>{challenger_name}</b> вызывает тебя на дуэль!\n"
            f"💰 Ставка: <b>{format_number(bet)} монет</b>\n\n"
            f"Принять или отклонить?",
            reply_markup=duel_accept_kb(duel_id),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("duel_accept:"))
async def duel_accept(cb: CallbackQuery) -> None:
    duel_id = int(cb.data.split(":")[1])
    user_id = cb.from_user.id
    db = await get_db()

    async with db.execute("SELECT * FROM duels WHERE id = ?", (duel_id,)) as cur:
        duel = await cur.fetchone()
    if not duel or duel["status"] != "pending":
        await cb.answer("❌ Дуэль недоступна.", show_alert=True)
        return
    if duel["opponent"] != user_id:
        await cb.answer("❌ Это не твоя дуэль!", show_alert=True)
        return

    challenger_row = await Database.get_user(duel["challenger"])
    opponent_row = await Database.get_user(user_id)
    bet = duel["bet"]

    # Check balances
    if bet > 0:
        if challenger_row["balance"] < bet:
            await cb.answer("❌ У вызывающего недостаточно монет!", show_alert=True)
            return
        if opponent_row["balance"] < bet:
            await cb.answer("❌ У тебя недостаточно монет!", show_alert=True)
            return

    # Battle calculation
    c_atk = challenger_row["attack"] + random.randint(0, 20)
    c_def = challenger_row["defense"]
    o_atk = opponent_row["attack"] + random.randint(0, 20)
    o_def = opponent_row["defense"]

    c_dmg = max(1, c_atk - o_def)
    o_dmg = max(1, o_atk - c_def)

    challenger_wins = c_dmg >= o_dmg

    winner_id = duel["challenger"] if challenger_wins else user_id
    loser_id = user_id if challenger_wins else duel["challenger"]
    winner_row = challenger_row if challenger_wins else opponent_row
    loser_row = opponent_row if challenger_wins else challenger_row

    if bet > 0:
        await Database.deduct_balance(loser_id, bet)
        await Database.add_balance(winner_id, bet * 2)

    await db.execute(
        "UPDATE duels SET status='finished', winner=?, finished_at=strftime('%s','now') WHERE id=?",
        (winner_id, duel_id)
    )
    await db.execute(
        "UPDATE users SET pvp_wins = pvp_wins + 1 WHERE user_id = ?", (winner_id,)
    )
    await db.execute(
        "UPDATE users SET pvp_losses = pvp_losses + 1 WHERE user_id = ?", (loser_id,)
    )
    await db.commit()

    xp_win = random.randint(30, 60)
    xp_loss = random.randint(10, 20)
    await Database.add_xp(winner_id, xp_win)
    await Database.add_xp(loser_id, xp_loss)

    result_text = (
        f"⚔️ <b>Дуэль завершена!</b>\n\n"
        f"🥊 {challenger_row['first_name']} (атака: {c_atk}) vs {opponent_row['first_name']} (атака: {o_atk})\n\n"
        f"🏆 Победитель: <b>{winner_row['first_name']}</b>\n"
        f"💰 Выигрыш: <b>{format_number(bet * 2 if bet > 0 else 0)} монет</b>"
    )

    await cb.message.edit_text(result_text, parse_mode="HTML")
    await cb.answer()

    try:
        await cb.bot.send_message(duel["challenger"], result_text, parse_mode="HTML")
    except Exception:
        pass

    await log_action("pvp", winner_id, f"Победил в дуэли #{duel_id}, выиграл {bet*2}")


@router.callback_query(F.data.startswith("duel_decline:"))
async def duel_decline(cb: CallbackQuery) -> None:
    duel_id = int(cb.data.split(":")[1])
    user_id = cb.from_user.id
    db = await get_db()

    async with db.execute("SELECT * FROM duels WHERE id = ?", (duel_id,)) as cur:
        duel = await cur.fetchone()
    if not duel or duel["opponent"] != user_id:
        await cb.answer("❌ Ошибка.", show_alert=True)
        return

    await db.execute("UPDATE duels SET status='declined' WHERE id=?", (duel_id,))
    await db.commit()
    await cb.message.edit_text("❌ <b>Дуэль отклонена.</b>", parse_mode="HTML")
    await cb.answer()
    try:
        await cb.bot.send_message(duel["challenger"], f"❌ {cb.from_user.first_name} отклонил(а) твой вызов.")
    except Exception:
        pass


@router.callback_query(F.data == "pvp_stats")
@router.callback_query(F.data == "duel_list")
async def pvp_stats(cb: CallbackQuery) -> None:
    row = await Database.get_user(cb.from_user.id)
    db = await get_db()
    async with db.execute(
        """SELECT d.*, u.first_name as opp_name
        FROM duels d JOIN users u ON (
            CASE WHEN d.challenger = ? THEN d.opponent ELSE d.challenger END = u.user_id
        )
        WHERE (d.challenger = ? OR d.opponent = ?) AND d.status = 'finished'
        ORDER BY d.finished_at DESC LIMIT 5""",
        (cb.from_user.id, cb.from_user.id, cb.from_user.id)
    ) as cur:
        recent = await cur.fetchall()

    lines = [
        f"📊 <b>PvP Статистика</b>\n",
        f"✅ Победы: <b>{row['pvp_wins']}</b>",
        f"❌ Поражения: <b>{row['pvp_losses']}</b>",
        f"\n<b>Последние дуэли:</b>",
    ]
    for d in recent:
        won = d["winner"] == cb.from_user.id
        sign = "✅" if won else "❌"
        lines.append(f"{sign} vs {d['opp_name']} — {'Победа' if won else 'Поражение'}")

    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("pvp_menu"), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "top_pvp")
async def top_pvp(cb: CallbackQuery) -> None:
    top = await Database.get_top_users("pvp_wins", 10)
    lines = ["🏆 <b>Топ PvP (победы)</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = u["first_name"] or "Игрок"
        lines.append(f"{medal} <b>{name}</b> — {u['pvp_wins']} побед")
    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("pvp_menu"), parse_mode="HTML")
    await cb.answer()
