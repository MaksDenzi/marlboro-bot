"""
Marlboro Project — Casino: Slots, Roulette, Dice, Blackjack, Coinflip
"""

import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database
from utils.keyboards import casino_menu_kb, roulette_color_kb, back_kb
from utils.texts import format_number
from utils.helpers import roll_slots, slots_result, blackjack_card, blackjack_total
from config import CASINO_MIN_BET, CASINO_MAX_BET

router = Router()


class CasinoState(StatesGroup):
    slots_bet = State()
    roulette_bet = State()
    roulette_color = State()
    dice_bet = State()
    bj_bet = State()
    bj_playing = State()
    coinflip_bet = State()
    coinflip_side = State()


@router.callback_query(F.data == "casino_menu")
async def casino_menu(cb: CallbackQuery) -> None:
    text = (
        "🎰 <b>Казино Marlboro</b>\n\n"
        "Испытай удачу! Выбери игру:\n\n"
        "🎰 Слоты — до 50x ставки!\n"
        "🎲 Кости — угадай результат\n"
        "🃏 Блэкджек — набери 21 очко\n"
        "🎡 Рулетка — выбери цвет\n"
        "🪙 Монетка — 50/50, двойной выигрыш\n\n"
        f"⚠️ Мин. ставка: {format_number(CASINO_MIN_BET)} | Макс.: {format_number(CASINO_MAX_BET)}"
    )
    await cb.message.edit_text(text, reply_markup=casino_menu_kb(), parse_mode="HTML")
    await cb.answer()


# ── Slots ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "slots")
@router.message(Command("slots"))
async def slots_start(event, state: FSMContext) -> None:
    await state.set_state(CasinoState.slots_bet)
    text = "🎰 <b>Игровые автоматы</b>\n\nВведи ставку (монет):"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("casino_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb("casino_menu"), parse_mode="HTML")


@router.message(CasinoState.slots_bet)
async def slots_play(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    try:
        bet = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return

    if bet < CASINO_MIN_BET:
        await msg.answer(f"❌ Минимальная ставка: {CASINO_MIN_BET} монет!")
        return
    if bet > CASINO_MAX_BET:
        await msg.answer(f"❌ Максимальная ставка: {format_number(CASINO_MAX_BET)} монет!")
        return

    ok = await Database.deduct_balance(user_id, bet)
    if not ok:
        await msg.answer("❌ Недостаточно монет!", reply_markup=back_kb("casino_menu"))
        await state.clear()
        return

    s1, s2, s3 = roll_slots()
    mult, result_msg = slots_result(s1, s2, s3)
    winnings = int(bet * mult)

    if winnings > 0:
        await Database.add_balance(user_id, winnings)

    net = winnings - bet
    net_str = f"+{format_number(net)}" if net >= 0 else format_number(net)

    text = (
        f"🎰 <b>Слоты</b>\n\n"
        f"┌ {s1} ┬ {s2} ┬ {s3} ┐\n\n"
        f"<b>{result_msg}</b>\n\n"
        f"Ставка: {format_number(bet)}\n"
        f"Выигрыш: {format_number(winnings)}\n"
        f"Итог: <b>{net_str} монет</b>"
    )
    await state.clear()
    await msg.answer(text, reply_markup=back_kb("casino_menu"), parse_mode="HTML")


# ── Roulette ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "roulette_menu")
@router.message(Command("roulette"))
async def roulette_start(event, state: FSMContext) -> None:
    await state.set_state(CasinoState.roulette_bet)
    text = "🎡 <b>Рулетка</b>\n\nВведи ставку (монет):"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("casino_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb("casino_menu"), parse_mode="HTML")


@router.message(CasinoState.roulette_bet)
async def roulette_bet(msg: Message, state: FSMContext) -> None:
    try:
        bet = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if bet < CASINO_MIN_BET or bet > CASINO_MAX_BET:
        await msg.answer(f"❌ Ставка: {CASINO_MIN_BET}–{format_number(CASINO_MAX_BET)} монет!")
        return
    await state.update_data(bet=bet)
    await state.set_state(CasinoState.roulette_color)
    await msg.answer(
        f"🎡 Ставка: <b>{format_number(bet)} монет</b>\n\nВыбери цвет:",
        reply_markup=roulette_color_kb(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("roulette:"), CasinoState.roulette_color)
async def roulette_play(cb: CallbackQuery, state: FSMContext) -> None:
    color = cb.data.split(":")[1]
    data = await state.get_data()
    bet = data["bet"]
    user_id = cb.from_user.id

    ok = await Database.deduct_balance(user_id, bet)
    if not ok:
        await cb.answer("❌ Недостаточно монет!", show_alert=True)
        await state.clear()
        return

    number = random.randint(0, 36)
    if number == 0:
        spin_color = "green"
        emoji = "🟢"
    elif number % 2 == 1:
        spin_color = "red"
        emoji = "🔴"
    else:
        spin_color = "black"
        emoji = "⚫"

    mult = {"red": 2, "black": 2, "green": 14}.get(color, 2)
    win = spin_color == color

    winnings = bet * mult if win else 0
    if winnings:
        await Database.add_balance(user_id, winnings)

    net = winnings - bet
    net_str = f"+{format_number(net)}" if net >= 0 else format_number(net)

    await cb.message.edit_text(
        f"🎡 <b>Рулетка</b>\n\n"
        f"Выпало: {emoji} <b>{number}</b>\n\n"
        f"{'🎉 Победа!' if win else '😞 Проигрыш'}\n"
        f"Ставка: {format_number(bet)} | Итог: <b>{net_str} монет</b>",
        reply_markup=back_kb("casino_menu"), parse_mode="HTML"
    )
    await state.clear()
    await cb.answer()


# ── Dice ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "dice_game")
@router.message(Command("dice"))
async def dice_start(event, state: FSMContext) -> None:
    await state.set_state(CasinoState.dice_bet)
    text = "🎲 <b>Кости</b>\n\nВведи ставку. Выкинь больше, чем бот!\nРавно — ничья (ставка возвращается)."
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("casino_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(CasinoState.dice_bet)
async def dice_play(msg: Message, state: FSMContext) -> None:
    try:
        bet = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if bet < CASINO_MIN_BET or bet > CASINO_MAX_BET:
        await msg.answer(f"❌ Ставка: {CASINO_MIN_BET}–{format_number(CASINO_MAX_BET)}!")
        return

    ok = await Database.deduct_balance(msg.from_user.id, bet)
    if not ok:
        await msg.answer("❌ Недостаточно монет!", reply_markup=back_kb("casino_menu"))
        await state.clear()
        return

    player = random.randint(1, 6)
    bot_roll = random.randint(1, 6)

    if player > bot_roll:
        winnings = bet * 2
        result = "🎉 Победа!"
    elif player == bot_roll:
        winnings = bet
        result = "🤝 Ничья!"
    else:
        winnings = 0
        result = "😞 Проигрыш!"

    if winnings:
        await Database.add_balance(msg.from_user.id, winnings)

    net = winnings - bet
    net_str = f"+{format_number(net)}" if net >= 0 else format_number(net)

    await msg.answer(
        f"🎲 <b>Кости</b>\n\n"
        f"Ты: <b>{player}</b>  🆚  Бот: <b>{bot_roll}</b>\n\n"
        f"<b>{result}</b>\n"
        f"Ставка: {format_number(bet)} | Итог: <b>{net_str}</b>",
        reply_markup=back_kb("casino_menu"), parse_mode="HTML"
    )
    await state.clear()


# ── Coinflip ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "coinflip")
@router.message(Command("coinflip"))
async def coinflip_start(event, state: FSMContext) -> None:
    await state.set_state(CasinoState.coinflip_bet)
    text = "🪙 <b>Монетка</b>\n\nВведи ставку:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("casino_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(CasinoState.coinflip_bet)
async def coinflip_bet(msg: Message, state: FSMContext) -> None:
    try:
        bet = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if bet < CASINO_MIN_BET or bet > CASINO_MAX_BET:
        await msg.answer(f"❌ Ставка: {CASINO_MIN_BET}–{format_number(CASINO_MAX_BET)}!")
        return
    await state.update_data(bet=bet)
    await state.set_state(CasinoState.coinflip_side)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="👑 Орёл", callback_data="cf:heads"),
        InlineKeyboardButton(text="🔵 Решка", callback_data="cf:tails"),
    ]])
    await msg.answer(
        f"🪙 Ставка: <b>{format_number(bet)}</b>\nВыбери сторону:",
        reply_markup=kb, parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("cf:"), CasinoState.coinflip_side)
async def coinflip_play(cb: CallbackQuery, state: FSMContext) -> None:
    choice = cb.data.split(":")[1]
    data = await state.get_data()
    bet = data["bet"]

    ok = await Database.deduct_balance(cb.from_user.id, bet)
    if not ok:
        await cb.answer("❌ Недостаточно монет!", show_alert=True)
        await state.clear()
        return

    result = random.choice(["heads", "tails"])
    win = result == choice
    winnings = bet * 2 if win else 0
    if winnings:
        await Database.add_balance(cb.from_user.id, winnings)

    res_emoji = "👑" if result == "heads" else "🔵"
    net = winnings - bet
    net_str = f"+{format_number(net)}" if net >= 0 else format_number(net)

    await cb.message.edit_text(
        f"🪙 <b>Монетка</b>\n\n"
        f"Выпало: {res_emoji} {'Орёл' if result=='heads' else 'Решка'}\n\n"
        f"{'🎉 Победа!' if win else '😞 Проигрыш!'}\n"
        f"Итог: <b>{net_str} монет</b>",
        reply_markup=back_kb("casino_menu"), parse_mode="HTML"
    )
    await state.clear()
    await cb.answer()


@router.callback_query(F.data == "casino_stats")
async def casino_stats(cb: CallbackQuery) -> None:
    await cb.answer("📊 Статистика казино скоро появится!", show_alert=False)
