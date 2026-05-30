"""
Marlboro Project — Admin panel (ROOT only: owner_id = 5341321001)
"""

import time
import os
import sys
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from database.backup import create_backup, list_backups, read_log_file
from utils.keyboards import admin_menu_kb, back_kb
from utils.helpers import generate_promo_code, ts_now
from utils.texts import format_number, get_item_data
from utils.logger import log_action, tg_log
from config import OWNER_ID, LOG_FILE

router = Router()


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def is_admin(user_id: int) -> bool:
    """True if owner OR has 'admin' role in staff_roles table."""
    if user_id == OWNER_ID:
        return True
    role = await Database.get_staff_role(user_id)
    return role in ("owner", "admin")


async def is_staff(user_id: int) -> bool:
    """True if owner, admin, OR tester."""
    if user_id == OWNER_ID:
        return True
    role = await Database.get_staff_role(user_id)
    return role in ("owner", "admin", "tester")


# ── Guard filter ──────────────────────────────────────────────────────────────
async def admin_guard(event) -> bool:
    uid = event.from_user.id if hasattr(event, "from_user") else None
    return uid is not None and await is_admin(uid)


# ── Commands ──────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(msg: Message) -> None:
    if not await is_admin(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    stats = await Database.get_stats()
    text = (
        f"🛠️ <b>Панель администратора</b>\n\n"
        f"👑 ROOT: {msg.from_user.first_name}\n\n"
        f"📊 Игроков: {stats['users_total']} | Онлайн: {stats['online']}\n"
        f"🏴 Кланов: {stats['clans_total']}\n"
        f"💰 Монет в обороте: {format_number(stats['total_money'])}\n\n"
        f"Версия: Marlboro Project v1.0.0"
    )
    await msg.answer(text, reply_markup=admin_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "adm_stats")
async def adm_stats(cb: CallbackQuery) -> None:
    if not await is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа.", show_alert=True)
        return
    stats = await Database.get_stats()
    db = await get_db()
    async with db.execute("SELECT COUNT(*) as cnt FROM transactions WHERE timestamp > ?", (ts_now() - 86400,)) as cur:
        tx_today = (await cur.fetchone())["cnt"]
    async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE registered_at > ?", (ts_now() - 86400,)) as cur:
        new_today = (await cur.fetchone())["cnt"]
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Игроков всего: {stats['users_total']}\n"
        f"✅ Активных: {stats['users_active']}\n"
        f"🆕 Новых за сутки: {new_today}\n"
        f"🟢 Онлайн (5 мин): {stats['online']}\n"
        f"🏴 Кланов: {stats['clans_total']}\n"
        f"🏛️ Аукционов: {stats['auctions']}\n"
        f"💰 Монет в игре: {format_number(stats['total_money'])}\n"
        f"📋 Транзакций за сутки: {tx_today}"
    )
    await cb.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
    await cb.answer()


# ── Give coins ────────────────────────────────────────────────────────────────

class GiveCoinsState(StatesGroup):
    user_id = State()
    amount = State()


@router.callback_query(F.data == "adm_give_coins")
@router.message(Command("give"))
async def adm_give_coins_start(event, state: FSMContext) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌ Нет доступа.", show_alert=True)
        return
    await state.set_state(GiveCoinsState.user_id)
    text = "💰 <b>Выдать монеты</b>\n\nВведи user_id или @username:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(GiveCoinsState.user_id)
async def adm_give_coins_uid(msg: Message, state: FSMContext) -> None:
    target_text = msg.text.strip().lstrip("@")
    db = await get_db()
    target_row = None
    try:
        tid = int(target_text)
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (tid,)) as cur:
            target_row = await cur.fetchone()
    except ValueError:
        async with db.execute("SELECT * FROM users WHERE username = ?", (target_text,)) as cur:
            target_row = await cur.fetchone()
    if not target_row:
        await msg.answer("❌ Игрок не найден!")
        return
    await state.update_data(target_id=target_row["user_id"], target_name=target_row["first_name"])
    await state.set_state(GiveCoinsState.amount)
    await msg.answer(f"💰 Игрок: <b>{target_row['first_name']}</b>\n\nВведи сумму (отрицательное = забрать):", parse_mode="HTML")


@router.message(GiveCoinsState.amount)
async def adm_give_coins_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    data = await state.get_data()
    target_id = data["target_id"]
    target_name = data["target_name"]
    if amount >= 0:
        await Database.add_balance(target_id, amount)
        action_str = f"выдал {amount} монет"
    else:
        await Database.deduct_balance(target_id, abs(amount))
        action_str = f"забрал {abs(amount)} монет"
    await state.clear()
    await Database.admin_log(msg.from_user.id, "give_coins", target_id, f"{amount} монет")
    await log_action("admin", msg.from_user.id, f"[ADMIN] {action_str} у {target_name} ({target_id})")
    await msg.answer(
        f"✅ <b>Готово!</b> {action_str} у игрока <b>{target_name}</b>",
        reply_markup=admin_menu_kb(), parse_mode="HTML"
    )
    try:
        sign = "+" if amount >= 0 else ""
        await msg.bot.send_message(target_id, f"🛠️ Администратор изменил твой баланс: <b>{sign}{format_number(amount)}</b> монет.", parse_mode="HTML")
    except Exception:
        pass


# ── Give item ─────────────────────────────────────────────────────────────────

class GiveItemState(StatesGroup):
    user_id = State()
    item_id = State()
    amount = State()


@router.callback_query(F.data == "adm_give_item")
@router.message(Command("giveitem"))
async def adm_give_item_start(event, state: FSMContext) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌", show_alert=True)
        return
    await state.set_state(GiveItemState.user_id)
    text = "🎒 <b>Выдать предмет</b>\n\nВведи user_id:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(GiveItemState.user_id)
async def adm_give_item_uid(msg: Message, state: FSMContext) -> None:
    try:
        tid = int(msg.text.strip())
    except ValueError:
        tid = None
    if not tid:
        await msg.answer("❌ Введи числовой user_id!")
        return
    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Игрок не найден!")
        return
    await state.update_data(target_id=tid, target_name=row["first_name"])
    await state.set_state(GiveItemState.item_id)
    await msg.answer(f"Игрок: {row['first_name']}\n\nВведи ID предмета (1–50):")


@router.message(GiveItemState.item_id)
async def adm_give_item_iid(msg: Message, state: FSMContext) -> None:
    try:
        item_id = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи ID предмета числом!")
        return
    item = get_item_data(item_id)
    if not item:
        await msg.answer("❌ Предмет не найден!")
        return
    await state.update_data(item_id=item_id, item_name=item["name"])
    await state.set_state(GiveItemState.amount)
    await msg.answer(f"Предмет: {item['name']}\n\nВведи количество:")


@router.message(GiveItemState.amount)
async def adm_give_item_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return
    data = await state.get_data()
    await Database.add_item(data["target_id"], data["item_id"], amount)
    await Database.admin_log(msg.from_user.id, "give_item", data["target_id"], f"item={data['item_id']} x{amount}")
    await state.clear()
    await msg.answer(
        f"✅ <b>{data['item_name']} × {amount}</b> выдан игроку <b>{data['target_name']}</b>",
        reply_markup=admin_menu_kb(), parse_mode="HTML"
    )


# ── Give VIP ──────────────────────────────────────────────────────────────────

class GiveVIPState(StatesGroup):
    user_id = State()
    level = State()


@router.callback_query(F.data == "adm_give_vip")
@router.message(Command("givevip"))
async def adm_give_vip_start(event, state: FSMContext) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌", show_alert=True)
        return
    await state.set_state(GiveVIPState.user_id)
    text = "💫 <b>Выдать VIP</b>\n\nВведи user_id:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(GiveVIPState.user_id)
async def adm_give_vip_uid(msg: Message, state: FSMContext) -> None:
    try:
        tid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи числовой ID!")
        return
    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Не найден!")
        return
    await state.update_data(target_id=tid, target_name=row["first_name"])
    await state.set_state(GiveVIPState.level)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🥈 Silver", callback_data="adm_vip_lvl:silver"),
        InlineKeyboardButton(text="🥇 Gold",   callback_data="adm_vip_lvl:gold"),
        InlineKeyboardButton(text="💎 Platinum", callback_data="adm_vip_lvl:platinum"),
    ]])
    await msg.answer(f"Игрок: {row['first_name']}\n\nВыбери уровень VIP:", reply_markup=kb)


@router.callback_query(F.data.startswith("adm_vip_lvl:"))
async def adm_give_vip_level(cb: CallbackQuery, state: FSMContext) -> None:
    level = cb.data.split(":")[1]
    data = await state.get_data()
    if not data.get("target_id"):
        await cb.answer("Состояние устарело.", show_alert=True)
        await state.clear()
        return
    expires = ts_now() + 30 * 86400
    await Database.update_user(data["target_id"], vip_status=level, vip_expires=expires)
    await Database.admin_log(cb.from_user.id, "give_vip", data["target_id"], level)
    await state.clear()
    await cb.message.edit_text(
        f"✅ VIP <b>{level}</b> выдан игроку <b>{data['target_name']}</b> на 30 дней!",
        parse_mode="HTML"
    )
    await cb.answer("✅ VIP выдан!")
    try:
        await cb.bot.send_message(data["target_id"], f"💫 Тебе выдан VIP {level} на 30 дней! Enjoy 🎉")
    except Exception:
        pass


# ── Ban / Unban / Mute ────────────────────────────────────────────────────────

class BanState(StatesGroup):
    user_id = State()
    reason = State()
    duration = State()


@router.callback_query(F.data == "adm_ban")
@router.message(Command("ban"))
async def adm_ban_start(event, state: FSMContext) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌", show_alert=True)
        return
    await state.set_state(BanState.user_id)
    text = "🚫 <b>Бан игрока</b>\n\nВведи user_id:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(BanState.user_id)
async def adm_ban_uid(msg: Message, state: FSMContext) -> None:
    try:
        tid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи числовой ID!")
        return
    if tid == OWNER_ID:
        await msg.answer("❌ Нельзя забанить владельца!")
        await state.clear()
        return
    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Игрок не найден!")
        return
    await state.update_data(target_id=tid, target_name=row["first_name"])
    await state.set_state(BanState.reason)
    await msg.answer(f"Игрок: {row['first_name']}\n\nПричина бана:")


@router.message(BanState.reason)
async def adm_ban_reason(msg: Message, state: FSMContext) -> None:
    await state.update_data(reason=msg.text.strip())
    await state.set_state(BanState.duration)
    await msg.answer("Длительность бана в часах (0 = навсегда):")


@router.message(BanState.duration)
async def adm_ban_duration(msg: Message, state: FSMContext) -> None:
    try:
        hours = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Число!")
        return
    data = await state.get_data()
    ban_expires = ts_now() + hours * 3600 if hours > 0 else None
    await Database.update_user(
        data["target_id"], is_banned=1,
        ban_reason=data["reason"], ban_expires=ban_expires
    )
    await Database.admin_log(msg.from_user.id, "ban", data["target_id"], data["reason"])
    await log_action("admin", msg.from_user.id, f"[BAN] {data['target_name']} ({data['target_id']}): {data['reason']}")
    await state.clear()
    await msg.answer(
        f"🚫 <b>{data['target_name']}</b> заблокирован!\nПричина: {data['reason']}\n"
        f"Срок: {'навсегда' if not ban_expires else f'{hours}ч'}",
        reply_markup=admin_menu_kb(), parse_mode="HTML"
    )
    try:
        await msg.bot.send_message(
            data["target_id"],
            f"🚫 Ты заблокирован в {__import__('config').BOT_NAME}.\nПричина: {data['reason']}"
        )
    except Exception:
        pass


@router.callback_query(F.data == "adm_unban")
@router.message(Command("unban"))
async def adm_unban(event) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌", show_alert=True)
        return
    text = "✅ <b>Разбан</b>\n\nВведи user_id (командой /unban <id>):"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
        await event.answer()
    else:
        parts = event.text.split()
        if len(parts) < 2:
            await event.answer(text, parse_mode="HTML")
            return
        try:
            tid = int(parts[1])
        except ValueError:
            await event.answer("❌ Неверный ID!")
            return
        await Database.update_user(tid, is_banned=0, ban_reason=None, ban_expires=None)
        await Database.admin_log(event.from_user.id, "unban", tid)
        await event.answer(f"✅ Игрок {tid} разбанен!", parse_mode="HTML")
        try:
            await event.bot.send_message(tid, "✅ Ты разблокирован!")
        except Exception:
            pass


# ── Mute ──────────────────────────────────────────────────────────────────────

class MuteState(StatesGroup):
    user_id = State()
    hours = State()


@router.callback_query(F.data == "adm_mute")
@router.message(Command("mute"))
async def adm_mute_start(event, state: FSMContext) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌", show_alert=True)
        return
    await state.set_state(MuteState.user_id)
    text = "🔇 <b>Мут игрока</b>\n\nВведи user_id:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(MuteState.user_id)
async def adm_mute_uid(msg: Message, state: FSMContext) -> None:
    try:
        tid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Числовой ID!")
        return
    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Не найден!")
        return
    await state.update_data(target_id=tid, target_name=row["first_name"])
    await state.set_state(MuteState.hours)
    await msg.answer(f"Игрок: {row['first_name']}\n\nНа сколько часов (0 = снять мут):")


@router.message(MuteState.hours)
async def adm_mute_hours(msg: Message, state: FSMContext) -> None:
    try:
        hours = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Число!")
        return
    data = await state.get_data()
    if hours == 0:
        await Database.update_user(data["target_id"], is_muted=0, mute_expires=None)
        action = "Мут снят"
    else:
        mute_exp = ts_now() + hours * 3600
        await Database.update_user(data["target_id"], is_muted=1, mute_expires=mute_exp)
        action = f"Замьючен на {hours}ч"
    await Database.admin_log(msg.from_user.id, "mute", data["target_id"], action)
    await state.clear()
    await msg.answer(f"🔇 <b>{data['target_name']}</b>: {action}", reply_markup=admin_menu_kb(), parse_mode="HTML")


# ── Promo create ──────────────────────────────────────────────────────────────

class PromoCreateState(StatesGroup):
    reward_type = State()
    reward_amount = State()
    uses = State()
    duration = State()


@router.callback_query(F.data == "adm_promo")
@router.message(Command("createpromo"))
async def adm_promo_start(event, state: FSMContext) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌", show_alert=True)
        return
    await state.set_state(PromoCreateState.reward_type)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💰 Монеты", callback_data="pcreate:coins"),
        InlineKeyboardButton(text="🎯 XP",     callback_data="pcreate:xp"),
    ]])
    text = "🎟️ <b>Создать промокод</b>\n\nТип награды:"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("pcreate:"))
async def adm_promo_type(cb: CallbackQuery, state: FSMContext) -> None:
    rtype = cb.data.split(":")[1]
    await state.update_data(reward_type=rtype)
    await state.set_state(PromoCreateState.reward_amount)
    await cb.message.edit_text(f"Тип: {rtype}\n\nВведи количество награды:", parse_mode="HTML")
    await cb.answer()


@router.message(PromoCreateState.reward_amount)
async def adm_promo_amount(msg: Message, state: FSMContext) -> None:
    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Число!")
        return
    await state.update_data(reward_amount=amount)
    await state.set_state(PromoCreateState.uses)
    await msg.answer("Количество использований (-1 = безлимит):")


@router.message(PromoCreateState.uses)
async def adm_promo_uses(msg: Message, state: FSMContext) -> None:
    try:
        uses = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Число!")
        return
    await state.update_data(uses=uses)
    await state.set_state(PromoCreateState.duration)
    await msg.answer("Срок действия в часах (0 = бессрочно):")


@router.message(PromoCreateState.duration)
async def adm_promo_duration(msg: Message, state: FSMContext) -> None:
    try:
        hours = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Число!")
        return
    data = await state.get_data()
    code = generate_promo_code()
    expires = ts_now() + hours * 3600 if hours > 0 else None
    db = await get_db()
    await db.execute(
        """INSERT INTO promo_codes (code, reward_type, reward_amount, uses_left, expires_at, created_by)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (code, data["reward_type"], data["reward_amount"], data["uses"], expires, msg.from_user.id)
    )
    await db.commit()
    await Database.admin_log(msg.from_user.id, "create_promo", None, f"{code}: {data['reward_type']} x{data['reward_amount']}")
    await state.clear()
    await msg.answer(
        f"✅ <b>Промокод создан!</b>\n\n"
        f"🎟️ Код: <code>{code}</code>\n"
        f"🎁 Тип: {data['reward_type']}\n"
        f"💰 Сумма: {data['reward_amount']}\n"
        f"🔢 Использований: {'∞' if data['uses'] < 0 else data['uses']}\n"
        f"⏰ Срок: {'∞' if not expires else f'{hours}ч'}",
        reply_markup=admin_menu_kb(), parse_mode="HTML"
    )


# ── Logs / Export / Backup ────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_logs")
@router.message(Command("logs"))
async def adm_logs(event) -> None:
    uid = event.from_user.id
    if not await is_admin(uid):
        if isinstance(event, Message):
            await event.answer("❌ Нет доступа.")
        return

    log_text = await read_log_file(100)
    if len(log_text) > 4000:
        log_text = "...\n" + log_text[-4000:]

    text = f"📋 <b>Последние логи:</b>\n\n<code>{log_text}</code>"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb("adm_main"), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(Command("exportdb"))
async def adm_exportdb(msg: Message) -> None:
    if not await is_admin(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    from config import DB_PATH
    if not os.path.isfile(DB_PATH):
        await msg.answer("❌ База данных не найдена!")
        return
    doc = FSInputFile(DB_PATH, filename="marlboro_database.db")
    await msg.answer_document(doc, caption="📊 База данных Marlboro Project")
    await log_action("admin", msg.from_user.id, "[ADMIN] Экспорт базы данных")


@router.callback_query(F.data == "adm_export")
async def adm_export_cb(cb: CallbackQuery) -> None:
    if not await is_admin(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    from config import DB_PATH
    if not os.path.isfile(DB_PATH):
        await cb.answer("❌ База данных не найдена!", show_alert=True)
        return
    doc = FSInputFile(DB_PATH, filename="marlboro_database.db")
    await cb.message.answer_document(doc, caption="📊 База данных Marlboro Project")
    await cb.answer("📤 Отправлено!")


@router.callback_query(F.data == "adm_backup")
@router.message(Command("backup"))
async def adm_backup(event) -> None:
    uid = event.from_user.id
    if not await is_admin(uid):
        if isinstance(event, Message):
            await event.answer("❌ Нет доступа.")
        return
    path = await create_backup()
    doc = FSInputFile(path, filename=os.path.basename(path))
    if isinstance(event, CallbackQuery):
        await event.message.answer_document(doc, caption=f"💾 Backup создан: {os.path.basename(path)}")
        await event.answer("💾 Backup готов!")
    else:
        await event.answer_document(doc, caption=f"💾 Backup создан: {os.path.basename(path)}")
    await log_action("admin", uid, "[ADMIN] Backup базы данных создан")


@router.callback_query(F.data == "adm_restart")
@router.message(Command("restart"))
async def adm_restart(event) -> None:
    uid = event.from_user.id
    if not is_owner(uid):
        if isinstance(event, CallbackQuery):
            await event.answer("❌ Только владелец!", show_alert=True)
        return
    text = "🔄 <b>Перезагрузка бота...</b>"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")
    await log_action("admin", uid, "[ADMIN] Перезагрузка бота")
    os.execv(sys.executable, [sys.executable] + sys.argv)


@router.callback_query(F.data == "adm_main")
async def adm_main(cb: CallbackQuery) -> None:
    if not await is_admin(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    await cb.message.edit_text(
        "🛠️ <b>Панель администратора</b>",
        reply_markup=admin_menu_kb(), parse_mode="HTML"
    )
    await cb.answer()


# ── /ahelp ────────────────────────────────────────────────────────────────────

@router.message(Command("ahelp"))
async def cmd_ahelp(msg: Message) -> None:
    if not await is_admin(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    text = (
        "🛠️ <b>Команды администратора</b>\n\n"
        "<b>Игроки:</b>\n"
        "  /give — 💰 Выдать монеты игроку\n"
        "  /giveitem — 🎒 Выдать предмет игроку\n"
        "  /givevip — 💫 Выдать VIP игроку\n"
        "  /ban — 🚫 Заблокировать игрока\n"
        "  /unban &lt;id&gt; — ✅ Разблокировать игрока\n"
        "  /mute — 🔇 Замьютить игрока\n\n"
        "<b>Стафф:</b>\n"
        "  /addadmin &lt;id&gt; — ➕ Назначить администратора\n"
        "  /removeadmin &lt;id&gt; — ➖ Снять администратора\n"
        "  /addtester &lt;id&gt; — 🔬 Назначить тестировщика\n"
        "  /removetester &lt;id&gt; — ➖ Снять тестировщика\n"
        "  /stafflist — 👥 Список всего стаффа\n\n"
        "<b>Предметы:</b>\n"
        "  /itemlist — 📋 Полный список предметов с ID\n\n"
        "<b>Система:</b>\n"
        "  /createpromo — 🎟️ Создать промокод\n"
        "  /logs — 📋 Последние логи\n"
        "  /exportdb — 📤 Экспорт базы данных\n"
        "  /backup — 💾 Создать резервную копию\n"
        "  /restart — 🔄 Перезагрузить бота\n"
        "  /admin — 🛠️ Панель администратора\n"
        "  /ahelp — ℹ️ Эта справка"
    )
    await msg.answer(text, parse_mode="HTML")


# ── Item list (admin + tester) ─────────────────────────────────────────────────

def _build_item_list_text(page: int = 0, page_size: int = 25) -> tuple[str, int]:
    """Build paginated item list text. Returns (text, total_pages)."""
    import json, os
    items_path = os.path.join(os.path.dirname(__file__), "..", "data", "items.json")
    with open(items_path, encoding="utf-8") as f:
        all_items = json.load(f)["items"]

    total_pages = (len(all_items) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    chunk = all_items[page * page_size:(page + 1) * page_size]

    rarity_emoji = {
        "common": "⬜", "uncommon": "🟩", "rare": "🟦",
        "epic": "🟪", "legendary": "🟧", "mythic": "🔴"
    }
    type_emoji = {
        "weapon": "⚔️", "armor": "🛡️", "consumable": "🧪",
        "farm_seed": "🌱", "farm_product": "🌾", "mining_tool": "⛏️",
        "resource": "🪨", "key": "🗝️", "special": "✨", "vip": "💫"
    }
    lines = [f"📋 <b>Список предметов</b> (стр. {page + 1}/{total_pages})\n"]
    for item in chunk:
        re = rarity_emoji.get(item.get("rarity", ""), "⬜")
        te = type_emoji.get(item.get("type", ""), "📦")
        lines.append(
            f"  <code>#{item['id']:>2}</code> {re}{te} <b>{item['name']}</b> — {item.get('price', 0):,}💰"
        )
    lines.append(f"\n<i>Всего предметов: {len(all_items)}</i>")
    return "\n".join(lines), total_pages


@router.message(Command("itemlist"))
async def cmd_itemlist(msg: Message) -> None:
    if not await is_staff(msg.from_user.id):
        await msg.answer("❌ Нет доступа.")
        return
    args = msg.text.split()
    page = int(args[1]) - 1 if len(args) > 1 and args[1].isdigit() else 0
    text, total = _build_item_list_text(page)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb_rows = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"itemlist:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"itemlist:{page + 1}"))
    kb_rows.append(nav)
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("itemlist:"))
async def cb_itemlist(cb: CallbackQuery) -> None:
    if not await is_staff(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    page = int(cb.data.split(":")[1])
    text, total = _build_item_list_text(page)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"itemlist:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"itemlist:{page + 1}"))
    kb = InlineKeyboardMarkup(inline_keyboard=[nav])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "adm_itemlist")
async def cb_adm_itemlist(cb: CallbackQuery) -> None:
    if not await is_staff(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    text, total = _build_item_list_text(0)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    nav = [InlineKeyboardButton(text=f"1/{total}", callback_data="noop")]
    if total > 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data="itemlist:1"))
    kb = InlineKeyboardMarkup(inline_keyboard=[nav, [InlineKeyboardButton(text="◀️ Назад", callback_data="adm_main")]])
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery) -> None:
    await cb.answer()


# ── Staff management ───────────────────────────────────────────────────────────

class AddStaffState(StatesGroup):
    user_id = State()


@router.callback_query(F.data == "adm_staff")
async def adm_staff_menu(cb: CallbackQuery) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("❌ Только владелец!", show_alert=True)
        return
    from utils.keyboards import staff_manage_kb
    await cb.message.edit_text(
        "👥 <b>Управление стаффом</b>\n\nВыбери действие:",
        reply_markup=staff_manage_kb(), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "adm_staff_list")
@router.message(Command("stafflist"))
async def adm_staff_list(event) -> None:
    if isinstance(event, Message) and not await is_admin(event.from_user.id):
        return
    if isinstance(event, CallbackQuery) and not await is_admin(event.from_user.id):
        await event.answer("❌", show_alert=True)
        return

    staff = await Database.get_all_staff()
    role_emoji = {"admin": "🛠️", "tester": "🔬"}
    lines = [f"👥 <b>Стафф проекта</b>\n\n👑 Владелец: <code>{OWNER_ID}</code>\n"]
    if staff:
        for s in staff:
            name = s["first_name"] or "—"
            uname = f"@{s['username']}" if s["username"] else ""
            re = role_emoji.get(s["role"], "❓")
            lines.append(f"  {re} <b>{name}</b> {uname} — <code>{s['user_id']}</code> [{s['role']}]")
    else:
        lines.append("  <i>Стафф пуст</i>")

    text = "\n".join(lines)
    if isinstance(event, CallbackQuery):
        from utils.keyboards import staff_manage_kb
        await event.message.edit_text(text, reply_markup=staff_manage_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "adm_add_admin")
async def adm_add_admin_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("❌ Только владелец!", show_alert=True)
        return
    await state.update_data(staff_role="admin")
    await state.set_state(AddStaffState.user_id)
    await cb.message.edit_text(
        "🛠️ <b>Назначить администратора</b>\n\nВведи user_id:",
        reply_markup=back_kb("adm_staff"), parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "adm_add_tester")
async def adm_add_tester_start(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("❌ Только владелец!", show_alert=True)
        return
    await state.update_data(staff_role="tester")
    await state.set_state(AddStaffState.user_id)
    await cb.message.edit_text(
        "🔬 <b>Назначить тестировщика</b>\n\nВведи user_id:",
        reply_markup=back_kb("adm_staff"), parse_mode="HTML"
    )
    await cb.answer()


@router.message(AddStaffState.user_id)
async def adm_add_staff_uid(msg: Message, state: FSMContext) -> None:
    try:
        tid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи числовой user_id!")
        return
    if tid == OWNER_ID:
        await msg.answer("❌ Владелец уже имеет максимальные права!")
        await state.clear()
        return

    data = await state.get_data()
    role = data.get("staff_role", "tester")
    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Игрок с таким ID не найден в базе!")
        await state.clear()
        return

    await Database.add_staff_role(tid, role, msg.from_user.id)
    await Database.admin_log(msg.from_user.id, f"add_{role}", tid)
    await state.clear()

    role_name = "Администратор" if role == "admin" else "Тестировщик"
    role_emoji = "🛠️" if role == "admin" else "🔬"
    await msg.answer(
        f"✅ {role_emoji} <b>{row['first_name']}</b> (<code>{tid}</code>) назначен как <b>{role_name}</b>!",
        parse_mode="HTML"
    )
    try:
        await msg.bot.send_message(
            tid,
            f"{role_emoji} Тебе выдана роль <b>{role_name}</b> в {__import__('config').BOT_NAME}! "
            f"Используй /{'ahelp' if role == 'admin' else 'thelp'} для просмотра команд.",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(Command("addadmin"))
async def cmd_addadmin(msg: Message) -> None:
    if not is_owner(msg.from_user.id):
        await msg.answer("❌ Только владелец!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /addadmin &lt;user_id&gt;", parse_mode="HTML")
        return
    try:
        tid = int(parts[1])
    except ValueError:
        await msg.answer("❌ Неверный ID!")
        return
    if tid == OWNER_ID:
        await msg.answer("❌ Владелец уже имеет максимальные права!")
        return
    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Игрок не найден!")
        return
    await Database.add_staff_role(tid, "admin", msg.from_user.id)
    await Database.admin_log(msg.from_user.id, "add_admin", tid)
    await msg.answer(f"✅ <b>{row['first_name']}</b> назначен администратором!", parse_mode="HTML")
    try:
        await msg.bot.send_message(tid, f"🛠️ Тебе выдана роль <b>Администратор</b>! Используй /ahelp.", parse_mode="HTML")
    except Exception:
        pass


@router.message(Command("removeadmin"))
async def cmd_removeadmin(msg: Message) -> None:
    if not is_owner(msg.from_user.id):
        await msg.answer("❌ Только владелец!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /removeadmin &lt;user_id&gt;", parse_mode="HTML")
        return
    try:
        tid = int(parts[1])
    except ValueError:
        await msg.answer("❌ Неверный ID!")
        return
    role = await Database.get_staff_role(tid)
    if role not in ("admin",):
        await msg.answer("❌ У этого игрока нет роли администратора!")
        return
    await Database.remove_staff_role(tid)
    await Database.admin_log(msg.from_user.id, "remove_admin", tid)
    await msg.answer(f"✅ Роль администратора снята с <code>{tid}</code>!", parse_mode="HTML")
    try:
        await msg.bot.send_message(tid, "⚠️ Твоя роль администратора была снята.")
    except Exception:
        pass


@router.message(Command("addtester"))
async def cmd_addtester(msg: Message) -> None:
    if not is_owner(msg.from_user.id):
        await msg.answer("❌ Только владелец!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /addtester &lt;user_id&gt;", parse_mode="HTML")
        return
    try:
        tid = int(parts[1])
    except ValueError:
        await msg.answer("❌ Неверный ID!")
        return
    if tid == OWNER_ID:
        await msg.answer("❌ Владелец уже имеет максимальные права!")
        return
    row = await Database.get_user(tid)
    if not row:
        await msg.answer("❌ Игрок не найден!")
        return
    await Database.add_staff_role(tid, "tester", msg.from_user.id)
    await Database.admin_log(msg.from_user.id, "add_tester", tid)
    await msg.answer(f"✅ <b>{row['first_name']}</b> назначен тестировщиком!", parse_mode="HTML")
    try:
        await msg.bot.send_message(tid, f"🔬 Тебе выдана роль <b>Тестировщик</b>! Используй /thelp.", parse_mode="HTML")
    except Exception:
        pass


@router.message(Command("removetester"))
async def cmd_removetester(msg: Message) -> None:
    if not is_owner(msg.from_user.id):
        await msg.answer("❌ Только владелец!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Использование: /removetester &lt;user_id&gt;", parse_mode="HTML")
        return
    try:
        tid = int(parts[1])
    except ValueError:
        await msg.answer("❌ Неверный ID!")
        return
    role = await Database.get_staff_role(tid)
    if role not in ("tester",):
        await msg.answer("❌ У этого игрока нет роли тестировщика!")
        return
    await Database.remove_staff_role(tid)
    await Database.admin_log(msg.from_user.id, "remove_tester", tid)
    await msg.answer(f"✅ Роль тестировщика снята с <code>{tid}</code>!", parse_mode="HTML")
    try:
        await msg.bot.send_message(tid, "⚠️ Твоя роль тестировщика была снята.")
    except Exception:
        pass


@router.callback_query(F.data == "adm_remove_staff")
async def adm_remove_staff_cb(cb: CallbackQuery) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("❌ Только владелец!", show_alert=True)
        return
    staff = await Database.get_all_staff()
    if not staff:
        await cb.answer("Стафф пуст!", show_alert=True)
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for s in staff:
        label = f"{'🛠️' if s['role'] == 'admin' else '🔬'} {s['first_name'] or s['user_id']} [{s['role']}]"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"kick_staff:{s['user_id']}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="adm_staff")])
    await cb.message.edit_text(
        "➖ <b>Снять роль</b>\n\nВыбери кого снять:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data.startswith("kick_staff:"))
async def adm_kick_staff_confirm(cb: CallbackQuery) -> None:
    if not is_owner(cb.from_user.id):
        await cb.answer("❌", show_alert=True)
        return
    tid = int(cb.data.split(":")[1])
    await Database.remove_staff_role(tid)
    await Database.admin_log(cb.from_user.id, "remove_staff", tid)
    await cb.answer("✅ Роль снята!", show_alert=True)
    try:
        await cb.bot.send_message(tid, "⚠️ Твоя роль стаффа была снята.")
    except Exception:
        pass
    staff = await Database.get_all_staff()
    from utils.keyboards import staff_manage_kb
    role_emoji = {"admin": "🛠️", "tester": "🔬"}
    lines = [f"👥 <b>Стафф проекта</b>\n\n👑 Владелец: <code>{OWNER_ID}</code>\n"]
    if staff:
        for s in staff:
            name = s["first_name"] or "—"
            uname = f"@{s['username']}" if s["username"] else ""
            re = role_emoji.get(s["role"], "❓")
            lines.append(f"  {re} <b>{name}</b> {uname} — <code>{s['user_id']}</code> [{s['role']}]")
    else:
        lines.append("  <i>Стафф пуст</i>")
    await cb.message.edit_text("\n".join(lines), reply_markup=staff_manage_kb(), parse_mode="HTML")
