"""
Marlboro Project — Clan system
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import clan_menu_kb, back_kb, confirm_kb
from utils.texts import format_number
from utils.logger import log_action
from config import CLAN_CREATE_PRICE, CLAN_MAX_MEMBERS

router = Router()


class ClanState(StatesGroup):
    create_name = State()
    create_tag = State()
    create_desc = State()
    search_query = State()
    invite_user = State()


@router.callback_query(F.data == "clan_menu")
@router.message(Command("clan"))
async def clan_menu(event) -> None:
    user_id = event.from_user.id
    clan = await Database.get_user_clan(user_id)
    in_clan = clan is not None
    text = (
        f"🏴 <b>Кланы</b>\n\n"
        f"{'Ты состоишь в клане: <b>' + clan['name'] + '</b>' if in_clan else 'Ты не состоишь в клане.'}\n\n"
        f"Создание клана: <b>{format_number(CLAN_CREATE_PRICE)} монет</b>"
    )
    kb = clan_menu_kb(in_clan)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "clan_create")
async def clan_create_start(cb: CallbackQuery, state: FSMContext) -> None:
    clan = await Database.get_user_clan(cb.from_user.id)
    if clan:
        await cb.answer("❌ Ты уже в клане!", show_alert=True)
        return
    await state.set_state(ClanState.create_name)
    await cb.message.edit_text(
        f"🏴 <b>Создание клана</b>\n\nСтоимость: <b>{format_number(CLAN_CREATE_PRICE)} монет</b>\n\n"
        f"Введи название клана (3–30 символов):",
        reply_markup=back_kb("clan_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(ClanState.create_name)
async def clan_create_name(msg: Message, state: FSMContext) -> None:
    name = msg.text.strip()
    if len(name) < 3 or len(name) > 30:
        await msg.answer("❌ Название: 3–30 символов!")
        return
    await state.update_data(name=name)
    await state.set_state(ClanState.create_tag)
    await msg.answer("Введи тег клана (2–6 символов, только буквы и цифры):")


@router.message(ClanState.create_tag)
async def clan_create_tag(msg: Message, state: FSMContext) -> None:
    tag = msg.text.strip().upper()
    if not tag.isalnum() or len(tag) < 2 or len(tag) > 6:
        await msg.answer("❌ Тег: 2–6 символов, только буквы и цифры!")
        return
    await state.update_data(tag=tag)
    await state.set_state(ClanState.create_desc)
    await msg.answer("Введи описание клана (до 100 символов, или пропусти командой /skip):")


@router.message(ClanState.create_desc)
async def clan_create_desc(msg: Message, state: FSMContext) -> None:
    desc = "" if msg.text.strip() == "/skip" else msg.text.strip()[:100]
    data = await state.get_data()
    user_id = msg.from_user.id

    ok = await Database.deduct_balance(user_id, CLAN_CREATE_PRICE)
    if not ok:
        await msg.answer(
            f"❌ Недостаточно монет! Нужно {format_number(CLAN_CREATE_PRICE)}.",
            reply_markup=back_kb("clan_menu")
        )
        await state.clear()
        return

    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO clans (name, tag, description, owner_id) VALUES (?, ?, ?, ?)",
            (data["name"], data["tag"], desc, user_id)
        )
        await db.commit()
        async with db.execute("SELECT last_insert_rowid() as id") as cur:
            clan_id = (await cur.fetchone())["id"]
        await db.execute(
            "INSERT INTO clan_members (clan_id, user_id, role) VALUES (?, ?, 'owner')", (clan_id, user_id)
        )
        await db.commit()
    except Exception:
        await Database.add_balance(user_id, CLAN_CREATE_PRICE)
        await msg.answer("❌ Клан с таким именем или тегом уже существует!", reply_markup=back_kb("clan_menu"))
        await state.clear()
        return

    await state.clear()
    await log_action("clan", user_id, f"Создал клан [{data['tag']}] {data['name']}")
    await msg.answer(
        f"🏴 <b>Клан [{data['tag']}] {data['name']} создан!</b>\n\nОпиcание: {desc or '—'}",
        reply_markup=back_kb("clan_menu"), parse_mode="HTML"
    )


@router.callback_query(F.data == "clan_info")
async def clan_info(cb: CallbackQuery) -> None:
    clan = await Database.get_user_clan(cb.from_user.id)
    if not clan:
        await cb.answer("❌ Ты не в клане!", show_alert=True)
        return

    db = await get_db()
    async with db.execute("SELECT COUNT(*) as cnt FROM clan_members WHERE clan_id = ?", (clan["id"],)) as cur:
        cnt = (await cur.fetchone())["cnt"]

    owner = await Database.get_user(clan["owner_id"])
    text = (
        f"🏴 <b>[{clan['tag']}] {clan['name']}</b>\n\n"
        f"📝 {clan['description'] or '—'}\n\n"
        f"👑 Лидер: <b>{owner['first_name'] if owner else '?'}</b>\n"
        f"👥 Участников: <b>{cnt}/{CLAN_MAX_MEMBERS}</b>\n"
        f"📊 Уровень: <b>{clan['level']}</b>\n"
        f"💰 Казна: <b>{format_number(clan['balance'])}</b>"
    )
    await cb.message.edit_text(text, reply_markup=back_kb("clan_menu"), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "clan_members")
async def clan_members(cb: CallbackQuery) -> None:
    clan = await Database.get_user_clan(cb.from_user.id)
    if not clan:
        await cb.answer("❌ Ты не в клане!", show_alert=True)
        return
    db = await get_db()
    async with db.execute(
        """SELECT u.first_name, u.level, cm.role FROM clan_members cm
        JOIN users u ON cm.user_id = u.user_id
        WHERE cm.clan_id = ? ORDER BY cm.role DESC, u.level DESC""",
        (clan["id"],)
    ) as cur:
        members = await cur.fetchall()
    role_emoji = {"owner": "👑", "officer": "⭐", "member": "👤"}
    lines = [f"👥 <b>Участники клана [{clan['tag']}]</b>\n"]
    for m in members:
        lines.append(f"{role_emoji.get(m['role'],'👤')} {m['first_name']} (ур. {m['level']}) — {m['role']}")
    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("clan_menu"), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "clan_list")
async def clan_list(cb: CallbackQuery) -> None:
    db = await get_db()
    async with db.execute(
        "SELECT name, tag, level, members, description FROM clans ORDER BY level DESC, members DESC LIMIT 10"
    ) as cur:
        clans = await cur.fetchall()
    if not clans:
        await cb.answer("Кланов пока нет!", show_alert=True)
        return
    lines = ["🏴 <b>Топ кланов</b>\n"]
    for c in clans:
        lines.append(f"[{c['tag']}] <b>{c['name']}</b> — ур.{c['level']}, {c['members']} чел.")
    await cb.message.edit_text("\n".join(lines), reply_markup=back_kb("clan_menu"), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "clan_leave")
async def clan_leave_confirm(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "⚠️ Ты уверен, что хочешь покинуть клан?",
        reply_markup=confirm_kb("clan_leave_yes", "clan_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "clan_leave_yes")
async def clan_leave_yes(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    clan = await Database.get_user_clan(user_id)
    if not clan:
        await cb.answer("Ты не в клане!", show_alert=True)
        return
    db = await get_db()
    if clan["owner_id"] == user_id:
        await cb.answer("❌ Ты лидер клана — передай руководство сначала!", show_alert=True)
        return
    await db.execute("DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?", (clan["id"], user_id))
    await db.execute("UPDATE clans SET members = members - 1 WHERE id = ?", (clan["id"],))
    await db.commit()
    await cb.message.edit_text("✅ Ты покинул клан.", reply_markup=back_kb("clan_menu"), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data == "clan_search")
async def clan_search_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ClanState.search_query)
    await cb.message.edit_text(
        "🔍 Введи название или тег клана для поиска:",
        reply_markup=back_kb("clan_menu")
    )
    await cb.answer()


@router.message(ClanState.search_query)
async def clan_search_results(msg: Message, state: FSMContext) -> None:
    query = f"%{msg.text.strip()}%"
    db = await get_db()
    async with db.execute(
        "SELECT id, name, tag, level, members, description FROM clans WHERE name LIKE ? OR tag LIKE ? LIMIT 5",
        (query, query)
    ) as cur:
        results = await cur.fetchall()

    await state.clear()
    if not results:
        await msg.answer("🔍 Кланов не найдено.", reply_markup=back_kb("clan_menu"))
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()
    lines = ["🔍 <b>Результаты поиска:</b>\n"]
    for c in results:
        lines.append(f"[{c['tag']}] <b>{c['name']}</b> — ур.{c['level']}, {c['members']} чел.")
        b.row(InlineKeyboardButton(
            text=f"[{c['tag']}] {c['name']} — Вступить",
            callback_data=f"clan_join:{c['id']}"
        ))
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="clan_menu"))
    await msg.answer("\n".join(lines), reply_markup=b.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("clan_join:"))
async def clan_join(cb: CallbackQuery) -> None:
    clan_id = int(cb.data.split(":")[1])
    user_id = cb.from_user.id
    existing = await Database.get_user_clan(user_id)
    if existing:
        await cb.answer("❌ Ты уже в клане!", show_alert=True)
        return
    db = await get_db()
    async with db.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)) as cur:
        clan = await cur.fetchone()
    if not clan or clan["members"] >= CLAN_MAX_MEMBERS:
        await cb.answer("❌ Клан переполнен или не существует!", show_alert=True)
        return
    await db.execute("INSERT INTO clan_members (clan_id, user_id) VALUES (?, ?)", (clan_id, user_id))
    await db.execute("UPDATE clans SET members = members + 1 WHERE id = ?", (clan_id,))
    await db.commit()
    await cb.message.edit_text(
        f"✅ Ты вступил в клан <b>[{clan['tag']}] {clan['name']}</b>!",
        reply_markup=back_kb("clan_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "clan_treasury")
async def clan_treasury(cb: CallbackQuery) -> None:
    clan = await Database.get_user_clan(cb.from_user.id)
    if not clan:
        await cb.answer("❌ Ты не в клане!", show_alert=True)
        return
    await cb.message.edit_text(
        f"💰 <b>Казна клана [{clan['tag']}]</b>\n\n"
        f"Баланс: <b>{format_number(clan['balance'])} монет</b>",
        reply_markup=back_kb("clan_menu"), parse_mode="HTML"
    )
    await cb.answer()
