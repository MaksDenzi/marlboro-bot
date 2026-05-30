"""
Marlboro Project — Cases / Loot Boxes
"""

import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from database.db import Database
from utils.keyboards import cases_menu_kb, back_kb
from utils.helpers import weighted_choice
from utils.texts import get_case_data, get_item_data, format_number
from utils.logger import log_action
from config import RARITIES, VIP_BONUSES

router = Router()


@router.callback_query(F.data == "cases_menu")
async def cases_menu(cb: CallbackQuery) -> None:
    text = (
        "📦 <b>Кейсы Marlboro</b>\n\n"
        "Открывай кейсы и получай уникальные предметы!\n\n"
        "📦 Обычный — 500 💰\n"
        "📫 Редкий — 1,500 💰\n"
        "💼 Эпический — 5,000 💰\n"
        "🌟 Легендарный — 15,000 💰\n"
        "🎁 Праздничный — 3,000 💰\n"
    )
    await cb.message.edit_text(text, reply_markup=cases_menu_kb(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("case_open:"))
async def open_case(cb: CallbackQuery) -> None:
    case_id = int(cb.data.split(":")[1])
    user_id = cb.from_user.id
    case = get_case_data(case_id)

    if not case:
        await cb.answer("❌ Кейс не найден!", show_alert=True)
        return

    # Check if key required
    key_id = case.get("key_id")
    row = await Database.get_user(user_id)

    if key_id:
        key_item = await Database.get_item_in_inventory(user_id, key_id)
        if key_item:
            # Use key
            ok = await Database.remove_item(user_id, key_id, 1)
            if not ok:
                # Fall back to coin purchase
                ok = await Database.deduct_balance(user_id, case["price"])
                if not ok:
                    await cb.answer(
                        f"❌ Нужен ключ или {format_number(case['price'])} монет!", show_alert=True
                    )
                    return
        else:
            # Buy with coins
            ok = await Database.deduct_balance(user_id, case["price"])
            if not ok:
                await cb.answer(
                    f"❌ Нужно {format_number(case['price'])} монет или ключ!", show_alert=True
                )
                return
    else:
        ok = await Database.deduct_balance(user_id, case["price"])
        if not ok:
            await cb.answer(f"❌ Нужно {format_number(case['price'])} монет!", show_alert=True)
            return

    # Roll reward
    vip = row["vip_status"]
    bonus = VIP_BONUSES.get(vip, VIP_BONUSES["none"])
    reward = weighted_choice(case["rewards"])

    if reward["type"] == "coins":
        amount = int(reward["amount"] * bonus["coins"])
        await Database.add_balance(user_id, amount)
        reward_text = f"💰 <b>{format_number(amount)} монет</b>"
        await log_action("case", user_id, f"Открыл кейс #{case_id}, получил {amount} монет")
    else:
        item_id = reward["item_id"]
        amount = reward.get("amount", 1)
        await Database.add_item(user_id, item_id, amount)
        item = get_item_data(item_id)
        rar = RARITIES.get(item.get("rarity", "common"), {}) if item else {}
        reward_text = (
            f"{item.get('emoji','📦')} <b>{item['name']}</b> × {amount}\n"
            f"{rar.get('emoji','')} {rar.get('color','')}"
        ) if item else f"Предмет #{item_id} × {amount}"

        # Check legendary achievement
        if item and item.get("rarity") in ("legendary", "mythic"):
            from database.db import get_db
            db = await get_db()
            await db.execute(
                "INSERT OR IGNORE INTO achievements (user_id, achievement) VALUES (?, 'legendary_item')",
                (user_id,)
            )
            await db.commit()

        await log_action("case", user_id, f"Открыл кейс #{case_id}, получил {item['name'] if item else item_id} x{amount}")

    text = (
        f"{'🌟' if case_id >= 3 else '📦'} <b>Кейс открыт: {case['name']}</b>\n\n"
        f"🎁 Выпало:\n{reward_text}"
    )
    await cb.message.edit_text(text, reply_markup=back_kb("cases_menu"), parse_mode="HTML")
    await cb.answer("🎁 Кейс открыт!")
