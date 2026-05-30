from keep_alive import keep_alive
"""
Marlboro Project — Minimal working version
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram import F

from config import BOT_TOKEN, OWNER_ID
from db import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Команды
BOT_COMMANDS = [
    BotCommand(command="start", description="🎮 Главное меню"),
    BotCommand(command="help", description="ℹ️ Помощь"),
]

async def on_startup(bot: Bot):
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())
    try:
        await bot.send_message(OWNER_ID, "🚀 <b>Marlboro Bot запущен!</b>", parse_mode="HTML")
    except:
        pass
    logger.info("Bot started!")

# Простой хендлер
async def start_cmd(message):
    await message.answer("👋 Привет! Бот запущен в минимальном режиме.\n\n"
                        "Пока работает только /start")

async def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN не найден!")
        sys.exit(1)

    # Инициализация базы
    await Database.init()
    logger.info("Database initialized.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Регистрация хендлеров
    dp.message.register(start_cmd, F.text == "/start")

    # Запуск keep_alive если есть
    try:
        from keep_alive import start_keep_alive
        port = int(os.environ.get("PORT", 8000))
        asyncio.create_task(start_keep_alive(port))
    except:
        pass

    dp.startup.register(on_startup)

    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        await Database.close()

if __name__ == "__main__":
    asyncio.run(main())
