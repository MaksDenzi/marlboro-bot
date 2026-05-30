"""
Marlboro Project — Logging system
Logs to: file, console, and Telegram group (async)
"""

import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_GROUP_ID

_bot_ref = None   # set after bot init via setup_telegram_logging()


def setup_logging() -> None:
    os.makedirs(os.path.dirname(LOG_FILE) if os.path.dirname(LOG_FILE) else ".", exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(ch)

    # Rotating file (10 MB × 5)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fh)

    # Silence noisy libs
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


def setup_telegram_logging(bot) -> None:
    """Call after bot is created to enable Telegram group logging."""
    global _bot_ref
    _bot_ref = bot


async def tg_log(message: str, level: str = "INFO") -> None:
    """Send a log message to the configured Telegram log group."""
    if not _bot_ref or not LOG_GROUP_ID:
        return
    emoji_map = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "🔴", "CRITICAL": "🆘", "DEBUG": "🔵"}
    emoji = emoji_map.get(level, "📋")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"{emoji} <b>[{level}]</b> <code>{ts}</code>\n"
        f"<code>{message[:3000]}</code>"
    )
    try:
        await _bot_ref.send_message(LOG_GROUP_ID, text, parse_mode="HTML")
    except Exception:
        pass


async def log_action(category: str, user_id: int, action: str, details: str = "") -> None:
    """Unified action logger: DB + Telegram."""
    from database.db import Database
    full = f"[{category}] uid={user_id} | {action}"
    if details:
        full += f" | {details}"
    logging.getLogger(category).info(full)
    await Database.log("INFO", category, full, user_id)
    await tg_log(full, "INFO")


async def log_error(source: str, error: Exception, user_id: int = None) -> None:
    msg = f"[ERROR] {source}: {type(error).__name__}: {error}"
    logging.getLogger("error").error(msg)
    from database.db import Database
    await Database.log("ERROR", source, str(error), user_id)
    await tg_log(msg, "ERROR")
