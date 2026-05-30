"""
from keep_alive import keep_alive
Marlboro Project — Main entry point
Starts the bot, registers all handlers and middlewares.
"""

import asyncio
import logging
import os
import sys
import time

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, OWNER_ID, LOG_GROUP_ID, ENERGY_REGEN_PER_HOUR, MAX_ENERGY
from db import Database
#from utils.logger import setup_logging, setup_telegram_logging, tg_log
#from middlewares import AntiSpamMiddleware, BanCheckMiddleware, RegisterMiddleware
from handlers import get_all_routers

logger = logging.getLogger(__name__)

# ── All public bot commands (shown when user types /) ─────────────────────────
BOT_COMMANDS = [
    BotCommand(command="start",        description="🎮 Главное меню"),
    BotCommand(command="menu",         description="🎮 Открыть меню"),
    BotCommand(command="profile",      description="👤 Мой профиль"),
    BotCommand(command="inventory",    description="🎒 Инвентарь"),
    BotCommand(command="balance",      description="💰 Баланс"),
    BotCommand(command="daily",        description="🎁 Ежедневный бонус"),
    BotCommand(command="work",         description="💼 Работать"),
    BotCommand(command="mine",         description="⛏️ Добывать ресурсы"),
    BotCommand(command="shop",         description="🏪 Магазин"),
    BotCommand(command="top",          description="🏆 Топ игроков"),
    BotCommand(command="duel",         description="⚔️ Вызвать на дуэль"),
    BotCommand(command="send",         description="💸 Перевести монеты"),
    BotCommand(command="promo",        description="🎟️ Активировать промокод"),
    BotCommand(command="trade",        description="🔁 Предложить обмен"),
    BotCommand(command="marry",        description="💍 Предложить руку"),
    BotCommand(command="clan",         description="🏴 Клановое меню"),
    BotCommand(command="event",        description="🌟 Текущее событие"),
    BotCommand(command="referral",     description="👥 Реферальная программа"),
    BotCommand(command="achievements", description="🏅 Достижения"),
    BotCommand(command="hug",          description="🤗 Обнять (ответом на сообщение)"),
    BotCommand(command="kiss",         description="😘 Поцеловать (ответом)"),
    BotCommand(command="punch",        description="👊 Ударить (ответом)"),
    BotCommand(command="dance",        description="🎵 Потанцевать (ответом)"),
    BotCommand(command="slots",        description="🎰 Игровые автоматы"),
    BotCommand(command="roulette",     description="🎡 Рулетка"),
    BotCommand(command="dice",         description="🎲 Кости"),
    BotCommand(command="coinflip",     description="🪙 Монетка"),
    BotCommand(command="id",           description="🆔 Узнать Telegram ID"),
    BotCommand(command="help",         description="ℹ️ Помощь"),
]

# Tester-only extra commands
TESTER_EXTRA_COMMANDS = [
    BotCommand(command="tpanel",   description="🔬 Панель тестировщика"),
    BotCommand(command="thelp",    description="ℹ️ Команды тестировщика"),
    BotCommand(command="tgive",    description="🎒 Выдать себе предмет"),
    BotCommand(command="tcoin",    description="💰 Выдать себе монеты"),
    BotCommand(command="treset",   description="⏰ Сбросить кулдауны"),
    BotCommand(command="tlevel",   description="📈 Установить уровень"),
    BotCommand(command="tinfo",    description="🔍 Инфо об игроке"),
    BotCommand(command="tstats",   description="📊 Статистика бота"),
    BotCommand(command="itemlist", description="📋 Список предметов"),
]

TESTER_COMMANDS = BOT_COMMANDS + TESTER_EXTRA_COMMANDS

# Admin-only commands
ADMIN_COMMANDS = BOT_COMMANDS + TESTER_EXTRA_COMMANDS + [
    BotCommand(command="admin",         description="🛠️ Панель администратора"),
    BotCommand(command="ahelp",         description="ℹ️ Команды администратора"),
    BotCommand(command="give",          description="💰 Выдать монеты игроку"),
    BotCommand(command="giveitem",      description="🎒 Выдать предмет игроку"),
    BotCommand(command="givevip",       description="💫 Выдать VIP игроку"),
    BotCommand(command="ban",           description="🚫 Забанить игрока"),
    BotCommand(command="unban",         description="✅ Разбанить игрока"),
    BotCommand(command="mute",          description="🔇 Замьютить игрока"),
    BotCommand(command="createpromo",   description="🎟️ Создать промокод"),
    BotCommand(command="stafflist",     description="👥 Список стаффа"),
    BotCommand(command="addadmin",      description="➕ Назначить администратора"),
    BotCommand(command="removeadmin",   description="➖ Снять администратора"),
    BotCommand(command="addtester",     description="🔬 Назначить тестировщика"),
    BotCommand(command="removetester",  description="➖ Снять тестировщика"),
    BotCommand(command="logs",          description="📋 Последние логи"),
    BotCommand(command="exportdb",      description="📤 Экспорт базы данных"),
    BotCommand(command="backup",        description="💾 Создать backup"),
    BotCommand(command="restart",       description="🔄 Перезагрузить бота"),
]


# ── Scheduled tasks ───────────────────────────────────────────────────────────

async def task_energy_regen() -> None:
    """Regenerate energy for all players every hour."""
    try:
        from db import get_db
        db = await get_db()
        await db.execute(
            f"UPDATE users SET energy = MIN({MAX_ENERGY}, energy + {ENERGY_REGEN_PER_HOUR})"
        )
        await db.commit()
        logger.info("Energy regenerated for all players.")
    except Exception as e:
        logger.error("Energy regen error: %s", e)


async def task_expire_auctions(bot: Bot) -> None:
    """Finalize expired auctions, refund / deliver items."""
    try:
        from database.db import get_db
        from utils.texts import get_item_data
        db = await get_db()
        now = int(time.time())
        async with db.execute(
            "SELECT * FROM auction WHERE status='active' AND expires_at <= ?", (now,)
        ) as cur:
            expired = await cur.fetchall()

        for lot in expired:
            if lot["buyer_id"] and lot["current_bid"]:
                # Winner gets item
                await Database.add_item(lot["buyer_id"], lot["item_id"], lot["amount"])
                # Seller gets money
                await Database.add_balance(lot["seller_id"], lot["current_bid"])
                await db.execute("UPDATE auction SET status='sold' WHERE id=?", (lot["id"],))
                try:
                    item = get_item_data(lot["item_id"])
                    iname = item["name"] if item else f"Предмет #{lot['item_id']}"
                    await bot.send_message(lot["buyer_id"], f"🏛️ Аукцион завершён! Ты выиграл: <b>{iname}</b> × {lot['amount']}", parse_mode="HTML")
                    await bot.send_message(lot["seller_id"], f"🏛️ Твой лот продан за <b>{lot['current_bid']:,}</b> монет!", parse_mode="HTML")
                except Exception:
                    pass
            else:
                # No bids — return item to seller
                await Database.add_item(lot["seller_id"], lot["item_id"], lot["amount"])
                await db.execute("UPDATE auction SET status='expired' WHERE id=?", (lot["id"],))
                try:
                    item = get_item_data(lot["item_id"])
                    iname = item["name"] if item else f"Предмет #{lot['item_id']}"
                    await bot.send_message(lot["seller_id"], f"🏛️ Твой лот не купили. <b>{iname}</b> возвращён в инвентарь.", parse_mode="HTML")
                except Exception:
                    pass
        await db.commit()
    except Exception as e:
        logger.error("Auction expiry error: %s", e)


async def task_expire_vip() -> None:
    """Remove expired VIP statuses."""
    try:
        from db import get_db
        db = await get_db()
        now = int(time.time())
        await db.execute(
            "UPDATE users SET vip_status='none', vip_expires=NULL WHERE vip_status != 'none' AND vip_expires IS NOT NULL AND vip_expires < ?",
            (now,)
        )
        await db.commit()
    except Exception as e:
        logger.error("VIP expiry error: %s", e)


async def task_auto_backup() -> None:
    """Create daily backup."""
    try:
        from database.backup import create_backup
        path = await create_backup()
        logger.info("Auto-backup: %s", path)
    except Exception as e:
        logger.error("Auto-backup error: %s", e)


# ── Bot startup ───────────────────────────────────────────────────────────────

async def on_startup(bot: Bot = None, **kwargs) -> None:
    # Set commands for all users
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())

    # Set extended commands for owner (has all commands)
    try:
        await bot.set_my_commands(
            ADMIN_COMMANDS,
            scope=BotCommandScopeChat(chat_id=OWNER_ID)
        )
    except Exception:
        pass

    # Dynamically set commands for all staff from DB
    try:
        staff = await Database.get_all_staff()
        for member in staff:
            uid = member["user_id"]
            role = member["role"]
            cmds = ADMIN_COMMANDS if role == "admin" else TESTER_COMMANDS
            try:
                await bot.set_my_commands(cmds, scope=BotCommandScopeChat(chat_id=uid))
            except Exception:
                pass
        if staff:
            logger.info("Commands set for %d staff members.", len(staff))
    except Exception as e:
        logger.warning("Could not set staff commands: %s", e)

    # Send startup message to owner
    try:
        await bot.send_message(
            OWNER_ID,
            f"🚀 <b>Marlboro Project запущен!</b>\n\n"
            f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🔧 Версия: 1.0.0",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Log to Telegram group
    await tg_log("🚀 Marlboro Project бот запущен!", "INFO")
    logger.info("Bot started successfully!")


async def on_shutdown(bot: Bot = None, **kwargs) -> None:
    await tg_log("⛔ Бот остановлен.", "WARNING")
    await Database.close()
    logger.info("Bot stopped.")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    # Setup logging first
    setup_logging()

    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set! Check your .env file.")
        sys.exit(1)

    # Start keep-alive HTTP server so UptimeRobot can ping us
    try:
        from keep_alive import start_keep_alive
        keep_alive_port = int(os.environ.get("PORT", 8000))
        await start_keep_alive(keep_alive_port)
    except Exception as e:
        logger.warning("Keep-alive server failed to start: %s", e)

    # Init DB
    await Database.init()
    logger.info("Database initialised.")

    # Create bot & dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Setup Telegram logging
    setup_telegram_logging(bot)

    # Register middlewares (order matters)
    dp.message.middleware(RegisterMiddleware())
    dp.callback_query.middleware(RegisterMiddleware())
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())
    dp.message.middleware(AntiSpamMiddleware())
    dp.callback_query.middleware(AntiSpamMiddleware())

    # Register all routers
    for router in get_all_routers():
        dp.include_router(router)

    # Scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(task_energy_regen,                    "interval", hours=1)
    scheduler.add_job(task_expire_vip,                      "interval", hours=1)
    scheduler.add_job(lambda: task_expire_auctions(bot),    "interval", minutes=5)
    scheduler.add_job(task_auto_backup,                     "cron",     hour=3, minute=0)
    scheduler.start()

    # Startup / shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling...")
    try:
        await dp.start_polling(bot, skip_updates=True, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
