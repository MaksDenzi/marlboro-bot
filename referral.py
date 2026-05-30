"""
Marlboro Project — Referral system
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from database.db import Database, get_db
from utils.keyboards import back_kb
from utils.texts import format_number
from config import REFERRAL_BONUS

router = Router()


@router.callback_query(F.data == "referrals")
@router.message(Command("referral"))
async def referral_info(event) -> None:
    user_id = event.from_user.id
    row = await Database.get_user(user_id)

    from aiogram import Bot
    if isinstance(event, CallbackQuery):
        bot: Bot = event.bot
    else:
        bot: Bot = event.bot

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    db = await get_db()
    async with db.execute(
        """SELECT u.first_name, u.level FROM users u WHERE u.referrer_id = ?
        ORDER BY u.registered_at DESC LIMIT 10""",
        (user_id,)
    ) as cur:
        refs = await cur.fetchall()

    refs_text = ""
    if refs:
        refs_text = "\n\n<b>Твои рефералы:</b>\n"
        for r in refs:
            refs_text += f"👤 {r['first_name']} (ур. {r['level']})\n"

    text = (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"Приглашай друзей и получай <b>{format_number(REFERRAL_BONUS)} монет</b> за каждого!\n"
        f"Твой друг также получит <b>{format_number(REFERRAL_BONUS // 2)} монет</b> при регистрации.\n\n"
        f"🔗 Твоя реферальная ссылка:\n<code>{ref_link}</code>\n\n"
        f"👥 Рефералов: <b>{row['referrals']}</b>"
        f"{refs_text}"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_kb(), parse_mode="HTML")
