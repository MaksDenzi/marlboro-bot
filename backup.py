"""
Marlboro Project — Backup utilities
"""

import asyncio
import os
import shutil
import time
import aiofiles
import logging
from config import DB_PATH, BACKUP_DIR

logger = logging.getLogger(__name__)


async def create_backup() -> str:
    """Create a timestamped copy of the database. Returns file path."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = int(time.time())
    dst = os.path.join(BACKUP_DIR, f"marlboro_backup_{ts}.db")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, shutil.copy2, DB_PATH, dst)
    logger.info("Backup created: %s", dst)
    return dst


async def list_backups() -> list[str]:
    files = []
    if os.path.isdir(BACKUP_DIR):
        for f in sorted(os.listdir(BACKUP_DIR)):
            if f.endswith(".db"):
                files.append(os.path.join(BACKUP_DIR, f))
    return files


async def read_log_file(tail: int = 200) -> str:
    from config import LOG_FILE
    if not os.path.isfile(LOG_FILE):
        return "Лог-файл пуст или не найден."
    async with aiofiles.open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        lines = await f.readlines()
    return "".join(lines[-tail:]) or "Нет записей."
