"""
Marlboro Project — Profile & Inventory handlers
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.db import Database
from utils.keyboards import back_kb, main_menu_kb
from utils.texts import profile_text, inventory_text

router = Router()


@router.message(Command("profile"))
@router.callback_query(F.data == "profile")
async def show_profile(event) -> None:
    user_id = event.from_user.id
    row = await Database.get_user(user_id)
    if not row:
        txt = "❌ Профиль не найден. Напиши /start"
        if isinstance(event, CallbackQuery):
            await event.answer(txt, show_alert=True)
        else:
            await event.answer(txt)
        return

    clan = await Database.get_user_clan(user_id)
    clan_name = clan["name"] if clan else None

    spouse_name = None
    if row["spouse_id"]:
        sp = await Database.get_user(row["spouse_id"])
        if sp:
            spouse_name = sp["first_name"]

    text = profile_text(dict(row), clan_name, spouse_name)

    from utils.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory"),
        InlineKeyboardButton(text="🏅 Достижения", callback_data="achievements"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    kb = b.as_markup()

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("inventory"))
@router.callback_query(F.data == "inventory")
async def show_inventory(event) -> None:
    user_id = event.from_user.id
    items = await Database.get_inventory(user_id)
    text = inventory_text(list(items))
    kb = back_kb("profile")

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")
