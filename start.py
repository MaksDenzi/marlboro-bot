"""
Marlboro Project — Start / Main Menu handler
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from database.db import Database
from utils.keyboards import main_menu_kb, back_kb
from utils.texts import welcome_text, already_registered_text, help_text
from utils.logger import log_action
from utils.helpers import ts_now, ACHIEVEMENTS_DEF
from config import STARTING_BALANCE, REFERRAL_BONUS, OWNER_ID

router = Router()


@router.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    user = msg.from_user
    row = await Database.get_user(user.id)

    # Parse referral
    referrer_id = None
    args = msg.text.split()
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user.id:
                ref_row = await Database.get_user(ref_id)
                if ref_row:
                    referrer_id = ref_id
        except (ValueError, TypeError):
            pass

    if not row:
        await Database.create_user(
            user.id,
            user.username or "",
            user.first_name or "Игрок",
            user.last_name or "",
            referrer_id,
        )

        # Give referral bonus
        if referrer_id:
            await Database.add_balance(referrer_id, REFERRAL_BONUS)
            await Database.add_balance(user.id, REFERRAL_BONUS // 2)
            db = await Database.get_db()  # type: ignore
            from database.db import get_db
            db = await get_db()
            await db.execute(
                "UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,)
            )
            await db.commit()

        await _grant_achievement(user.id, "first_login")
        await log_action("registration", user.id, f"Новый игрок: @{user.username}")
        text = welcome_text(user.first_name or "Игрок")
    else:
        text = already_registered_text(user.first_name or "Игрок")

    await msg.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery) -> None:
    user = cb.from_user
    text = already_registered_text(user.first_name or "Игрок")
    await cb.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.message(Command("menu"))
async def cmd_menu(msg: Message) -> None:
    await msg.answer(
        f"🎮 Главное меню",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "help")
@router.message(Command("help"))
async def cb_help(event) -> None:
    text = help_text()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb(), parse_mode="HTML")


@router.callback_query(F.data == "stats")
async def cb_stats(cb: CallbackQuery) -> None:
    stats = await Database.get_stats()
    text = (
        f"📊 <b>Статистика {__import__('config').BOT_NAME}</b>\n\n"
        f"👥 Всего игроков: <b>{stats['users_total']:,}</b>\n"
        f"✅ Активных: <b>{stats['users_active']:,}</b>\n"
        f"🟢 Онлайн (5 мин): <b>{stats['online']}</b>\n"
        f"🏴 Кланов: <b>{stats['clans_total']}</b>\n"
        f"🏛️ Активных аукционов: <b>{stats['auctions']}</b>\n"
        f"💰 Денег в обороте: <b>{stats['total_money']:,}</b>\n"
    )
    await cb.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
    await cb.answer()


@router.message(Command("id"))
async def cmd_id(msg: Message) -> None:
    parts = msg.text.split(maxsplit=1)
    arg = parts[1].lstrip("@").strip() if len(parts) > 1 else None

    if arg:
        from database.db import get_db
        db = await get_db()
        row = None
        # Try numeric ID first
        if arg.isdigit():
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (int(arg),)) as cur:
                row = await cur.fetchone()
        else:
            async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (arg,)) as cur:
                row = await cur.fetchone()
        if not row:
            await msg.answer(
                f"❌ Пользователь <b>@{arg}</b> не найден в базе бота.\n\n"
                f"<i>Пользователь должен был написать боту хотя бы раз.</i>",
                parse_mode="HTML"
            )
            return
        username = f"@{row['username']}" if row["username"] else "<i>нет username</i>"
        name = f"{row['first_name']} {row['last_name'] or ''}".strip() or "—"
        text = (
            f"🆔 <b>Информация о пользователе</b>\n\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📛 Username: {username}\n"
            f"🔢 Telegram ID: <code>{row['user_id']}</code>"
        )
    elif msg.reply_to_message:
        target = msg.reply_to_message.from_user
        username = f"@{target.username}" if target.username else "<i>нет username</i>"
        name = target.full_name or target.first_name or "—"
        text = (
            f"🆔 <b>Информация о пользователе</b>\n\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📛 Username: {username}\n"
            f"🔢 Telegram ID: <code>{target.id}</code>"
        )
    else:
        me = msg.from_user
        username = f"@{me.username}" if me.username else "<i>нет username</i>"
        name = me.full_name or me.first_name or "—"
        text = (
            f"🆔 <b>Твои данные</b>\n\n"
            f"👤 Имя: <b>{name}</b>\n"
            f"📛 Username: {username}\n"
            f"🔢 Telegram ID: <code>{me.id}</code>\n\n"
            f"<i>Использование:\n"
            f"• /id — свой ID\n"
            f"• /id @username — ID по нику\n"
            f"• /id 123456789 — ID по числу\n"
            f"• Ответить на сообщение + /id</i>"
        )
    await msg.answer(text, parse_mode="HTML")


async def _grant_achievement(user_id: int, key: str) -> bool:
    """Grant achievement if not already unlocked. Returns True if new."""
    from database.db import get_db
    db = await get_db()
    async with db.execute(
        "SELECT 1 FROM achievements WHERE user_id = ? AND achievement = ?", (user_id, key)
    ) as cur:
        if await cur.fetchone():
            return False
    await db.execute(
        "INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, ?)", (user_id, key)
    )
    await db.commit()
    return True
