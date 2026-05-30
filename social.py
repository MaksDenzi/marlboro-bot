"""
Marlboro Project — Marriage & Friends
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import social_menu_kb, back_kb, confirm_kb
from utils.helpers import mention
from utils.logger import log_action

router = Router()


class MarryState(StatesGroup):
    target = State()


class FriendState(StatesGroup):
    target = State()


@router.callback_query(F.data == "social_menu")
async def social_menu(cb: CallbackQuery) -> None:
    row = await Database.get_user(cb.from_user.id)
    spouse_text = "Холост(а)"
    if row["spouse_id"]:
        sp = await Database.get_user(row["spouse_id"])
        spouse_text = f"💍 Женат/Замужем — {sp['first_name'] if sp else '?'}"

    db = await get_db()
    async with db.execute(
        "SELECT COUNT(*) as cnt FROM friends WHERE (user_id=? OR friend_id=?) AND status='accepted'",
        (cb.from_user.id, cb.from_user.id)
    ) as cur:
        friend_cnt = (await cur.fetchone())["cnt"]

    text = (
        f"👨‍👩‍👧‍👦 <b>Семья и Друзья</b>\n\n"
        f"💑 Статус: {spouse_text}\n"
        f"🤝 Друзей: {friend_cnt}"
    )
    await cb.message.edit_text(text, reply_markup=social_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "marry_propose")
@router.message(Command("marry"))
async def marry_propose_start(event, state: FSMContext) -> None:
    await state.set_state(MarryState.target)
    text = "💍 <b>Предложение руки и сердца</b>\n\nВведи @username или ID:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("social_menu"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(MarryState.target)
async def marry_propose(msg: Message, state: FSMContext) -> None:
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
        await msg.answer("❌ Игрок не найден!", reply_markup=back_kb("social_menu"))
        return
    if target_row["user_id"] == msg.from_user.id:
        await msg.answer("❌ Нельзя предложить себе!")
        return

    row = await Database.get_user(msg.from_user.id)
    if row["spouse_id"]:
        await msg.answer("❌ Ты уже состоишь в браке! Сначала разведись.", reply_markup=back_kb("social_menu"))
        return
    if target_row["spouse_id"]:
        await msg.answer("❌ Этот игрок уже в браке!", reply_markup=back_kb("social_menu"))
        return

    # Check for ring
    ring = await Database.get_item_in_inventory(msg.from_user.id, 36)
    if not ring:
        await msg.answer(
            "💍 Для предложения нужно кольцо помолвки!\nКупи в магазине (💎 Особые предметы).",
            reply_markup=back_kb("social_menu")
        )
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Принять!", callback_data=f"marry_accept:{msg.from_user.id}"),
        InlineKeyboardButton(text="💔 Отклонить", callback_data=f"marry_decline:{msg.from_user.id}"),
    ]])

    await msg.answer(f"💍 Предложение отправлено <b>{target_row['first_name']}</b>!", parse_mode="HTML")
    try:
        await msg.bot.send_message(
            target_row["user_id"],
            f"💍 <b>{msg.from_user.first_name}</b> делает тебе предложение!\n\nТы принимаешь?",
            reply_markup=kb, parse_mode="HTML"
        )
    except Exception:
        await msg.answer("❌ Не удалось отправить предложение — игрок недоступен.")


@router.callback_query(F.data.startswith("marry_accept:"))
async def marry_accept(cb: CallbackQuery) -> None:
    proposer_id = int(cb.data.split(":")[1])
    accepter_id = cb.from_user.id
    proposer = await Database.get_user(proposer_id)
    accepter = await Database.get_user(accepter_id)

    if not proposer or not accepter:
        await cb.answer("❌ Ошибка!", show_alert=True)
        return
    if proposer["spouse_id"] or accepter["spouse_id"]:
        await cb.answer("❌ Один из игроков уже в браке!", show_alert=True)
        return

    await Database.remove_item(proposer_id, 36, 1)
    await Database.update_user(proposer_id, spouse_id=accepter_id)
    await Database.update_user(accepter_id, spouse_id=proposer_id)

    from database.db import get_db as gdb
    db = await gdb()
    await db.execute("INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, 'married')", (proposer_id,))
    await db.execute("INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, 'married')", (accepter_id,))
    await db.commit()

    await cb.message.edit_text(
        f"💍 <b>{proposer['first_name']}</b> и <b>{accepter['first_name']}</b> теперь женаты! 🎊",
        parse_mode="HTML"
    )
    await cb.answer("💍 Поздравляем!")
    try:
        await cb.bot.send_message(proposer_id, f"💍 <b>{accepter['first_name']}</b> приняла(принял) предложение! Вы женаты! 🎊", parse_mode="HTML")
    except Exception:
        pass
    await log_action("social", proposer_id, f"Женился на {accepter_id}")


@router.callback_query(F.data.startswith("marry_decline:"))
async def marry_decline(cb: CallbackQuery) -> None:
    proposer_id = int(cb.data.split(":")[1])
    await cb.message.edit_text("💔 Предложение отклонено.")
    await cb.answer()
    try:
        await cb.bot.send_message(proposer_id, f"💔 {cb.from_user.first_name} отклонил(а) твоё предложение.")
    except Exception:
        pass


@router.callback_query(F.data == "marry_divorce")
async def marry_divorce(cb: CallbackQuery) -> None:
    row = await Database.get_user(cb.from_user.id)
    if not row["spouse_id"]:
        await cb.answer("❌ Ты не состоишь в браке!", show_alert=True)
        return
    await cb.message.edit_text(
        "💔 Ты уверен, что хочешь развестись?",
        reply_markup=confirm_kb("marry_divorce_yes", "social_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "marry_divorce_yes")
async def marry_divorce_yes(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    row = await Database.get_user(user_id)
    spouse_id = row["spouse_id"]
    if not spouse_id:
        await cb.answer("Ты уже холост!", show_alert=True)
        return
    await Database.update_user(user_id, spouse_id=None)
    await Database.update_user(spouse_id, spouse_id=None)
    await cb.message.edit_text("💔 <b>Развод оформлен.</b>", reply_markup=back_kb("social_menu"), parse_mode="HTML")
    await cb.answer()
    try:
        await cb.bot.send_message(spouse_id, f"💔 {cb.from_user.first_name} подал(а) на развод.")
    except Exception:
        pass


@router.callback_query(F.data == "friend_add")
async def friend_add_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FriendState.target)
    await cb.message.edit_text(
        "🤝 <b>Добавить в друзья</b>\n\nВведи @username или ID:",
        reply_markup=back_kb("social_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(FriendState.target)
async def friend_add(msg: Message, state: FSMContext) -> None:
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
        await msg.answer("❌ Игрок не найден!", reply_markup=back_kb("social_menu"))
        return

    user_id = msg.from_user.id
    if target_row["user_id"] == user_id:
        await msg.answer("❌ Нельзя добавить себя!")
        return

    async with db.execute(
        "SELECT status FROM friends WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
        (user_id, target_row["user_id"], target_row["user_id"], user_id)
    ) as cur:
        existing = await cur.fetchone()

    if existing:
        status = existing["status"]
        await msg.answer(f"❌ Уже {('в друзьях' if status == 'accepted' else 'ждёт ответа')}!")
        return

    await db.execute(
        "INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)",
        (user_id, target_row["user_id"])
    )
    await db.commit()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Принять", callback_data=f"friend_accept:{user_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"friend_decline:{user_id}"),
    ]])
    await msg.answer(f"✅ Запрос дружбы отправлен <b>{target_row['first_name']}</b>!", parse_mode="HTML")
    try:
        await msg.bot.send_message(
            target_row["user_id"],
            f"🤝 <b>{msg.from_user.first_name}</b> хочет добавить тебя в друзья!",
            reply_markup=kb, parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("friend_accept:"))
async def friend_accept(cb: CallbackQuery) -> None:
    requester_id = int(cb.data.split(":")[1])
    db = await get_db()
    await db.execute(
        "UPDATE friends SET status='accepted' WHERE user_id=? AND friend_id=?",
        (requester_id, cb.from_user.id)
    )
    await db.commit()
    await cb.message.edit_text(f"🤝 Вы теперь друзья с {cb.from_user.first_name}!")
    await cb.answer("🤝 Друг добавлен!")


@router.callback_query(F.data.startswith("friend_decline:"))
async def friend_decline(cb: CallbackQuery) -> None:
    requester_id = int(cb.data.split(":")[1])
    db = await get_db()
    await db.execute("DELETE FROM friends WHERE user_id=? AND friend_id=?", (requester_id, cb.from_user.id))
    await db.commit()
    await cb.message.edit_text("❌ Запрос отклонён.")
    await cb.answer()


@router.callback_query(F.data == "friend_list")
async def friend_list(cb: CallbackQuery) -> None:
    db = await get_db()
    async with db.execute(
        """SELECT u.first_name, u.level FROM users u
        JOIN friends f ON (f.friend_id = u.user_id OR f.user_id = u.user_id)
        WHERE (f.user_id = ? OR f.friend_id = ?) AND f.status = 'accepted'
        AND u.user_id != ?""",
        (cb.from_user.id, cb.from_user.id, cb.from_user.id)
    ) as cur:
        friends = await cur.fetchall()

    if not friends:
        text = "👥 <b>Друзья</b>\n\nУ тебя пока нет друзей."
    else:
        lines = ["👥 <b>Мои друзья</b>\n"]
        for f in friends:
            lines.append(f"🤝 {f['first_name']} (ур. {f['level']})")
        text = "\n".join(lines)

    await cb.message.edit_text(text, reply_markup=back_kb("social_menu"), parse_mode="HTML")
    await cb.answer()
