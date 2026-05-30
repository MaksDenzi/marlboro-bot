"""
Marlboro Project — RP (Role-Play) commands
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import rp_menu_kb, back_kb
from utils.helpers import RP_ACTIONS, mention

router = Router()


class RPState(StatesGroup):
    choose_target = State()
    action = State()


@router.callback_query(F.data == "rp_menu")
async def rp_menu(cb: CallbackQuery) -> None:
    text = (
        "🎭 <b>RP Команды</b>\n\n"
        "Взаимодействуй с другими игроками!\n"
        "Выбери действие:"
    )
    await cb.message.edit_text(text, reply_markup=rp_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("rp:"))
async def rp_action_start(cb: CallbackQuery, state: FSMContext) -> None:
    action = cb.data.split(":")[1]
    if action not in RP_ACTIONS:
        await cb.answer("❌ Действие не найдено", show_alert=True)
        return
    await state.set_state(RPState.choose_target)
    await state.update_data(action=action)
    await cb.message.edit_text(
        f"🎭 Введи @username или ID цели для действия «{RP_ACTIONS[action]['emoji']} {RP_ACTIONS[action]['text'].split('{')[0].strip()}»:",
        reply_markup=back_kb("rp_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(RPState.choose_target)
async def rp_execute(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    action = data.get("action", "hug")
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

    await state.clear()

    if not target_row:
        await msg.answer("❌ Игрок не найден!", reply_markup=back_kb("rp_menu"))
        return

    act = RP_ACTIONS[action]
    from_name = mention(msg.from_user.id, msg.from_user.first_name)
    to_name = mention(target_row["user_id"], target_row["first_name"])
    text = act["text"].replace("{from}", from_name).replace("{to}", to_name)

    await msg.answer(text, reply_markup=back_kb("rp_menu"), parse_mode="HTML")

    # Notify target
    try:
        await msg.bot.send_message(
            target_row["user_id"],
            f"🎭 {text}",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ── Text-based RP commands ────────────────────────────────────────────────────

@router.message(Command("hug"))
async def cmd_hug(msg: Message) -> None:
    await _rp_cmd(msg, "hug")


@router.message(Command("kiss"))
async def cmd_kiss(msg: Message) -> None:
    await _rp_cmd(msg, "kiss")


@router.message(Command("punch"))
async def cmd_punch(msg: Message) -> None:
    await _rp_cmd(msg, "punch")


@router.message(Command("dance"))
async def cmd_dance(msg: Message) -> None:
    await _rp_cmd(msg, "dance")


async def _rp_cmd(msg: Message, action: str) -> None:
    if not msg.reply_to_message:
        await msg.answer(f"❌ Ответь на сообщение игрока чтобы использовать /{action}!")
        return
    target = msg.reply_to_message.from_user
    if not target or target.is_bot or target.id == msg.from_user.id:
        await msg.answer("❌ Некорректная цель!")
        return
    act = RP_ACTIONS.get(action, RP_ACTIONS["hug"])
    from_name = mention(msg.from_user.id, msg.from_user.first_name)
    to_name = mention(target.id, target.first_name)
    text = act["text"].replace("{from}", from_name).replace("{to}", to_name)
    await msg.answer(text, parse_mode="HTML")
