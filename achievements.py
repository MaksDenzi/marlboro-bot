"""
Marlboro Project — Achievements system
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from database.db import get_db
from utils.keyboards import back_kb
from utils.helpers import ACHIEVEMENTS_DEF

router = Router()


@router.callback_query(F.data == "achievements")
@router.message(Command("achievements"))
async def show_achievements(event) -> None:
    user_id = event.from_user.id
    db = await get_db()
    async with db.execute(
        "SELECT achievement, unlocked_at FROM achievements WHERE user_id = ? ORDER BY unlocked_at",
        (user_id,)
    ) as cur:
        unlocked = {row["achievement"]: row["unlocked_at"] for row in await cur.fetchall()}

    lines = ["🏅 <b>Достижения</b>\n"]
    total = len(ACHIEVEMENTS_DEF)
    got = sum(1 for k in ACHIEVEMENTS_DEF if k in unlocked)

    lines.append(f"Получено: <b>{got}/{total}</b>\n")

    for key, ach in ACHIEVEMENTS_DEF.items():
        if key in unlocked:
            import time
            date = time.strftime("%d.%m.%Y", time.localtime(unlocked[key]))
            lines.append(f"✅ {ach['name']}\n   <i>{ach['desc']}</i> — {date}")
        else:
            lines.append(f"🔒 {ach['name']}\n   <i>{ach['desc']}</i>")

    text = "\n".join(lines)
    kb = back_kb("profile")

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")
