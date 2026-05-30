"""
Marlboro Project — Tester panel
Commands available to users with role 'tester' (or higher) in staff_roles.
"""

import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import Database, get_db
from utils.keyboards import tester_menu_kb, back_kb
from utils.texts import format_number
from config import OWNER_ID

router = Router()


# ── Role helpers ──────────────────────────────────────────────────────────────

async def is_tester_or_above(user_id: int) -> bool:
    """True for owner, admin, or tester."""
    if user_id == OWNER_ID:
        return True
    role = await Database.get_staff_role(user_id)
    return role in ("owner", "admin", "tester")


# ── /tpanel ───────────────────────────────────────────────────────────────────

@router.message(Command("tpanel"))
async def cmd_tpanel(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    role = await Database.get_staff_role(msg.from_user.id)
    role_label = {"owner": "👑 Владелец", "admin": "🛠️ Администратор", "tester": "🔬 Тестировщик"}.get(role or "", "❓")
    await msg.answer(
        f"🔬 <b>Панель тестировщика</b>\n\n"
        f"Роль: {role_label}\n\n"
        f"Используй кнопки или команды (/thelp):",
        reply_markup=tester_menu_kb(),
        parse_mode="HTML"
    )


# ── /thelp ────────────────────────────────────────────────────────────────────

@router.message(Command("thelp"))
async def cmd_thelp(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    text = (
        "🔬 <b>Команды тестировщика</b>\n\n"
        "<b>Панель:</b>\n"
        "  /tpanel — 🔬 Открыть панель тестировщика\n"
        "  /thelp — ℹ️ Эта справка\n\n"
        "<b>Предметы и ресурсы:</b>\n"
        "  /tgive &lt;item_id&gt; [кол-во] — 🎒 Выдать себе предмет по ID\n"
        "  /tcoin &lt;сумма&gt; — 💰 Выдать себе монеты\n\n"
        "<b>Кулдауны и прогресс:</b>\n"
        "  /treset — ⏰ Сбросить все кулдауны (работа/майнинг/ферма/ежедневный)\n"
        "  /tlevel &lt;уровень&gt; — 📈 Установить свой уровень\n\n"
        "<b>Информация:</b>\n"
        "  /itemlist [стр.] — 📋 Список всех предметов с ID\n"
        "  /tinfo &lt;user_id&gt; — 🔍 Подробная инфо об игроке\n"
        "  /tstats — 📊 Быстрая статистика бота\n\n"
        "<i>Все действия логируются администрацией.</i>"
    )
    await msg.answer(text, parse_mode="HTML")


# ── /tgive ────────────────────────────────────────────────────────────────────

class TGiveState(StatesGroup):
    item_id = State()
    amount = State()


@router.message(Command("tgive"))
async def cmd_tgive(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /tgive &lt;item_id&gt; [кол-во]\nПример: /tgive 5 3\n\nСписок предметов: /itemlist", parse_mode="HTML")
        return
    try:
        item_id = int(parts[1])
        amount = int(parts[2]) if len(parts) > 2 else 1
    except ValueError:
        await msg.answer("❌ Неверные параметры!")
        return
    if amount < 1 or amount > 9999:
        await msg.answer("❌ Количество от 1 до 9999!")
        return

    from utils.texts import get_item_data
    item = get_item_data(item_id)
    if not item:
        await msg.answer(f"❌ Предмет с ID <code>{item_id}</code> не найден!\nСписок: /itemlist", parse_mode="HTML")
        return

    await Database.add_item(msg.from_user.id, item_id, amount)
    await Database.admin_log(msg.from_user.id, "tester_give_item", msg.from_user.id, f"item={item_id} x{amount}")
    await msg.answer(
        f"✅ <b>{item['emoji']} {item['name']}</b> × {amount} выдан в инвентарь!\n"
        f"<i>ID предмета: #{item_id}</i>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "test_give_item")
async def cb_test_give_item(cb: CallbackQuery, state: FSMContext) -> None:
    if not await is_tester_or_above(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    await state.set_state(TGiveState.item_id)
    await cb.message.edit_text(
        "🎒 <b>Выдать предмет себе</b>\n\nВведи ID предмета (список: /itemlist):",
        reply_markup=back_kb("tpanel_menu"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(TGiveState.item_id)
async def tgive_item_id(msg: Message, state: FSMContext) -> None:
    try:
        item_id = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи числовой ID предмета!")
        return
    from utils.texts import get_item_data
    item = get_item_data(item_id)
    if not item:
        await msg.answer(f"❌ Предмет #{item_id} не найден! Список: /itemlist")
        return
    await state.update_data(item_id=item_id, item_name=item["name"], item_emoji=item.get("emoji", "📦"))
    await state.set_state(TGiveState.amount)
    await msg.answer(f"Предмет: {item.get('emoji', '')} <b>{item['name']}</b>\n\nКоличество:", parse_mode="HTML")


@router.message(TGiveState.amount)
async def tgive_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = int(msg.text.strip())
        if amount < 1:
            raise ValueError
    except ValueError:
        await msg.answer("❌ Введи положительное число!")
        return
    data = await state.get_data()
    await Database.add_item(msg.from_user.id, data["item_id"], amount)
    await Database.admin_log(msg.from_user.id, "tester_give_item", msg.from_user.id, f"item={data['item_id']} x{amount}")
    await state.clear()
    await msg.answer(
        f"✅ {data['item_emoji']} <b>{data['item_name']}</b> × {amount} добавлен в инвентарь!",
        reply_markup=tester_menu_kb(), parse_mode="HTML"
    )


# ── /tcoin ────────────────────────────────────────────────────────────────────

@router.message(Command("tcoin"))
async def cmd_tcoin(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /tcoin &lt;сумма&gt;\nПример: /tcoin 5000", parse_mode="HTML")
        return
    try:
        amount = int(parts[1])
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    if amount == 0:
        await msg.answer("❌ Сумма не может быть 0!")
        return
    if abs(amount) > 10_000_000:
        await msg.answer("❌ Максимум ±10,000,000 за раз!")
        return

    if amount > 0:
        await Database.add_balance(msg.from_user.id, amount)
        await msg.answer(f"✅ +<b>{format_number(amount)}</b> 💰 добавлено на баланс!", parse_mode="HTML")
    else:
        await Database.deduct_balance(msg.from_user.id, abs(amount))
        await msg.answer(f"✅ -<b>{format_number(abs(amount))}</b> 💰 снято с баланса!", parse_mode="HTML")
    await Database.admin_log(msg.from_user.id, "tester_give_coins", msg.from_user.id, str(amount))


@router.callback_query(F.data == "test_give_coins")
async def cb_test_give_coins(cb: CallbackQuery) -> None:
    if not await is_tester_or_above(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    await cb.message.edit_text(
        "💰 <b>Выдать монеты</b>\n\nОтправь: /tcoin &lt;сумма&gt;\nПример: /tcoin 10000\n\n<i>Отрицательное число = забрать монеты</i>",
        reply_markup=back_kb("tpanel_menu"), parse_mode="HTML"
    )
    await cb.answer()


# ── /treset ───────────────────────────────────────────────────────────────────

@router.message(Command("treset"))
async def cmd_treset(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    db = await get_db()
    await db.execute(
        "UPDATE users SET last_work=NULL, last_farm=NULL, last_mine=NULL, last_daily=NULL WHERE user_id=?",
        (msg.from_user.id,)
    )
    await db.commit()
    await Database.admin_log(msg.from_user.id, "tester_reset_cd", msg.from_user.id)
    await msg.answer(
        "✅ <b>Все кулдауны сброшены!</b>\n\n"
        "⏰ Работа — готово\n"
        "⛏️ Майнинг — готово\n"
        "🌾 Ферма — готово\n"
        "🎁 Ежедневный бонус — готово",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "test_reset_cd")
async def cb_test_reset_cd(cb: CallbackQuery) -> None:
    if not await is_tester_or_above(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    db = await get_db()
    await db.execute(
        "UPDATE users SET last_work=NULL, last_farm=NULL, last_mine=NULL, last_daily=NULL WHERE user_id=?",
        (cb.from_user.id,)
    )
    await db.commit()
    await Database.admin_log(cb.from_user.id, "tester_reset_cd", cb.from_user.id)
    await cb.answer("✅ Все кулдауны сброшены!", show_alert=True)


# ── /tlevel ───────────────────────────────────────────────────────────────────

@router.message(Command("tlevel"))
async def cmd_tlevel(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /tlevel &lt;уровень&gt;\nПример: /tlevel 10", parse_mode="HTML")
        return
    try:
        level = int(parts[1])
        if level < 1 or level > 999:
            raise ValueError
    except ValueError:
        await msg.answer("❌ Уровень от 1 до 999!")
        return

    from config import xp_for_level
    xp = xp_for_level(level)
    await Database.update_user(msg.from_user.id, level=level, xp=xp)
    await Database.admin_log(msg.from_user.id, "tester_set_level", msg.from_user.id, str(level))
    await msg.answer(
        f"✅ <b>Уровень установлен: {level}</b>\n"
        f"📈 XP: <code>{format_number(xp)}</code>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "test_set_level")
async def cb_test_set_level(cb: CallbackQuery) -> None:
    if not await is_tester_or_above(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    await cb.message.edit_text(
        "📈 <b>Установить уровень</b>\n\nОтправь: /tlevel &lt;уровень&gt;\nПример: /tlevel 25",
        reply_markup=back_kb("tpanel_menu"), parse_mode="HTML"
    )
    await cb.answer()


# ── /tinfo ────────────────────────────────────────────────────────────────────

@router.message(Command("tinfo"))
async def cmd_tinfo(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /tinfo &lt;user_id&gt;", parse_mode="HTML")
        return
    try:
        tid = int(parts[1])
    except ValueError:
        await msg.answer("❌ Введи числовой ID!")
        return

    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Игрок не найден!")
        return

    db = await get_db()
    async with db.execute("SELECT COUNT(*) as cnt FROM inventory WHERE user_id=?", (tid,)) as cur:
        inv_count = (await cur.fetchone())["cnt"]
    async with db.execute("SELECT COUNT(*) as cnt FROM friends WHERE user_id=? AND status='accepted'", (tid,)) as cur:
        friends_count = (await cur.fetchone())["cnt"]

    staff_role = await Database.get_staff_role(tid)
    staff_label = {"owner": "👑 Владелец", "admin": "🛠️ Администратор", "tester": "🔬 Тестировщик"}.get(staff_role or "", "👤 Игрок")

    def fmt_ts(ts):
        if not ts:
            return "—"
        return time.strftime("%d.%m.%y %H:%M", time.localtime(ts))

    text = (
        f"🔍 <b>Инфо об игроке</b>\n\n"
        f"🆔 ID: <code>{row['user_id']}</code>\n"
        f"👤 Имя: <b>{row['first_name']}</b> {row['last_name'] or ''}\n"
        f"📛 @{row['username'] or '—'}\n"
        f"🎖️ Роль: {staff_label}\n\n"
        f"📊 <b>Прогресс:</b>\n"
        f"  📈 Уровень: {row['level']} | XP: {format_number(row['xp'])}\n"
        f"  ❤️ HP: {row['health']}/{row['max_health']}\n"
        f"  ⚡ Энергия: {row['energy']}/100\n"
        f"  ⚔️ Атака: {row['attack']} | 🛡️ Защита: {row['defense']}\n\n"
        f"💰 <b>Экономика:</b>\n"
        f"  💵 Баланс: {format_number(row['balance'])}\n"
        f"  🏦 Банк: {format_number(row['bank'])}\n"
        f"  📈 Всего заработал: {format_number(row['total_earned'])}\n"
        f"  📉 Всего потратил: {format_number(row['total_spent'])}\n\n"
        f"⚔️ <b>PvP:</b> {row['pvp_wins']}W / {row['pvp_losses']}L\n"
        f"🎒 Предметов: {inv_count} | 🤝 Друзей: {friends_count}\n"
        f"💫 VIP: {row['vip_status']}\n"
        f"🚫 Бан: {'Да — ' + (row['ban_reason'] or '') if row['is_banned'] else 'Нет'}\n\n"
        f"🕐 <b>Временны́е метки:</b>\n"
        f"  Регистрация: {fmt_ts(row['registered_at'])}\n"
        f"  Последний вход: {fmt_ts(row['last_seen'])}\n"
        f"  Последняя работа: {fmt_ts(row['last_work'])}\n"
        f"  Последний майнинг: {fmt_ts(row['last_mine'])}\n"
        f"  Последняя ферма: {fmt_ts(row['last_farm'])}"
    )
    await msg.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "test_userinfo")
async def cb_test_userinfo(cb: CallbackQuery) -> None:
    if not await is_tester_or_above(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    await cb.message.edit_text(
        "🔍 <b>Инфо об игроке</b>\n\nОтправь: /tinfo &lt;user_id&gt;",
        reply_markup=back_kb("tpanel_menu"), parse_mode="HTML"
    )
    await cb.answer()


# ── /tstats ───────────────────────────────────────────────────────────────────

@router.message(Command("tstats"))
async def cmd_tstats(msg: Message) -> None:
    if not await is_tester_or_above(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    stats = await Database.get_stats()
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Игроков: {stats['users_total']}\n"
        f"✅ Активных: {stats['users_active']}\n"
        f"🟢 Онлайн (5 мин): {stats['online']}\n"
        f"🏴 Кланов: {stats['clans_total']}\n"
        f"🏛️ Активных аукционов: {stats['auctions']}\n"
        f"💰 Монет в игре: {format_number(stats['total_money'])}"
    )
    await msg.answer(text, parse_mode="HTML")


# ── Callback back to tpanel ───────────────────────────────────────────────────

@router.callback_query(F.data == "tpanel_menu")
async def cb_tpanel_menu(cb: CallbackQuery) -> None:
    if not await is_tester_or_above(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    role = await Database.get_staff_role(cb.from_user.id)
    role_label = {"owner": "👑 Владелец", "admin": "🛠️ Администратор", "tester": "🔬 Тестировщик"}.get(role or "", "❓")
    await cb.message.edit_text(
        f"🔬 <b>Панель тестировщика</b>\n\nРоль: {role_label}",
        reply_markup=tester_menu_kb(), parse_mode="HTML"
    )
    await cb.answer()
